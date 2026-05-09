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
    "Positive", # Ijobiy fikrlar
    "Negative", # Salbiy fikrlar
    "Neutral"   # Neytral, savollar, spam
]


# ── Prompt Shablon ─────────────────────────────────────────────────────

_SYSTEM_PROMPT = """
Siz Instagram izohlari (comments) ni o'zbek tilida tahlil qiluvchi va kategoriyalarga ajratuvchi professional sun'iy intellektsiz.
Sizga foydalanuvchilar tomonidan yozilgan bir qancha izohlar beriladi.

Sizning vazifangiz:
1. Umumiy izohlarning kayfiyatini (sentiment) tahlil qilib, 1-2 gap bilan O'ZBEK tilida qisqacha xulosa (summary_uz) yozish.
2. Ijobiy (positive_percent), salbiy (negative_percent) va neytral (neutral_percent) izohlarning umumiy foizini hisoblash (uchalasining yig'indisi doim 100 bo'lishi shart).
3. HAR BIR izohni quyidagi 3 ta kategoriyadan ENG MOS bittasiga joylashtirish:
   - "Positive" (Maqtov, duo, minnatdorchilik, xursandchilik bildirilgan izohlar va ijobiy emojilar)
   - "Negative" (Tanqid, yomon ko'rish, shikoyat, salbiy fikrlar va salbiy emojilar)
   - "Neutral" (Oddiy so'zlar, savollar, takliflar, spam yoki aniq ijobiy/salbiy bo'lmagan izohlar)

DIQQAT: Natijani FAKATGINA quyidagi toza JSON formatida qaytaring! Hech qanday boshqa matn yoki tushuntirish yozmang.

JSON format nusxasi:
{
  "summary_uz": "Umumiy xulosa bu yerga...",
  "positive_percent": 0,
  "negative_percent": 0,
  "neutral_percent": 0,
  "categories": {
    "Positive": [{"username": "user1", "text": "izoh1"}],
    "Negative": [],
    "Neutral": []
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


# ── Zaxira (Fallback) mexanizmi uchun lug'atlar ──────────────────────────

POSITIVE_WORDS = [
    "zo'r", "ajoyib", "yaxshi", "gap yo'q", "rahmat", "barakalla", "qoyil", 
    "chiroyli", "super", "omad", "zor", "klass", "gap yõq", "yaxwi", "zur",
    "👍", "❤️", "🔥", "👏", "😍", "🥰", "💯"
]

NEGATIVE_WORDS = [
    "yomon", "yoqmadi", "qimmat", "aldov", "fuflo", "rasvo", "daxshat", 
    "chatoq", "tavsiya qilmayman", "beziyon", "jirkanch", "axlat",
    "👎", "🤬", "😡", "💩", "🤮", "🤡"
]

def _fallback_analyze(scrape_result: ScrapeResult) -> AnalysisResult:
    """API ishlamay qolganda lug'at yordamida tahlil qiladi."""
    categories_obj = {
        "Positive": CategoryData(),
        "Negative": CategoryData(),
        "Neutral": CategoryData()
    }
    
    pos_count = 0
    neg_count = 0
    neu_count = 0
    
    for comment in scrape_result.comments:
        text_lower = comment.text.lower()
        
        is_pos = any(word in text_lower for word in POSITIVE_WORDS)
        is_neg = any(word in text_lower for word in NEGATIVE_WORDS)
        
        comment_dict = {"username": comment.username, "text": comment.text}
        
        if is_pos and not is_neg:
            categories_obj["Positive"].comments.append(comment_dict)
            categories_obj["Positive"].count += 1
            pos_count += 1
        elif is_neg and not is_pos:
            categories_obj["Negative"].comments.append(comment_dict)
            categories_obj["Negative"].count += 1
            neg_count += 1
        else:
            categories_obj["Neutral"].comments.append(comment_dict)
            categories_obj["Neutral"].count += 1
            neu_count += 1
            
    total = len(scrape_result.comments)
    pos_pct = int(pos_count / total * 100) if total else 0
    neg_pct = int(neg_count / total * 100) if total else 0
    neu_pct = 100 - pos_pct - neg_pct if total else 0
    
    return AnalysisResult(
        summary_uz="Tahlil AI xizmatidagi muammolar sababli oddiy so'zlar lug'ati yordamida avtomatik amalga oshirildi.",
        positive_percent=pos_pct,
        negative_percent=neg_pct,
        neutral_percent=neu_pct,
        categories=categories_obj,
        post_url=scrape_result.post_url,
        total_analyzed=total
    )


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
    logger.error("Barcha bepul modellar hozircha band (Rate Limited). Zaxira (fallback) tizim ishga tushirildi.")
    return _fallback_analyze(scrape_result)


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
