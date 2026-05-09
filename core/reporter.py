"""
Instagram Comment Analyzer — Hisobot tayyorlovchi (Reporter).

Bu modul tahlil natijalarini turli formatlar (Telegram, Web, CLI)
uchun tayyorlash funksionalligini ta'minlaydi.
"""

from __future__ import annotations

import logging

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from core.analyzer import AnalysisResult, CategoryData

logger = logging.getLogger(__name__)

# ── Emoji va label mapping ────────────────────────────────────────────
_CATEGORY_META = {
    "Positive": {"emoji": "🟢", "label": "Ijobiy",  "color": "green"},
    "Negative": {"emoji": "🔴", "label": "Salbiy",  "color": "red"},
    "Neutral":  {"emoji": "⚪", "label": "Neytral", "color": "white"},
}


def _escape_md(text: str) -> str:
    """Markdown uchun xavfli belgilarni tozalaydi."""
    # Telegram MARKDOWN legacy uchun _ va * ni escape qilamiz
    if not isinstance(text, str):
        return str(text)
    return text.replace("_", "\\_").replace("*", "\\*").replace("[", "\\[")


def _sentiment_bar(value: float, width: int = 20) -> str:
    """Foiz ko'rsatkichni matnli progress bar ga aylantiradi."""
    filled = int(value / 100 * width)
    empty = width - filled
    return "█" * filled + "░" * empty


# ══════════════════════════════════════════════════════════════════════
# TELEGRAM FORMAT
# ══════════════════════════════════════════════════════════════════════

def format_for_telegram(result: AnalysisResult) -> str:
    """
    Tahlil natijasini Telegram xabar uchun Markdown formatda tayyorlaydi.
    """
    total = result.total_analyzed

    lines = [
        f"📊 *Instagram Kommentariya Tahlili*",
        f"━━━━━━━━━━━━━━━━━━━━━━",
        f"🔗 Post: {_escape_md(result.post_url)}",
        f"💬 Jami tahlil qilindi: *{total}*",
        "",
        "📈 *Sentiment Tahlili:*",
        f"  🟢 Ijobiy:  {result.positive_percent}%",
        f"  🔴 Salbiy:  {result.negative_percent}%",
        f"  ⚪ Neytral: {result.neutral_percent}%",
        "",
        "📂 *Kategoriyalar:*",
    ]

    for key, meta in _CATEGORY_META.items():
        cat_data = result.categories.get(key)
        count = cat_data.count if cat_data else 0
        if count > 0:
            pct = count / total * 100 if total > 0 else 0
            lines.append(
                f"  {meta['emoji']} {meta['label']}: {count} ({pct:.0f}%)"
            )

    lines.append("")
    lines.append("📝 *Xulosa:*")
    lines.append(_escape_md(result.summary_uz))

    return "\n".join(lines)


# ══════════════════════════════════════════════════════════════════════
# WEB FORMAT
# ══════════════════════════════════════════════════════════════════════

def format_for_web(result: AnalysisResult) -> dict:
    """
    Tahlil natijasini Web sahifa uchun dict/JSON formatda tayyorlaydi.
    """
    total = result.total_analyzed

    # ── Kategoriyalar statistikasi ────────────────────────────────────
    categories_stats = []
    for key, meta in _CATEGORY_META.items():
        cat_data = result.categories.get(key)
        count = cat_data.count if cat_data else 0
        
        categories_stats.append({
            "key": key,
            "label": meta["label"],
            "emoji": meta["emoji"],
            "color": meta["color"],
            "count": count,
            "percentage": round(count / total * 100, 1) if total > 0 else 0,
            "comments": cat_data.comments if cat_data else [],
        })

    # ── Natija ────────────────────────────────────────────────────────
    return {
        "post_url": result.post_url,
        "total_comments": total,
        "sentiment": {
            "positive": result.positive_percent,
            "negative": result.negative_percent,
            "neutral": result.neutral_percent,
        },
        "categories": categories_stats,
        "top_topics": [], # Groq versiyasida hozircha o'chirildi
        "summary": result.summary_uz,
    }


# ══════════════════════════════════════════════════════════════════════
# CLI FORMAT
# ══════════════════════════════════════════════════════════════════════

def format_for_cli(result: AnalysisResult) -> None:
    """
    Tahlil natijasini terminal uchun rich formatda chiqaradi.
    """
    console = Console()
    total = result.total_analyzed

    # ── Sarlavha ──────────────────────────────────────────────────────
    console.print(
        Panel(
            f"[bold bright_white]📊 Instagram Kommentariya Tahlili[/bold bright_white]\n"
            f"[dim]🔗 {result.post_url}[/dim]\n"
            f"[bold]💬 Jami tahlil qilindi: {total} ta kommentariya[/bold]",
            border_style="bright_magenta",
            padding=(1, 4),
        )
    )

    # ── Sentiment ─────────────────────────────────────────────────────
    console.print("\n[bold cyan]📈 Sentiment Tahlili:[/bold cyan]")

    sentiment_table = Table(show_header=False, box=None, padding=(0, 2))
    sentiment_table.add_column("Label", style="bold", min_width=10)
    sentiment_table.add_column("Bar", min_width=22)
    sentiment_table.add_column("Foiz", justify="right", min_width=6)

    sentiment_table.add_row(
        "🟢 Ijobiy",
        f"[green]{_sentiment_bar(result.positive_percent)}[/green]",
        f"[green]{result.positive_percent}%[/green]",
    )
    sentiment_table.add_row(
        "🔴 Salbiy",
        f"[red]{_sentiment_bar(result.negative_percent)}[/red]",
        f"[red]{result.negative_percent}%[/red]",
    )
    sentiment_table.add_row(
        "⚪ Neytral",
        f"[white]{_sentiment_bar(result.neutral_percent)}[/white]",
        f"[white]{result.neutral_percent}%[/white]",
    )

    console.print(sentiment_table)

    # ── Kategoriyalar ─────────────────────────────────────────────────
    console.print("\n[bold cyan]📂 Kategoriyalar:[/bold cyan]")

    cat_table = Table(
        show_header=True,
        header_style="bold bright_white",
        padding=(0, 2),
    )
    cat_table.add_column("#", style="dim", width=3)
    cat_table.add_column("Kategoriya", min_width=16)
    cat_table.add_column("Soni", justify="center", min_width=5)
    cat_table.add_column("Foiz", justify="center", min_width=7)
    cat_table.add_column("Bar", min_width=12)

    for i, (key, meta) in enumerate(_CATEGORY_META.items(), 1):
        cat_data = result.categories.get(key)
        count = cat_data.count if cat_data else 0
        pct = count / total * 100 if total > 0 else 0
        bar_width = int(pct / 100 * 10)

        cat_table.add_row(
            str(i),
            f"{meta['emoji']} {meta['label']}",
            str(count),
            f"{pct:.0f}%",
            f"[{meta['color']}]{'█' * bar_width}{'░' * (10 - bar_width)}[/{meta['color']}]",
        )

    console.print(cat_table)

    # ── Xulosa ────────────────────────────────────────────────────────
    console.print(
        Panel(
            f"[italic]{result.summary_uz}[/italic]",
            title="[bold]📝 Xulosa",
            border_style="bright_green",
            padding=(1, 3),
        )
    )
