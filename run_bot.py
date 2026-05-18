"""
Instagram Comment Analyzer — Telegram Bot runner.

Usage:
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

# ── Setup Logging ───────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)-25s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S",
)
# Silence unnecessary third-party logs
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("aiohttp").setLevel(logging.WARNING)
logging.getLogger("instagrapi").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


async def start_bot(config: Config) -> None:
    """
    Initializes and starts the Telegram bot in polling mode.

    Args:
        config: Validated project configuration.
    """
    # ── Initialize Bot and Dispatcher ────────────────────────────────────
    bot = Bot(
        token=config.telegram_bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN),
    )
    dp = Dispatcher()

    # ── Pass config to handlers via middleware ─────────────
    dp["config"] = config

    # ── Register Router ────────────────────────────────
    dp.include_router(router)

    # ── Check bot info ─────────────────────────────────
    bot_info = await bot.get_me()
    console.print(
        Panel(
            f"[bold green]✅ Bot connected successfully![/bold green]\n\n"
            f"[bold white]🤖 Bot:[/bold white]     @{bot_info.username}\n"
            f"[bold white]📛 Name:[/bold white]    {bot_info.full_name}\n"
            f"[bold white]🆔 ID:[/bold white]      {bot_info.id}\n\n"
            f"[dim]Press Ctrl+C to stop the bot[/dim]",
            title="[bold bright_cyan]🤖 Telegram Bot",
            border_style="bright_cyan",
            padding=(1, 3),
        )
    )

    # ── Start Polling ──────────────────────────────────────────────
    logger.info("Polling started...")
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


def main() -> None:
    """Main entry point."""
    console.print(
        Panel(
            "[bold bright_white]🤖 Instagram Comment Analyzer[/bold bright_white]\n"
            "[dim]Telegram Bot Mode[/dim]",
            border_style="bright_cyan",
            padding=(1, 4),
        )
    )

    # ── Load Configuration ──────────────────────────────────────
    try:
        config = load_config()
    except ValueError as e:
        console.print(f"[bold red]✗ Configuration error:[/bold red] {e}")
        sys.exit(1)

    display_config(config)

    # ── Start Bot ─────────────────────────────────────────
    try:
        asyncio.run(start_bot(config))
    except KeyboardInterrupt:
        console.print("\n[bold yellow]⏹ Bot stopped.[/bold yellow]")
    except Exception as e:
        console.print(f"[bold red]✗ Bot error:[/bold red] {e}")
        logger.exception("Error starting the bot")
        sys.exit(1)


if __name__ == "__main__":
    main()
