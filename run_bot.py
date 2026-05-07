"""
Instagram Comment Analyzer — Telegram Botni ishga tushirish.

Ishlatish:
    python run_bot.py
"""

import asyncio
import logging
import sys

from rich.console import Console
from rich.panel import Panel

from config import load_config

console = Console()

# ── Logging sozlash ───────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)-20s | %(levelname)-8s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


async def start_bot() -> None:
    """Telegram botni ishga tushiradi."""
    console.print(
        Panel(
            "[bold bright_white]🤖 Instagram Comment Analyzer Bot[/bold bright_white]\n"
            "[dim]Telegram Bot rejimi[/dim]",
            border_style="bright_cyan",
            padding=(1, 4),
        )
    )

    try:
        config = load_config()
    except ValueError as e:
        console.print(f"[bold red]✗ XATO:[/bold red] {e}")
        sys.exit(1)

    console.print("[bold green]✓[/bold green] Konfiguratsiya yuklandi.")

    # TODO: 4-bosqichda to'liq implementatsiya qilinadi
    # - aiogram Dispatcher va Bot yaratish
    # - Handlerlarni ro'yxatdan o'tkazish
    # - Polling boshlash
    console.print(
        "[bold yellow]⚠ Telegram Bot 4-bosqichda implementatsiya qilinadi.[/bold yellow]"
    )


def main() -> None:
    """Entry point."""
    try:
        asyncio.run(start_bot())
    except KeyboardInterrupt:
        console.print("\n[bold yellow]Bot to'xtatildi.[/bold yellow]")


if __name__ == "__main__":
    main()
