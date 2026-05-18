"""
Instagram Comment Analyzer Bot — CLI mode.

To run the application via terminal:
    python main.py <instagram_post_url>
"""

import sys

from rich.console import Console
from rich.panel import Panel

from config import display_config, load_config

console = Console()


def main() -> None:
    """CLI entry point for the application."""
    console.print(
        Panel(
            "[bold bright_white]📊 Instagram Comment Analyzer[/bold bright_white]\n"
            "[dim]Analyze comments using AI[/dim]",
            border_style="bright_magenta",
            padding=(1, 4),
        )
    )

    # ── Load Configuration ──────────────────────────────────────
    try:
        config = load_config()
    except ValueError as e:
        console.print(f"[bold red]✗ ERROR:[/bold red] {e}")
        sys.exit(1)

    display_config(config)
    console.print("[bold green]✓[/bold green] Configuration loaded successfully!\n")

    # ── Validate Post URL ────────────────────────────────────────
    if len(sys.argv) < 2:
        console.print(
            "[bold yellow]⚠ Usage:[/bold yellow] "
            "python main.py <instagram_post_url>\n"
            "[dim]Example: python main.py https://www.instagram.com/p/ABC123/[/dim]"
        )
        sys.exit(1)

    post_url = sys.argv[1]
    console.print(f"[bold cyan]🔗 Post URL:[/bold cyan] {post_url}\n")

    # ── Placeholder for next steps ──────────────────────────────
    console.print(
        Panel(
            "[dim]📌 Select an interface:\n"
            "   • python run_bot.py  → Telegram Bot\n"
            "   • python run_web.py  → Web Site\n"
            "   • python main.py URL → CLI Mode[/dim]",
            title="[bold]Available Modes",
            border_style="bright_yellow",
        )
    )


if __name__ == "__main__":
    main()
