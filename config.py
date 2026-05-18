"""
Configuration loader for the Instagram Comment Analyzer Bot.

Loads and validates all configuration settings from the .env file.
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
    openrouter_api_key: str
    telegram_bot_token: str
    max_comments: int
    openrouter_model: str


def _require_env(name: str) -> str:
    """
    Validates the presence of a required environment variable.

    Args:
        name: Name of the environment variable.

    Returns:
        The value of the environment variable.

    Raises:
        ValueError: If the variable is missing or contains a placeholder.
    """
    value = getenv(name)
    if not value or value.startswith("your_"):
        raise ValueError(
            f"Environment variable '{name}' is missing or not set. "
            f"Please check the .env file."
        )
    return value


def load_config() -> Config:
    """
    Loads all configurations from the .env file and returns a Config object.

    Returns:
        Config: Validated configuration object.

    Raises:
        ValueError: If a required environment variable is missing.
    """
    config = Config(
        apify_api_token=_require_env("APIFY_API_TOKEN"),
        openrouter_api_key=_require_env("OPENROUTER_API_KEY"),
        telegram_bot_token=_require_env("TELEGRAM_BOT_TOKEN"),
        max_comments=int(getenv("MAX_COMMENTS", "50")),
        openrouter_model=getenv("OPENROUTER_MODEL", "google/gemma-4-31b-it:free"),
    )

    logger.info("Configuration loaded successfully.")
    return config


def display_config(config: Config) -> None:
    """Displays configuration details in a formatted table."""
    table = Table(
        title="⚙️  Configuration",
        show_header=True,
        header_style="bold cyan",
    )
    table.add_column("Parameter", style="bold white", min_width=22)
    table.add_column("Value", style="green")

    table.add_row("Apify API Token", "•" * 12 + config.apify_api_token[-4:] if config.apify_api_token else "Kiritilmagan")
    table.add_row("OpenRouter API", config.openrouter_api_key[:10] + "••••••••")
    table.add_row("OpenRouter Model", config.openrouter_model)
    table.add_row("Telegram Bot", config.telegram_bot_token[:10] + "••••••••")
    table.add_row("Max Comments", str(config.max_comments))

    console.print(Panel(table, border_style="bright_blue", padding=(1, 2)))
