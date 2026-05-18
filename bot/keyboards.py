"""
Telegram Bot — Inline keyboards.

This module contains functions to generate all inline keyboard
buttons for the bot.
"""

from __future__ import annotations

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


# ── Callback data constants ───────────────────────────────────────

class CB:
    """Callback data constants."""

    # Main actions
    NEW_ANALYSIS   = "action:new"
    HELP           = "action:help"

    # Category details view
    CAT_POSITIVE   = "cat:Positive"
    CAT_NEGATIVE   = "cat:Negative"
    CAT_NEUTRAL    = "cat:Neutral"

    # Detailed results
    SHOW_DETAILS   = "action:details"
    BACK_TO_RESULT = "action:back"


def main_result_keyboard(has_details: bool = True) -> InlineKeyboardMarkup:
    """
    Main keyboard displayed below the analysis result message.
    """
    builder = InlineKeyboardBuilder()

    if has_details:
        builder.button(
            text="📂 Kategoriyalar batafsil",
            callback_data=CB.SHOW_DETAILS,
        )
        builder.adjust(1)

    builder.button(
        text="🔄 Yangi tahlil",
        callback_data=CB.NEW_ANALYSIS,
    )
    builder.button(
        text="❓ Yordam",
        callback_data=CB.HELP,
    )
    builder.adjust(1, 2)

    return builder.as_markup()


def categories_keyboard() -> InlineKeyboardMarkup:
    """
    Keyboard for displaying the list of categories.

    Allows the user to select a specific category
    and view only its comments.
    """
    builder = InlineKeyboardBuilder()

    categories = [
        (CB.CAT_POSITIVE,   "🟢 Ijobiy"),
        (CB.CAT_NEGATIVE,   "🔴 Salbiy"),
        (CB.CAT_NEUTRAL,    "⚪ Neytral"),
    ]

    for callback_data, text in categories:
        builder.button(text=text, callback_data=callback_data)

    builder.adjust(2, 1)  # 2-1 layout

    builder.button(text="⬅️ Orqaga", callback_data=CB.BACK_TO_RESULT)
    builder.adjust(2, 1, 1)

    return builder.as_markup()


def back_keyboard() -> InlineKeyboardMarkup:
    """Keyboard containing only the 'Back' button."""
    builder = InlineKeyboardBuilder()
    builder.button(text="⬅️ Natijaga qaytish", callback_data=CB.BACK_TO_RESULT)
    builder.button(text="🔄 Yangi tahlil", callback_data=CB.NEW_ANALYSIS)
    builder.adjust(1, 1)
    return builder.as_markup()
