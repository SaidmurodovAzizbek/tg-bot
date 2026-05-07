"""
Instagram Scraper moduli (Apify orqali ishlaydi).

Bu modul Apify xizmati yordamida hech qanday login yoki parolsiz,
qora ro'yxatga tushish xavfisiz Instagram postlaridan izohlarni yig'adi.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import List, Dict, Any

from apify_client import ApifyClient
from config import Config

logger = logging.getLogger(__name__)

# ── Ma'lumotlar modellari ──────────────────────────────────────────────

@dataclass
class ScrapedComment:
    """Yagona kommentariyani ifodalovchi data-class."""
    id: str
    username: str
    text: str
    likes_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "username": self.username,
            "text": self.text,
            "likes_count": self.likes_count,
        }

@dataclass
class ScrapeResult:
    """Scraping natijasini saqlovchi obyekt."""
    post_url: str
    media_id: str = "unknown"
    comments: List[ScrapedComment] = field(default_factory=list)
    total_comments: int = 0


# ── Validatsiya ────────────────────────────────────────────────────────

_INSTAGRAM_URL_PATTERN = re.compile(
    r"^https?://(www\.)?instagram\.com/(p|reel|tv)/[\w-]+/?(.*?)$"
)

# ── Asosiy Scraper Sinfi ───────────────────────────────────────────────

class ApifyInstagramScraper:
    """Apify orqali Instagram postlaridan izohlarni yig'uvchi sinf."""

    def __init__(self, config: Config):
        self._config = config
        
        if not self._config.apify_api_token or self._config.apify_api_token.startswith("your_"):
            raise ValueError(
                "APIFY_API_TOKEN kiritilmagan! "
                "Iltimos, apify.com saytidan ro'yxatdan o'tib token oling va .env fayliga kiriting."
            )
            
        self.client = ApifyClient(self._config.apify_api_token)

    def scrape_comments(self, post_url: str) -> ScrapeResult:
        """
        Apify xizmati orqali berilgan URL dan izohlarni yig'adi.
        """
        self._validate_url(post_url)
        
        logger.info(f"Apify orqali URL tahlil qilinmoqda: {post_url}")
        
        # Apify dagi rasmiy "instagram-comment-scraper" aktyori (Actor)
        actor_id = "apify/instagram-comment-scraper"
        
        # Aktyorga yuboriladigan ma'lumotlar
        run_input = {
            "directUrls": [post_url],
            "resultsLimit": self._config.max_comments,
        }

        try:
            logger.info("Apify scraper ishga tushirilmoqda. Bu bir necha soniya olishi mumkin...")
            # Run the actor synchronously
            run = self.client.actor(actor_id).call(run_input=run_input)
            
            # Natijalarni (Dataset) olish
            dataset_id = run["defaultDatasetId"]
            items = list(self.client.dataset(dataset_id).iterate_items())
            
            logger.info(f"Apify jami {len(items)} ta izoh topdi.")
            
            scraped_comments = []
            for item in items:
                # Apify qaytargan JSON formatni o'zimizga moslash
                scraped_comments.append(
                    ScrapedComment(
                        id=item.get("id", "unknown"),
                        username=item.get("ownerUsername", "unknown"),
                        text=item.get("text", ""),
                        likes_count=item.get("likesCount", 0),
                    )
                )

            return ScrapeResult(
                post_url=post_url,
                media_id=self._extract_shortcode(post_url),
                comments=scraped_comments,
                total_comments=len(scraped_comments)
            )
            
        except Exception as e:
            logger.error(f"Apify bilan aloqada xatolik yuz berdi: {e}")
            raise ConnectionError(f"Ma'lumot yig'ishda xatolik (Apify): {e}")

    @staticmethod
    def _validate_url(url: str) -> None:
        """Instagram URL ni tekshiradi."""
        if not _INSTAGRAM_URL_PATTERN.match(url):
            raise ValueError(
                f"Noto'g'ri Instagram URL: {url}\n"
                f"To'g'ri format: https://www.instagram.com/p/XXXXXX/"
            )

    @staticmethod
    def _extract_shortcode(url: str) -> str:
        """URL dan post shortcode ni ajratib oladi."""
        # https://www.instagram.com/p/ABC123/?igsh=...
        try:
            clean_url = url.split("?")[0].rstrip("/")
            parts = clean_url.split("/")
            return parts[-1] if parts else "unknown"
        except Exception:
            return "unknown"


# ── Convenience wrapper ───────────────────────────────────────────────

def scrape_comments(config: Config, post_url: str) -> ScrapeResult:
    """
    Tashqi foydalanish uchun qulay o'ram (wrapper).
    """
    scraper = ApifyInstagramScraper(config)
    return scraper.scrape_comments(post_url)
