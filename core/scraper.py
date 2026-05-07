"""
Instagram Comment Analyzer — Kommentariya yig'uvchi (Scraper).

Bu modul Instagram postidan kommentariyalarni yig'ish
funksionalligini ta'minlaydi. instagrapi kutubxonasi orqali
Instagram'ga kiradi va berilgan post URL'dan kommentariyalarni oladi.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from functools import lru_cache

from instagrapi import Client
from instagrapi.exceptions import (
    ClientError,
    LoginRequired,
    MediaNotFound,
    UserNotFound,
)

from config import Config

logger = logging.getLogger(__name__)

# ── Instagram URL validatsiya pattern ─────────────────────────────────
_INSTAGRAM_URL_PATTERN = re.compile(
    r"https?://(www\.)?instagram\.com/(p|reel|tv)/[\w-]+/?",
)


# ── Data Classes ──────────────────────────────────────────────────────

@dataclass
class Comment:
    """Bitta Instagram kommentariyasini ifodalovchi data class."""

    username: str
    text: str
    timestamp: datetime
    like_count: int = 0


@dataclass
class ScrapeResult:
    """Scraping natijasini saqlash uchun data class."""

    post_url: str
    post_shortcode: str
    total_comments: int
    comments: list[Comment] = field(default_factory=list)


# ── Instagram Client boshqaruvchisi ──────────────────────────────────

class InstagramScraper:
    """
    Instagram kommentariyalarini yig'ish uchun sinf.

    Login sessiyasini boshqaradi va kommentariyalarni
    strukturalangan formatda qaytaradi.
    """

    def __init__(self, config: Config) -> None:
        self._config = config
        self._client: Client | None = None

    def _login(self) -> Client:
        """
        Instagram'ga login qiladi va Client obyektini qaytaradi.

        Returns:
            Client: Autentifikatsiya qilingan Instagram client.

        Raises:
            ConnectionError: Login muvaffaqiyatsiz bo'lganda.
        """
        if self._client is not None:
            return self._client

        logger.info("Instagram'ga kirilmoqda: %s", self._config.instagram_username)

        client = Client()
        # ── Xavfsizlik sozlamalari ────────────────────────────────────
        client.delay_range = [1, 3]  # So'rovlar orasida 1-3 soniya kutish

        try:
            client.login(
                self._config.instagram_username,
                self._config.instagram_password,
            )
        except (LoginRequired, ClientError, Exception) as e:
            msg = (
                f"Instagram'ga kirish muvaffaqiyatsiz: {e}\n"
                f"Username va passwordni tekshiring."
            )
            logger.error(msg)
            raise ConnectionError(msg) from e

        logger.info("Instagram'ga muvaffaqiyatli kirildi.")
        self._client = client
        return client

    def scrape_comments(self, post_url: str) -> ScrapeResult:
        """
        Berilgan Instagram post URL'dan kommentariyalarni yig'adi.

        Args:
            post_url: Instagram post URL manzili.
                Masalan: https://www.instagram.com/p/ABC123/

        Returns:
            ScrapeResult: Yig'ilgan kommentariyalar natijasi.

        Raises:
            ValueError: Noto'g'ri URL format bo'lganda.
            ConnectionError: Instagram'ga ulanishda xato bo'lganda.
            LookupError: Post topilmaganda.
        """
        # ── URL validatsiya ───────────────────────────────────────────
        self._validate_url(post_url)

        # ── Login ─────────────────────────────────────────────────────
        client = self._login()

        # ── Media PK olish ────────────────────────────────────────────
        try:
            media_pk = client.media_pk_from_url(post_url)
            media_id = client.media_id(media_pk)
        except (MediaNotFound, ClientError, Exception) as e:
            msg = f"Post topilmadi: {post_url} — {e}"
            logger.error(msg)
            raise LookupError(msg) from e

        logger.info("Post topildi: media_pk=%s, media_id=%s", media_pk, media_id)

        # ── Shortcode ajratib olish ───────────────────────────────────
        shortcode = self._extract_shortcode(post_url)

        # ── Kommentariyalarni yig'ish ─────────────────────────────────
        max_comments = self._config.max_comments
        logger.info("Kommentariyalar yig'ilmoqda (max: %d)...", max_comments)

        try:
            raw_comments = client.media_comments(media_id, amount=max_comments)
        except (ClientError, Exception) as e:
            msg = f"Kommentariyalarni olishda xato: {e}"
            logger.error(msg)
            raise ConnectionError(msg) from e

        # ── Natijalarni strukturalash ─────────────────────────────────
        comments = [
            Comment(
                username=c.user.username,
                text=c.text,
                timestamp=c.created_at_utc,
                like_count=c.like_count or 0,
            )
            for c in raw_comments
            if c.text  # Bo'sh kommentlarni o'tkazib yuborish
        ]

        result = ScrapeResult(
            post_url=post_url,
            post_shortcode=shortcode,
            total_comments=len(comments),
            comments=comments,
        )

        logger.info(
            "✅ %d ta kommentariya yig'ildi (post: %s)",
            result.total_comments,
            shortcode,
        )

        return result

    @staticmethod
    def _validate_url(url: str) -> None:
        """
        Instagram post URL formatini tekshiradi.

        Args:
            url: Tekshiriladigan URL.

        Raises:
            ValueError: Noto'g'ri format bo'lganda.
        """
        if not _INSTAGRAM_URL_PATTERN.match(url):
            raise ValueError(
                f"Noto'g'ri Instagram URL: {url}\n"
                f"To'g'ri format: https://www.instagram.com/p/XXXXXX/"
            )

    @staticmethod
    def _extract_shortcode(url: str) -> str:
        """URL dan post shortcode ni ajratib oladi."""
        # https://www.instagram.com/p/ABC123/ → ABC123
        parts = url.rstrip("/").split("/")
        return parts[-1] if parts else "unknown"


# ── Convenience function ──────────────────────────────────────────────

def scrape_comments(config: Config, post_url: str) -> ScrapeResult:
    """
    Instagram postidan kommentariyalarni yig'adi (convenience wrapper).

    Bu funksiya InstagramScraper sinfini yaratadi va
    kommentariyalarni yig'ib qaytaradi. Har bir chaqiruvda
    yangi login sessiyasi ochiladi.

    Args:
        config: Loyiha konfiguratsiyasi.
        post_url: Instagram post URL manzili.

    Returns:
        ScrapeResult: Yig'ilgan kommentariyalar natijasi.
    """
    scraper = InstagramScraper(config)
    return scraper.scrape_comments(post_url)
