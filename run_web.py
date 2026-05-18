"""
Instagram Comment Analyzer — Web Server runner.

Usage:
    python run_web.py
"""

import logging
import sys
import uvicorn

from rich.console import Console
from rich.panel import Panel

from config import load_config
from web.app import init_app

console = Console()

# ── Setup Logging ───────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)-20s | %(levelname)-8s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def main() -> None:
    """Starts the web server."""
    console.print(
        Panel(
            "[bold bright_white]🌐 Instagram Comment Analyzer[/bold bright_white]\n"
            "[dim]Web Server Mode[/dim]",
            border_style="bright_green",
            padding=(1, 4),
        )
    )

    try:
        config = load_config()
    except ValueError as e:
        console.print(f"[bold red]✗ ERROR:[/bold red] {e}")
        sys.exit(1)

    console.print("[bold green]✓[/bold green] Configuration loaded.")
    
    # Initialize the app
    app = init_app(config)
    
    console.print("[bold cyan]🚀 Server is starting...[/bold cyan]")
    console.print("[dim]Open in browser: http://localhost:8000[/dim]")
    
    # Run server via Uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="warning")


if __name__ == "__main__":
    main()
