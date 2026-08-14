"""Run automated checks for Quickex 100-criteria SEO checklist."""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

from app.checklist_catalog import load_catalog
from app.config_loader import load_config
from app.nuxt_auditor import analyze_nuxt_html, check_nuxt_assets, detect_nuxt, evaluate_nuxt_item
from app.pro_seo_auditor import (
    SiteProContext,
    build_priority_roadmap,
    build_site_pro_context,
    evaluate_pro_item,
)

TIMEOUT = 25
DEFER_IDS = {"071", "072", "073"}
TICKER_DUP = re.compile(r"\b([A-Z]{2,10})\s*\(\1\)", re.I)
BAD_TEMPLATE = re.compile(r"\{instrument|\[template:|1122|\b123\b", re.I)
OVERCLAIM = re.compile(r"100%\s*(anonymous|untraceable)|untraceable", re.I)


@dataclass
class AuditContext:
    url: str
    page_type: str
    lang: str
    pair: str
    top_keyword: str
    label: str
    final_url: str = ""
    http_status: int | None = None
    latency_ms: float = 0
    html: str = ""
    soup: BeautifulSoup | None = None
    visible_text: str = ""
    robots_text: str = ""
    sitemap_text: str = ""
    hreflang_map: dict[str, str] = field(default_factory=dict)
    json_ld_raw: list[str] = field(default_factory=list)
    is_nuxt: bool = False
    nuxt_info: dict[str, Any] = field(default_factory=dict)
    nuxt_asset_ok: bool = False
    nuxt_asset_note: str = ""
    stack: str = ""


def _scope_applies(scope: str, ctx: AuditContext) -> bool:
    if scope == "ALL":
        return True
    if scope == "SITE":
        return True
    if scope == "RU":
        return ctx.lang == "ru" or "/ru/" in ctx.url
    if scope == "EX":
        return ctx.page_type == "exchange"
    if scope == "HP":
        return ctx.page_type == "homepage"
    if scope == "PR":
        return ctx.page_type == "premium"
    return True


def _na(item_id: str, note: str = "") -> dict[str, Any]:
    return {"status": "na", "evidence": note or "Не применимо к этой странице"}


def _pass(evidence: str = "") -> dict[str, Any]:
    return {"status": "pass", "evidence": evidence}


def _warn(evidence: str) -> dict[str, Any]:
    return {"status": "warn", "evidence": evidence}


def _fail(evidence: str) -> dict[str, Any]:
    return {"status": "fail", "evidence": evidence}


def _manual(note: str = "Требует ручной проверки или TMS/Ahrefs") -> dict[str, Any]:
    return {"status": "manual", "evidence": note}


def _meta(soup: BeautifulSoup, name: str | None = None, prop: str | None = None) -> str | None:
    if name:
        tag = soup.find("meta", attrs={"name": name})
        if tag and tag.get("content"):
            return str(tag["content"]).strip()
    if prop:
        tag = soup.find("meta", attrs={"property": prop})
        if tag and tag.get("content"):
            return str(tag["content"]).strip()
    return None


def _h1(soup: BeautifulSoup) -> str | None:
    el = soup.find("h1")
    return el.get_text(strip=True) if el else None


def _canonical(soup: BeautifulSoup) -> str | None:
    tag = soup.find("link", rel="canonical")
    return str(tag["href"]).strip() if tag and tag.get("href") else None


def _pair_from_url(url: str) -> str:
    m = re.search(r"/exchange-([a-z0-9]+)-([a-z0-9]+)", url, re.I)
    if m:
        return f"{m.group(1)}-{m.group(2)}".lower()
    return ""


def _evaluate(item: dict, ctx: AuditContext) -> dict[str, Any]:
    iid = item["id"]
    if iid in DEFER_IDS:
        return _na(iid, "DEFER — не оценивается без явного запроса")

    if not _scope_applies(item["scope"], ctx):
        return _na(iid)

    soup = ctx.soup
    text = ctx.visible_text
    title = soup.title.string.strip() if soup and soup.title and soup.title.string else None
    desc = _meta(soup, name="description") if soup else None
    h1 = _h1(soup) if soup else None
    canonical = _canonical(soup) if soup else None
    robots = _meta(soup, name="robots") if soup else None

    handlers: dict[str, Any] = {}

    # A — Technical
    if iid == "001":
        return _pass(f"HTTP {ctx.http_status}") if ctx.http_status == 200 else _fail(f"HTTP {ctx.http_status}")
    if iid == "002":
        if not canonical:
            return _warn("Canonical отсутствует — нельзя сверить final URL")
        c_path = urlparse(canonical).path.rstrip("/")
        f_path = urlparse(ctx.final_url).path.rstrip("/")
        return _pass() if c_path == f_path else _warn(f"canonical={c_path} vs final={f_path}")
    if iid == "003":
        if robots and "noindex" in robots.lower():
            return _fail(f"robots: {robots}")
        return _pass(robots or "index по умолчанию")
    if iid == "004":
        return _pass(canonical) if canonical else _fail("Canonical не найден")
    if iid == "005":
        if ctx.page_type != "exchange":
            return _na(iid)
        if not canonical:
            return _fail("Нет canonical")
        pair = ctx.pair or _pair_from_url(ctx.url)
        return _pass() if pair and pair in canonical.lower() else _fail(f"canonical не содержит пару {pair}")
    if iid == "006":
        return _pass() if ctx.url.startswith("https://") else _fail("Не HTTPS")
    if iid == "007":
        return _manual("Проверка www/non-www — site-level")
    if iid == "008":
        return _manual("Сравнить trailing slash policy")
    if iid == "009":
        if not ctx.robots_text:
            return _fail("robots.txt недоступен")
        if re.search(r"Disallow:\s*/\s*$", ctx.robots_text, re.M):
            return _fail("Disallow: / блокирует всё")
        return _pass("robots.txt OK")
    if iid == "010":
        return _pass() if "Sitemap:" in ctx.robots_text else _fail("Нет Sitemap: в robots.txt")
    if iid == "011":
        if not ctx.sitemap_text:
            return _fail("sitemap недоступен")
        if "<urlset" in ctx.sitemap_text or "<sitemapindex" in ctx.sitemap_text:
            return _pass("XML sitemap OK")
        return _fail("Невалидный sitemap")
    if iid == "012":
        if ctx.page_type != "exchange":
            return _na(iid)
        path = urlparse(ctx.url).path
        return _pass() if path in ctx.sitemap_text else _warn(f"URL не найден в sitemap: {path}")
    if iid == "013":
        if not h1:
            return _fail("H1 отсутствует — возможен пустой shell")
        return _pass() if len(text) > 200 else _warn(f"Мало текста в body: {len(text)} chars")
    if iid == "014":
        vp = soup.find("meta", attrs={"name": "viewport"}) if soup else None
        return _pass() if vp else _fail("Нет viewport meta")
    if iid == "015":
        charset = soup.find("meta", charset=True) if soup else None
        if charset:
            return _pass(str(charset.get("charset", "")))
        ct = _meta(soup, name=None)  # noqa — check http-equiv
        tag = soup.find("meta", attrs={"http-equiv": re.compile("content-type", re.I)}) if soup else None
        return _pass() if tag or charset else _warn("Charset не явно задан")
    if iid == "016":
        return _manual("Link checker на первом экране")
    if iid == "017":
        if ctx.page_type != "exchange":
            return _na(iid)
        pair = ctx.pair or _pair_from_url(ctx.url)
        parts = pair.split("-") if pair else []
        if h1 and parts and all(p.upper() in h1.upper() for p in parts[:2]):
            return _pass(h1[:80])
        return _warn(f"H1 может не соответствовать slug {pair}")
    if iid == "018":
        if ctx.latency_ms <= 3000:
            return _pass(f"{ctx.latency_ms}ms")
        if ctx.latency_ms <= 6000:
            return _warn(f"{ctx.latency_ms}ms (>3s)")
        return _fail(f"{ctx.latency_ms}ms (>6s)")
    if iid == "019":
        return _manual("Проверка UTM/session дублей")
    if iid == "020":
        return _manual("Проверка кастомной 404 — отдельный URL")

    # B — Meta
    if iid == "021":
        return _pass(title[:60]) if title else _fail("Title пустой")
    if iid == "022":
        if not title:
            return _fail("Нет title")
        n = len(title)
        return _pass(f"{n} chars") if 45 <= n <= 65 else _warn(f"{n} chars (норма 45–65)")
    if iid == "023":
        if ctx.page_type != "exchange" or not ctx.top_keyword:
            return _manual("Нужен top_keyword из Ahrefs")
        kw = ctx.top_keyword.lower().split()[0]
        return _pass() if kw in (title or "").lower() else _warn(f"KW «{kw}» не в начале title")
    if iid == "024":
        return _pass() if title and "quickex" in title.lower() else _warn("Quickex не в title")
    if iid == "025":
        return _manual("Уникальность title — сравнение с другими парами")
    if iid == "026":
        return _pass() if desc else _fail("meta description отсутствует")
    if iid == "027":
        if not desc:
            return _fail("Нет description")
        n = len(desc)
        return _pass(f"{n}") if 120 <= n <= 170 else _warn(f"{n} chars (норма 120–170)")
    if iid == "028":
        if not desc:
            return _fail("Нет description")
        return _fail(f"{len(desc)} chars — похоже на body-copy") if len(desc) > 300 else _pass(f"{len(desc)} chars")
    if iid == "029":
        if title and h1 and title.strip().lower() == h1.strip().lower():
            return _warn("Title дублирует H1")
        return _pass()
    if iid == "030":
        return _manual("Оценка intent+CTA — editorial")
    if iid == "031":
        og = _meta(soup, prop="og:title") if soup else None
        return _pass() if og else _warn("og:title пуст")
    if iid == "032":
        og = _meta(soup, prop="og:description") if soup else None
        return _pass() if og else _warn("og:description пуст")
    if iid == "033":
        og = _meta(soup, prop="og:image") if soup else None
        if og and og.startswith("http"):
            return _pass(og[:60])
        return _warn("og:image отсутствует или относительный URL")
    if iid == "034":
        tw = soup.find("meta", attrs={"name": "twitter:card"}) if soup else None
        return _pass() if tw else _warn("twitter:card не задан")
    if iid == "035":
        tw_t = soup.find("meta", attrs={"name": "twitter:title"}) if soup else None
        tw_d = soup.find("meta", attrs={"name": "twitter:description"}) if soup else None
        return _pass() if tw_t and tw_d else _warn("Twitter meta неполный")

    # C — Content
    if iid == "036":
        h1s = soup.find_all("h1") if soup else []
        if len(h1s) == 1:
            return _pass(h1[:80] if h1 else "")
        return _fail(f"Найдено H1: {len(h1s)}")
    if iid == "037":
        if not h1:
            return _fail("Нет H1")
        if re.search(r"\([A-Z]{2,10}\)", h1) and " to " in h1.lower():
            return _pass(h1[:80])
        return _warn("H1 без полного формата «Name (TICKER) to …»")
    if iid == "038":
        return _fail("Найден BTC (BTC) паттерн") if h1 and TICKER_DUP.search(h1) else _pass()
    if iid == "039":
        if title and h1 and title.lower() == h1.lower():
            return _warn("H1 = title")
        return _pass()
    if iid == "040":
        if ctx.page_type != "exchange":
            return _na(iid)
        sub = soup.find(class_=re.compile("subtitle|main_subtitle", re.I)) if soup else None
        return _pass() if sub and sub.get_text(strip=True) else _warn("Subtitle не найден в HTML")
    if iid in {"041", "045", "046", "047", "053", "054", "055", "056", "057"}:
        if ctx.page_type != "exchange":
            return _na(iid)
        keywords = {
            "041": r"how|exchange|step",
            "045": r"rate|today|exchange rate",
            "046": r"exchange|other crypto|pair",
            "047": r"swap|crypto to",
            "053": r"why|benefit",
            "054": r"kyc|anonymous|registration",
            "055": r"transparent|rate|fee",
            "056": r"instant|swap|fast",
            "057": r"review|trust|rating",
        }
        return _pass() if re.search(keywords[iid], text, re.I) else _warn("Блок не обнаружен по тексту")
    if iid == "042":
        if ctx.page_type != "exchange":
            return _na(iid)
        steps = len(re.findall(r"how.?step|step\s*[1-4]", text, re.I))
        return _pass(f"~{steps} step refs") if steps >= 2 else _warn("Мало how-step контента")
    if iid == "043":
        return _manual("how_text bodies — нужен expand/TMS")
    if iid == "044":
        chunk = text[:8000]
        if BAD_TEMPLATE.search(chunk) or TICKER_DUP.search(chunk):
            return _fail("Template leak или TICKER (TICKER) в контенте")
        return _pass()
    if iid == "048":
        return _manual("Клик по перелинковке")
    if iid == "049":
        faq = len(re.findall(r"faq|accordion|question", text, re.I))
        return _pass() if faq >= 2 else _warn("FAQ блок слабо выражен")
    if iid == "050":
        return _manual("Editorial: уникальность FAQ")
    if iid == "051":
        if ctx.page_type != "exchange":
            return _na(iid)
        return _pass() if re.search(r"what is|about|bitcoin|monero", text, re.I) else _warn("About block не найден")
    if iid == "052":
        if re.search(r"BTC\s*\(\s*Bitcoin\s*\)", text, re.I):
            return _fail("Найден BTC (Bitcoin):")
        return _pass()
    if iid == "058":
        return _manual("Клик nav anchors")
    if iid == "059":
        if ctx.page_type != "homepage":
            return _na(iid)
        return _pass(h1[:60]) if h1 and len(h1) > 15 else _warn("Слабый H1 на homepage")
    if iid == "060":
        if ctx.page_type != "premium":
            return _na(iid)
        if title and len(title) > 100:
            return _fail("Title слишком длинный — body in meta")
        if desc and len(desc) > 300:
            return _fail("Description — body-copy")
        return _pass()

    # D — LQA
    if iid == "061":
        return _manual("Сверка направления пары с виджетом")
    if iid == "062":
        if ctx.lang != "ru" and "/ru/" not in ctx.url:
            return _na(iid)
        if re.search(r"\bswap\b", text, re.I):
            return _fail("Латинское swap в RU тексте")
        return _pass()
    if iid == "063":
        return _manual("EN↔RU parity — side by side")
    if iid == "064":
        if re.search(r"\b[2-9]\d?%\s*(fee|commission)", text, re.I):
            return _warn("Нестандартный % fee в тексте")
        if re.search(r"1%|0\.5%|1 %|0\.5 %", text):
            return _pass("Fee 1% / 0.5% упомянуты")
        return _warn("Fee не найдены в тексте")
    if iid == "065":
        if OVERCLAIM.search(text):
            return _fail("Overclaim anonymous/untraceable")
        return _pass()
    if iid == "066":
        if "xmr" in ctx.pair and OVERCLAIM.search(text):
            return _fail("Privacy overclaim на xmr-паре")
        return _pass() if "xmr" in ctx.pair else _na(iid)
    if iid == "067":
        if re.search(r"USDT\s*\(\s*USDT\s*\)", text, re.I):
            return _fail("USDT (USDT)")
        return _pass()
    if iid in {"068", "069", "070"}:
        return _manual("TMS GET required")
    if iid == "074":
        if re.search(r"Quicex|Quick Ex", text, re.I):
            return _fail("Опечатка бренда")
        return _pass()
    if iid == "075":
        if re.search(r"we store|мы храним|custodial", text, re.I):
            return _warn("Custodial wording")
        return _pass()

    # E — Keywords (mostly manual)
    if iid in {f"{i:03d}" for i in range(76, 86)}:
        if iid == "079":
            return _pass()  # skip stuffing auto
        if iid == "080" and "xmr" in ctx.pair:
            if re.search(r"anonymous|no kyc|private|fast", text, re.I):
                return _pass()
            return _warn("Privacy KW слабо выражены")
        return _manual("Ahrefs / competitor data")

    # F — Schema
    if iid == "086":
        return _pass(f"{len(ctx.json_ld_raw)} blocks") if ctx.json_ld_raw else _warn("JSON-LD отсутствует")
    if iid == "087":
        has_faq = any("FAQPage" in j for j in ctx.json_ld_raw)
        has_faq_text = "faq" in text.lower()
        if has_faq_text and not has_faq:
            return _warn("FAQ на странице, но FAQPage schema нет")
        return _pass() if has_faq else _na(iid)
    if iid == "088":
        return _manual("Сверка FAQ schema vs visible")
    if iid == "089":
        if ctx.page_type == "homepage":
            has_org = any("Organization" in j or "WebSite" in j for j in ctx.json_ld_raw)
            return _pass() if has_org else _warn("Нет Organization/WebSite")
        return _manual("Site-level schema")
    if iid == "090":
        for raw in ctx.json_ld_raw:
            try:
                json.loads(raw)
            except json.JSONDecodeError as e:
                return _fail(str(e))
        return _pass() if ctx.json_ld_raw else _warn("Нет JSON-LD")

    # G — i18n
    if iid == "091":
        return _pass(f"{len(ctx.hreflang_map)} langs") if ctx.hreflang_map else _fail("hreflang отсутствует")
    if iid == "092":
        return _pass() if "x-default" in ctx.hreflang_map else _warn("Нет x-default")
    if iid == "093":
        return _manual("Reciprocal hreflang — нужен fetch других lang URL")
    if iid == "094":
        return _manual("Fetch каждого hreflang URL")
    if iid == "095":
        if ctx.lang == "ru" or "/ru/" in ctx.url:
            if re.search(r"[а-яА-ЯёЁ]{20,}", text):
                return _pass("Есть кириллица")
            return _fail("RU страница без кириллицы — возможен EN duplicate")
        return _na(iid)

    # H — Trust
    if iid == "096":
        icon = soup.find("link", rel=re.compile("icon", re.I)) if soup else None
        return _pass() if icon else _warn("Favicon не найден")
    if iid == "097":
        return _manual("Visual: popups")
    if iid == "098":
        if ctx.page_type != "exchange":
            return _na(iid)
        widget = soup.find(class_=re.compile("exchange|swap|widget", re.I)) if soup else None
        return _pass() if widget or "exchange" in text.lower() else _warn("Widget не найден в DOM")
    if iid == "099":
        return _pass(f"TTFB {ctx.latency_ms}ms") if ctx.latency_ms < 2500 else _warn("LCP proxy via TTFB >2.5s")
    if iid == "100":
        imgs = soup.find_all("img") if soup else []
        if not imgs:
            return _pass("Нет img")
        missing_alt = sum(1 for img in imgs[:20] if not img.get("alt"))
        return _warn(f"{missing_alt} img без alt (sample 20)") if missing_alt else _pass()

    return _manual("Handler not implemented")


def _score_results(results: list[dict]) -> dict[str, Any]:
    points = {"pass": 1.0, "warn": 0.5, "fail": 0.0, "manual": 0.0, "na": None}
    total = 0.0
    applicable = 0
    counts = {k: 0 for k in ("pass", "warn", "fail", "manual", "na")}
    critical_fail = 0

    for r in results:
        st = r["status"]
        counts[st] = counts.get(st, 0) + 1
        if st == "na":
            continue
        applicable += 1
        p = points.get(st, 0)
        if p is not None:
            total += p
        if st == "fail" and r.get("severity") == "critical":
            critical_fail += 1

    score = round((total / applicable) * 100, 1) if applicable else 0
    if critical_fail:
        grade = "F"
    elif score >= 90:
        grade = "A"
    elif score >= 75:
        grade = "B"
    elif score >= 60:
        grade = "C"
    else:
        grade = "F"

    return {
        "score": score,
        "grade": grade,
        "applicable": applicable,
        "counts": counts,
        "critical_fail": critical_fail,
        "status": "fail" if critical_fail else ("warn" if counts["fail"] or counts["warn"] else "ok"),
    }


async def _fetch_site_assets(client: httpx.AsyncClient, base: str) -> tuple[str, str]:
    robots, sitemap = "", ""
    try:
        r = await client.get(f"{base}/robots.txt")
        if r.status_code == 200:
            robots = r.text
    except Exception:
        pass
    try:
        s = await client.get(f"{base}/sitemap.xml")
        if s.status_code == 200:
            sitemap = s.text
    except Exception:
        pass
    return robots, sitemap


async def run_checklist_audit(
    page: dict[str, str] | None = None,
    pro_ctx: SiteProContext | None = None,
) -> dict[str, Any]:
    cfg = load_config()
    seo_cfg = cfg.get("seo") or {}
    pages = seo_cfg.get("pages") or []

    if page is None:
        for p in pages:
            if p.get("pair") and p.get("type", "html") == "html":
                page = p
                break
        if page is None and pages:
            page = pages[0]

    if not page:
        return {"error": "Нет страницы для аудита в config", "results": []}

    url = page["url"]
    parsed = urlparse(url)
    base = f"{parsed.scheme}://{parsed.netloc}"
    page_type = page.get("page_type") or ("exchange" if "exchange-" in url else "homepage")

    async with httpx.AsyncClient(timeout=TIMEOUT, follow_redirects=True) as client:
        started = time.perf_counter()
        resp = await client.get(url)
        latency_ms = round((time.perf_counter() - started) * 1000, 1)
        html = resp.text
        robots, sitemap = await _fetch_site_assets(client, base)

        stack = page.get("stack") or ""
        visible_raw = BeautifulSoup(html, "lxml").get_text("\n", strip=True)
        nuxt_info = analyze_nuxt_html(html, url, visible_raw)
        if stack:
            nuxt_info["is_nuxt"] = detect_nuxt(html, stack)
        asset_ok, asset_note = await check_nuxt_assets(client, nuxt_info.get("nuxt_js_urls") or [])

        html_pages = [p for p in pages if p.get("type", "html") == "html"]
        page_urls = [p["url"] for p in html_pages]
        if pro_ctx is None:
            pro_ctx = await build_site_pro_context(client, base, page_urls, robots)

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

    catalog = load_catalog()
    current_snap: dict[str, Any] = {}
    for snap in pro_ctx.page_snapshots:
        snap_url = str(snap.get("url", "")).rstrip("/")
        if snap_url == url.rstrip("/") or snap_url == str(resp.url).rstrip("/"):
            current_snap = snap
            break
    if not current_snap:
        current_snap = _page_meta_from_ctx(ctx)

    results = []
    for item in catalog:
        iid = int(item["id"])
        if item["block"] == "N" or (101 <= iid <= 120):
            ev = evaluate_nuxt_item(item["id"], nuxt_info, asset_ok, asset_note, url)
        elif iid >= 121:
            ev = evaluate_pro_item(item["id"], pro_ctx, current_snap)
        else:
            ev = _evaluate(item, ctx)
        results.append({**item, **ev})

    roadmap = build_priority_roadmap(results)

    summary = _score_results(results)
    block_stats: dict[str, dict] = {}
    for r in results:
        b = r["block"]
        block_stats.setdefault(b, {"pass": 0, "warn": 0, "fail": 0, "manual": 0, "na": 0, "name": r["block_name"]})
        block_stats[b][r["status"]] += 1

    return {
        "error": None,
        "url": url,
        "label": ctx.label,
        "pair": ctx.pair,
        "lang": ctx.lang,
        "page_type": page_type,
        "summary": summary,
        "blocks": block_stats,
        "results": results,
        "latency_ms": latency_ms,
        "stack": stack,
        "is_nuxt": bool(nuxt_info.get("is_nuxt")),
        "roadmap": roadmap,
        "pro_summary": {
            "bot_access": pro_ctx.bot_access,
            "duplicate_titles": pro_ctx.duplicate_titles,
            "duplicate_descriptions": pro_ctx.duplicate_descriptions,
            "llms_txt_ok": pro_ctx.llms_txt_ok,
        },
    }


def _page_meta_from_ctx(ctx: AuditContext) -> dict[str, Any]:
    """Fallback page snapshot from current audit context."""
    soup = ctx.soup or BeautifulSoup(ctx.html, "lxml")
    title_tag = soup.find("title")
    desc_tag = soup.find("meta", attrs={"name": "description"})
    h1_el = soup.find("h1")
    return {
        "url": ctx.url,
        "title": title_tag.get_text(strip=True) if title_tag else "",
        "description": str(desc_tag["content"]).strip() if desc_tag and desc_tag.get("content") else "",
        "h1": h1_el.get_text(strip=True) if h1_el else "",
        "canonical": _canonical(soup) or "",
        "internal_links": len(soup.find_all("a", href=True)),
        "mixed_http": len(re.findall(r'(?:src|href)=["\']http://', ctx.html, re.I)),
        "tables": len(soup.find_all("table")),
        "faq_schema": any("FAQPage" in raw for raw in ctx.json_ld_raw),
        "ld_names": [],
    }
