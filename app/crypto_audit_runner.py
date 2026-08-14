"""EEAT and YMYL automated audits for crypto exchange projects."""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

from app.checklist_runner import AuditContext, _fetch_site_assets, _pair_from_url
from app.config_loader import load_config
from app.nuxt_auditor import analyze_nuxt_html, check_nuxt_assets, detect_nuxt
from app.pro_seo_auditor import build_priority_roadmap, build_site_pro_context
from app.specialist_catalog import catalog_by_type, load_eeat_catalog, load_ymyl_catalog

TIMEOUT = 25
SITE_PATHS = (
    "/about",
    "/about-us",
    "/company",
    "/privacy",
    "/privacy-policy",
    "/terms",
    "/terms-of-service",
    "/tos",
    "/security",
    "/fees",
    "/contact",
    "/support",
    "/aml",
    "/kyc",
    "/how-it-works",
    "/blog",
)
OVERCLAIM = re.compile(
    r"100%\s*(anonymous|untraceable)|guaranteed\s+(profit|returns)|risk[- ]free",
    re.I,
)
DISCLAIMER = re.compile(
    r"not\s+financial\s+advice|informational\s+purposes|do\s+not\s+constitute\s+investment",
    re.I,
)
RISK_LOSS = re.compile(r"risk|may\s+lose|loss\s+of\s+(capital|funds)|volatile", re.I)
NON_CUSTODIAL = re.compile(r"non[- ]custodial|do\s+not\s+(hold|store)\s+(your\s+)?(funds|keys)", re.I)
KYC_AML = re.compile(r"kyc|aml|anti[- ]money|know your customer", re.I)
LAST_UPDATED = re.compile(r"last\s+updated|updated:\s*\d|datemodified|dateModified", re.I)
MSB_LICENSE = re.compile(r"msb|fincen|money\s+service\s+business|fca\s+register|mica", re.I)
FAQ_COUNT = re.compile(r"<h[23][^>]*>.*\?", re.I)


@dataclass
class SiteCorpus:
    base: str
    domain: str
    pages: dict[str, str] = field(default_factory=dict)
    combined_text: str = ""
    combined_html: str = ""
    json_ld: list[str] = field(default_factory=list)
    footer_links: list[str] = field(default_factory=list)
    llms_txt: str = ""


def _pass(evidence: str = "") -> dict[str, Any]:
    return {"status": "pass", "evidence": evidence}


def _warn(evidence: str) -> dict[str, Any]:
    return {"status": "warn", "evidence": evidence}


def _fail(evidence: str) -> dict[str, Any]:
    return {"status": "fail", "evidence": evidence}


def _manual(note: str = "Требует ручной проверки") -> dict[str, Any]:
    return {"status": "manual", "evidence": note}


def _na(note: str = "Не применимо") -> dict[str, Any]:
    return {"status": "na", "evidence": note}


def _scope_applies(scope: str, ctx: AuditContext) -> bool:
    if scope == "ALL":
        return True
    if scope == "SITE":
        return True
    if scope == "EX":
        return ctx.page_type == "exchange" or "exchange" in ctx.url
    if scope == "BLOG":
        return "/blog" in ctx.url or ctx.page_type == "blog"
    if scope == "HP":
        return ctx.page_type == "homepage"
    return True


async def _fetch_site_corpus(client: httpx.AsyncClient, base: str) -> SiteCorpus:
    domain = urlparse(base).netloc
    corpus = SiteCorpus(base=base, domain=domain)
    texts: list[str] = []
    htmls: list[str] = []

    async def _get(path: str) -> str | None:
        try:
            r = await client.get(urljoin(base, path))
            if r.status_code == 200 and "text/html" in r.headers.get("content-type", ""):
                return r.text
        except Exception:
            pass
        return None

    home = await _get("/")
    if home:
        corpus.pages["/"] = home
        texts.append(BeautifulSoup(home, "lxml").get_text("\n", strip=True))
        htmls.append(home)
        for a in BeautifulSoup(home, "lxml").find_all("a", href=True):
            href = str(a["href"])
            if href.startswith("/") and len(href) < 80:
                corpus.footer_links.append(href.lower())

    for path in SITE_PATHS:
        html = await _get(path)
        if html:
            corpus.pages[path] = html
            texts.append(BeautifulSoup(html, "lxml").get_text("\n", strip=True))
            htmls.append(html)
            for script in BeautifulSoup(html, "lxml").find_all("script", type="application/ld+json"):
                corpus.json_ld.append(script.get_text(strip=True))

    for html in htmls:
        for script in BeautifulSoup(html, "lxml").find_all("script", type="application/ld+json"):
            raw = script.get_text(strip=True)
            if raw and raw not in corpus.json_ld:
                corpus.json_ld.append(raw)

    try:
        r = await client.get(urljoin(base, "/llms.txt"))
        if r.status_code == 200:
            corpus.llms_txt = r.text
    except Exception:
        pass

    corpus.combined_text = "\n".join(texts).lower()
    corpus.combined_html = "\n".join(htmls).lower()
    return corpus


def _has_path(corpus: SiteCorpus, *needles: str) -> bool:
    for path in corpus.pages:
        if any(n in path for n in needles):
            return True
    for link in corpus.footer_links:
        if any(n in link for n in needles):
            return True
    return False


def _org_schema(corpus: SiteCorpus) -> dict[str, Any]:
    for raw in corpus.json_ld:
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            continue
        items = data if isinstance(data, list) else [data]
        for item in items:
            if not isinstance(item, dict):
                continue
            t = item.get("@type", "")
            if t == "Organization" or (isinstance(t, list) and "Organization" in t):
                return item
            if "@graph" in item:
                for g in item["@graph"]:
                    if isinstance(g, dict) and g.get("@type") == "Organization":
                        return g
    return {}


def _score_results(results: list[dict]) -> dict[str, Any]:
    counts = {"pass": 0, "warn": 0, "fail": 0, "manual": 0, "na": 0}
    scored = 0
    points = 0.0
    weights = {"critical": 3, "high": 2, "medium": 1, "low": 0.5}
    for r in results:
        st = r["status"]
        counts[st] = counts.get(st, 0) + 1
        if st in ("pass", "warn", "fail"):
            w = weights.get(r.get("severity", "medium"), 1)
            scored += w
            if st == "pass":
                points += w
            elif st == "warn":
                points += w * 0.5
    score = round(points / max(scored, 1) * 100, 1)
    grade = "A" if score >= 90 else "B" if score >= 75 else "C" if score >= 60 else "D" if score >= 45 else "F"
    return {"score": score, "grade": grade, "counts": counts, "status": "ok" if counts["fail"] == 0 else "partial"}


def _evaluate_eeat(item: dict, ctx: AuditContext, corpus: SiteCorpus) -> dict[str, Any]:
    iid = item["id"]
    if not _scope_applies(item["scope"], ctx):
        return _na()

    text = corpus.combined_text
    page_text = ctx.visible_text.lower()
    soup = ctx.soup
    org = _org_schema(corpus)

    if iid == "EE01":
        steps = len(re.findall(r"step\s*\d|шаг\s*\d|1\.|2\.|3\.", page_text + text))
        return _pass(f"~{steps} step markers") if steps >= 3 else _warn("Мало пошагового how-it-works")
    if iid == "EE02":
        hints = sum(1 for w in ("network fee", "min amount", "max amount", "комисс", "лимит") if w in page_text)
        return _pass(f"{hints} UX hints") if hints >= 2 else _warn("Нет fee/limit/ETA деталей")
    if iid == "EE03":
        faq = len(re.findall(r"\?", page_text))
        return _pass(f"{faq} FAQ markers") if faq >= 5 else _warn(f"Мало FAQ ({faq})")
    if iid == "EE04":
        return _manual("Проверить blog: author + first-hand experience")
    if iid == "EE05":
        return _manual("Проверить testimonials на подлинность")

    if iid == "EE06":
        if _has_path(corpus, "about", "editorial", "author"):
            return _pass("About/editorial page found")
        return _fail("Нет editorial policy / about")
    if iid == "EE07":
        if "author" in text or "Person" in corpus.combined_html:
            return _pass("Author signals present") if "author" in text else _warn("Person schema — проверить bio")
        return _warn("Нет named authors")
    if iid == "EE08":
        terms = sum(1 for w in ("slippage", "on-chain", "custodial", "non-custodial", "liquidity") if w in text)
        return _pass(f"{terms} expert terms") if terms >= 2 else _warn("Мало crypto-терминологии")
    if iid == "EE09":
        return _manual("Сверить comparison tables с фактами")
    if iid == "EE10":
        if LAST_UPDATED.search(ctx.html) or LAST_UPDATED.search(corpus.combined_html):
            return _pass("Last updated найден")
        return _warn("Нет dateModified / Last updated")

    if iid == "EE11":
        if org.get("name") and org.get("url"):
            return _pass(f"Organization: {org.get('name')}")
        if "organization" in corpus.combined_html:
            return _warn("Organization schema без name/url")
        return _fail("Нет Organization schema")
    if iid == "EE12":
        same = org.get("sameAs") or []
        if isinstance(same, list) and len(same) >= 2:
            return _pass(f"sameAs: {len(same)} links")
        return _warn("sameAs неполный или отсутствует")
    if iid == "EE13":
        if any(w in text for w in ("ltd", "llc", "inc", "registered", "основан", "founded")):
            return _pass("Legal entity hints found")
        return _warn("Нет юрлица / founding info")
    if iid == "EE14":
        if _has_path(corpus, "press", "media", "partner", "news"):
            return _pass("Press/media page")
        return _manual("Проверить earned media вне сайта")
    if iid == "EE15":
        emails = set(re.findall(r"[\w.+-]+@[\w-]+\.\w+", corpus.combined_html))
        return _pass(f"{len(emails)} contact emails") if emails else _warn("Email не найден")
    if iid == "EE16":
        return _manual("Google Knowledge Graph — ручная проверка")

    if iid == "EE17":
        return _pass() if ctx.url.startswith("https://") else _fail("Не HTTPS")
    if iid == "EE18":
        return _pass("Privacy найден") if _has_path(corpus, "privacy") else _fail("Нет Privacy Policy")
    if iid == "EE19":
        return _pass("Terms найден") if _has_path(corpus, "terms", "tos") else _fail("Нет Terms of Service")
    if iid == "EE20":
        if DISCLAIMER.search(text) or DISCLAIMER.search(page_text):
            return _pass("Financial disclaimer найден")
        return _fail("Нет investment/financial disclaimer")
    if iid == "EE21":
        if re.search(r"support@|contact@|help@|/contact|live\s*chat", text):
            return _pass("Contact channel найден")
        return _fail("Нет контакта support")
    if iid == "EE22":
        if _has_path(corpus, "security") or "2fa" in text or "encryption" in text:
            return _pass("Security signals")
        return _warn("Нет /security или trust block")
    if iid == "EE23":
        if OVERCLAIM.search(page_text) or OVERCLAIM.search(text):
            return _fail("Overclaim: anonymous/guaranteed")
        return _pass("Нет опасных overclaim")
    if iid == "EE24":
        if "cookie" in text or "gdpr" in text:
            return _pass("Cookie/GDPR mention")
        return _warn("Cookie consent не обнаружен")
    if iid == "EE25":
        if "aggregaterating" in corpus.combined_html:
            return _manual("AggregateRating — проверить подлинность отзывов")
        return _pass("Нет review schema (OK)")
    if iid == "EE26":
        if "fee" in text or "комисс" in text:
            return _pass("Fees упомянуты")
        return _warn("Fees не прозрачны на сайте")
    if iid == "EE27":
        if corpus.llms_txt:
            return _pass(f"llms.txt {len(corpus.llms_txt)} chars")
        return _warn("llms.txt отсутствует")
    if iid == "EE28":
        if "status." in text or _has_path(corpus, "status"):
            return _pass("Status page signal")
        return _manual("Status page — опционально")

    return _manual(f"Нет автоматики для {iid}")


def _evaluate_ymyl(item: dict, ctx: AuditContext, corpus: SiteCorpus) -> dict[str, Any]:
    iid = item["id"]
    if not _scope_applies(item["scope"], ctx):
        return _na()

    text = corpus.combined_text
    page_text = ctx.visible_text.lower()

    if iid == "YY01":
        return _pass("Crypto exchange = clear YMYL Financial Security (G-QRG §2.3)")
    if iid == "YY02":
        if ctx.page_type == "exchange" or "exchange-" in ctx.url:
            return _pass("Money page — high YMYL scrutiny")
        return _warn("Не exchange page — ниже риск")
    if iid == "YY03":
        if "/blog" in ctx.url:
            return _warn("Blog на crypto topics — YMYL bar")
        return _na("Не blog")
    if iid == "YY04":
        return _manual("Оценить factual harm potential editorially")

    if iid == "YY05":
        return _pass() if DISCLAIMER.search(text) else _fail("Нет «not financial advice»")
    if iid == "YY06":
        return _pass() if RISK_LOSS.search(text) else _fail("Нет warning о риске потерь")
    if iid == "YY07":
        return _pass() if NON_CUSTODIAL.search(text) else _warn("Non-custodial не объяснён")
    if iid == "YY08":
        return _fail("Guaranteed returns claim") if OVERCLAIM.search(text) else _pass()
    if iid == "YY09":
        if "phishing" in text or "official" in text and "domain" in text:
            return _pass("Scam/phishing warning")
        return _warn("Нет anti-phishing блока")
    if iid == "YY10":
        return _pass("AML/KYC page") if _has_path(corpus, "aml", "kyc") or KYC_AML.search(text) else _warn("AML/KYC не найден")
    if iid == "YY11":
        if "restricted" in text or "not available" in text and "country" in text:
            return _pass("Geo restrictions")
        return _manual("Проверить restricted countries list")

    if iid == "YY12":
        if "fee" in text or "spread" in text or "rate" in text:
            return _pass("Fee/rate disclosure")
        return _warn("Fees/rates не явны")
    if iid == "YY13":
        return _manual("Проверить citations в blog posts")
    if iid == "YY14":
        if LAST_UPDATED.search(corpus.combined_html):
            return _pass("Content freshness signal")
        return _warn("Нет дат обновления >12 мес риск")
    if iid == "YY15":
        if re.search(r"#1|best exchange|лучший обмен", text):
            return _warn("Superlative claims — нужны доказательства")
        return _pass()
    if iid == "YY16":
        return _pass("Нет health claims") if "medical" not in text else _warn("Health claims на crypto site")

    if iid == "YY17":
        if MSB_LICENSE.search(text):
            return _pass("Regulatory mention — верифицировать номер") if re.search(r"\d{4,}", text) else _warn("License без номера")
        return _manual("Проверить FinCEN/FCA register")
    if iid == "YY18":
        if "regulated by" in text and not re.search(r"\d{4,}", text):
            return _warn("«Regulated» без verifiable number")
        return _pass()
    if iid == "YY19":
        return _manual("Поиск scam reports: Trustpilot, Reddit, BBB")
    if iid == "YY20":
        return _pass("Ownership info") if any(w in text for w in ("ltd", "llc", "team", "about")) else _warn("Ownership непрозрачен")
    if iid == "YY21":
        return _manual("Проверить историю инцидентов")

    if iid == "YY22":
        return _pass() if ctx.url.startswith("https://") else _fail("Не HTTPS")
    if iid == "YY23":
        if "refund" in text or "stuck" in text or "support" in text:
            return _pass("Support/refund policy hints")
        return _warn("Нет refund/stuck tx policy")
    if iid == "YY24":
        if re.search(r"min\.?\s*\d|max\.?\s*\d|minimum|maximum|лимит", page_text):
            return _pass("Limits visible")
        return _warn("Min/max limits не на странице")
    if iid == "YY25":
        return _manual("Проверить реальность 24/7 support")
    if iid == "YY26":
        if "financialservice" in corpus.combined_html:
            return _pass("FinancialService schema")
        return _warn("Нет FinancialService schema")
    if iid == "YY27":
        if "visa" in text or "mastercard" in text or "moonpay" in text:
            return _manual("Verify payment partner logos")
        return _na("Нет card on-ramp")
    if iid == "YY28":
        if re.search(r"security@|bug\s*bounty|hackerone", text):
            return _pass("Security contact")
        return _manual("Bug bounty — optional")

    return _manual(f"Нет автоматики для {iid}")


async def run_specialist_audit(
    checklist_type: str,
    page_index: int = 0,
) -> dict[str, Any]:
    """Run EEAT or YMYL audit (checklist_type: eeat | ymyl)."""
    cfg = load_config()
    pages = [p for p in (cfg.get("seo") or {}).get("pages") or [] if p.get("type", "html") == "html"]
    if not pages:
        return {"error": "Нет HTML-страниц в config", "results": []}

    page = pages[min(page_index, len(pages) - 1)]
    catalog = catalog_by_type(checklist_type)
    if not catalog:
        return {"error": f"Каталог {checklist_type} пуст", "results": []}

    started = time.perf_counter()
    url = page["url"]
    parsed = urlparse(url)
    base = f"{parsed.scheme}://{parsed.netloc}"
    page_type = page.get("page_type") or ("exchange" if "exchange-" in url else "homepage")

    async with httpx.AsyncClient(timeout=TIMEOUT, follow_redirects=True) as client:
        resp = await client.get(url)
        latency_ms = round((time.perf_counter() - started) * 1000, 1)
        html = resp.text
        robots, sitemap = await _fetch_site_assets(client, base)
        corpus = await _fetch_site_corpus(client, base)

        stack = page.get("stack") or ""
        visible_raw = BeautifulSoup(html, "lxml").get_text("\n", strip=True)
        nuxt_info = analyze_nuxt_html(html, url, visible_raw)
        if stack:
            nuxt_info["is_nuxt"] = detect_nuxt(html, stack)
        asset_ok, asset_note = await check_nuxt_assets(client, nuxt_info.get("nuxt_js_urls") or [])

    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    visible = soup.get_text("\n", strip=True)

    hreflang_map: dict[str, str] = {}
    for link in BeautifulSoup(html, "lxml").find_all("link", rel="alternate"):
        hl = link.get("hreflang")
        href = link.get("href")
        if hl and href:
            hreflang_map[str(hl)] = str(href)

    json_ld_raw = [
        s.get_text(strip=True)
        for s in BeautifulSoup(html, "lxml").find_all("script", type="application/ld+json")
    ]

    ctx = AuditContext(
        url=url,
        page_type=page_type,
        lang=page.get("lang") or ("ru" if "/ru/" in url else "en"),
        pair=page.get("pair") or _pair_from_url(url),
        top_keyword=page.get("top_keyword") or "",
        label=page.get("label") or url,
        final_url=str(resp.url),
        http_status=resp.status_code,
        latency_ms=latency_ms,
        html=html,
        soup=soup,
        visible_text=visible,
        robots_text=robots,
        sitemap_text=sitemap,
        hreflang_map=hreflang_map,
        json_ld_raw=json_ld_raw,
        is_nuxt=bool(nuxt_info.get("is_nuxt")),
        nuxt_info=nuxt_info,
        nuxt_asset_ok=asset_ok,
        nuxt_asset_note=asset_note,
        stack=stack,
    )

    evaluator = _evaluate_eeat if checklist_type == "eeat" else _evaluate_ymyl
    results = []
    for item in catalog:
        ev = evaluator(item, ctx, corpus)
        results.append({**item, **ev})

    summary = _score_results(results)
    block_stats: dict[str, dict] = {}
    for r in results:
        b = r["block"]
        block_stats.setdefault(
            b,
            {"pass": 0, "warn": 0, "fail": 0, "manual": 0, "na": 0, "name": r["block_name"]},
        )
        block_stats[b][r["status"]] += 1

    summary["blocks"] = block_stats
    roadmap = build_priority_roadmap(results)

    return {
        "error": None,
        "checklist_type": checklist_type,
        "url": ctx.url,
        "label": ctx.label,
        "pair": ctx.pair,
        "lang": ctx.lang,
        "page_type": ctx.page_type,
        "summary": summary,
        "results": results,
        "roadmap": roadmap,
        "site_pages_found": list(corpus.pages.keys()),
        "site_corpus": {
            path: BeautifulSoup(html, "lxml").get_text("\n", strip=True)[:3500]
            for path, html in corpus.pages.items()
        },
        "json_ld_corpus": corpus.json_ld[:12],
        "footer_links": corpus.footer_links[:50],
        "llms_txt": (corpus.llms_txt or "")[:2000],
        "latency_ms": round((time.perf_counter() - started) * 1000, 1),
    }
