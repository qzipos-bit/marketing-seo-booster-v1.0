"""YMYL document library — harm prevention, regulators, scam signals, Quickex cases."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

from app.config_loader import DATA_DIR
from app.storage import connect


def _ymyl_dir() -> Path:
    from app.config_loader import DATA_DIR as data_dir

    return data_dir / "ymyl-library"


def _docs_dir() -> Path:
    return _ymyl_dir() / "docs"


YMYL_DIR = DATA_DIR / "ymyl-library"
DOCS_DIR = YMYL_DIR / "docs"

TIER_LABELS = {
    "T1_official": "Google / регуляторы",
    "T1_site": "Quickex (официально)",
    "T2_authoritative": "Отрасль / конкуренты",
    "T3_ugc": "Жалобы / мониторы",
    "T3_forum": "Форумы",
}

CATEGORY_LABELS = {
    "google": "Google YMYL",
    "regulator": "Регуляторы",
    "quickex_official": "Quickex legal",
    "industry": "Индустрия",
    "reputation": "User harm signals",
    "forum": "Форумы",
    "competitor": "Benchmark",
}

HARM_LABELS = {
    "financial_loss": "Потеря средств",
    "misleading_claim": "Вводящие claims",
    "regulatory_false": "Ложная регуляторика",
    "scam_phishing": "Scam / phishing",
    "aml_freeze": "AML freeze",
    "geo_sanctions": "Санкции / geo",
    "support_failure": "Support / refund",
    "volatility_risk": "Риск волатильности",
}

SUPPORTS_LABELS = {
    "mitigates_harm": "✅ Снижает вред",
    "increases_harm": "⚠️ Увеличивает вред",
    "mixed": "〰️ Смешанно",
    "neutral": "— Нейтрально",
}

BLOCK_LABELS = {
    "Y1": "Классификация YMYL",
    "Y2": "Предотвращение вреда",
    "Y3": "Точность",
    "Y4": "Регуляторика",
    "Y5": "Transactional trust",
}

DOCUMENTS: list[dict[str, Any]] = [
    # ── Google YMYL ──
    {
        "id": "YMYL-G-QRG-YMYL",
        "title": "Google QRG §2.3 — YMYL Financial Security",
        "tier": "T1_official",
        "doc_type": "google_guideline",
        "source_id": "G-QRG",
        "category": "google",
        "credibility": "official",
        "source_url": "https://static.googleusercontent.com/media/guidelines.raterhub.com/en//searchqualityevaluatorguidelines.pdf",
        "published": "2025-09-11",
        "publisher": "Google",
        "language": "en",
        "ymyl_block": "Y1",
        "harm_category": "financial_loss",
        "criteria_ids": ["YY01", "YY02", "YY04"],
        "relevance_score": 5,
        "supports_brand": "neutral",
        "summary": "Crypto exchange = YMYL Financial Security. Неточность на money pages → реальный финансовый вред пользователю. Highest PQ bar.",
        "file": "google-qrg-ymyl-section.md",
    },
    {
        "id": "YMYL-G-SPAM-CLAIMS",
        "title": "Google Spam Policies — misleading claims",
        "tier": "T1_official",
        "doc_type": "google_guideline",
        "source_id": "G-SPAM",
        "category": "google",
        "credibility": "official",
        "source_url": "https://developers.google.com/search/docs/essentials/spam-policies",
        "published": "2024-01-01",
        "publisher": "Google",
        "language": "en",
        "ymyl_block": "Y2",
        "harm_category": "misleading_claim",
        "criteria_ids": ["YY08", "YY12", "YY15"],
        "relevance_score": 5,
        "supports_brand": "neutral",
        "summary": "Guaranteed returns, risk-free profit, deceptive fees — прямой harm risk для crypto marketing.",
        "file": "google-spam-misleading.md",
    },
    # ── US Regulators ──
    {
        "id": "YMYL-R-SEC-BITCOIN",
        "title": "SEC — Bitcoin and Virtual Currency-Related Investments",
        "tier": "T1_official",
        "doc_type": "regulation",
        "source_id": "R-SEC",
        "category": "regulator",
        "credibility": "official",
        "source_url": "https://www.sec.gov/resources-for-investors/investor-alerts-bulletins/investoralertsia_bitcoin",
        "published": "2014-05-07",
        "publisher": "U.S. SEC",
        "language": "en",
        "ymyl_block": "Y2",
        "harm_category": "financial_loss",
        "criteria_ids": ["YY05", "YY06", "YY08"],
        "relevance_score": 5,
        "supports_brand": "neutral",
        "summary": "Bitcoin investments heightened fraud risk; limited recovery if stolen; volatility. Bar для risk disclaimers на exchange.",
        "file": "sec-bitcoin-investor-alert.md",
    },
    {
        "id": "YMYL-R-SEC-CRYPTO5",
        "title": "SEC — 5 Ways Fraudsters Lure Crypto Victims (2024)",
        "tier": "T1_official",
        "doc_type": "regulation",
        "source_id": "R-SEC-CRYPTO",
        "category": "regulator",
        "credibility": "official",
        "source_url": "https://www.sec.gov/oiea/investor-alert-5-ways-fraudsters-may-lure-victims-scams-involving-crypto-asset",
        "published": "2024-05-29",
        "publisher": "U.S. SEC OIEA",
        "language": "en",
        "ymyl_block": "Y2",
        "harm_category": "scam_phishing",
        "criteria_ids": ["YY08", "YY09", "YY19"],
        "relevance_score": 5,
        "supports_brand": "neutral",
        "summary": "Fraudsters exploit crypto popularity — social media, guaranteed returns. Anti-phishing block на сайте = mitigation (YY09).",
        "file": "sec-crypto-fraud-5ways.md",
    },
    {
        "id": "YMYL-R-SEC-PONZI",
        "title": "SEC — Ponzi Schemes Using Virtual Currencies",
        "tier": "T1_official",
        "doc_type": "regulation",
        "source_id": "R-SEC",
        "category": "regulator",
        "credibility": "official",
        "source_url": "https://www.sec.gov/investor/alerts/ia_virtualcurrencies.pdf",
        "published": "2013-01-01",
        "publisher": "U.S. SEC",
        "language": "en",
        "ymyl_block": "Y2",
        "harm_category": "misleading_claim",
        "criteria_ids": ["YY08", "YY19"],
        "relevance_score": 4,
        "supports_brand": "neutral",
        "summary": "High returns + little risk = Ponzi pattern. Exchanges must not mirror Ponzi-style marketing.",
        "file": "sec-ponzi-virtual-currency.md",
    },
    {
        "id": "YMYL-R-FTC-SCAMS",
        "title": "FTC — What to Know About Cryptocurrency and Scams",
        "tier": "T1_official",
        "doc_type": "regulation",
        "source_id": "R-FTC",
        "category": "regulator",
        "credibility": "official",
        "source_url": "https://consumer.ftc.gov/articles/what-know-about-cryptocurrency-and-scams",
        "published": "2024-01-01",
        "publisher": "U.S. FTC",
        "language": "en",
        "ymyl_block": "Y2",
        "harm_category": "scam_phishing",
        "criteria_ids": ["YY09", "YY19"],
        "relevance_score": 5,
        "supports_brand": "neutral",
        "summary": "Consumer harm patterns: impersonation, fake sites, investment scams. Verify official URL messaging.",
        "file": "ftc-crypto-scams.md",
    },
    {
        "id": "YMYL-R-CFTC-RISKS",
        "title": "CFTC — Understand the Risks of Virtual Currency Trading",
        "tier": "T1_official",
        "doc_type": "regulation",
        "source_id": "R-CFTC",
        "category": "regulator",
        "credibility": "official",
        "source_url": "https://www.cftc.gov/LearnAndProtect/AdvisoriesAndArticles/understand_risks_of_virtual_currency.html",
        "published": "2020-01-01",
        "publisher": "U.S. CFTC",
        "language": "en",
        "ymyl_block": "Y2",
        "harm_category": "volatility_risk",
        "criteria_ids": ["YY06", "YY07", "YY12"],
        "relevance_score": 5,
        "supports_brand": "neutral",
        "summary": "Bitcoin = commodity; cash markets unregulated; hacking/phishing; no assurance of recourse if stolen.",
        "file": "cftc-virtual-currency-risks.md",
    },
    {
        "id": "YMYL-R-CFTC-FRAUD-WEB",
        "title": "CFTC/SEC — Fraudulent Crypto Trading Websites",
        "tier": "T1_official",
        "doc_type": "regulation",
        "source_id": "R-CFTC",
        "category": "regulator",
        "credibility": "official",
        "source_url": "https://www.cftc.gov/LearnAndProtect/AdvisoriesAndArticles/watch_out_for_digital_fraud.html",
        "published": "2021-01-01",
        "publisher": "CFTC + SEC",
        "language": "en",
        "ymyl_block": "Y2",
        "harm_category": "scam_phishing",
        "criteria_ids": ["YY09", "YY19"],
        "relevance_score": 5,
        "supports_brand": "neutral",
        "summary": "Red flags: guaranteed 20–50% returns, little risk. Fake mirrors harm users — official domain verification critical.",
        "file": "cftc-fraudulent-websites.md",
    },
    # ── EU Regulators ──
    {
        "id": "YMYL-R-ESMA-2024",
        "title": "ESMA — Warning on Crypto-assets (Dec 2024)",
        "tier": "T1_official",
        "doc_type": "regulation",
        "source_id": "R-ESMA",
        "category": "regulator",
        "credibility": "official",
        "source_url": "https://www.esma.europa.eu/document/warning-crypto-assets",
        "published": "2024-12-13",
        "publisher": "ESMA",
        "language": "en",
        "ymyl_block": "Y2",
        "harm_category": "financial_loss",
        "criteria_ids": ["YY04", "YY06", "YY11"],
        "relevance_score": 5,
        "supports_brand": "neutral",
        "summary": "Crypto highly speculative — may lose all capital. Non-EU firms = lower safeguards, fraud risk, limited recourse.",
        "file": "esma-warning-2024.md",
    },
    {
        "id": "YMYL-R-ESMA-JOINT-2025",
        "title": "Joint ESAs — Revised Warning on Crypto-assets (Oct 2025)",
        "tier": "T1_official",
        "doc_type": "regulation",
        "source_id": "R-ESMA",
        "category": "regulator",
        "credibility": "official",
        "source_url": "https://www.esma.europa.eu/sites/default/files/2025-10/Joint_ESAs_revised_warning_on_crypto-assets.pdf",
        "published": "2025-10-06",
        "publisher": "ESAs (EBA, EIOPA, ESMA)",
        "language": "en",
        "ymyl_block": "Y4",
        "harm_category": "regulatory_false",
        "criteria_ids": ["YY17", "YY18", "YY11"],
        "relevance_score": 5,
        "supports_brand": "neutral",
        "summary": "Only MiCA-authorised firms on ESMA register. Transitional until Jul 2026 — no full protection. Verify EU claims.",
        "file": "esma-joint-warning-2025.md",
    },
    {
        "id": "YMYL-R-FATF-FREEZE",
        "title": "FATF — AML/CFT for Virtual Assets (freeze risk)",
        "tier": "T1_official",
        "doc_type": "regulation",
        "source_id": "R-FATF",
        "category": "regulator",
        "credibility": "official",
        "source_url": "https://www.fatf-gafi.org/en/topics/virtual-assets.html",
        "published": "2023-06-01",
        "publisher": "FATF",
        "language": "en",
        "ymyl_block": "Y2",
        "harm_category": "aml_freeze",
        "criteria_ids": ["YY10", "YY23", "YY04"],
        "relevance_score": 5,
        "supports_brand": "neutral",
        "summary": "VASPs must flag suspicious txs — user harm when funds frozen without clear refund path. Quickex AML policy alignment.",
        "file": "fatf-aml-freeze-harm.md",
    },
    {
        "id": "YMYL-R-FCA-WARNING",
        "title": "FCA — Cryptoasset investment warnings",
        "tier": "T1_official",
        "doc_type": "regulation",
        "source_id": "R-FCA",
        "category": "regulator",
        "credibility": "official",
        "source_url": "https://www.fca.org.uk/consumers/cryptoassets",
        "published": "2024-01-01",
        "publisher": "UK FCA",
        "language": "en",
        "ymyl_block": "Y4",
        "harm_category": "financial_loss",
        "criteria_ids": ["YY06", "YY17", "YY18"],
        "relevance_score": 4,
        "supports_brand": "neutral",
        "summary": "UK consumers: crypto unregulated for most activities; lose all money; FCA register for authorised firms only.",
        "file": "fca-crypto-consumer-warning.md",
    },
    {
        "id": "YMYL-R-OFAC-SANCTIONS",
        "title": "OFAC — Sanctions compliance for virtual currency",
        "tier": "T1_official",
        "doc_type": "regulation",
        "source_id": "R-OFAC",
        "category": "regulator",
        "credibility": "official",
        "source_url": "https://ofac.treasury.gov/sanctions-programs-and-country-information/virtual-currency",
        "published": "2024-01-01",
        "publisher": "U.S. Treasury OFAC",
        "language": "en",
        "ymyl_block": "Y2",
        "harm_category": "geo_sanctions",
        "criteria_ids": ["YY11", "YY10"],
        "relevance_score": 4,
        "supports_brand": "neutral",
        "summary": "Sanctions on virtual currency addresses — geo-restrictions must be disclosed (YY11) to prevent user legal harm.",
        "file": "ofac-virtual-currency.md",
    },
    # ── Quickex official (harm angle) ──
    {
        "id": "YMYL-QX-AML",
        "title": "Quickex AML Policy — user harm from freeze",
        "tier": "T1_site",
        "doc_type": "legal_page",
        "source_id": "QX-LEGAL",
        "category": "quickex_official",
        "credibility": "primary_source",
        "source_url": "https://quickex.io/docs/aml-policy",
        "published": "2025-01-01",
        "publisher": "Quickex",
        "language": "en",
        "ymyl_block": "Y2",
        "harm_category": "aml_freeze",
        "criteria_ids": ["YY10", "YY04", "YY23"],
        "relevance_score": 5,
        "supports_brand": "mixed",
        "summary": "Freeze high-risk txs; full KYC for refund; mixer flags — mitigates regulatory harm but conflicts with «no KYC» marketing.",
        "file": "quickex-aml-harm.md",
    },
    {
        "id": "YMYL-QX-TERMS",
        "title": "Quickex Terms — delays, refunds, liquidity risk",
        "tier": "T1_site",
        "doc_type": "legal_page",
        "source_id": "QX-LEGAL",
        "category": "quickex_official",
        "credibility": "primary_source",
        "source_url": "https://quickex.io/docs/terms-of-use",
        "published": "2025-01-01",
        "publisher": "Quickex",
        "language": "en",
        "ymyl_block": "Y5",
        "harm_category": "support_failure",
        "criteria_ids": ["YY23", "YY05", "YY06"],
        "relevance_score": 5,
        "supports_brand": "mitigates_harm",
        "summary": "AML delays possible; third-party liquidity; no guaranteed speed — must be visible BEFORE transaction (YY23, YY24).",
        "file": "quickex-terms-harm.md",
    },
    {
        "id": "YMYL-QX-PRIVACY",
        "title": "Quickex Privacy — KYC data collection harm disclosure",
        "tier": "T1_site",
        "doc_type": "legal_page",
        "source_id": "QX-LEGAL",
        "category": "quickex_official",
        "credibility": "primary_source",
        "source_url": "https://quickex.io/docs/privacy-policy",
        "published": "2025-01-01",
        "publisher": "Quickex",
        "language": "en",
        "ymyl_block": "Y2",
        "harm_category": "misleading_claim",
        "criteria_ids": ["YY10", "YY04"],
        "relevance_score": 4,
        "supports_brand": "mitigates_harm",
        "summary": "Discloses KYC/AML data collection — reduces harm from surprise verification if linked from swap flow.",
        "file": "quickex-privacy-harm.md",
    },
    # ── User harm signals ──
    {
        "id": "YMYL-W-TRUSTPILOT",
        "title": "Trustpilot — stuck funds / AML freeze complaints",
        "tier": "T3_ugc",
        "doc_type": "review_platform",
        "source_id": "W-TRUSTPILOT",
        "category": "reputation",
        "credibility": "ugc_verified",
        "source_url": "https://www.trustpilot.com/review/quickex.io",
        "published": "2026-03-01",
        "publisher": "Trustpilot",
        "language": "en",
        "ymyl_block": "Y4",
        "harm_category": "aml_freeze",
        "criteria_ids": ["YY19", "YY23", "YY04"],
        "relevance_score": 5,
        "supports_brand": "increases_harm",
        "summary": "Users report AML flag, KYC surprise on privacy pairs, refund minus blockchain fee. Pattern of financial harm (YY19).",
        "file": "reputation-trustpilot-harm.md",
    },
    {
        "id": "YMYL-W-BESTCHANGE",
        "title": "BestChange — delist + financial claims harm",
        "tier": "T3_ugc",
        "doc_type": "review_platform",
        "source_id": "W-BESTCHANGE",
        "category": "reputation",
        "credibility": "ugc_monitor",
        "source_url": "https://www.bestchange.com/quickex-exchanger.html",
        "published": "2024-06-23",
        "publisher": "BestChange",
        "language": "ru",
        "ymyl_block": "Y4",
        "harm_category": "financial_loss",
        "criteria_ids": ["YY19", "YY04"],
        "relevance_score": 5,
        "supports_brand": "increases_harm",
        "summary": "DELISTED 23.06.2024. 36 financial claims. Users directed to caution — reputation harm → user trust harm.",
        "file": "reputation-bestchange-harm.md",
    },
    {
        "id": "YMYL-F-BCT-FREEZE",
        "title": "Bitcointalk — 9.5 ETH frozen (user harm case)",
        "tier": "T3_forum",
        "doc_type": "forum",
        "source_id": "W-BCT",
        "category": "forum",
        "credibility": "ugc_accusation",
        "source_url": "https://bitcointalk.org/index.php?topic=5577804.0",
        "published": "2025-10-01",
        "publisher": "Bitcointalk",
        "language": "en",
        "ymyl_block": "Y2",
        "harm_category": "aml_freeze",
        "criteria_ids": ["YY04", "YY23", "YY10"],
        "relevance_score": 5,
        "supports_brand": "increases_harm",
        "summary": "9.5 ETH frozen — liquidity provider AML flag. Documented user harm on privacy-route swap.",
        "file": "forum-bitcointalk-freeze-harm.md",
    },
    # ── Competitor harm prevention benchmark ──
    {
        "id": "YMYL-C-CHANGENOW",
        "title": "ChangeNOW — risk disclaimer benchmark",
        "tier": "T2_authoritative",
        "doc_type": "competitor",
        "source_id": "C-CHANGENOW",
        "category": "competitor",
        "credibility": "competitor",
        "source_url": "https://changenow.io/terms-of-use",
        "published": "2026-01-01",
        "publisher": "ChangeNOW",
        "language": "en",
        "ymyl_block": "Y2",
        "harm_category": "volatility_risk",
        "criteria_ids": ["YY05", "YY06", "YY10"],
        "relevance_score": 4,
        "supports_brand": "neutral",
        "summary": "Benchmark: risk disclaimers, AML/KYC clauses, non-custodial explanation — compare with Quickex money pages.",
        "file": "competitor-changenow-harm.md",
    },
    {
        "id": "YMYL-C-CHANGELLY",
        "title": "Changelly — transactional trust benchmark",
        "tier": "T2_authoritative",
        "doc_type": "competitor",
        "source_id": "C-CHANGELLY",
        "category": "competitor",
        "credibility": "competitor",
        "source_url": "https://changelly.com/terms-of-use",
        "published": "2026-01-01",
        "publisher": "Changelly",
        "language": "en",
        "ymyl_block": "Y5",
        "harm_category": "support_failure",
        "criteria_ids": ["YY23", "YY24", "YY25"],
        "relevance_score": 3,
        "supports_brand": "neutral",
        "summary": "Refund policy, limits, support channels — harm prevention gap analysis vs Quickex.",
        "file": "competitor-changelly-harm.md",
    },
    {
        "id": "YMYL-I-CRAWLUX",
        "title": "Crawlux — Crypto YMYL harm prevention checklist",
        "tier": "T2_authoritative",
        "doc_type": "industry_guide",
        "source_id": "I-CRAWLUX",
        "category": "industry",
        "credibility": "industry_analysis",
        "source_url": "https://www.crawlux.com/guides/eeat-ymyl-crypto/",
        "published": "2026-01-01",
        "publisher": "Crawlux",
        "language": "en",
        "ymyl_block": "Y2",
        "harm_category": "misleading_claim",
        "criteria_ids": ["YY05", "YY09", "YY12"],
        "relevance_score": 3,
        "supports_brand": "neutral",
        "summary": "Operational harm signals: disclaimers, anti-phishing, fee transparency for crypto YMYL.",
        "file": "industry-crawlux-ymyl-harm.md",
    },
    {
        "id": "YMYL-R-FINRA-CYBER",
        "title": "FINRA — Digital currency investor alert",
        "tier": "T1_official",
        "doc_type": "regulation",
        "source_id": "R-FINRA",
        "category": "regulator",
        "credibility": "official",
        "source_url": "https://www.finra.org/investors/insights/high-yield-cybersecurity-risks",
        "published": "2024-01-01",
        "publisher": "FINRA",
        "language": "en",
        "ymyl_block": "Y2",
        "harm_category": "scam_phishing",
        "criteria_ids": ["YY09", "YY19"],
        "relevance_score": 3,
        "supports_brand": "neutral",
        "summary": "Cyber risks, phishing, pump-and-dump — supplemental US investor harm bar.",
        "file": "finra-digital-currency-alert.md",
    },
]

INSIGHTS: list[dict[str, Any]] = [
    {
        "id": "INS-Y-AML-GAP",
        "document_id": "YMYL-QX-AML",
        "title": "Marketing «no KYC» vs AML freeze — user harm gap",
        "severity": "critical",
        "ymyl_block": "Y2",
        "harm_category": "aml_freeze",
        "criteria_ids": ["YY10", "YY04"],
        "recommendation": "На privacy-парах: pre-swap warning «AML check may freeze funds» + link /docs/aml-policy. Синхронизировать meta с policy до отправки.",
    },
    {
        "id": "INS-Y-BESTCHANGE",
        "document_id": "YMYL-W-BESTCHANGE",
        "title": "BestChange delist — reputation harm → user trust harm",
        "severity": "critical",
        "harm_category": "financial_loss",
        "ymyl_block": "Y4",
        "criteria_ids": ["YY19", "YY04"],
        "recommendation": "Trust page с объяснением статуса; не скрывать delist; план compliance audit для re-listing.",
    },
    {
        "id": "INS-Y-RISK-DISCLOSURE",
        "document_id": "YMYL-R-SEC-BITCOIN",
        "title": "Missing volatility/total loss warning on money pages",
        "severity": "high",
        "harm_category": "volatility_risk",
        "ymyl_block": "Y2",
        "criteria_ids": ["YY05", "YY06"],
        "recommendation": "Добавить risk banner на все exchange pages: not financial advice + may lose all funds + non-custodial responsibility.",
    },
    {
        "id": "INS-Y-PRIVACY-FREEZE",
        "document_id": "YMYL-F-BCT-FREEZE",
        "title": "Documented 9.5 ETH freeze — privacy pair harm",
        "severity": "critical",
        "harm_category": "aml_freeze",
        "ymyl_block": "Y2",
        "criteria_ids": ["YY04", "YY23", "YY10"],
        "recommendation": "FAQ: что делать при freeze; сроки refund; ссылка на liquidity provider policy. Убрать «100% anonymous» claims.",
    },
    {
        "id": "INS-Y-REG-FALSE",
        "document_id": "YMYL-R-ESMA-JOINT-2025",
        "title": "EU/MiCA claims without ESMA register proof",
        "severity": "high",
        "harm_category": "regulatory_false",
        "ymyl_block": "Y4",
        "criteria_ids": ["YY17", "YY18"],
        "recommendation": "Не заявлять EU licensed без номера CASP. Если нет — явный disclaimer «not MiCA authorised» для EU users.",
    },
    {
        "id": "INS-Y-REFUND",
        "document_id": "YMYL-W-TRUSTPILOT",
        "title": "Refund disputes — blockchain fee deduction harm",
        "severity": "high",
        "harm_category": "support_failure",
        "ymyl_block": "Y5",
        "criteria_ids": ["YY23", "YY25"],
        "recommendation": "Публиковать refund policy с fee breakdown ДО swap; support SLA на stuck transactions.",
    },
    {
        "id": "INS-Y-PHISHING",
        "document_id": "YMYL-R-CFTC-FRAUD-WEB",
        "title": "Anti-phishing / verify URL block missing",
        "severity": "medium",
        "harm_category": "scam_phishing",
        "ymyl_block": "Y2",
        "criteria_ids": ["YY09"],
        "recommendation": "Footer + FAQ: official domain quickex.io only; warning about Telegram/social media impersonators.",
    },
    {
        "id": "INS-Y-LIMITS",
        "document_id": "YMYL-C-CHANGELLY",
        "title": "Min/max limits not visible pre-transaction",
        "severity": "medium",
        "harm_category": "financial_loss",
        "ymyl_block": "Y5",
        "criteria_ids": ["YY24"],
        "recommendation": "Показывать min/max amount до ввода суммы на всех 635 exchange pages.",
    },
]


def _read_doc_file(filename: str) -> str:
    path = _docs_dir() / filename
    if path.exists():
        return path.read_text(encoding="utf-8")
    return ""


def seed_ymyl_library(force: bool = False) -> dict[str, int]:
    with connect() as conn:
        count = conn.execute("SELECT COUNT(*) FROM ymyl_documents").fetchone()[0]
        if count and not force:
            return {
                "documents": count,
                "insights": _insight_count(conn),
                "seeded": False,
            }

        if force:
            conn.execute("DELETE FROM ymyl_insights WHERE id NOT LIKE 'INS-AI-%'")
            conn.execute(
                "DELETE FROM ymyl_documents WHERE COALESCE(origin, 'seed') = 'seed'",
            )

        for doc in DOCUMENTS:
            content = _read_doc_file(doc["file"])
            conn.execute(
                """
                INSERT OR REPLACE INTO ymyl_documents
                (id, title, tier, doc_type, source_id, category, credibility, source_url,
                 published, publisher, language, ymyl_block, harm_category, criteria_ids_json,
                 relevance_score, supports_brand, summary, content_md, file_name,
                 origin, accessed_date)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'seed', ?)
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
                    doc["ymyl_block"],
                    doc["harm_category"],
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
                INSERT OR REPLACE INTO ymyl_insights
                (id, document_id, title, severity, ymyl_block, harm_category,
                 criteria_ids_json, recommendation)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    ins["id"],
                    ins["document_id"],
                    ins["title"],
                    ins["severity"],
                    ins.get("ymyl_block"),
                    ins.get("harm_category"),
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
    return conn.execute("SELECT COUNT(*) FROM ymyl_insights").fetchone()[0]


def library_stats() -> dict[str, int]:
    with connect() as conn:
        docs = conn.execute("SELECT COUNT(*) FROM ymyl_documents").fetchone()[0]
        insights = conn.execute("SELECT COUNT(*) FROM ymyl_insights").fetchone()[0]
        by_tier = {}
        by_harm = {}
        for row in conn.execute(
            "SELECT tier, COUNT(*) AS c FROM ymyl_documents GROUP BY tier",
        ).fetchall():
            by_tier[row["tier"]] = row["c"]
        for row in conn.execute(
            "SELECT harm_category, COUNT(*) AS c FROM ymyl_documents GROUP BY harm_category",
        ).fetchall():
            by_harm[row["harm_category"]] = row["c"]
        return {
            "documents": docs,
            "insights": insights,
            "by_tier": by_tier,
            "by_harm": by_harm,
        }


def list_documents(
    category: str | None = None,
    tier: str | None = None,
    harm_category: str | None = None,
) -> list[dict[str, Any]]:
    with connect() as conn:
        q = "SELECT * FROM ymyl_documents WHERE 1=1"
        params: list[Any] = []
        if category:
            q += " AND category = ?"
            params.append(category)
        if tier:
            q += " AND tier = ?"
            params.append(tier)
        if harm_category:
            q += " AND harm_category = ?"
            params.append(harm_category)
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
        row = conn.execute("SELECT * FROM ymyl_documents WHERE id = ?", (doc_id,)).fetchone()
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
            FROM ymyl_insights i
            LEFT JOIN ymyl_documents d ON d.id = i.document_id
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


def library_snapshot_for_prompt(limit: int = 24) -> list[dict[str, Any]]:
    docs = list_documents()[:limit]
    return [
        {
            "id": d["id"],
            "source_id": d.get("source_id"),
            "harm_category": d.get("harm_category"),
            "title": d.get("title"),
            "url": d.get("source_url"),
            "supports_brand": d.get("supports_brand"),
            "criteria_ids": d.get("criteria_ids", [])[:6],
        }
        for d in docs
    ]


def insights_snapshot_for_prompt(limit: int = 10) -> list[dict[str, Any]]:
    return [
        {
            "id": i["id"],
            "severity": i.get("severity"),
            "harm_category": i.get("harm_category"),
            "title": i.get("title"),
            "criteria_ids": i.get("criteria_ids", []),
            "recommendation": (i.get("recommendation") or "")[:200],
        }
        for i in list_insights()[:limit]
    ]


def export_library_markdown() -> str:
    docs = list_documents()
    insights = list_insights()
    lines = [
        "# YMYL Document Library — Quickex",
        "",
        f"Документов: {len(docs)} · Insights: {len(insights)}",
        "",
        "## Реестр документов",
        "",
        "| ID | Tier | Harm | Title | Brand | URL |",
        "|----|------|------|-------|-------|-----|",
    ]
    for d in docs:
        lines.append(
            f"| {d['id']} | {d['tier']} | {d.get('harm_category', '')} | {d['title']} | "
            f"{d['supports_brand']} | {d['source_url']} |"
        )
    lines.extend(["", "## Insights", ""])
    for i in insights:
        lines.append(f"### {i['id']} — {i['title']} ({i['severity']})")
        lines.append(f"**Критерии:** {', '.join(i['criteria_ids'])}")
        lines.append(f"**Рекомендация:** {i['recommendation']}")
        lines.append("")
    return "\n".join(lines)


HARM_SCENARIOS: list[dict[str, Any]] = [
    {
        "id": "HS-AML-FREEZE",
        "title": "Stuck/frozen swap (AML flag)",
        "likelihood": "high",
        "severity": "critical",
        "mitigation": "partial",
        "criteria_ids": ["YY10", "YY23"],
        "library_doc_id": "YMYL-QX-AML",
    },
    {
        "id": "HS-WRONG-ADDR",
        "title": "Wrong address / irreversible send",
        "likelihood": "medium",
        "severity": "critical",
        "mitigation": "partial",
        "criteria_ids": ["YY07", "YY24"],
        "library_doc_id": "YMYL-R-CFTC-RISKS",
    },
    {
        "id": "HS-NO-KYC-SURPRISE",
        "title": "«No KYC» marketing → surprise verification",
        "likelihood": "high",
        "severity": "high",
        "mitigation": "weak",
        "criteria_ids": ["YY05", "YY10"],
        "library_doc_id": "YMYL-W-TRUSTPILOT",
    },
    {
        "id": "HS-PHISHING",
        "title": "Phishing via fake mirror",
        "likelihood": "medium",
        "severity": "high",
        "mitigation": "unknown",
        "criteria_ids": ["YY09"],
        "library_doc_id": "YMYL-R-CFTC-FRAUD-WEB",
    },
    {
        "id": "HS-HIDDEN-FEES",
        "title": "Hidden fees / rate bait-and-switch",
        "likelihood": "medium",
        "severity": "medium",
        "mitigation": "partial",
        "criteria_ids": ["YY12"],
        "library_doc_id": "YMYL-G-SPAM-CLAIMS",
    },
    {
        "id": "HS-FALSE-REG",
        "title": "False regulatory trust signal",
        "likelihood": "low",
        "severity": "high",
        "mitigation": "unknown",
        "criteria_ids": ["YY17", "YY18"],
        "library_doc_id": "YMYL-R-ESMA-JOINT-2025",
    },
    {
        "id": "HS-PRIVACY-FREEZE",
        "title": "XMR/BTC user expects anonymity → funds frozen",
        "likelihood": "high",
        "severity": "critical",
        "mitigation": "weak",
        "criteria_ids": ["YY04", "YY10"],
        "library_doc_id": "YMYL-F-BCT-FREEZE",
    },
]


def _index_by_criteria(docs: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    out: dict[str, list[dict[str, Any]]] = {}
    for doc in docs:
        for cid in doc.get("criteria_ids") or []:
            out.setdefault(cid, []).append(
                {
                    "id": doc["id"],
                    "title": doc["title"],
                    "url": doc.get("source_url"),
                    "harm_category": doc.get("harm_category"),
                    "supports_brand": doc.get("supports_brand"),
                }
            )
    return out


def documents_for_criterion(criterion_id: str) -> list[dict[str, Any]]:
    return _index_by_criteria(list_documents()).get(criterion_id, [])


def insights_for_criterion(criterion_id: str) -> list[dict[str, Any]]:
    return [i for i in list_insights() if criterion_id in (i.get("criteria_ids") or [])]


def criteria_document_map() -> dict[str, list[dict[str, Any]]]:
    return _index_by_criteria(list_documents())


def enrich_display_items(
    catalog: list[dict[str, Any]],
    results_map: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    doc_index = _index_by_criteria(list_documents())
    display: list[dict[str, Any]] = []
    for item in catalog:
        evaluated = results_map.get(item["id"])
        row = dict(evaluated if evaluated else {**item, "status": "pending", "evidence": ""})
        row["library_docs"] = doc_index.get(item["id"], [])[:5]
        row["library_insights"] = insights_for_criterion(item["id"])[:2]
        display.append(row)
    return display


def critical_insights(limit: int = 6) -> list[dict[str, Any]]:
    return [i for i in list_insights() if i.get("severity") in ("critical", "high")][:limit]


def block_audit_stats(results: list[dict[str, Any]] | None) -> dict[str, dict[str, int]]:
    stats: dict[str, dict[str, int]] = {}
    if not results:
        return stats
    for r in results:
        block = r.get("block") or "Y?"
        stats.setdefault(block, {"pass": 0, "warn": 0, "fail": 0, "manual": 0, "pending": 0, "na": 0})
        status = r.get("status") or "pending"
        if status not in stats[block]:
            stats[block][status] = 0
        stats[block][status] += 1
    return stats
