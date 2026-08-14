"""Parse AI E-E-A-T research output and ingest into eeat_documents / eeat_insights."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import date
from typing import Any

from app.eeat_library import list_documents, list_insights
from app.storage import connect

_JSON_BLOCK = re.compile(r"```json\s*(.*?)\s*```", re.DOTALL | re.IGNORECASE)
_EXEC_SUMMARY = re.compile(
    r"(?:EXECUTIVE SUMMARY|Исполнительное резюме)[^\n]*\n(.*?)(?=\n#{1,3}\s|\nЧасть\s*2|\n```json|\Z)",
    re.DOTALL | re.IGNORECASE,
)

_TIER_MAP = {
    "T1_official": "T1_official",
    "T1_site": "T1_site",
    "T2_authoritative": "T2_authoritative",
    "T3_ugc": "T3_ugc",
    "T3_forum": "T3_forum",
    "T4_research": "T2_authoritative",
}

_TYPE_CATEGORY = {
    "regulation": "regulator",
    "google_guideline": "google",
    "legal_page": "quickex_official",
    "press": "reputation",
    "review": "reputation",
    "forum": "forum",
    "entity": "reputation",
    "schema": "google",
    "competitor": "industry",
    "leak_rule": "industry",
}

_SUPPORTS_MAP = {
    True: "positive",
    False: "negative",
    "true": "positive",
    "false": "negative",
    "positive": "positive",
    "negative": "negative",
    "mixed": "mixed",
    "neutral": "neutral",
}


def library_snapshot_for_prompt(limit: int = 36) -> list[dict[str, Any]]:
    """Compact registry of already-collected documents for AI context."""
    docs = list_documents()[:limit]
    return [
        {
            "id": d["id"],
            "source_id": d.get("source_id"),
            "tier": d.get("tier"),
            "title": d.get("title"),
            "url": d.get("source_url"),
            "supports_brand": d.get("supports_brand"),
            "criteria_ids": d.get("criteria_ids", [])[:6],
        }
        for d in docs
    ]


def insights_snapshot_for_prompt(limit: int = 10) -> list[dict[str, Any]]:
    """Open gaps / insights to focus AI research."""
    return [
        {
            "id": i["id"],
            "severity": i.get("severity"),
            "title": i.get("title"),
            "criteria_ids": i.get("criteria_ids", []),
            "recommendation": (i.get("recommendation") or "")[:200],
        }
        for i in list_insights()[:limit]
    ]


def extract_executive_summary(text: str) -> str:
    match = _EXEC_SUMMARY.search(text)
    if match:
        return match.group(1).strip()[:4000]
    lines = text.splitlines()
    summary: list[str] = []
    in_summary = False
    for line in lines:
        low = line.lower()
        if "executive summary" in low or "исполнительное резюме" in low:
            in_summary = True
            continue
        if in_summary and (line.startswith("```") or line.startswith("Часть 2") or line.startswith("## ")):
            break
        if in_summary and line.strip():
            summary.append(line)
    return "\n".join(summary)[:4000]


def parse_research_response(text: str) -> dict[str, Any]:
    """Extract JSON registry + criteria audit from AI markdown response."""
    registry: dict[str, Any] = {}
    criteria: dict[str, Any] = {}
    for block in _JSON_BLOCK.findall(text):
        try:
            data = json.loads(block)
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict):
            if "documents" in data and not registry:
                registry = data
            elif "criteria" in data and not criteria:
                criteria = data
            elif "documents" in data:
                registry = data
            elif "criteria" in data:
                criteria = data
        elif isinstance(data, list) and data and isinstance(data[0], dict):
            if "tier" in data[0] or "source_id" in data[0]:
                registry = {"documents": data}
            elif "id" in data[0] and str(data[0].get("id", "")).startswith("EE"):
                criteria = {"criteria": data}
    return {
        "registry": registry,
        "criteria": criteria,
        "executive_summary": extract_executive_summary(text),
    }


def _normalize_url(url: str) -> str:
    return (url or "").strip().rstrip("/").lower()


def _existing_urls() -> set[str]:
    with connect() as conn:
        rows = conn.execute(
            "SELECT source_url FROM eeat_documents WHERE source_url IS NOT NULL",
        ).fetchall()
    return {_normalize_url(r[0]) for r in rows if r[0]}


def _existing_source_ids() -> set[str]:
    with connect() as conn:
        rows = conn.execute(
            "SELECT source_id FROM eeat_documents WHERE source_id IS NOT NULL",
        ).fetchall()
    return {str(r[0]).upper() for r in rows if r[0]}


def _map_supports(val: Any) -> str:
    if val in _SUPPORTS_MAP:
        return _SUPPORTS_MAP[val]
    return "neutral"


def _doc_id_from_ai(doc: dict[str, Any], idx: int) -> str:
    raw = doc.get("doc_id") or doc.get("id") or f"DOC-{idx:03d}"
    if str(raw).startswith("EEAT-"):
        return str(raw)
    url = doc.get("url") or ""
    if url:
        h = hashlib.sha1(url.encode()).hexdigest()[:8]
        return f"EEAT-AI-{h}"
    return f"EEAT-AI-{idx:03d}"


def _build_content_md(doc: dict[str, Any]) -> str:
    lines = [f"# {doc.get('title') or 'Research document'}", ""]
    if doc.get("url"):
        lines.append(f"**URL:** {doc['url']}")
    if doc.get("publisher"):
        lines.append(f"**Publisher:** {doc['publisher']}")
    if doc.get("published_date") or doc.get("published"):
        lines.append(f"**Published:** {doc.get('published_date') or doc.get('published')}")
    lines.append("")
    if doc.get("summary"):
        lines.append(doc["summary"])
    quotes = doc.get("key_quotes") or []
    if quotes:
        lines.append("")
        lines.append("## Key quotes")
        for q in quotes[:3]:
            lines.append(f"> {q}")
    return "\n".join(lines)


def ingest_research_documents(
    registry: dict[str, Any],
    *,
    research_run_id: int | None = None,
) -> dict[str, int]:
    """Merge new documents from AI registry into eeat_documents."""
    documents = registry.get("documents") or []
    if not documents:
        return {"added": 0, "skipped": 0, "updated": 0}

    known_urls = _existing_urls()
    known_sids = _existing_source_ids()
    today = date.today().isoformat()
    added = skipped = updated = 0

    with connect() as conn:
        for idx, doc in enumerate(documents, start=1):
            url = (doc.get("url") or "").strip()
            if not url or url.lower() in ("not found", "n/a", "null"):
                skipped += 1
                continue

            norm_url = _normalize_url(url)
            source_id = str(doc.get("source_id") or "NEW-AI").upper()
            if norm_url in known_urls:
                skipped += 1
                continue
            if source_id not in ("NEW-AI", "NEW-XXX") and source_id in known_sids:
                skipped += 1
                continue

            doc_id = _doc_id_from_ai(doc, idx)
            tier = _TIER_MAP.get(doc.get("tier") or "", doc.get("tier") or "T3_ugc")
            doc_type = doc.get("type") or "press"
            category = _TYPE_CATEGORY.get(doc_type, "reputation")
            criteria = doc.get("criteria_ids") or []
            if isinstance(criteria, str):
                criteria = [c.strip() for c in criteria.split(",") if c.strip()]

            content = _build_content_md(doc)
            pillar = (doc.get("eeat_pillar") or "T")[:1].upper()

            existing = conn.execute(
                "SELECT id FROM eeat_documents WHERE id = ?",
                (doc_id,),
            ).fetchone()
            if existing:
                conn.execute(
                    """
                    UPDATE eeat_documents SET
                      summary = ?, content_md = ?, research_run_id = ?,
                      verification = ?, accessed_date = ?, origin = 'ai_research'
                    WHERE id = ?
                    """,
                    (
                        doc.get("summary") or "",
                        content,
                        research_run_id,
                        doc.get("verification") or "search_snippet",
                        doc.get("accessed_date") or today,
                        doc_id,
                    ),
                )
                updated += 1
            else:
                conn.execute(
                    """
                    INSERT INTO eeat_documents
                    (id, title, tier, doc_type, source_id, category, credibility,
                     source_url, published, publisher, language, eeat_pillar,
                     criteria_ids_json, relevance_score, supports_brand, summary,
                     content_md, file_name, origin, research_run_id, verification, accessed_date)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'ai_research', ?, ?, ?)
                    """,
                    (
                        doc_id,
                        doc.get("title") or url,
                        tier,
                        doc_type,
                        source_id,
                        category,
                        doc.get("verification") or "search_snippet",
                        url,
                        doc.get("published_date") or doc.get("published"),
                        doc.get("publisher"),
                        doc.get("language") or "en",
                        pillar,
                        json.dumps(criteria, ensure_ascii=False),
                        int(doc.get("relevance_score") or 3),
                        _map_supports(doc.get("supports_brand")),
                        doc.get("summary") or "",
                        content,
                        None,
                        research_run_id,
                        doc.get("verification") or "search_snippet",
                        doc.get("accessed_date") or today,
                    ),
                )
                added += 1
            known_urls.add(norm_url)
            if source_id not in ("NEW-AI", "NEW-XXX"):
                known_sids.add(source_id)

    return {"added": added, "skipped": skipped, "updated": updated}


def ingest_research_insights(
    criteria: dict[str, Any],
    *,
    research_run_id: int | None = None,
    min_priority: str = "P1",
) -> int:
    """Create insights from fail/warn criteria in AI audit."""
    items = criteria.get("criteria") or []
    if not items:
        return 0

    priority_rank = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}
    min_rank = priority_rank.get(min_priority, 1)
    severity_map = {"fail": "high", "warn": "medium", "manual": "low"}
    added = 0

    with connect() as conn:
        for item in items:
            status = (item.get("status") or "").lower()
            if status not in ("fail", "warn"):
                continue
            fix = item.get("fix_priority") or "P2"
            if priority_rank.get(fix, 9) > min_rank:
                continue

            crit_id = item.get("id") or "EE00"
            ins_id = f"INS-AI-{crit_id}-{research_run_id or 0}"
            if conn.execute("SELECT id FROM eeat_insights WHERE id = ?", (ins_id,)).fetchone():
                continue

            gap = item.get("gap") or item.get("evidence") or ""
            rec = gap if gap else f"Исправить {crit_id} — статус {status}"
            criteria_ids = [crit_id]
            for doc in item.get("supporting_docs") or []:
                if str(doc).startswith("EE"):
                    criteria_ids.append(str(doc))

            conn.execute(
                """
                INSERT OR REPLACE INTO eeat_insights
                (id, document_id, title, severity, eeat_pillar, criteria_ids_json, recommendation)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    ins_id,
                    None,
                    f"AI Research: {crit_id} — {status}",
                    severity_map.get(status, "medium"),
                    (item.get("pillar") or "T")[:1].upper(),
                    json.dumps(list(dict.fromkeys(criteria_ids)), ensure_ascii=False),
                    rec[:500],
                ),
            )
            added += 1
    return added


def process_research_ingest(
    review_text: str,
    *,
    research_run_id: int | None = None,
) -> dict[str, Any]:
    """Full pipeline: parse AI response → ingest docs + insights."""
    parsed = parse_research_response(review_text)
    doc_stats = ingest_research_documents(
        parsed.get("registry") or {},
        research_run_id=research_run_id,
    )
    insight_count = ingest_research_insights(
        parsed.get("criteria") or {},
        research_run_id=research_run_id,
    )
    return {
        "parsed": {
            "has_registry": bool((parsed.get("registry") or {}).get("documents")),
            "has_criteria": bool((parsed.get("criteria") or {}).get("criteria")),
            "executive_summary_len": len(parsed.get("executive_summary") or ""),
        },
        "documents": doc_stats,
        "insights_added": insight_count,
        "registry": parsed.get("registry"),
        "criteria": parsed.get("criteria"),
        "executive_summary": parsed.get("executive_summary"),
    }
