"""
Instagram Comment Analyzer Bot — CLI rejimi.

Dasturni terminal orqali ishga tushirish uchun:
    python main.py <instagram_post_url>
"""

import sys

from rich.console import Console
from rich.panel import Panel

from config import display_config, load_config

console = Console()


def main() -> None:
    """Dasturning CLI kirish nuqtasi."""
    console.print(
        Panel(
            "[bold bright_white]📊 Instagram Comment Analyzer[/bold bright_white]\n"
            "[dim]Kommentariyalarni AI yordamida tahlil qiling[/dim]",
            border_style="bright_magenta",
            padding=(1, 4),
        )
    )

    # ── Konfiguratsiyani yuklash ──────────────────────────────────────
    try:
        config = load_config()
    except ValueError as e:
        console.print(f"[bold red]✗ XATO:[/bold red] {e}")
        sys.exit(1)

    display_config(config)
    console.print("[bold green]✓[/bold green] Konfiguratsiya muvaffaqiyatli yuklandi!\n")

    # ── Post URL ni tekshirish ────────────────────────────────────────
    if len(sys.argv) < 2:
        console.print(
            "[bold yellow]⚠ Foydalanish:[/bold yellow] "
            "python main.py <instagram_post_url>\n"
            "[dim]Misol: python main.py https://www.instagram.com/p/ABC123/[/dim]"
        )
        sys.exit(1)

    post_url = sys.argv[1]
    console.print(f"[bold cyan]🔗 Post URL:[/bold cyan] {post_url}\n")

    # ── Keyingi bosqichlar uchun placeholder ──────────────────────────
    console.print(
        Panel(
            "[dim]📌 Interfeys tanlang:\n"
            "   • python run_bot.py  → Telegram Bot\n"
            "   • python run_web.py  → Web Sayt\n"
            "   • python main.py URL → CLI rejimi[/dim]",
            title="[bold]Mavjud rejimlar",
            border_style="bright_yellow",
        )
    )


if __name__ == "__main__":
    main()
