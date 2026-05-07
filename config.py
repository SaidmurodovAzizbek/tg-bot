"""
Instagram Comment Analyzer Bot — Konfiguratsiya yuklagich.

Bu modul loyihaning barcha konfiguratsiya sozlamalarini
.env faylidan yuklaydi va validatsiya qiladi.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from os import getenv
from pathlib import Path

from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

logger = logging.getLogger(__name__)
console = Console()

_env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=_env_path)

@dataclass(frozen=True)
class Config:
    apify_api_token: str
    gemini_api_key: str
    telegram_bot_token: str
    max_comments: int
    gemini_model: str


def _require_env(name: str) -> str:
    """
    Berilgan environment variable mavjudligini tekshiradi.

    Args:
        name: Environment variable nomi.

    Returns:
        Environment variable qiymati.

    Raises:
        ValueError: Agar o'zgaruvchi topilmasa yoki to'ldirilmagan bo'lsa.
    """
    value = getenv(name)
    if not value or value.startswith("your_"):
        raise ValueError(
            f"'{name}' environment variable topilmadi yoki to'ldirilmagan. "
            f".env faylini tekshiring va haqiqiy qiymatni kiriting."
        )
    return value


def load_config() -> Config:
    """
    .env faylidan barcha konfiguratsiyalarni yuklaydi va Config obyektini qaytaradi.

    Returns:
        Config: Validatsiya qilingan konfiguratsiya obyekti.

    Raises:
        ValueError: Agar majburiy environment variable topilmasa.
    """
    config = Config(
        apify_api_token=_require_env("APIFY_API_TOKEN"),
        gemini_api_key=_require_env("GEMINI_API_KEY"),
        telegram_bot_token=_require_env("TELEGRAM_BOT_TOKEN"),
        max_comments=int(getenv("MAX_COMMENTS", "50")),
        gemini_model=getenv("GEMINI_MODEL", "gemini-2.0-flash"),
    )

    logger.info("Konfiguratsiya muvaffaqiyatli yuklandi.")
    return config


def display_config(config: Config) -> None:
    """Konfiguratsiya ma'lumotlarini chiroyli formatda terminalga chiqaradi."""
    table = Table(
        title="⚙️  Konfiguratsiya",
        show_header=True,
        header_style="bold cyan",
    )
    table.add_column("Parametr", style="bold white", min_width=22)
    table.add_column("Qiymat", style="green")

    table.add_row("Apify API Token", "•" * 12 + config.apify_api_token[-4:] if config.apify_api_token else "Kiritilmagan")
    table.add_row("Gemini API Key", config.gemini_api_key[:10] + "••••••••")
    table.add_row("Gemini Model", config.gemini_model)
    table.add_row("Telegram Bot", config.telegram_bot_token[:10] + "••••••••")
    table.add_row("Max Comments", str(config.max_comments))

    console.print(Panel(table, border_style="bright_blue", padding=(1, 2)))
