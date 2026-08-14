"""Feature 4: Citability / GEO Score engine (0–100)."""

from __future__ import annotations

import re
from typing import Any

from bs4 import BeautifulSoup

STAT_PATTERN = re.compile(
    r"\b\d{1,3}(?:[.,]\d+)?%|\b\d{1,3}(?:,\d{3})+\b|\$\d+|\b\d+\s*(?:million|billion|thousand|млн|тыс)\b",
    re.I,
)
QUESTION_H2 = re.compile(r"^(what|how|why|when|where|who|which|can|does|is|are|как|что|почему|где)\b", re.I)
PRONOUN_HEAVY = re.compile(r"\b(it|they|this|that|these|those|он|она|они|это|этот)\b", re.I)
DATE_MODIFIED = re.compile(r"dateModified|datePublished|article:modified_time|article:published_time", re.I)


def score_citability(html: str, url: str = "") -> dict[str, Any]:
    soup = BeautifulSoup(html, "lxml")
    visible = soup.get_text("\n", strip=True)
    words = visible.split()
    word_count = len(words)

    first_para = ""
    for p in soup.find_all("p"):
        t = p.get_text(strip=True)
        if len(t) > 40:
            first_para = t
            break

    h2s = [h.get_text(strip=True) for h in soup.find_all("h2")]
    h2_questions = sum(1 for h in h2s if "?" in h or QUESTION_H2.match(h))

    tables = soup.find_all("table")
    table_rows = sum(len(t.find_all("tr")) for t in tables)

    faq_schema = False
    faq_visible = bool(soup.find(string=re.compile(r"\bFAQ\b|часто задаваем", re.I)))
    for script in soup.find_all("script", type="application/ld+json"):
        raw = script.get_text(strip=True)
        if "FAQPage" in raw:
            faq_schema = True

    stats_count = len(STAT_PATTERN.findall(visible[:8000]))
    pronoun_ratio = len(PRONOUN_HEAVY.findall(visible[:3000])) / max(len(words[:500]), 1)

    author = bool(
        soup.find(class_=re.compile(r"author", re.I))
        or soup.find(attrs={"rel": "author"})
        or soup.find("meta", attrs={"name": "author"})
    )
    has_date = bool(DATE_MODIFIED.search(html) or soup.find("time"))

    # Scoring weights (max 100)
    scores: dict[str, int] = {}
    scores["answer_capsule"] = 15 if len(first_para) >= 80 and stats_count >= 1 else (8 if len(first_para) >= 50 else 0)
    scores["statistics"] = min(15, stats_count * 5)
    scores["faq"] = 15 if faq_schema and faq_visible else (10 if faq_schema or faq_visible else 0)
    scores["h2_questions"] = min(10, h2_questions * 3)
    scores["tables"] = 10 if table_rows >= 3 else (5 if tables else 0)
    scores["author_date"] = 10 if author and has_date else (5 if author or has_date else 0)
    scores["entity_clarity"] = 10 if pronoun_ratio < 0.08 else (5 if pronoun_ratio < 0.15 else 0)
    scores["content_depth"] = min(15, word_count // 200)

    total = min(100, sum(scores.values()))
    grade = "A" if total >= 80 else "B" if total >= 65 else "C" if total >= 50 else "D" if total >= 35 else "F"

    tips: list[str] = []
    if scores["answer_capsule"] < 10:
        tips.append("Добавь answer capsule в первый абзац: определение + 1 stat")
    if scores["statistics"] < 10:
        tips.append("Добавь конкретные цифры/проценты (Princeton GEO +40%)")
    if scores["faq"] < 10:
        tips.append("FAQ секция + FAQPage schema")
    if scores["tables"] < 5:
        tips.append("HTML table для сравнений (4x AI citations на форумах)")
    if scores["h2_questions"] < 5:
        tips.append("H2 в форме вопросов: Как… / Что такое…")
    if scores["author_date"] < 5:
        tips.append("Author bio + dateModified в schema")

    return {
        "url": url,
        "score": total,
        "grade": grade,
        "breakdown": scores,
        "signals": {
            "word_count": word_count,
            "first_para_len": len(first_para),
            "stats_count": stats_count,
            "h2_questions": h2_questions,
            "table_rows": table_rows,
            "faq_schema": faq_schema,
            "author": author,
            "has_date": has_date,
            "pronoun_ratio": round(pronoun_ratio, 3),
        },
        "tips": tips,
    }


async def score_pages_from_config(pages: list[dict] | None = None) -> dict[str, Any]:
    import httpx
    from app.config_loader import load_config

    cfg = load_config()
    page_list = pages or [
        p for p in (cfg.get("seo") or {}).get("pages") or [] if p.get("type", "html") == "html"
    ]
    results = []
    async with httpx.AsyncClient(timeout=25, follow_redirects=True) as client:
        for p in page_list:
            url = p["url"]
            try:
                resp = await client.get(url)
                sc = score_citability(resp.text, url)
                sc["label"] = p.get("label") or url
                sc["http_status"] = resp.status_code
                results.append(sc)
            except Exception as exc:
                results.append({"url": url, "label": p.get("label"), "error": str(exc)[:120], "score": 0, "grade": "F"})

    avg = round(sum(r.get("score", 0) for r in results) / max(len(results), 1), 1)
    return {
        "error": None,
        "summary": {"pages": len(results), "avg_score": avg},
        "results": results,
    }
