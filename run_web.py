"""
Instagram Comment Analyzer — Web Serverni ishga tushirish.

Ishlatish:
    python run_web.py
"""

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


def main() -> None:
    """Web serverni ishga tushiradi."""
    console.print(
        Panel(
            "[bold bright_white]🌐 Instagram Comment Analyzer[/bold bright_white]\n"
            "[dim]Web Server rejimi[/dim]",
            border_style="bright_green",
            padding=(1, 4),
        )
    )

    try:
        config = load_config()
    except ValueError as e:
        console.print(f"[bold red]✗ XATO:[/bold red] {e}")
        sys.exit(1)

    console.print("[bold green]✓[/bold green] Konfiguratsiya yuklandi.")

    # TODO: 5-bosqichda to'liq implementatsiya qilinadi
    # - FastAPI ilova yaratish
    # - uvicorn bilan serverni ishga tushirish
    # - http://localhost:8000 da ishlaydi
    console.print(
        "[bold yellow]⚠ Web Server 5-bosqichda implementatsiya qilinadi.[/bold yellow]"
    )


if __name__ == "__main__":
    main()
