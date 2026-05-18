"""
Telegram Bot — Handlers.

This module contains the logic for processing all Telegram bot
commands and callback queries.

Supported commands:
    /start   — Start the bot and show the guide
    /analyze — Analyze an Instagram post URL
    /help    — Show the help message

Callbacks:
    View categories, navigate back, request new analysis, etc.
"""

from __future__ import annotations

import logging
from typing import Any

from aiogram import F, Router
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart
from aiogram.types import CallbackQuery, Message

from config import Config
from core.analyzer import AnalysisResult, analyze_comments
from core.reporter import format_for_telegram
from core.scraper import ApifyInstagramScraper, ScrapeResult

from .keyboards import CB, back_keyboard, categories_keyboard, main_result_keyboard

logger = logging.getLogger(__name__)

router = Router(name="main")

# ── In-memory session storage ──────────────────────────────────────────
# (For production, consider using Redis or a Database)
_user_results: dict[int, AnalysisResult] = {}
_user_scraped: dict[int, ScrapeResult] = {}

def _save_to_cache(cache: dict, key: int, value: Any, max_size: int = 100) -> None:
    """Saves to cache and evicts oldest item if max_size is exceeded to prevent memory leaks."""
    if key not in cache and len(cache) >= max_size:
        oldest = next(iter(cache))
        del cache[oldest]
    cache[key] = value


# ══════════════════════════════════════════════════════════════════════
# /start — Salomlashish
# ══════════════════════════════════════════════════════════════════════

@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    """
    /start command handler.
    Greets the user and provides instructions on how to use the bot.
    """
    first_name = message.from_user.first_name if message.from_user else "Foydalanuvchi"

    text = (
        f"👋 Salom, {first_name}!\n\n"
        f"📊 *Instagram Comment Analyzer Bot*\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"Men Instagram postidagi kommentariyalarni "
        f"AI yordamida tahlil qilib, kategoriyalarga ajrataman.\n\n"
        f"📌 *Qanday foydalanish:*\n"
        f"1️⃣ Instagram postining URL manzilini yuboring\n"
        f"   _Masalan:_ `https://www.instagram.com/p/ABC123/`\n"
        f"2️⃣ Yoki `/analyze` komandasi bilan:\n"
        f"   `/analyze https://www.instagram.com/p/ABC123/`\n\n"
        f"⚡ Tahlil 30-60 soniya davom etishi mumkin.\n\n"
        f"❓ Yordam uchun: /help"
    )

    await message.answer(text, parse_mode=ParseMode.MARKDOWN)


# ══════════════════════════════════════════════════════════════════════
# /help — Yordam
# ══════════════════════════════════════════════════════════════════════

@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    """/help command handler."""
    text = (
        "❓ *Yordam — Instagram Comment Analyzer*\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "📋 *Komandalar:*\n"
        "  /start   — Botni boshlash\n"
        "  /analyze — Postni tahlil qilish\n"
        "  /help    — Shu yordam xabari\n\n"
        "📂 *Tahlil natijalari:*\n"
        "  📣 Maqtov — ijobiy fikrlar\n"
        "  😡 Tanqid — salbiy fikrlar\n"
        "  ❓ Savol  — savollar\n"
        "  💡 Taklif — takliflar\n"
        "  🗑️ Spam   — reklama va spam\n"
        "  😐 Neytral — oddiy izohlar\n"
        "  😀 Emoji  — faqat emoji\n\n"
        "⚠️ *Muhim eslatmalar:*\n"
        "• Post ochiq bo'lishi kerak\n"
        "• Faqat oddiy post URL'lari qo'llab-quvvatlanadi\n"
        "  `instagram.com/p/...` yoki `instagram.com/reel/...`\n\n"
        "📬 Muammo bo'lsa, URL ni tekshiring va qayta urinib ko'ring."
    )

    await message.answer(text, parse_mode=ParseMode.MARKDOWN)


# ══════════════════════════════════════════════════════════════════════
# /analyze + Oddiy URL xabar — Asosiy tahlil
# ══════════════════════════════════════════════════════════════════════

@router.message(Command("analyze"))
async def cmd_analyze(message: Message, config: Config) -> None:
    """
    /analyze <url> command handler.
    Extracts the Instagram post URL and initiates the analysis.
    """
    # ── Extract URL from command ──────────────────────────────────────
    parts = message.text.split(maxsplit=1) if message.text else []
    if len(parts) < 2:
        await message.answer(
            "⚠️ *URL kiritilmagan!*\n\n"
            "Foydalanish:\n"
            "`/analyze https://www.instagram.com/p/ABC123/`",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    post_url = parts[1].strip()
    await _run_analysis(message, config, post_url)


@router.message(F.text.startswith("https://www.instagram.com/") | F.text.startswith("https://instagram.com/"))
async def handle_instagram_url(message: Message, config: Config) -> None:
    """
    Automatically starts analysis when a user sends an Instagram URL.
    Works without the /analyze command.
    """
    post_url = message.text.strip() if message.text else ""
    await _run_analysis(message, config, post_url)


async def _run_analysis(message: Message, config: Config, post_url: str) -> None:
    """
    Manages the core analysis workflow.

    1. Sends a loading message
    2. Scrapes comments (async to avoid blocking)
    3. Performs AI analysis (async to avoid blocking)
    4. Delivers the result
    """
    user_id = message.from_user.id if message.from_user else 0

    # ── Loading Message ────────────────────────────────────────────────
        loading_msg = await message.answer(
        "⏳ *Tahlil boshlanmoqda...*\n\n"
        f"🔗 `{post_url}`\n\n"
        "📥 Kommentariyalar yuklanmoqda...",
        parse_mode=ParseMode.MARKDOWN,
    )

    # ── URL Validation ───────────────────────────────────────────────
    try:
        ApifyInstagramScraper._validate_url(post_url)
    except ValueError:
        await loading_msg.edit_text(
            "❌ *Noto'g'ri URL!*\n\n"
            "To'g'ri format:\n"
            "`https://www.instagram.com/p/ABC123/`\n\n"
            "Yoki:\n"
            "`https://www.instagram.com/reel/ABC123/`",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    # ── Instagram Scraping ────────────────────────────────────────────
    try:
        scraper = ApifyInstagramScraper(config)
        scrape_result = await asyncio.to_thread(scraper.scrape_comments, post_url)
        _save_to_cache(_user_scraped, user_id, scrape_result)
    except ValueError as e:
        await loading_msg.edit_text(
            f"❌ *URL xatosi:*\n{e}",
            parse_mode=ParseMode.MARKDOWN,
        )
        return
    except LookupError:
        await loading_msg.edit_text(
            "❌ *Post topilmadi!*\n\n"
            "Post o'chirilgan yoki maxfiy bo'lishi mumkin.\n"
            "Ochiq post URL'sini kiriting.",
            parse_mode=ParseMode.MARKDOWN,
        )
        return
    except ConnectionError as e:
        await loading_msg.edit_text(
            f"❌ *Instagram ulanish xatosi:*\n`{e}`\n\n"
            "Instagram login ma'lumotlarini tekshiring.",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    # ── AI Analysis ─────────────────────────────────────────────────────
    await loading_msg.edit_text(
        f"⏳ *Tahlil davom etmoqda...*\n\n"
        f"🔗 `{post_url}`\n"
        f"✅ {scrape_result.total_comments} ta kommentariya yuklandi\n\n"
        f"🤖 AI tahlil qilmoqda...",
        parse_mode=ParseMode.MARKDOWN,
    )

    try:
        analysis_result = await asyncio.to_thread(analyze_comments, config, scrape_result)
        _save_to_cache(_user_results, user_id, analysis_result)
    except (ValueError, ConnectionError) as e:
        await loading_msg.edit_text(
            f"❌ *AI tahlil xatosi:*\n`{e}`\n\n"
            "Gemini API kalitini tekshiring.",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    # ── Output Result ────────────────────────────────────────────
    result_text = format_for_telegram(analysis_result)
    await loading_msg.delete()
    await message.answer(
        result_text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=main_result_keyboard(),
    )
    logger.info(
        "Tahlil yakunlandi | user_id=%d | comments=%d",
        user_id,
        scrape_result.total_comments,
    )


# ══════════════════════════════════════════════════════════════════════
# Callback Handlers — Inline tugmalar
# ══════════════════════════════════════════════════════════════════════

@router.callback_query(F.data == CB.SHOW_DETAILS)
async def cb_show_details(callback: CallbackQuery) -> None:
    """Displays the list of categories when the 'Category details' button is pressed."""
    user_id = callback.from_user.id if callback.from_user else 0
    result = _user_results.get(user_id)

    if not result:
        await callback.answer("❌ Natija topilmadi. Qayta tahlil qiling.", show_alert=True)
        return

    counts = {
        "Positive": len(result.categories.get("Positive").comments) if "Positive" in result.categories else 0,
        "Negative": len(result.categories.get("Negative").comments) if "Negative" in result.categories else 0,
        "Neutral":  len(result.categories.get("Neutral").comments) if "Neutral" in result.categories else 0,
    }
    total = result.total_comments

    lines = [
        "📂 *Kategoriyalar tafsiloti*",
        f"━━━━━━━━━━━━━━━━━━━━━━",
        f"💬 Jami: {total} ta kommentariya\n",
        "Kerakli kategoriyani tanlang:",
    ]

    # Nol bo'lmagan kategoriyalar sonini ko'rsatish
    meta_map = {
        "Positive": "🟢 Ijobiy",
        "Negative": "🔴 Salbiy",
        "Neutral":  "⚪ Neytral",
    }
    for key, label in meta_map.items():
        count = counts[key]
        if count > 0:
            pct = round(count / total * 100) if total else 0
            lines.append(f"  {label}: *{count}* ({pct}%)")

    if callback.message:
        await callback.message.edit_text(
            "\n".join(lines),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=categories_keyboard(),
        )
    await callback.answer()


@router.callback_query(F.data.startswith("cat:"))
async def cb_category_detail(callback: CallbackQuery) -> None:
    """Shows the comments of the selected category."""
    user_id = callback.from_user.id if callback.from_user else 0
    result = _user_results.get(user_id)

    if not result:
        await callback.answer("❌ Natija topilmadi.", show_alert=True)
        return

    cat_key = callback.data.split(":", 1)[1] if callback.data else ""

    cat_map = {
        "Positive": ("🟢 Ijobiy", result.categories.get("Positive").comments if "Positive" in result.categories else []),
        "Negative": ("🔴 Salbiy", result.categories.get("Negative").comments if "Negative" in result.categories else []),
        "Neutral":  ("⚪ Neytral", result.categories.get("Neutral").comments if "Neutral" in result.categories else []),
    }

    if cat_key not in cat_map:
        await callback.answer("Noma'lum kategoriya.", show_alert=True)
        return

    label, comments = cat_map[cat_key]

    if not comments:
        await callback.answer(
            f"{label} — bu kategoriyada kommentariya yo'q.",
            show_alert=True,
        )
        return

    lines = [
        f"{label} kategoriyasi",
        f"━━━━━━━━━━━━━━━━━━━━━━",
        f"Jami: {len(comments)} ta kommentariya\n",
    ]

    # Telegram xabar limiti 4096 harf — max 15 ta komment ko'rsatamiz
    for item in comments[:15]:
        username = item.get("username", "???")
        text     = item.get("text", "")
        lines.append(f"• @{username}: {text}")

    if len(comments) > 15:
        lines.append(f"\n_... va yana {len(comments) - 15} ta_")

    if callback.message:
        await callback.message.edit_text(
            "\n".join(lines),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=back_keyboard(),
        )
    await callback.answer()


@router.callback_query(F.data == CB.BACK_TO_RESULT)
async def cb_back_to_result(callback: CallbackQuery) -> None:
    """'Back' button — returns to the main analysis result."""
    user_id = callback.from_user.id if callback.from_user else 0
    result = _user_results.get(user_id)

    if not result:
        await callback.answer("❌ Natija topilmadi.", show_alert=True)
        return

    result_text = format_for_telegram(result)
    if callback.message:
        await callback.message.edit_text(
            result_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=main_result_keyboard(),
        )
    await callback.answer()


@router.callback_query(F.data == CB.NEW_ANALYSIS)
async def cb_new_analysis(callback: CallbackQuery) -> None:
    """'New analysis' button — asks the user for a new URL."""
    text = (
        "🔄 *Yangi tahlil*\n\n"
        "Instagram post URL'sini yuboring:\n"
        "`https://www.instagram.com/p/ABC123/`"
    )
    if callback.message:
        await callback.message.edit_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
        )
    await callback.answer()


@router.callback_query(F.data == CB.HELP)
async def cb_help(callback: CallbackQuery) -> None:
    """'Help' button callback handler."""
    await cb_back_to_result.__wrapped__(callback) if hasattr(cb_back_to_result, "__wrapped__") else None
    await callback.answer("Yordam uchun /help buyrug'ini yuboring.", show_alert=True)
