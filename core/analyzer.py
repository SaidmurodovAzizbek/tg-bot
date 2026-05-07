"""
AI Analyzer moduli (OpenRouter API orqali).

Ushbu modul yig'ilgan kommentariyalarni OpenRouter API
(masalan: Llama 3) yordamida tahlil qilib, ularni kategoriyalarga ajratadi.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Dict, List, Any

from openai import OpenAI, RateLimitError
from config import Config
from core.scraper import ScrapeResult

logger = logging.getLogger(__name__)

# ── Ma'lumotlar modellari (Data Models) ────────────────────────────────

@dataclass
class CategoryData:
    """Bitta kategoriya ostidagi kommentariyalar to'plami."""
    count: int = 0
    comments: List[str] = field(default_factory=list)

@dataclass
class AnalysisResult:
    """AI Tahlil natijasini saqlovchi obyekt."""
    summary_uz: str
    positive_percent: int
    negative_percent: int
    neutral_percent: int
    categories: Dict[str, CategoryData]
    post_url: str
    total_analyzed: int


# ── Kategoriyalar ro'yxati ─────────────────────────────────────────────

CATEGORIES = [
    "Praise",     # Maqtov, ijobiy fikrlar
    "Criticism",  # Tanqid, salbiy fikrlar
    "Question",   # Savollar
    "Suggestion", # Taklif yoki maslahatlar
    "Spam",       # Reklama, botlar, ssilka
    "Neutral",    # Neytral, oddiy belgilashlar (masalan: ok, +)
    "Emojis"      # Faqat smayliklardan iborat
]


# ── Prompt Shablon ─────────────────────────────────────────────────────

_SYSTEM_PROMPT = """
Siz Instagram izohlari (comments) ni o'zbek tilida tahlil qiluvchi va kategoriyalarga ajratuvchi professional sun'iy intellektsiz.
Sizga foydalanuvchilar tomonidan yozilgan bir qancha izohlar beriladi.

Sizning vazifangiz:
1. Umumiy izohlarning kayfiyatini (sentiment) tahlil qilib, 1-2 gap bilan O'ZBEK tilida qisqacha xulosa (summary_uz) yozish.
2. Ijobiy (positive_percent), salbiy (negative_percent) va neytral (neutral_percent) izohlarning umumiy foizini hisoblash (uchalasining yig'indisi doim 100 bo'lishi shart).
3. HAR BIR izohni quyidagi 7 ta kategoriyadan ENG MOS bittasiga joylashtirish:
   - "Praise" (Maqtov, duo, minnatdorchilik)
   - "Criticism" (Tanqid, yomon ko'rish, shikoyat)
   - "Question" (Savol, narxini yoki manzilni so'rash)
   - "Suggestion" (Taklif, shunday qilsa yaxshi bo'lardi kabi)
   - "Spam" (Reklama, obuna bo'ling, botlar yozgan so'zlar)
   - "Neutral" (Oddiy so'zlar, masalan: "ha", "yo'q", "ok", "+")
   - "Emojis" (Faqatgina emojilardan iborat bo'lgan izohlar)

DIQQAT: Natijani FAKATGINA quyidagi toza JSON formatida qaytaring! Hech qanday boshqa matn yoki tushuntirish yozmang.

JSON format nusxasi:
{
  "summary_uz": "Umumiy xulosa bu yerga...",
  "positive_percent": 0,
  "negative_percent": 0,
  "neutral_percent": 0,
  "categories": {
    "Praise": ["izoh1", "izoh2"],
    "Criticism": [],
    "Question": [],
    "Suggestion": [],
    "Spam": [],
    "Neutral": [],
    "Emojis": []
  }
}
"""


def _extract_json_from_text(text: str) -> dict:
    """LLM javobidan JSON qismini xavfsiz ajratib oladi."""
    try:
        # Eng oddiy holat: matn o'zi toza JSON bo'lsa
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Markdown bloklari (```json ... ```) orasidan qidirish
    match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass
            
    # Umumiy { } qavslar orasini qidirish (Eng oxirgi chora)
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass

    raise ValueError("LLM javobidan yaroqli JSON topilmadi.")


# ── Asosiy funksiya ────────────────────────────────────────────────────

def analyze_comments(config: Config, scrape_result: ScrapeResult) -> AnalysisResult:
    """
    OpenRouter API yordamida izohlarni tahlil qiladi.
    """
    if not scrape_result.comments:
        logger.warning("Tahlil uchun kommentariyalar yo'q.")
        return _empty_result(scrape_result.post_url)

    logger.info(f"OpenRouter API ga {len(scrape_result.comments)} ta kommentariya yuborilmoqda (model: {config.openrouter_model})...")

    # OpenRouter uchun OpenAI mijozini sozlash
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=config.openrouter_api_key,
    )

    # Izohlarni matn holatiga keltirish
    comments_text = "\n".join(
        f"- {c.username}: {c.text}" for c in scrape_result.comments
    )
    user_prompt = f"Quyidagi izohlarni tahlil qiling va JSON formatida qaytaring:\n\n{comments_text}"

    # OpenRouter API ba'zan bepul modellarga limit qo'yadi (429 Xato)
    # Shuning uchun agar birinchi model ishlamasa, boshqa bepul modellarni sinab ko'ramiz
    fallback_models = [
        config.openrouter_model,
        "meta-llama/llama-3.3-70b-instruct:free",
        "google/gemma-4-26b-a4b-it:free",
        "qwen/qwen3-coder:free",
        "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free",
        "openai/gpt-oss-120b:free"
    ]

    for model_name in fallback_models:
        logger.info(f"OpenRouter API ga {len(scrape_result.comments)} ta kommentariya yuborilmoqda (model: {model_name})...")
        try:
            # OpenRouter ga so'rov yuborish
            completion = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.1,
            )
            
            raw_output = completion.choices[0].message.content
            logger.info(f"OpenRouter API dan javob muvaffaqiyatli olindi (Ishlagan model: {model_name}).")
            
            # Natijani JSON formatga o'tkazish
            parsed_data = _extract_json_from_text(raw_output)
            return _build_result(parsed_data, scrape_result)

        except Exception as e:
            # Agar rate limit xatosi (429) bo'lsa yoki model topilmasa (404), davom etamiz
            if "429" in str(e) or "404" in str(e) or "rate-limited" in str(e).lower():
                logger.warning(f"Model {model_name} band yoki o'chirilgan. Boshqasiga o'tilmoqda... Xato: {e}")
                continue
            
            # Agar boshqa jiddiy xato bo'lsa, to'xtatamiz
            logger.error(f"Kutilmagan API xatosi ({model_name}): {e}")
            break

    # Agar hamma modellar xato bergan bo'lsa:
    logger.error("Barcha bepul modellar hozircha band (Rate Limited). Tahlil amalga oshmadi.")
    return _empty_result(scrape_result.post_url)


def _build_result(data: Dict[str, Any], scrape_result: ScrapeResult) -> AnalysisResult:
    """JSON ma'lumotni AnalysisResult obyektiga o'giradi."""
    categories_obj = {}
    
    cats_data = data.get("categories", {})
    for cat_name in CATEGORIES:
        comments_list = cats_data.get(cat_name, [])
        categories_obj[cat_name] = CategoryData(
            count=len(comments_list),
            comments=comments_list
        )

    return AnalysisResult(
        summary_uz=data.get("summary_uz", "Xulosa olinmadi."),
        positive_percent=int(data.get("positive_percent", 0)),
        negative_percent=int(data.get("negative_percent", 0)),
        neutral_percent=int(data.get("neutral_percent", 0)),
        categories=categories_obj,
        post_url=scrape_result.post_url,
        total_analyzed=len(scrape_result.comments)
    )


def _empty_result(post_url: str) -> AnalysisResult:
    """Xato yuz berganda yoki izoh yo'q bo'lganda bo'sh obyekt qaytaradi."""
    return AnalysisResult(
        summary_uz="Hech qanday ma'lumot tahlil qilinmadi yoki xatolik yuz berdi.",
        positive_percent=0,
        negative_percent=0,
        neutral_percent=0,
        categories={cat: CategoryData() for cat in CATEGORIES},
        post_url=post_url,
        total_analyzed=0
    )
