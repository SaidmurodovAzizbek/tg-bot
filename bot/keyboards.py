"""
Telegram Bot — Inline klaviaturalar (Keyboards).

Bu modul bot uchun barcha inline klaviatura tugmalarini
yaratish funksiyalarini o'z ichiga oladi.
"""

from __future__ import annotations

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


# ── Callback data konstantalari ───────────────────────────────────────

class CB:
    """Callback data konstantalari — nomlangan satrlar."""

    # Asosiy harakatlar
    NEW_ANALYSIS   = "action:new"
    HELP           = "action:help"

    # Kategoriyalar batafsil ko'rinishi
    CAT_PRAISE     = "cat:praise"
    CAT_CRITICISM  = "cat:criticism"
    CAT_QUESTION   = "cat:question"
    CAT_SUGGESTION = "cat:suggestion"
    CAT_SPAM       = "cat:spam"
    CAT_NEUTRAL    = "cat:neutral"
    CAT_EMOJI      = "cat:emoji_only"

    # Batafsil natija
    SHOW_DETAILS   = "action:details"
    BACK_TO_RESULT = "action:back"


def main_result_keyboard(has_details: bool = True) -> InlineKeyboardMarkup:
    """
    Tahlil natijasi xabari ostida ko'rsatiladigan asosiy klaviatura.

    Tugmalar:
      - 📂 Kategoriyalar batafsil
      - 🔄 Yangi tahlil
      - ❓ Yordam
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
    Kategoriyalar ro'yxatini ko'rsatish uchun klaviatura.

    Foydalanuvchi ma'lum bir kategoriyani tanlab,
    faqat o'sha kategoriya kommentariyalarini ko'rishi mumkin.
    """
    builder = InlineKeyboardBuilder()

    categories = [
        (CB.CAT_PRAISE,     "📣 Maqtov"),
        (CB.CAT_CRITICISM,  "😡 Tanqid"),
        (CB.CAT_QUESTION,   "❓ Savol"),
        (CB.CAT_SUGGESTION, "💡 Taklif"),
        (CB.CAT_SPAM,       "🗑️ Spam"),
        (CB.CAT_NEUTRAL,    "😐 Neytral"),
        (CB.CAT_EMOJI,      "😀 Faqat emoji"),
    ]

    for callback_data, text in categories:
        builder.button(text=text, callback_data=callback_data)

    builder.adjust(2, 2, 2, 1)  # 2-2-2-1 joylashuv

    builder.button(text="⬅️ Orqaga", callback_data=CB.BACK_TO_RESULT)
    builder.adjust(2, 2, 2, 1, 1)

    return builder.as_markup()


def back_keyboard() -> InlineKeyboardMarkup:
    """Faqat 'Orqaga' tugmasini o'z ichiga olgan klaviatura."""
    builder = InlineKeyboardBuilder()
    builder.button(text="⬅️ Natijaga qaytish", callback_data=CB.BACK_TO_RESULT)
    builder.button(text="🔄 Yangi tahlil", callback_data=CB.NEW_ANALYSIS)
    builder.adjust(1, 1)
    return builder.as_markup()
