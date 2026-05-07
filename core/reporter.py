"""
Instagram Comment Analyzer — Hisobot tayyorlovchi (Reporter).

Bu modul tahlil natijalarini turli formatlar (Telegram, Web, CLI)
uchun tayyorlash funksionalligini ta'minlaydi.
"""

from __future__ import annotations

import logging
from dataclasses import asdict

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from core.analyzer import AnalysisResult, CategoryBreakdown

logger = logging.getLogger(__name__)

# ── Emoji va label mapping ────────────────────────────────────────────
_CATEGORY_META = {
    "praise":     {"emoji": "📣", "label": "Maqtov",      "color": "green"},
    "criticism":  {"emoji": "😡", "label": "Tanqid",      "color": "red"},
    "question":   {"emoji": "❓", "label": "Savol",       "color": "blue"},
    "suggestion": {"emoji": "💡", "label": "Taklif",      "color": "yellow"},
    "spam":       {"emoji": "🗑️", "label": "Spam",        "color": "dim"},
    "neutral":    {"emoji": "😐", "label": "Neytral",     "color": "white"},
    "emoji_only": {"emoji": "😀", "label": "Faqat emoji", "color": "bright_magenta"},
}


def _category_count(categories: CategoryBreakdown) -> dict[str, int]:
    """Har bir kategoriya uchun kommentariya sonini hisoblaydi."""
    return {
        key: len(getattr(categories, key))
        for key in _CATEGORY_META
    }


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

    Args:
        result: AI tahlil natijasi.

    Returns:
        Telegram MarkdownV2 formatdagi xabar matni.
    """
    counts = _category_count(result.categories)
    total = result.total_comments

    lines = [
        f"📊 *Instagram Kommentariya Tahlili*",
        f"━━━━━━━━━━━━━━━━━━━━━━",
        f"🔗 Post: {result.post_url}",
        f"💬 Jami kommentariyalar: *{total}*",
        "",
        "📈 *Sentiment Tahlili:*",
        f"  🟢 Ijobiy:  {result.sentiment.positive:.0f}%",
        f"  🔴 Salbiy:  {result.sentiment.negative:.0f}%",
        f"  ⚪ Neytral: {result.sentiment.neutral:.0f}%",
        "",
        "📂 *Kategoriyalar:*",
    ]

    for key, meta in _CATEGORY_META.items():
        count = counts.get(key, 0)
        if count > 0:
            pct = count / total * 100 if total > 0 else 0
            lines.append(
                f"  {meta['emoji']} {meta['label']}: {count} ({pct:.0f}%)"
            )

    if result.top_topics:
        lines.append("")
        lines.append("🏷️ *Top mavzular:*")
        for i, topic in enumerate(result.top_topics[:5], 1):
            lines.append(f"  {i}. {topic}")

    lines.append("")
    lines.append("📝 *Xulosa:*")
    lines.append(result.summary)

    return "\n".join(lines)


# ══════════════════════════════════════════════════════════════════════
# WEB FORMAT
# ══════════════════════════════════════════════════════════════════════

def format_for_web(result: AnalysisResult) -> dict:
    """
    Tahlil natijasini Web sahifa uchun dict/JSON formatda tayyorlaydi.

    Args:
        result: AI tahlil natijasi.

    Returns:
        Web sahifa uchun tayyorlangan ma'lumotlar (dict).
    """
    counts = _category_count(result.categories)
    total = result.total_comments

    # ── Kategoriyalar statistikasi ────────────────────────────────────
    categories_stats = []
    for key, meta in _CATEGORY_META.items():
        count = counts.get(key, 0)
        categories_stats.append({
            "key": key,
            "label": meta["label"],
            "emoji": meta["emoji"],
            "color": meta["color"],
            "count": count,
            "percentage": round(count / total * 100, 1) if total > 0 else 0,
            "comments": getattr(result.categories, key),
        })

    # ── Natija ────────────────────────────────────────────────────────
    return {
        "post_url": result.post_url,
        "total_comments": total,
        "sentiment": {
            "positive": round(result.sentiment.positive, 1),
            "negative": round(result.sentiment.negative, 1),
            "neutral": round(result.sentiment.neutral, 1),
        },
        "categories": categories_stats,
        "top_topics": result.top_topics[:5],
        "summary": result.summary,
    }


# ══════════════════════════════════════════════════════════════════════
# CLI FORMAT
# ══════════════════════════════════════════════════════════════════════

def format_for_cli(result: AnalysisResult) -> None:
    """
    Tahlil natijasini terminal uchun rich formatda chiqaradi.

    Args:
        result: AI tahlil natijasi.
    """
    console = Console()
    counts = _category_count(result.categories)
    total = result.total_comments

    # ── Sarlavha ──────────────────────────────────────────────────────
    console.print(
        Panel(
            f"[bold bright_white]📊 Instagram Kommentariya Tahlili[/bold bright_white]\n"
            f"[dim]🔗 {result.post_url}[/dim]\n"
            f"[bold]💬 Jami: {total} ta kommentariya[/bold]",
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
        f"[green]{_sentiment_bar(result.sentiment.positive)}[/green]",
        f"[green]{result.sentiment.positive:.0f}%[/green]",
    )
    sentiment_table.add_row(
        "🔴 Salbiy",
        f"[red]{_sentiment_bar(result.sentiment.negative)}[/red]",
        f"[red]{result.sentiment.negative:.0f}%[/red]",
    )
    sentiment_table.add_row(
        "⚪ Neytral",
        f"[white]{_sentiment_bar(result.sentiment.neutral)}[/white]",
        f"[white]{result.sentiment.neutral:.0f}%[/white]",
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
        count = counts.get(key, 0)
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

    # ── Kategoriya tafsilotlari ───────────────────────────────────────
    for key, meta in _CATEGORY_META.items():
        items = getattr(result.categories, key)
        if not items:
            continue

        console.print(
            f"\n  [bold {meta['color']}]{meta['emoji']} {meta['label']} "
            f"({len(items)} ta):[/bold {meta['color']}]"
        )
        for item in items[:5]:  # Har bir kategoriyadan max 5 ta ko'rsatish
            username = item.get("username", "???")
            text = item.get("text", "")
            reason = item.get("reason", "")
            console.print(f"    [dim]@{username}:[/dim] {text}")
            if reason:
                console.print(f"      [italic dim]→ {reason}[/italic dim]")

    # ── Top mavzular ──────────────────────────────────────────────────
    if result.top_topics:
        console.print("\n[bold cyan]🏷️ Top mavzular:[/bold cyan]")
        for i, topic in enumerate(result.top_topics[:5], 1):
            console.print(f"  [bold]{i}.[/bold] {topic}")

    # ── Xulosa ────────────────────────────────────────────────────────
    console.print(
        Panel(
            f"[italic]{result.summary}[/italic]",
            title="[bold]📝 Xulosa",
            border_style="bright_green",
            padding=(1, 3),
        )
    )
