"""E-E-A-T document library — official sources, Quickex legal, forums & reputation."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

from app.config_loader import DATA_DIR
from app.storage import connect


def _eeat_dir() -> Path:
    from app.config_loader import DATA_DIR as data_dir

    return data_dir / "eeat-library"


def _docs_dir() -> Path:
    return _eeat_dir() / "docs"


EEAT_DIR = DATA_DIR / "eeat-library"
DOCS_DIR = EEAT_DIR / "docs"

TIER_LABELS = {
    "T1_official": "Google / регуляторы",
    "T1_site": "Quickex (официально)",
    "T2_authoritative": "Отраслевые гайды",
    "T3_ugc": "Отзывы / каталоги",
    "T3_forum": "Форумы",
}

CATEGORY_LABELS = {
    "google": "Google",
    "regulator": "Регуляторы",
    "quickex_official": "Quickex",
    "industry": "Индустрия",
    "reputation": "Репутация",
    "forum": "Форумы",
}

SUPPORTS_LABELS = {
    "positive": "✅ Поддерживает",
    "negative": "⚠️ Риск",
    "mixed": "〰️ Смешанно",
    "neutral": "— Нейтрально",
}

PILLAR_LABELS = {"E": "Experience", "X": "Expertise", "A": "Authoritativeness", "T": "Trust"}

# tier: T1_official | T1_site | T2_authoritative | T3_ugc | T3_forum
DOCUMENTS: list[dict[str, Any]] = [
    # ── Google official ──
    {
        "id": "EEAT-G-QRG",
        "title": "Google Search Quality Rater Guidelines (Sep 2025)",
        "tier": "T1_official",
        "doc_type": "google_guideline",
        "source_id": "G-QRG",
        "category": "google",
        "credibility": "official",
        "source_url": "https://static.googleusercontent.com/media/guidelines.raterhub.com/en//searchqualityevaluatorguidelines.pdf",
        "published": "2025-09-11",
        "publisher": "Google",
        "language": "en",
        "eeat_pillar": "T",
        "criteria_ids": ["EE06", "EE11", "EE17", "EE18", "EE20"],
        "relevance_score": 5,
        "supports_brand": "neutral",
        "summary": "182-стр. руководство для quality raters. Trust — центр E-E-A-T; YMYL finance требует высокий PQ; сент. 2025 — AI Overviews + расширение YMYL Society.",
        "file": "google-qrg-2025.md",
    },
    {
        "id": "EEAT-G-HC",
        "title": "Creating helpful, reliable, people-first content",
        "tier": "T1_official",
        "doc_type": "google_guideline",
        "source_id": "G-HC",
        "category": "google",
        "credibility": "official",
        "source_url": "https://developers.google.com/search/docs/fundamentals/creating-helpful-content",
        "published": "2024-01-01",
        "publisher": "Google Search Central",
        "language": "en",
        "eeat_pillar": "T",
        "criteria_ids": ["EE04", "EE10", "EE23"],
        "relevance_score": 5,
        "supports_brand": "neutral",
        "summary": "Официальный гайд Google: people-first контент, E-E-A-T, избегать scaled/thin content на YMYL.",
        "file": "google-helpful-content.md",
    },
    {
        "id": "EEAT-G-SPAM",
        "title": "Spam policies for Google web search",
        "tier": "T1_official",
        "doc_type": "google_guideline",
        "source_id": "G-SPAM",
        "category": "google",
        "credibility": "official",
        "source_url": "https://developers.google.com/search/docs/essentials/spam-policies",
        "published": "2024-01-01",
        "publisher": "Google",
        "language": "en",
        "eeat_pillar": "T",
        "criteria_ids": ["EE09", "EE23", "EE25"],
        "relevance_score": 4,
        "supports_brand": "neutral",
        "summary": "Misleading claims, fake reviews, scaled content — прямо релевантно crypto overclaim («100% anonymous», guaranteed returns).",
        "file": "google-spam-policies.md",
    },
    {
        "id": "EEAT-G-ORG",
        "title": "Organization structured data",
        "tier": "T1_official",
        "doc_type": "google_guideline",
        "source_id": "G-ORG",
        "category": "google",
        "credibility": "official",
        "source_url": "https://developers.google.com/search/docs/appearance/structured-data/organization",
        "published": "2024-01-01",
        "publisher": "Google",
        "language": "en",
        "eeat_pillar": "A",
        "criteria_ids": ["EE11", "EE12", "EE15"],
        "relevance_score": 4,
        "supports_brand": "neutral",
        "summary": "Organization JSON-LD: name, url, logo, sameAs — entity signals для Authoritativeness.",
        "file": "google-organization-sd.md",
    },
    {
        "id": "EEAT-G-RAT",
        "title": "Review snippet structured data policies",
        "tier": "T1_official",
        "doc_type": "google_guideline",
        "source_id": "G-RAT",
        "category": "google",
        "credibility": "official",
        "source_url": "https://developers.google.com/search/docs/appearance/structured-data/review-snippet",
        "published": "2024-01-01",
        "publisher": "Google",
        "language": "en",
        "eeat_pillar": "T",
        "criteria_ids": ["EE25", "EE05"],
        "relevance_score": 4,
        "supports_brand": "neutral",
        "summary": "AggregateRating только при реальных отзывах; self-serving reviews = spam.",
        "file": "google-review-snippet.md",
    },
    # ── Regulators ──
    {
        "id": "EEAT-R-FATF",
        "title": "FATF Virtual Assets Guidance",
        "tier": "T1_official",
        "doc_type": "regulation",
        "source_id": "R-FATF",
        "category": "regulator",
        "credibility": "official",
        "source_url": "https://www.fatf-gafi.org/en/topics/virtual-assets.html",
        "published": "2023-06-01",
        "publisher": "FATF",
        "language": "en",
        "eeat_pillar": "T",
        "criteria_ids": ["EE18", "EE20", "EE24", "YY04"],
        "relevance_score": 5,
        "supports_brand": "neutral",
        "summary": "Travel Rule, AML/KYC для VASPs — обосновывает AML-политику Quickex и риск freeze на privacy-парах.",
        "file": "fatf-virtual-assets.md",
    },
    {
        "id": "EEAT-R-SEC",
        "title": "SEC Crypto Assets hub",
        "tier": "T1_official",
        "doc_type": "regulation",
        "source_id": "R-SEC-CRYPTO",
        "category": "regulator",
        "credibility": "official",
        "source_url": "https://www.sec.gov/crypto",
        "published": "2024-01-01",
        "publisher": "U.S. SEC",
        "language": "en",
        "eeat_pillar": "T",
        "criteria_ids": ["EE20", "EE23", "YY02"],
        "relevance_score": 4,
        "supports_brand": "neutral",
        "summary": "Investor alerts: crypto scams, unregistered offerings — bar для финансовых claims на сайте.",
        "file": "sec-crypto-hub.md",
    },
    {
        "id": "EEAT-R-FTC",
        "title": "FTC — What to know about cryptocurrency and scams",
        "tier": "T1_official",
        "doc_type": "regulation",
        "source_id": "R-FTC",
        "category": "regulator",
        "credibility": "official",
        "source_url": "https://consumer.ftc.gov/articles/what-know-about-cryptocurrency-and-scams",
        "published": "2024-01-01",
        "publisher": "U.S. FTC",
        "language": "en",
        "eeat_pillar": "T",
        "criteria_ids": ["EE20", "EE23", "YY02"],
        "relevance_score": 4,
        "supports_brand": "neutral",
        "summary": "Паттерны crypto-scam для потребителей — контраст с маркетингом «no KYC / anonymous».",
        "file": "ftc-crypto-scams.md",
    },
    {
        "id": "EEAT-R-MICA",
        "title": "EU MiCA — Crypto-assets regulation",
        "tier": "T1_official",
        "doc_type": "regulation",
        "source_id": "R-MICA",
        "category": "regulator",
        "credibility": "official",
        "source_url": "https://finance.ec.europa.eu/regulation-and-supervision/fintech/crypto-assets_en",
        "published": "2024-06-01",
        "publisher": "European Commission",
        "language": "en",
        "eeat_pillar": "T",
        "criteria_ids": ["EE24", "YY04", "YY20"],
        "relevance_score": 4,
        "supports_brand": "neutral",
        "summary": "EU licensing для CASP — релевантно GDPR/cookie и claims о EU compliance.",
        "file": "eu-mica.md",
    },
    # ── Quickex official (site) ──
    {
        "id": "EEAT-QX-PRIVACY",
        "title": "Quickex Privacy Policy",
        "tier": "T1_site",
        "doc_type": "legal_page",
        "source_id": "QX-LEGAL",
        "category": "quickex_official",
        "credibility": "primary_source",
        "source_url": "https://quickex.io/docs/privacy-policy",
        "published": "2025-01-01",
        "publisher": "Quickex",
        "language": "en",
        "eeat_pillar": "T",
        "criteria_ids": ["EE18", "EE24", "EE21"],
        "relevance_score": 5,
        "supports_brand": "positive",
        "summary": "Сбор KYC/AML данных, шифрование, права пользователя, ссылка на Terms. Подтверждает EE18.",
        "file": "quickex-privacy-policy.md",
    },
    {
        "id": "EEAT-QX-TERMS",
        "title": "Quickex Terms of Use",
        "tier": "T1_site",
        "doc_type": "legal_page",
        "source_id": "QX-LEGAL",
        "category": "quickex_official",
        "credibility": "primary_source",
        "source_url": "https://quickex.io/docs/terms-of-use",
        "published": "2025-01-01",
        "publisher": "Quickex",
        "language": "en",
        "eeat_pillar": "T",
        "criteria_ids": ["EE19", "EE20", "EE26", "YY05"],
        "relevance_score": 5,
        "supports_brand": "neutral",
        "summary": "AML/KYC задержки, third-party liquidity providers, отказ от гарантий — важно для EE20 и маркетинг-parity.",
        "file": "quickex-terms-of-use.md",
    },
    {
        "id": "EEAT-QX-AML",
        "title": "Quickex AML / KYC Policy",
        "tier": "T1_site",
        "doc_type": "legal_page",
        "source_id": "QX-LEGAL",
        "category": "quickex_official",
        "credibility": "primary_source",
        "source_url": "https://quickex.io/docs/aml-policy",
        "published": "2025-01-01",
        "publisher": "Quickex",
        "language": "en",
        "eeat_pillar": "T",
        "criteria_ids": ["EE20", "EE23", "YY04", "YY05"],
        "relevance_score": 5,
        "supports_brand": "neutral",
        "summary": "5AMLD, freeze high-risk txs, full KYC для refund, mixer flags — ключевой документ для privacy-пар trust gap.",
        "file": "quickex-aml-policy.md",
    },
    {
        "id": "EEAT-QX-BLOG-AML",
        "title": "Quickex Blog — What is an AML Check",
        "tier": "T1_site",
        "doc_type": "editorial",
        "source_id": "QX-BLOG",
        "category": "quickex_official",
        "credibility": "primary_source",
        "source_url": "https://quickex.io/blog/guide/what-is-an-anti-money-laundering-aml-check",
        "published": "2025-01-01",
        "publisher": "Quickex",
        "language": "en",
        "eeat_pillar": "X",
        "criteria_ids": ["EE04", "EE08", "EE23"],
        "relevance_score": 3,
        "supports_brand": "positive",
        "summary": "Объясняет AML для пользователей; упоминает BTC→XMR и право запросить verification — expertise + transparency.",
        "file": "quickex-blog-aml-guide.md",
    },
    {
        "id": "EEAT-QX-HOME",
        "title": "Quickex Homepage — trust claims",
        "tier": "T1_site",
        "doc_type": "marketing",
        "source_id": "QX-SITE",
        "category": "quickex_official",
        "credibility": "primary_source",
        "source_url": "https://quickex.io/",
        "published": "2026-01-01",
        "publisher": "Quickex",
        "language": "en",
        "eeat_pillar": "T",
        "criteria_ids": ["EE01", "EE17", "EE22", "EE23"],
        "relevance_score": 4,
        "supports_brand": "neutral",
        "summary": "«Non-custodial since 2018», how-it-works, privacy/security claims — baseline для проверки overclaim.",
        "file": "quickex-homepage-trust.md",
    },
    # ── Industry ──
    {
        "id": "EEAT-I-CRAWLUX",
        "title": "Crypto E-E-A-T & YMYL 2026 (Crawlux)",
        "tier": "T2_authoritative",
        "doc_type": "industry_guide",
        "source_id": "I-CRAWLUX",
        "category": "industry",
        "credibility": "industry_analysis",
        "source_url": "https://www.crawlux.com/guides/eeat-ymyl-crypto/",
        "published": "2026-01-01",
        "publisher": "Crawlux",
        "language": "en",
        "eeat_pillar": "T",
        "criteria_ids": ["EE17", "EE22", "EE26", "EE28"],
        "relevance_score": 3,
        "supports_brand": "neutral",
        "summary": "Операционный чеклист trust signals для crypto exchanges (не официальный Google).",
        "file": "industry-crawlux-eeat.md",
    },
    {
        "id": "EEAT-I-GUIDEX",
        "title": "Google QRG Explained — Sep 2025 (GuideX)",
        "tier": "T2_authoritative",
        "doc_type": "industry_guide",
        "source_id": "I-GUIDEX",
        "category": "industry",
        "credibility": "industry_analysis",
        "source_url": "https://theguidex.com/insights/google-quality-rater-guidelines",
        "published": "2025-09-15",
        "publisher": "GuideX",
        "language": "en",
        "eeat_pillar": "T",
        "criteria_ids": ["EE06", "EE11", "EE17"],
        "relevance_score": 3,
        "supports_brand": "neutral",
        "summary": "Разбор Sep 2025 QRG: Trust foundation, YMYL finance, AI Overview rating.",
        "file": "industry-guidex-qrg.md",
    },
    # ── Reputation UGC ──
    {
        "id": "EEAT-W-TRUSTPILOT",
        "title": "Trustpilot — quickex.io reviews",
        "tier": "T3_ugc",
        "doc_type": "review_platform",
        "source_id": "W-TRUSTPILOT",
        "category": "reputation",
        "credibility": "ugc_verified",
        "source_url": "https://www.trustpilot.com/review/quickex.io",
        "published": "2026-03-15",
        "publisher": "Trustpilot",
        "language": "en",
        "eeat_pillar": "A",
        "criteria_ids": ["EE05", "EE14", "EE16"],
        "relevance_score": 4,
        "supports_brand": "mixed",
        "summary": "~4.5–4.6★, 52–57 отзывов. Позитив: скорость, UI. Негатив: AML freeze, KYC на privacy-парах, refund −5%.",
        "file": "reputation-trustpilot.md",
    },
    {
        "id": "EEAT-W-BESTCHANGE",
        "title": "BestChange — Quickex monitor status",
        "tier": "T3_ugc",
        "doc_type": "review_platform",
        "source_id": "W-BESTCHANGE",
        "category": "reputation",
        "credibility": "ugc_monitor",
        "source_url": "https://www.bestchange.com/quickex-exchanger.html",
        "published": "2024-06-23",
        "publisher": "BestChange",
        "language": "ru",
        "eeat_pillar": "A",
        "criteria_ids": ["EE14", "EE15", "YY04"],
        "relevance_score": 5,
        "supports_brand": "negative",
        "summary": "DELISTED 23.06.2024. 445 отзывов, 36 financial claims. Критичный reputation signal для EEAT-A.",
        "file": "reputation-bestchange.md",
    },
    {
        "id": "EEAT-W-CRYPTORADAR",
        "title": "Cryptoradar — Quickex exchange profile",
        "tier": "T3_ugc",
        "doc_type": "review_platform",
        "source_id": "W-CRYPTORADAR",
        "category": "reputation",
        "credibility": "ugc_aggregator",
        "source_url": "https://cryptoradar.com/exchanges/quickex",
        "published": "2026-01-01",
        "publisher": "Cryptoradar",
        "language": "en",
        "eeat_pillar": "A",
        "criteria_ids": ["EE05", "EE13", "EE14"],
        "relevance_score": 3,
        "supports_brand": "positive",
        "summary": "4.7/5, 16 ratings. Based in Seychelles. В основном позитивные отзывы о скорости и rates.",
        "file": "reputation-cryptoradar.md",
    },
    {
        "id": "EEAT-W-HACKERNOON",
        "title": "HackerNoon — Quickex Review 2026",
        "tier": "T3_ugc",
        "doc_type": "press",
        "source_id": "W-PRESS",
        "category": "reputation",
        "credibility": "editorial_sponsored",
        "source_url": "https://hackernoon.com/quickex-review-2026-instant-crypto-swaps-and-fiat-cashouts-without-kyc",
        "published": "2026-01-01",
        "publisher": "HackerNoon",
        "language": "en",
        "eeat_pillar": "A",
        "criteria_ids": ["EE09", "EE14", "EE23"],
        "relevance_score": 2,
        "supports_brand": "positive",
        "summary": "Sponsored/editorial: no-KYC since 2018, 5–20 min swaps. Проверить independence для EE14.",
        "file": "reputation-hackernoon-2026.md",
    },
    {
        "id": "EEAT-W-BLOCKSPOT",
        "title": "Blockspot — Quickex exchange info",
        "tier": "T3_ugc",
        "doc_type": "entity_listing",
        "source_id": "W-BLOCKSPOT",
        "category": "reputation",
        "credibility": "directory",
        "source_url": "https://blockspot.io/exchange/quickex/",
        "published": "2025-01-01",
        "publisher": "Blockspot",
        "language": "en",
        "eeat_pillar": "A",
        "criteria_ids": ["EE13", "EE15", "EE16"],
        "relevance_score": 3,
        "supports_brand": "neutral",
        "summary": "Panama jurisdiction, Bitcointalk link, non-custodial since 2018 — entity footprint (NAP check needed).",
        "file": "reputation-blockspot.md",
    },
    # ── Forums ──
    {
        "id": "EEAT-F-BCT-ANN",
        "title": "Bitcointalk — Quickex announcement thread",
        "tier": "T3_forum",
        "doc_type": "forum",
        "source_id": "W-BCT",
        "category": "forum",
        "credibility": "community_official",
        "source_url": "https://bitcointalk.org/index.php?topic=5503896.0",
        "published": "2018-01-01",
        "publisher": "Bitcointalk",
        "language": "en",
        "eeat_pillar": "A",
        "criteria_ids": ["EE14", "EE21"],
        "relevance_score": 4,
        "supports_brand": "positive",
        "summary": "Официальный ANN с 2018, 2400+ replies, активный rep Quickex Exchange — long-term entity signal.",
        "file": "forum-bitcointalk-ann.md",
    },
    {
        "id": "EEAT-F-BCT-SCAM",
        "title": "Bitcointalk — 9.5 ETH blocked / scam accusation",
        "tier": "T3_forum",
        "doc_type": "forum",
        "source_id": "W-BCT",
        "category": "forum",
        "credibility": "ugc_accusation",
        "source_url": "https://bitcointalk.org/index.php?topic=5577804.0",
        "published": "2025-10-01",
        "publisher": "Bitcointalk",
        "language": "en",
        "eeat_pillar": "T",
        "criteria_ids": ["EE20", "EE23", "YY04", "YY05"],
        "relevance_score": 5,
        "supports_brand": "negative",
        "summary": "9.5 ETH frozen — SwissBorg hack linkage, liquidity provider flag. Rep ответил с AMLbot/Crystal refs.",
        "file": "forum-bitcointalk-scam-eth.md",
    },
    # ── Schema.org ──
    {
        "id": "EEAT-S-ORG",
        "title": "Schema.org — Organization",
        "tier": "T1_official",
        "doc_type": "schema",
        "source_id": "S-ORG",
        "category": "google",
        "credibility": "official",
        "source_url": "https://schema.org/Organization",
        "published": "2024-01-01",
        "publisher": "Schema.org",
        "language": "en",
        "eeat_pillar": "A",
        "criteria_ids": ["EE11", "EE12", "EE15"],
        "relevance_score": 4,
        "supports_brand": "neutral",
        "summary": "Organization: name, url, logo, sameAs, contactPoint — entity signals для Authoritativeness.",
        "file": "schema-organization.md",
    },
    {
        "id": "EEAT-S-FS",
        "title": "Schema.org — FinancialService",
        "tier": "T1_official",
        "doc_type": "schema",
        "source_id": "S-FS",
        "category": "google",
        "credibility": "official",
        "source_url": "https://schema.org/FinancialService",
        "published": "2024-01-01",
        "publisher": "Schema.org",
        "language": "en",
        "eeat_pillar": "T",
        "criteria_ids": ["EE26", "YY26"],
        "relevance_score": 3,
        "supports_brand": "neutral",
        "summary": "FinancialService schema для crypto exchange — fees, areaServed, provider.",
        "file": "schema-financial-service.md",
    },
    # ── More regulators ──
    {
        "id": "EEAT-R-FINCEN",
        "title": "FinCEN MSB Registrant Search",
        "tier": "T1_official",
        "doc_type": "regulation",
        "source_id": "R-FINCEN",
        "category": "regulator",
        "credibility": "official",
        "source_url": "https://www.fincen.gov/msb-registrant-search",
        "published": "2024-01-01",
        "publisher": "FinCEN",
        "language": "en",
        "eeat_pillar": "T",
        "criteria_ids": ["EE13", "EE24", "YY04"],
        "relevance_score": 4,
        "supports_brand": "neutral",
        "summary": "Проверка US MSB registration — если Quickex заявляет MSB, должен быть в реестре.",
        "file": "fincen-msb-search.md",
    },
    {
        "id": "EEAT-R-FCA",
        "title": "FCA Cryptoasset Register (UK)",
        "tier": "T1_official",
        "doc_type": "regulation",
        "source_id": "R-FCA",
        "category": "regulator",
        "credibility": "official",
        "source_url": "https://register.fca.org.uk/s/search",
        "published": "2024-01-01",
        "publisher": "FCA",
        "language": "en",
        "eeat_pillar": "T",
        "criteria_ids": ["EE13", "EE24"],
        "relevance_score": 3,
        "supports_brand": "neutral",
        "summary": "UK authorization claims — проверить наличие Quickex в FCA register.",
        "file": "fca-crypto-register.md",
    },
    {
        "id": "EEAT-R-CFTC",
        "title": "CFTC Virtual Currency Resources",
        "tier": "T1_official",
        "doc_type": "regulation",
        "source_id": "R-CFTC",
        "category": "regulator",
        "credibility": "official",
        "source_url": "https://www.cftc.gov/digitalassets/index.htm",
        "published": "2024-01-01",
        "publisher": "CFTC",
        "language": "en",
        "eeat_pillar": "T",
        "criteria_ids": ["EE20", "YY02"],
        "relevance_score": 3,
        "supports_brand": "neutral",
        "summary": "Commodity fraud alerts — bar для финансовых claims на US audience.",
        "file": "cftc-digital-assets.md",
    },
    {
        "id": "EEAT-G-AI",
        "title": "Google AI-generated content guidance",
        "tier": "T1_official",
        "doc_type": "google_guideline",
        "source_id": "G-AI",
        "category": "google",
        "credibility": "official",
        "source_url": "https://developers.google.com/search/docs/fundamentals/creating-helpful-content",
        "published": "2024-01-01",
        "publisher": "Google",
        "language": "en",
        "eeat_pillar": "T",
        "criteria_ids": ["EE08", "EE09", "EE10"],
        "relevance_score": 4,
        "supports_brand": "neutral",
        "summary": "AI content на YMYL — требует human review, author attribution, fact-checking.",
        "file": "google-ai-content.md",
    },
    {
        "id": "EEAT-G-SG",
        "title": "Google structured data general guidelines",
        "tier": "T1_official",
        "doc_type": "google_guideline",
        "source_id": "G-SG",
        "category": "google",
        "credibility": "official",
        "source_url": "https://developers.google.com/search/docs/appearance/structured-data/sd-policies",
        "published": "2024-01-01",
        "publisher": "Google",
        "language": "en",
        "eeat_pillar": "A",
        "criteria_ids": ["EE11", "EE25"],
        "relevance_score": 4,
        "supports_brand": "neutral",
        "summary": "Schema abuse policies — required fields, no misleading markup.",
        "file": "google-structured-data.md",
    },
    # ── Entity footprint ──
    {
        "id": "EEAT-W-LINKEDIN",
        "title": "LinkedIn — Quickex company page",
        "tier": "T3_ugc",
        "doc_type": "entity",
        "source_id": "W-LINKEDIN",
        "category": "reputation",
        "credibility": "directory",
        "source_url": "https://www.linkedin.com/company/quickex/",
        "published": "2026-01-01",
        "publisher": "LinkedIn",
        "language": "en",
        "eeat_pillar": "A",
        "criteria_ids": ["EE13", "EE15", "EE16"],
        "relevance_score": 3,
        "supports_brand": "neutral",
        "summary": "Entity footprint: team, HQ, founded — NAP consistency check vs About/footer.",
        "file": "entity-linkedin.md",
    },
    {
        "id": "EEAT-W-CRUNCHBASE",
        "title": "Crunchbase — Quickex profile",
        "tier": "T3_ugc",
        "doc_type": "entity",
        "source_id": "W-CRUNCH",
        "category": "reputation",
        "credibility": "directory",
        "source_url": "https://www.crunchbase.com/organization/quickex",
        "published": "2026-01-01",
        "publisher": "Crunchbase",
        "language": "en",
        "eeat_pillar": "A",
        "criteria_ids": ["EE13", "EE14"],
        "relevance_score": 2,
        "supports_brand": "neutral",
        "summary": "Funding, founding date, HQ — triangulate с LinkedIn и legal pages.",
        "file": "entity-crunchbase.md",
    },
    {
        "id": "EEAT-W-REDDIT",
        "title": "Reddit — Quickex mentions (r/cryptocurrency)",
        "tier": "T3_forum",
        "doc_type": "forum",
        "source_id": "W-REDDIT",
        "category": "forum",
        "credibility": "ugc",
        "source_url": "https://www.reddit.com/search/?q=quickex.io",
        "published": "2026-01-01",
        "publisher": "Reddit",
        "language": "en",
        "eeat_pillar": "A",
        "criteria_ids": ["EE05", "EE14"],
        "relevance_score": 3,
        "supports_brand": "mixed",
        "summary": "UGC sentiment triangulation — scam accusations, speed praise, AML complaints.",
        "file": "forum-reddit-quickex.md",
    },
    # ── Competitor trust benchmark ──
    {
        "id": "EEAT-C-CHANGENOW",
        "title": "ChangeNOW — trust & legal pages benchmark",
        "tier": "T2_authoritative",
        "doc_type": "competitor",
        "source_id": "C-CHANGENOW",
        "category": "industry",
        "credibility": "competitor",
        "source_url": "https://changenow.io/terms-of-use",
        "published": "2026-01-01",
        "publisher": "ChangeNOW",
        "language": "en",
        "eeat_pillar": "T",
        "criteria_ids": ["EE17", "EE18", "EE20"],
        "relevance_score": 3,
        "supports_brand": "neutral",
        "summary": "Benchmark: AML/KYC disclosure, risk disclaimer, entity info — сравнить с Quickex.",
        "file": "competitor-changenow-trust.md",
    },
    {
        "id": "EEAT-C-CHANGELLY",
        "title": "Changelly — trust & legal pages benchmark",
        "tier": "T2_authoritative",
        "doc_type": "competitor",
        "source_id": "C-CHANGELLY",
        "category": "industry",
        "credibility": "competitor",
        "source_url": "https://changelly.com/terms-of-use",
        "published": "2026-01-01",
        "publisher": "Changelly",
        "language": "en",
        "eeat_pillar": "T",
        "criteria_ids": ["EE17", "EE18", "EE20"],
        "relevance_score": 3,
        "supports_brand": "neutral",
        "summary": "Benchmark: legal stack, KYC policy, security page — trust gap analysis.",
        "file": "competitor-changelly-trust.md",
    },
]

INSIGHTS: list[dict[str, Any]] = [
    {
        "id": "INS-TRUST-001",
        "document_id": "EEAT-G-QRG",
        "title": "Trust — центр E-E-A-T (QRG §3.4)",
        "severity": "critical",
        "eeat_pillar": "T",
        "criteria_ids": ["EE17", "EE18", "EE19", "EE20"],
        "recommendation": "Приоритет legal stack: Privacy + Terms + AML на видном месте; risk disclaimer на money pages; синхронизировать маркетинг «no KYC» с AML policy.",
    },
    {
        "id": "INS-QX-AML-001",
        "document_id": "EEAT-QX-AML",
        "title": "AML freeze на privacy-парах — policy vs marketing gap",
        "severity": "critical",
        "eeat_pillar": "T",
        "criteria_ids": ["EE20", "EE23", "YY04"],
        "recommendation": "На XMR/ZEC/DASH pages: явный disclaimer «AML check may apply» + ссылка на /docs/aml-policy до отправки средств. Убрать «100% anonymous» из meta.",
    },
    {
        "id": "INS-BC-DELIST",
        "document_id": "EEAT-W-BESTCHANGE",
        "title": "BestChange delist Jun 2024 — reputation red flag",
        "severity": "high",
        "eeat_pillar": "A",
        "criteria_ids": ["EE14", "EE15"],
        "recommendation": "Подготовить press/trust page с объяснением статуса; мониторить claims; рассмотреть re-listing через compliance audit.",
    },
    {
        "id": "INS-TP-MIXED",
        "document_id": "EEAT-W-TRUSTPILOT",
        "title": "Trustpilot mixed — отвечать на negative 66%",
        "severity": "medium",
        "eeat_pillar": "A",
        "criteria_ids": ["EE05", "EE14", "EE21"],
        "recommendation": "Публиковать ответы с ссылками на AML policy; не использовать AggregateRating schema без верификации источника.",
    },
    {
        "id": "INS-BCT-ENTITY",
        "document_id": "EEAT-F-BCT-ANN",
        "title": "Bitcointalk ANN since 2018 — positive entity longevity",
        "severity": "low",
        "eeat_pillar": "A",
        "criteria_ids": ["EE13", "EE14"],
        "recommendation": "Ссылаться на Bitcointalk ANN в About; поддерживать активность rep — сигнал для «what others say» (QRG).",
    },
    {
        "id": "INS-JURISDICTION",
        "document_id": "EEAT-W-BLOCKSPOT",
        "title": "Jurisdiction inconsistency (Seychelles vs Panama)",
        "severity": "high",
        "eeat_pillar": "A",
        "criteria_ids": ["EE13", "EE15"],
        "recommendation": "Унифицировать legal entity + country в About, footer, Organization schema, Crunchbase/LinkedIn.",
    },
    {
        "id": "INS-FATF-AML",
        "document_id": "EEAT-R-FATF",
        "title": "FATF Travel Rule — обоснование KYC на VASP",
        "severity": "high",
        "eeat_pillar": "T",
        "criteria_ids": ["EE18", "EE24", "YY04"],
        "recommendation": "В AML policy и FAQ сослаться на FATF/5AMLD framework — усиливает EE20 trust для регуляторно-осведомлённых пользователей.",
    },
]


def _read_doc_file(filename: str) -> str:
    path = _docs_dir() / filename
    if path.exists():
        return path.read_text(encoding="utf-8")
    return ""


def seed_eeat_library(force: bool = False) -> dict[str, int]:
    with connect() as conn:
        count = conn.execute("SELECT COUNT(*) FROM eeat_documents").fetchone()[0]
        if count and not force:
            return {
                "documents": count,
                "insights": _insight_count(conn),
                "seeded": False,
            }

        if force:
            conn.execute("DELETE FROM eeat_insights WHERE id NOT LIKE 'INS-AI-%'")
            conn.execute(
                "DELETE FROM eeat_documents WHERE COALESCE(origin, 'seed') = 'seed'",
            )

        for doc in DOCUMENTS:
            content = _read_doc_file(doc["file"])
            conn.execute(
                """
                INSERT OR REPLACE INTO eeat_documents
                (id, title, tier, doc_type, source_id, category, credibility, source_url,
                 published, publisher, language, eeat_pillar, criteria_ids_json,
                 relevance_score, supports_brand, summary, content_md, file_name,
                 origin, verification, accessed_date)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'seed', 'verified_url', ?)
                """,
                (
                    doc["id"],
                    doc["title"],
                    doc["tier"],
                    doc["doc_type"],
                    doc["source_id"],
                    doc["category"],
                    doc["credibility"],
                    doc["source_url"],
                    doc["published"],
                    doc["publisher"],
                    doc.get("language", "en"),
                    doc["eeat_pillar"],
                    json.dumps(doc["criteria_ids"], ensure_ascii=False),
                    doc["relevance_score"],
                    doc["supports_brand"],
                    doc["summary"],
                    content,
                    doc["file"],
                    date.today().isoformat(),
                ),
            )

        for ins in INSIGHTS:
            conn.execute(
                """
                INSERT OR REPLACE INTO eeat_insights
                (id, document_id, title, severity, eeat_pillar, criteria_ids_json, recommendation)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    ins["id"],
                    ins["document_id"],
                    ins["title"],
                    ins["severity"],
                    ins["eeat_pillar"],
                    json.dumps(ins["criteria_ids"], ensure_ascii=False),
                    ins["recommendation"],
                ),
            )

        return {
            "documents": len(DOCUMENTS),
            "insights": len(INSIGHTS),
            "seeded": True,
        }


def _insight_count(conn) -> int:
    return conn.execute("SELECT COUNT(*) FROM eeat_insights").fetchone()[0]


def library_stats() -> dict[str, int]:
    with connect() as conn:
        docs = conn.execute("SELECT COUNT(*) FROM eeat_documents").fetchone()[0]
        insights = conn.execute("SELECT COUNT(*) FROM eeat_insights").fetchone()[0]
        by_tier = {}
        for row in conn.execute(
            "SELECT tier, COUNT(*) AS c FROM eeat_documents GROUP BY tier",
        ).fetchall():
            by_tier[row["tier"]] = row["c"]
        return {"documents": docs, "insights": insights, "by_tier": by_tier}


def list_documents(
    category: str | None = None,
    tier: str | None = None,
) -> list[dict[str, Any]]:
    with connect() as conn:
        q = "SELECT * FROM eeat_documents WHERE 1=1"
        params: list[Any] = []
        if category:
            q += " AND category = ?"
            params.append(category)
        if tier:
            q += " AND tier = ?"
            params.append(tier)
        q += " ORDER BY relevance_score DESC, published DESC"
        rows = conn.execute(q, params).fetchall()
        out = []
        for row in rows:
            item = dict(row)
            item["criteria_ids"] = json.loads(item.pop("criteria_ids_json") or "[]")
            out.append(item)
        return out


def get_document(doc_id: str) -> dict[str, Any] | None:
    with connect() as conn:
        row = conn.execute("SELECT * FROM eeat_documents WHERE id = ?", (doc_id,)).fetchone()
        if not row:
            return None
        item = dict(row)
        item["criteria_ids"] = json.loads(item.pop("criteria_ids_json") or "[]")
        return item


def list_insights() -> list[dict[str, Any]]:
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT i.*, d.title AS document_title, d.source_url AS document_url
            FROM eeat_insights i
            LEFT JOIN eeat_documents d ON d.id = i.document_id
            ORDER BY
              CASE i.severity WHEN 'critical' THEN 0 WHEN 'high' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END,
              i.id
            """,
        ).fetchall()
        out = []
        for row in rows:
            item = dict(row)
            item["criteria_ids"] = json.loads(item.pop("criteria_ids_json") or "[]")
            out.append(item)
        return out


def export_library_markdown() -> str:
    docs = list_documents()
    insights = list_insights()
    lines = [
        "# E-E-A-T Document Library — Quickex",
        "",
        f"Документов: {len(docs)} · Insights: {len(insights)}",
        "",
        "## Реестр документов",
        "",
        "| ID | Tier | Title | Pillar | Brand | URL |",
        "|----|------|-------|--------|-------|-----|",
    ]
    for d in docs:
        lines.append(
            f"| {d['id']} | {d['tier']} | {d['title']} | {d['eeat_pillar']} | {d['supports_brand']} | {d['source_url']} |"
        )
    lines.extend(["", "## Insights", ""])
    for i in insights:
        lines.append(f"### {i['id']} — {i['title']} ({i['severity']})")
        lines.append(f"**Критерии:** {', '.join(i['criteria_ids'])}")
        lines.append(f"**Рекомендация:** {i['recommendation']}")
        lines.append("")
    return "\n".join(lines)
