"""
Instagram Comment Analyzer — AI Tahlilchi (Analyzer).

Bu modul Google Gemini AI yordamida kommentariyalarni
tahlil qilish funksionalligini ta'minlaydi. Kommentariyalarni
kategoriyalarga ajratadi va sentiment tahlilini bajaradi.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field

import google.generativeai as genai

from config import Config
from core.scraper import ScrapeResult

logger = logging.getLogger(__name__)


# ── Data Classes ──────────────────────────────────────────────────────

@dataclass
class CategoryBreakdown:
    """Kommentariya kategoriyalari taqsimoti."""

    praise: list[dict] = field(default_factory=list)       # 📣 Maqtov
    criticism: list[dict] = field(default_factory=list)     # 😡 Tanqid
    question: list[dict] = field(default_factory=list)      # ❓ Savol
    suggestion: list[dict] = field(default_factory=list)    # 💡 Taklif
    spam: list[dict] = field(default_factory=list)          # 🗑️ Spam
    neutral: list[dict] = field(default_factory=list)       # 😐 Neytral
    emoji_only: list[dict] = field(default_factory=list)    # 😀 Faqat emoji


@dataclass
class SentimentScore:
    """Sentiment (kayfiyat) ko'rsatkichlari."""

    positive: float = 0.0   # Ijobiy foiz (0-100)
    negative: float = 0.0   # Salbiy foiz (0-100)
    neutral: float = 0.0    # Neytral foiz (0-100)


@dataclass
class AnalysisResult:
    """To'liq tahlil natijasi."""

    post_url: str
    total_comments: int
    sentiment: SentimentScore = field(default_factory=SentimentScore)
    categories: CategoryBreakdown = field(default_factory=CategoryBreakdown)
    top_topics: list[str] = field(default_factory=list)
    summary: str = ""


# ── Gemini AI Prompt ──────────────────────────────────────────────────

_SYSTEM_INSTRUCTION = """Sen Instagram kommentariyalarini tahlil qiluvchi AI yordamchisisanga. 
Senga Instagram postidagi kommentariyalar ro'yxati beriladi. 
Sening vazifang ularni chuqur tahlil qilish.

MUHIM QOIDALAR:
1. Javobni FAQAT JSON formatda ber
2. Har bir kommentariyani tegishli kategoriyaga joylashtir
3. Sentiment foizlarining yig'indisi 100 bo'lishi kerak
4. Xulosa o'zbek tilida bo'lsin
5. Top mavzularni aniqlashda umumiy tendentsiyalarni ko'r"""

_ANALYSIS_PROMPT_TEMPLATE = """Quyidagi {count} ta Instagram kommentariyasini tahlil qil:

--- KOMMENTARIYALAR ---
{comments_text}
--- KOMMENTARIYALAR TUGADI ---

Quyidagi JSON formatda javob ber (FAQAT JSON, boshqa hech narsa yo'q):
{{
  "sentiment": {{
    "positive": <ijobiy_foiz_0_100>,
    "negative": <salbiy_foiz_0_100>,
    "neutral": <neytral_foiz_0_100>
  }},
  "categories": {{
    "praise": [
      {{"username": "...", "text": "...", "reason": "..."}}
    ],
    "criticism": [
      {{"username": "...", "text": "...", "reason": "..."}}
    ],
    "question": [
      {{"username": "...", "text": "...", "reason": "..."}}
    ],
    "suggestion": [
      {{"username": "...", "text": "...", "reason": "..."}}
    ],
    "spam": [
      {{"username": "...", "text": "...", "reason": "..."}}
    ],
    "neutral": [
      {{"username": "...", "text": "...", "reason": "..."}}
    ],
    "emoji_only": [
      {{"username": "...", "text": "...", "reason": "..."}}
    ]
  }},
  "top_topics": ["mavzu1", "mavzu2", "mavzu3", "mavzu4", "mavzu5"],
  "summary": "O'zbek tilida 3-5 jumlalik umumiy xulosa..."
}}

ESLATMA: 
- Har bir kommentariya faqat BITTA kategoriyaga tegishli bo'lsin
- "reason" — nima uchun shu kategoriyaga joylashtirilganini qisqacha tushuntir
- Agar kommentariya faqat emoji (❤️, 🔥, 👍 va h.k.) bo'lsa, "emoji_only" ga joylashtir
- Sentiment foizlari yig'indisi aynan 100 bo'lishi shart"""


# ── Analyzer funksiyalari ─────────────────────────────────────────────

def _format_comments_for_prompt(scrape_result: ScrapeResult) -> str:
    """Kommentariyalarni prompt uchun matnli formatga o'tkazadi."""
    lines = []
    for i, comment in enumerate(scrape_result.comments, 1):
        lines.append(f"{i}. @{comment.username}: {comment.text}")
    return "\n".join(lines)


def _parse_ai_response(raw_text: str) -> dict:
    """
    Gemini AI javobini JSON dict ga o'tkazadi.

    Args:
        raw_text: AI dan kelgan xom javob matni.

    Returns:
        dict: Parse qilingan JSON ma'lumot.

    Raises:
        ValueError: JSON parse qilishda xato bo'lganda.
    """
    # ── JSON blokni topish (```json ... ``` yoki oddiy JSON) ──────
    text = raw_text.strip()

    # Markdown code block ichidan olish
    if "```json" in text:
        text = text.split("```json", 1)[1]
        text = text.split("```", 1)[0]
    elif "```" in text:
        text = text.split("```", 1)[1]
        text = text.split("```", 1)[0]

    text = text.strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        logger.error("AI javobini parse qilishda xato: %s", e)
        logger.debug("Xom javob: %s", raw_text[:500])
        raise ValueError(
            f"AI javobini JSON formatda o'qib bo'lmadi: {e}"
        ) from e


def _build_analysis_result(
    data: dict,
    post_url: str,
    total_comments: int,
) -> AnalysisResult:
    """Parse qilingan AI javobidan AnalysisResult obyekti yaratadi."""

    # ── Sentiment ─────────────────────────────────────────────────────
    sentiment_data = data.get("sentiment", {})
    sentiment = SentimentScore(
        positive=float(sentiment_data.get("positive", 0)),
        negative=float(sentiment_data.get("negative", 0)),
        neutral=float(sentiment_data.get("neutral", 0)),
    )

    # ── Categories ────────────────────────────────────────────────────
    cat_data = data.get("categories", {})
    categories = CategoryBreakdown(
        praise=cat_data.get("praise", []),
        criticism=cat_data.get("criticism", []),
        question=cat_data.get("question", []),
        suggestion=cat_data.get("suggestion", []),
        spam=cat_data.get("spam", []),
        neutral=cat_data.get("neutral", []),
        emoji_only=cat_data.get("emoji_only", []),
    )

    # ── Top topics ────────────────────────────────────────────────────
    top_topics = data.get("top_topics", [])

    # ── Summary ───────────────────────────────────────────────────────
    summary = data.get("summary", "Xulosa mavjud emas.")

    return AnalysisResult(
        post_url=post_url,
        total_comments=total_comments,
        sentiment=sentiment,
        categories=categories,
        top_topics=top_topics,
        summary=summary,
    )


def analyze_comments(
    config: Config,
    scrape_result: ScrapeResult,
) -> AnalysisResult:
    """
    Yig'ilgan kommentariyalarni Gemini AI bilan tahlil qiladi.

    Args:
        config: Loyiha konfiguratsiyasi (Gemini API key va model nomi).
        scrape_result: Scraper natijasi (kommentariyalar ro'yxati).

    Returns:
        AnalysisResult: AI tahlil natijasi — sentiment, kategoriyalar,
            mavzular va xulosa.

    Raises:
        ValueError: AI javobini parse qilishda xato.
        ConnectionError: Gemini API ga ulanishda xato.
    """
    if not scrape_result.comments:
        logger.warning("Tahlil qilish uchun kommentariya yo'q.")
        return AnalysisResult(
            post_url=scrape_result.post_url,
            total_comments=0,
            summary="Kommentariyalar topilmadi.",
        )

    # ── Gemini API sozlash ────────────────────────────────────────────
    genai.configure(api_key=config.gemini_api_key)

    model = genai.GenerativeModel(
        model_name=config.gemini_model,
        system_instruction=_SYSTEM_INSTRUCTION,
        generation_config=genai.GenerationConfig(
            temperature=0.3,          # Aniq va barqaror natija
            top_p=0.9,
            max_output_tokens=4096,
            response_mime_type="application/json",
        ),
    )

    # ── Prompt tayyorlash ─────────────────────────────────────────────
    comments_text = _format_comments_for_prompt(scrape_result)
    prompt = _ANALYSIS_PROMPT_TEMPLATE.format(
        count=scrape_result.total_comments,
        comments_text=comments_text,
    )

    logger.info(
        "Gemini AI ga %d ta kommentariya yuborilmoqda (model: %s)...",
        scrape_result.total_comments,
        config.gemini_model,
    )

    # ── AI ga so'rov yuborish ─────────────────────────────────────────
    try:
        response = model.generate_content(prompt)
    except Exception as e:
        msg = f"Gemini API xatosi: {e}"
        logger.error(msg)
        raise ConnectionError(msg) from e

    if not response.text:
        raise ValueError("Gemini AI bo'sh javob qaytardi.")

    logger.info("Gemini AI javob berdi. Parse qilinmoqda...")

    # ── Javobni parse qilish ──────────────────────────────────────────
    parsed_data = _parse_ai_response(response.text)

    # ── Natijani yaratish ─────────────────────────────────────────────
    result = _build_analysis_result(
        data=parsed_data,
        post_url=scrape_result.post_url,
        total_comments=scrape_result.total_comments,
    )

    logger.info(
        "✅ Tahlil yakunlandi: ijobiy=%.0f%%, salbiy=%.0f%%, neytral=%.0f%%",
        result.sentiment.positive,
        result.sentiment.negative,
        result.sentiment.neutral,
    )

    return result
