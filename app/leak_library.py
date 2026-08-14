"""Google leak library — documents, rules, SQLite storage."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from app.config_loader import DATA_DIR, ROOT
from app.storage import connect

LEAKS_DIR = DATA_DIR / "google-leaks"
DOCS_DIR = LEAKS_DIR / "docs"

DOCUMENTS: list[dict[str, Any]] = [
    {
        "id": "DOC-CW-2024",
        "title": "Content Warehouse API Leak (2024)",
        "category": "api_leak",
        "credibility": "google_confirmed",
        "source_url": "https://sparktoro.com/blog/an-anonymous-source-shared-thousands-of-leaked-google-search-api-documents-with-me-everyone-in-seo-should-see-them/",
        "published": "2024-05-28",
        "summary": "14,014 API attributes from Google Content Warehouse; confirmed by Google May 2024.",
        "file": "content-warehouse-leak-2024.md",
    },
    {
        "id": "DOC-NAVBOOST",
        "title": "NavBoost & Clickstream Signals",
        "category": "ranking_system",
        "credibility": "leak_plus_trial",
        "source_url": "https://ipullrank.com/google-algo-leak",
        "published": "2024-05-28",
        "summary": "goodClicks, badClicks, NavBoost — user engagement re-ranking.",
        "file": "navboost-clickstream.md",
    },
    {
        "id": "DOC-CHROME",
        "title": "Chrome Browser Quality Signals",
        "category": "user_signals",
        "credibility": "leak_reported",
        "source_url": "https://www.winwithoptimal.com/insights/google-api-leak/",
        "published": "2024-05-28",
        "summary": "chromeInTotal, chrome_trans_clicks — aggregated Chrome telemetry in scoring.",
        "file": "chrome-quality-signals.md",
    },
    {
        "id": "DOC-AUTHORITY",
        "title": "Site Authority & Topicality",
        "category": "site_signals",
        "credibility": "leak_reported",
        "source_url": "https://growfusely.com/blog/google-api-leak/",
        "published": "2024-05-28",
        "summary": "siteAuthority, siteFocusScore, siteRadius, titlematchScore.",
        "file": "site-authority-topicality.md",
    },
    {
        "id": "DOC-DEMOTION",
        "title": "Demotion Signals + QRG Patterns",
        "category": "quality_filters",
        "credibility": "leak_plus_official",
        "source_url": "https://static.googleusercontent.com/media/guidelines.raterhub.com/en//searchqualityevaluatorguidelines.pdf",
        "published": "2025-09-01",
        "summary": "Panda/helpful content, nav demotion, link mismatch + official QRG YMYL/E-E-A-T.",
        "file": "demotion-signals-qrg.md",
    },
    {
        "id": "DOC-TRIAL",
        "title": "US v. Google Antitrust Trial (2023)",
        "category": "court_record",
        "credibility": "official_testimony",
        "source_url": "https://www.searchengineland.com/google-search-documentation-leak-442617",
        "published": "2023-10-01",
        "summary": "On-record testimony validating click-based systems (NavBoost).",
        "file": "antitrust-trial-2023.md",
    },
]

# Rules: audit_triggers = checklist IDs that activate this recommendation
LEAK_RULES: list[dict[str, Any]] = [
    {
        "id": "LK-NAV-001",
        "document_id": "DOC-NAVBOOST",
        "name": "NavBoost — reduce bad clicks",
        "category": "user_signals",
        "severity": "critical",
        "leak_attributes": "goodClicks, badClicks, lastLongestClicks, navBoost",
        "google_public": "Clicks are not a direct ranking factor",
        "leak_evidence": "Leaked NavBoost modules + antitrust trial testimony (Nayak)",
        "recommendation": "Перепиши title/meta/H1 на money pages: обещание = контент above the fold. Убери clickbait на YMYL — badClicks демотируют.",
        "audit_triggers": ["EE18", "EE19", "YY02", "YY03", "C12", "C13", "C14"],
    },
    {
        "id": "LK-NAV-002",
        "document_id": "DOC-NAVBOOST",
        "name": "SERP snippet ↔ intent match",
        "category": "user_signals",
        "severity": "high",
        "leak_attributes": "titlematchScore",
        "google_public": "Titles should be descriptive",
        "leak_evidence": "titlematchScore attribute in Content Warehouse leak",
        "recommendation": "Синхронизируй <title>, H1 и top_keyword с фактическим контентом пары. Добавь rate/limit/steps в сниппет-зону.",
        "audit_triggers": ["C12", "C13", "C14", "C15", "P04", "P05"],
    },
    {
        "id": "LK-AUTH-001",
        "document_id": "DOC-AUTHORITY",
        "name": "Site authority (siteAuthority)",
        "category": "site_signals",
        "severity": "critical",
        "leak_attributes": "siteAuthority",
        "google_public": "We do not use domain authority",
        "leak_evidence": "siteAuthority-style metrics in leaked API docs",
        "recommendation": "Усиль site-wide trust: About, team, licenses, press (DR 30+), Organization schema, sameAs. Не полагайся только на pair SEO.",
        "audit_triggers": ["EE11", "EE12", "EE13", "EE14", "EE15", "YY20", "YY21", "YY22"],
    },
    {
        "id": "LK-TOPIC-001",
        "document_id": "DOC-AUTHORITY",
        "name": "Topical focus (siteFocusScore / siteRadius)",
        "category": "site_signals",
        "severity": "high",
        "leak_attributes": "siteFocusScore, siteRadius",
        "google_public": "Create helpful content for your audience",
        "leak_evidence": "Topical embedding / focus attributes in leak",
        "recommendation": "Срежь off-topic контент и spam-кластеры. Свяжи блог только topically relevant темами (swap guides, privacy coins).",
        "audit_triggers": ["EE07", "EE08", "YY01", "C22", "C23"],
    },
    {
        "id": "LK-CHROME-001",
        "document_id": "DOC-CHROME",
        "name": "Chrome engagement proxies",
        "category": "user_signals",
        "severity": "medium",
        "leak_attributes": "chromeInTotal, chrome_trans_clicks",
        "google_public": "Chrome data not used for ranking",
        "leak_evidence": "Chrome telemetry fields in leaked documentation",
        "recommendation": "Инвестируй в brand + UX: быстрый swap flow, HTTPS, security headers, повторные визиты. Покупной трафик без бренда не заменит.",
        "audit_triggers": ["P12", "P13", "P14", "EE25", "EE26"],
    },
    {
        "id": "LK-LINK-001",
        "document_id": "DOC-DEMOTION",
        "name": "Link relevance & spam demotion",
        "category": "link_graph",
        "severity": "high",
        "leak_attributes": "link reputation demotion modules",
        "google_public": "We ignore bad links",
        "leak_evidence": "Irrelevant link / anchor mismatch demotion in analyst crosswalk",
        "recommendation": "Мониторь Ahrefs weekly: disavow только после ручного review. Фокус на editorial DR 20+ в crypto/fintech.",
        "audit_triggers": ["EE22", "EE23", "YY18", "P18"],
    },
    {
        "id": "LK-NAVUX-001",
        "document_id": "DOC-DEMOTION",
        "name": "Navigation demotion",
        "category": "ux",
        "severity": "medium",
        "leak_attributes": "nav demotion / poor UX classifiers",
        "google_public": "Make sites usable",
        "leak_evidence": "Nav experience demotion cited in Optimal/iPullRank summaries",
        "recommendation": "Footer: policies, fees, support, AML. Breadcrumbs на pair pages. Orphan money pages — исправь internal links.",
        "audit_triggers": ["C31", "C32", "P08", "P09", "EE16"],
    },
    {
        "id": "LK-HCU-001",
        "document_id": "DOC-DEMOTION",
        "name": "Helpful Content / thin affiliate demotion",
        "category": "content_quality",
        "severity": "critical",
        "leak_attributes": "helpful content / panda lineage",
        "google_public": "Helpful content system",
        "leak_evidence": "HCU-style demotion attributes in leak mappings",
        "recommendation": "Добавь first-hand value: авторы с bio, дата, sources, уникальные rates/limitations. Убери thin affiliate шаблоны.",
        "audit_triggers": ["EE01", "EE02", "EE03", "EE07", "C20", "C21", "YY05"],
    },
    {
        "id": "LK-QRG-YMYL",
        "document_id": "DOC-DEMOTION",
        "name": "QRG YMYL — financial harm bar",
        "category": "ymyl",
        "severity": "critical",
        "leak_attributes": "quality raters encode YMYL PQ",
        "google_public": "QRG for raters (official)",
        "leak_evidence": "QRG §2.3 + leak quality modules align on harm prevention",
        "recommendation": "Risk disclosures, KYC/AML прозрачность, no guaranteed returns. Compliance pages linked from every money page.",
        "audit_triggers": ["YY02", "YY03", "YY04", "YY05", "YY06", "YY07", "YY08"],
    },
    {
        "id": "LK-QRG-EEAT",
        "document_id": "DOC-DEMOTION",
        "name": "QRG E-E-A-T — Lowest PQ avoidance",
        "category": "eeat",
        "severity": "critical",
        "leak_attributes": "rater PQ + site authority",
        "google_public": "E-E-A-T in QRG",
        "leak_evidence": "QRG §3.4 mapped to siteAuthority / trust attributes",
        "recommendation": "Whois/company, physical address, support email, author pages, editorial policy. Scam signals = Lowest PQ.",
        "audit_triggers": ["EE11", "EE12", "EE17", "EE18", "EE19", "EE20", "EE21"],
    },
    {
        "id": "LK-ENTITY-001",
        "document_id": "DOC-AUTHORITY",
        "name": "Entity & structured data",
        "category": "entity",
        "severity": "high",
        "leak_attributes": "entity / KG related fields",
        "google_public": "Structured data helps understanding",
        "leak_evidence": "Entity linking in warehouse modules (analyst notes)",
        "recommendation": "Organization + FinancialService JSON-LD, logo, sameAs (Twitter, LinkedIn, Crunchbase). FAQ только для реальных Q&A.",
        "audit_triggers": ["EE14", "EE15", "C40", "C41", "C42", "P15"],
    },
    {
        "id": "LK-AI-001",
        "document_id": "DOC-CW-2024",
        "name": "AI Overviews citation bias",
        "category": "geo",
        "severity": "medium",
        "leak_attributes": "SGE/AI overview selection (industry studies)",
        "google_public": "AI answers use quality sources",
        "leak_evidence": "Industry studies 2024–2026 + entity strength correlation",
        "recommendation": "Усиль цитируемость: Wikipedia/Wikidata mentions, press, structured facts, llms.txt. Проверь Citation Radar в SEO Lab.",
        "audit_triggers": ["EE24", "EE25", "EE26", "EE27"],
    },
    {
        "id": "LK-BOT-001",
        "document_id": "DOC-CW-2024",
        "name": "Crawl/index consistency",
        "category": "technical",
        "severity": "high",
        "leak_attributes": "indexing / forwarding dup modules",
        "google_public": "Googlebot should see same as users",
        "leak_evidence": "CompositeDoc / indexing modules in leak",
        "recommendation": "Исправь bot mismatch (SEO Lab): SSR для Nuxt, robots, canonical. Cloaking → manual action risk.",
        "audit_triggers": ["P01", "P02", "P03", "P10", "P11"],
    },
    {
        "id": "LK-FRESH-001",
        "document_id": "DOC-CW-2024",
        "name": "Freshness for volatile queries",
        "category": "freshness",
        "severity": "medium",
        "leak_attributes": "freshness / date signals",
        "google_public": "Query deserves freshness",
        "leak_evidence": "Freshness attributes in warehouse docs",
        "recommendation": "Обновляй rates, fees, supported coins на pair pages. dateModified в schema + visible 'Last updated'.",
        "audit_triggers": ["C24", "C25", "YY09"],
    },
    {
        "id": "LK-TRIAL-001",
        "document_id": "DOC-TRIAL",
        "name": "Trial-validated click systems",
        "category": "user_signals",
        "severity": "high",
        "leak_attributes": "NavBoost (trial testimony)",
        "google_public": "Ranking is complex",
        "leak_evidence": "DOJ trial — Nayak on click-based systems since ~2005",
        "recommendation": "Приоритет P0: UX + honest snippets. Trial подтверждает — игнорировать engagement нельзя.",
        "audit_triggers": ["EE18", "YY02", "C12"],
    },
]


def _read_doc_file(filename: str) -> str:
    bundled = DOCS_DIR / filename
    if bundled.exists():
        return bundled.read_text(encoding="utf-8")
    return ""


def seed_leak_library(force: bool = False) -> dict[str, int]:
    """Populate leak_documents + leak_rules from bundled seed if empty."""
    with connect() as conn:
        count = conn.execute("SELECT COUNT(*) FROM leak_documents").fetchone()[0]
        if count and not force:
            return {"documents": count, "rules": _rule_count(conn), "seeded": False}

        if force:
            conn.execute("DELETE FROM leak_rules")
            conn.execute("DELETE FROM leak_documents")

        for doc in DOCUMENTS:
            content = _read_doc_file(doc["file"])
            conn.execute(
                """
                INSERT OR REPLACE INTO leak_documents
                (id, title, category, credibility, source_url, published, summary, content_md, file_name)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    doc["id"],
                    doc["title"],
                    doc["category"],
                    doc["credibility"],
                    doc["source_url"],
                    doc["published"],
                    doc["summary"],
                    content,
                    doc["file"],
                ),
            )

        for rule in LEAK_RULES:
            conn.execute(
                """
                INSERT OR REPLACE INTO leak_rules
                (id, document_id, name, category, severity, leak_attributes, google_public,
                 leak_evidence, recommendation, audit_triggers_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    rule["id"],
                    rule["document_id"],
                    rule["name"],
                    rule["category"],
                    rule["severity"],
                    rule["leak_attributes"],
                    rule["google_public"],
                    rule["leak_evidence"],
                    rule["recommendation"],
                    json.dumps(rule["audit_triggers"], ensure_ascii=False),
                ),
            )

        return {
            "documents": len(DOCUMENTS),
            "rules": len(LEAK_RULES),
            "seeded": True,
        }


def _rule_count(conn) -> int:
    return conn.execute("SELECT COUNT(*) FROM leak_rules").fetchone()[0]


def list_documents(category: str | None = None) -> list[dict[str, Any]]:
    with connect() as conn:
        if category:
            rows = conn.execute(
                "SELECT id, title, category, credibility, source_url, published, summary, file_name FROM leak_documents WHERE category = ? ORDER BY published DESC",
                (category,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT id, title, category, credibility, source_url, published, summary, file_name FROM leak_documents ORDER BY published DESC",
            ).fetchall()
        return [dict(r) for r in rows]


def get_document(doc_id: str) -> dict[str, Any] | None:
    with connect() as conn:
        row = conn.execute("SELECT * FROM leak_documents WHERE id = ?", (doc_id,)).fetchone()
        return dict(row) if row else None


def list_rules(category: str | None = None) -> list[dict[str, Any]]:
    with connect() as conn:
        if category:
            rows = conn.execute(
                "SELECT * FROM leak_rules WHERE category = ? ORDER BY severity, id",
                (category,),
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM leak_rules ORDER BY severity, id").fetchall()
        out = []
        for row in rows:
            item = dict(row)
            item["audit_triggers"] = json.loads(item.pop("audit_triggers_json") or "[]")
            out.append(item)
        return out


def get_rule(rule_id: str) -> dict[str, Any] | None:
    with connect() as conn:
        row = conn.execute("SELECT * FROM leak_rules WHERE id = ?", (rule_id,)).fetchone()
        if not row:
            return None
        item = dict(row)
        item["audit_triggers"] = json.loads(item.pop("audit_triggers_json") or "[]")
        return item


def library_stats() -> dict[str, int]:
    with connect() as conn:
        docs = conn.execute("SELECT COUNT(*) FROM leak_documents").fetchone()[0]
        rules = conn.execute("SELECT COUNT(*) FROM leak_rules").fetchone()[0]
        cats = conn.execute("SELECT COUNT(DISTINCT category) FROM leak_rules").fetchone()[0]
        return {"documents": docs, "rules": rules, "categories": cats}


CREDIBILITY_LABELS = {
    "google_confirmed": "Google confirmed",
    "leak_plus_trial": "Leak + trial",
    "leak_reported": "Leak (analyst)",
    "leak_plus_official": "Leak + QRG official",
    "official_testimony": "Court testimony",
}

CATEGORY_LABELS = {
    "api_leak": "API leak",
    "ranking_system": "Ranking system",
    "user_signals": "User signals",
    "site_signals": "Site authority",
    "quality_filters": "Quality / demotion",
    "court_record": "Court record",
    "link_graph": "Links",
    "ux": "UX / Navigation",
    "content_quality": "Content quality",
    "ymyl": "YMYL",
    "eeat": "E-E-A-T",
    "entity": "Entity",
    "geo": "AI / GEO",
    "technical": "Technical",
    "freshness": "Freshness",
}


def render_doc_html(md: str) -> str:
    """Reuse specialist sources renderer."""
    from app.specialist_catalog import render_sources_html

    return render_sources_html(md)
