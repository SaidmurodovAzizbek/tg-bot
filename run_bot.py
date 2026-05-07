"""
Instagram Comment Analyzer — Telegram Botni ishga tushirish.

Ishlatish:
    source venv/bin/activate
    python run_bot.py
"""

import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from rich.console import Console
from rich.panel import Panel

from bot.handlers import router
from config import Config, display_config, load_config

console = Console()

# ── Logging sozlash ───────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)-25s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S",
)
# Keraksiz kutubxona loglarini sokinlashtirish
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("aiohttp").setLevel(logging.WARNING)
logging.getLogger("instagrapi").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


async def start_bot(config: Config) -> None:
    """
    Telegram botni yaratadi va polling rejimida ishga tushiradi.

    Args:
        config: Validatsiya qilingan loyiha konfiguratsiyasi.
    """
    # ── Bot va Dispatcher yaratish ────────────────────────────────────
    bot = Bot(
        token=config.telegram_bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN),
    )
    dp = Dispatcher()

    # ── Config ni middleware orqali handler'larga uzatish ─────────────
    dp["config"] = config

    # ── Router'ni ro'yxatdan o'tkazish ────────────────────────────────
    dp.include_router(router)

    # ── Bot ma'lumotlarini tekshirish ─────────────────────────────────
    bot_info = await bot.get_me()
    console.print(
        Panel(
            f"[bold green]✅ Bot muvaffaqiyatli ulandi![/bold green]\n\n"
            f"[bold white]🤖 Bot:[/bold white]     @{bot_info.username}\n"
            f"[bold white]📛 Nomi:[/bold white]    {bot_info.full_name}\n"
            f"[bold white]🆔 ID:[/bold white]      {bot_info.id}\n\n"
            f"[dim]Botni to'xtatish uchun Ctrl+C bosing[/dim]",
            title="[bold bright_cyan]🤖 Telegram Bot",
            border_style="bright_cyan",
            padding=(1, 3),
        )
    )

    # ── Polling boshlash ──────────────────────────────────────────────
    logger.info("Polling boshlandi...")
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


def main() -> None:
    """Asosiy kirish nuqtasi."""
    console.print(
        Panel(
            "[bold bright_white]🤖 Instagram Comment Analyzer[/bold bright_white]\n"
            "[dim]Telegram Bot rejimi[/dim]",
            border_style="bright_cyan",
            padding=(1, 4),
        )
    )

    # ── Konfiguratsiyani yuklash ──────────────────────────────────────
    try:
        config = load_config()
    except ValueError as e:
        console.print(f"[bold red]✗ Konfiguratsiya xatosi:[/bold red] {e}")
        sys.exit(1)

    display_config(config)

    # ── Botni ishga tushirish ─────────────────────────────────────────
    try:
        asyncio.run(start_bot(config))
    except KeyboardInterrupt:
        console.print("\n[bold yellow]⏹ Bot to'xtatildi.[/bold yellow]")
    except Exception as e:
        console.print(f"[bold red]✗ Bot xatosi:[/bold red] {e}")
        logger.exception("Bot ishga tushirishda xato")
        sys.exit(1)


if __name__ == "__main__":
    main()
