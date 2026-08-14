"""Daily competitor site monitor — titles, meta, content, new landings."""

from __future__ import annotations

import asyncio
import hashlib
import logging
import re
import xml.etree.ElementTree as ET
from typing import Any
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

from app.config_loader import load_config
from app.drift_monitor import capture_seo_snapshot
from app.storage import (
    finish_competitor_run,
    get_competitor_urls_from_last_run,
    get_known_competitor_paths,
    get_known_competitor_urls,
    get_previous_competitor_snapshots,
    insert_competitor_changes,
    insert_competitor_snapshots,
    start_competitor_run,
    upsert_known_competitor_paths,
)

logger = logging.getLogger(__name__)

TIMEOUT = 25
USER_AGENT = (
    "Mozilla/5.0 (compatible; MarketingSEOBooster/1.0; +https://quickex.io) "
    "CompetitorMonitor/1.0"
)

LANDING_PATTERNS = re.compile(
    r"/(exchange|swap|convert|coins?|currency|pair|buy|sell|blog|learn|how-to|"
    r"about|fees|faq|help|support|api|widget|affiliate|partners?)[/\-_a-z0-9]*",
    re.I,
)

NON_PAGE_EXT = re.compile(
    r"\.(xml|pdf|jpg|jpeg|png|gif|svg|webp|css|js|json|zip|gz|mp4|woff2?|ico)$",
    re.I,
)

SITEMAP_NS = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}


def competitors_config() -> list[dict[str, Any]]:
    cfg = load_config()
    items = (cfg.get("competitors") or {}).get("sites") or []
    if items:
        return items
    return _default_competitors()


def _default_competitors() -> list[dict[str, Any]]:
    return [
        {"id": "changenow", "name": "ChangeNOW", "domain": "changenow.io", "homepage": "https://changenow.io/"},
        {"id": "changelly", "name": "Changelly", "domain": "changelly.com", "homepage": "https://changelly.com/"},
        {"id": "simpleswap", "name": "SimpleSwap", "domain": "simpleswap.io", "homepage": "https://simpleswap.io/"},
        {"id": "godex", "name": "Godex", "domain": "godex.io", "homepage": "https://godex.io/"},
        {"id": "exolix", "name": "Exolix", "domain": "exolix.com", "homepage": "https://exolix.com/"},
        {"id": "fixedfloat", "name": "FixedFloat", "domain": "fixedfloat.com", "homepage": "https://fixedfloat.com/"},
        {"id": "stealthex", "name": "StealthEX", "domain": "stealthex.io", "homepage": "https://stealthex.io/"},
        {"id": "swapzone", "name": "Swapzone", "domain": "swapzone.io", "homepage": "https://swapzone.io/"},
    ]


def _content_hash(title: str, desc: str, h1: str, word_count: int) -> str:
    raw = f"{title}|{desc}|{h1}|{word_count}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def _normalize_path(url: str) -> str:
    p = urlparse(url)
    path = p.path.rstrip("/") or "/"
    return path.lower()


def _domain_match(url: str, domain: str) -> bool:
    host = urlparse(url).netloc.lower().replace("www.", "")
    return host == domain.lower().replace("www.", "") or host.endswith("." + domain.lower().replace("www.", ""))


def _is_page_url(url: str) -> bool:
    path = _normalize_path(url)
    if NON_PAGE_EXT.search(path):
        return False
    if path.startswith("/api/") or "/wp-json" in path:
        return False
    return True


def _score_path(path: str) -> int:
    path = path.lower()
    if path == "/":
        return 95
    if re.search(r"/(exchange|swap|convert|pair)[/\-_]", path):
        return 100
    if re.search(r"/(exchange|swap|convert|pair)$", path):
        return 98
    if re.search(r"/coins?|/currency", path):
        return 85
    if re.search(r"/blog|/learn|/how-to|/news", path):
        return 70
    if re.search(r"/about|/fees|/faq|/help|/support", path):
        return 55
    if LANDING_PATTERNS.search(path):
        return 50
    if re.search(r"/(buy|sell|affiliate|partners?|widget|api)", path):
        return 35
    return 25


async def _fetch_text(client: httpx.AsyncClient, url: str) -> tuple[int, str]:
    try:
        resp = await client.get(url, headers={"User-Agent": USER_AGENT})
        return resp.status_code, resp.text
    except Exception as exc:
        logger.warning("fetch failed %s: %s", url, exc)
        return 0, ""


def _extract_sitemap_locs(xml_text: str) -> tuple[list[str], list[str]]:
    """Return (child_sitemap_urls, page_urls)."""
    child_sitemaps: list[str] = []
    page_urls: list[str] = []
    if not xml_text.strip():
        return child_sitemaps, page_urls
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return child_sitemaps, page_urls

    for loc in root.findall(".//sm:sitemap/sm:loc", SITEMAP_NS):
        if loc.text:
            child_sitemaps.append(loc.text.strip())
    if child_sitemaps:
        return child_sitemaps, page_urls

    for loc in root.findall(".//sm:loc", SITEMAP_NS):
        if loc.text:
            page_urls.append(loc.text.strip())
    if not page_urls:
        for loc in root.findall(".//loc"):
            if loc.text:
                page_urls.append(loc.text.strip())
    return child_sitemaps, page_urls


async def _fetch_sitemap_urls(
    client: httpx.AsyncClient,
    sitemap_url: str,
    domain: str,
    limit: int,
    depth: int = 0,
    max_depth: int = 2,
    max_child_sitemaps: int = 12,
) -> list[str]:
    status, xml = await _fetch_text(client, sitemap_url)
    if status != 200 or not xml:
        return []

    child_sitemaps, page_urls = _extract_sitemap_locs(xml)
    collected: list[str] = []

    if child_sitemaps and depth < max_depth:
        for child in child_sitemaps[:max_child_sitemaps]:
            collected.extend(
                await _fetch_sitemap_urls(
                    client, child, domain, limit, depth + 1, max_depth, max_child_sitemaps
                )
            )
            if len(collected) >= limit * 2:
                break

    for u in page_urls:
        if _domain_match(u, domain) and _is_page_url(u):
            collected.append(u.split("#")[0])

    seen: set[str] = set()
    scored: list[tuple[int, str]] = []
    for u in collected:
        path = _normalize_path(u)
        if path in seen:
            continue
        seen.add(path)
        scored.append((_score_path(path), u))

    scored.sort(key=lambda x: (-x[0], x[1]))
    return [u for _, u in scored[:limit]]


async def _discover_urls(
    client: httpx.AsyncClient,
    spec: dict[str, Any],
    max_pages: int,
) -> list[str]:
    domain = spec["domain"]
    homepage = spec.get("homepage") or f"https://{domain}/"
    base = f"https://{domain}"
    cid = spec["id"]

    urls: list[str] = [homepage]
    urls.extend(get_known_competitor_urls(cid))
    urls.extend(get_competitor_urls_from_last_run(cid))

    seed_paths = spec.get("seed_paths") or [
        "/exchange",
        "/exchange-btc-eth",
        "/coins",
        "/blog",
        "/about",
        "/fees",
        "/faq",
    ]
    for path in seed_paths:
        urls.append(urljoin(base, path))

    sitemap_url = spec.get("sitemap") or f"https://{domain}/sitemap.xml"
    urls.extend(await _fetch_sitemap_urls(client, sitemap_url, domain, max_pages))

    extra_sitemaps = spec.get("sitemap_indexes") or []
    for sm in extra_sitemaps:
        urls.extend(await _fetch_sitemap_urls(client, sm, domain, max_pages))

    status, html = await _fetch_text(client, homepage)
    if status == 200 and html:
        soup = BeautifulSoup(html, "lxml")
        for a in soup.find_all("a", href=True):
            href = urljoin(homepage, str(a["href"]))
            if _domain_match(href, domain) and _is_page_url(href):
                urls.append(href.split("#")[0])

    scored: list[tuple[int, str]] = []
    seen_paths: set[str] = set()
    for u in urls:
        if not _domain_match(u, domain) or not _is_page_url(u):
            continue
        path = _normalize_path(u)
        if path in seen_paths:
            continue
        seen_paths.add(path)
        scored.append((_score_path(path), u))

    scored.sort(key=lambda x: (-x[0], x[1]))
    return [u for _, u in scored[:max_pages]]


async def _capture_page(client: httpx.AsyncClient, url: str) -> dict[str, Any]:
    try:
        snap = await capture_seo_snapshot(url)
    except Exception as exc:
        return {
            "url": url,
            "path": _normalize_path(url),
            "http_status": 0,
            "error": str(exc)[:200],
            "title": "",
            "meta_description": "",
            "h1": "",
            "word_count": 0,
            "content_preview": "",
            "content_hash": "",
        }

    h1 = " | ".join(snap.get("h1") or [])[:300]
    preview = ""
    try:
        status, html = await _fetch_text(client, url)
        if status == 200:
            soup = BeautifulSoup(html, "lxml")
            for tag in soup(["script", "style", "noscript"]):
                tag.decompose()
            preview = soup.get_text(" ", strip=True)[:500]
    except Exception:
        pass

    return {
        "url": url,
        "path": _normalize_path(url),
        "final_url": snap.get("final_url", url),
        "http_status": snap.get("http_status", 0),
        "title": snap.get("title", ""),
        "meta_description": snap.get("meta_description", ""),
        "h1": h1,
        "word_count": snap.get("word_count", 0),
        "content_preview": preview,
        "content_hash": _content_hash(
            snap.get("title", ""),
            snap.get("meta_description", ""),
            h1,
            snap.get("word_count", 0),
        ),
        "html_hash": snap.get("html_hash", ""),
    }


def _diff_pages(
    competitor_id: str,
    previous: dict[str, dict[str, Any]],
    known_paths: set[str],
    current_pages: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    changes: list[dict[str, Any]] = []
    prev_paths = set(previous.keys())
    has_history = bool(known_paths)

    for page in current_pages:
        path = page["path"]
        prev = previous.get(path)

        if not prev:
            if has_history and path not in known_paths:
                changes.append(
                    {
                        "competitor_id": competitor_id,
                        "url": page["url"],
                        "path": path,
                        "change_type": "new_landing",
                        "field": "url",
                        "before_val": "",
                        "after_val": page["url"],
                        "severity": "high",
                        "title": page.get("title", ""),
                        "meta_description": page.get("meta_description", ""),
                    }
                )
                page["is_new"] = True
            else:
                page["is_new"] = False
            continue

        page["is_new"] = False
        checks = [
            ("title", "title_changed", "warning", prev.get("title"), page.get("title")),
            ("meta_description", "description_changed", "warning", prev.get("meta_description"), page.get("meta_description")),
            ("h1", "h1_changed", "info", prev.get("h1"), page.get("h1")),
            ("content_hash", "content_changed", "warning", prev.get("content_hash"), page.get("content_hash")),
        ]
        for field, ctype, sev, before, after in checks:
            if before != after and (before or after):
                changes.append(
                    {
                        "competitor_id": competitor_id,
                        "url": page["url"],
                        "path": path,
                        "change_type": ctype,
                        "field": field,
                        "before_val": (before or "")[:500],
                        "after_val": (after or "")[:500],
                        "severity": sev,
                        "title": page.get("title", ""),
                        "meta_description": page.get("meta_description", ""),
                    }
                )

        wc_before = prev.get("word_count") or 0
        wc_after = page.get("word_count") or 0
        if wc_before and abs(wc_after - wc_before) / wc_before > 0.15:
            changes.append(
                {
                    "competitor_id": competitor_id,
                    "url": page["url"],
                    "path": path,
                    "change_type": "word_count_changed",
                    "field": "word_count",
                    "before_val": str(wc_before),
                    "after_val": str(wc_after),
                    "severity": "info",
                    "title": page.get("title", ""),
                    "meta_description": page.get("meta_description", ""),
                }
            )

    for path in prev_paths - {_normalize_path(p["url"]) for p in current_pages}:
        prev = previous[path]
        changes.append(
            {
                "competitor_id": competitor_id,
                "url": prev.get("url", path),
                "path": path,
                "change_type": "page_removed",
                "field": "url",
                "before_val": prev.get("url", ""),
                "after_val": "",
                "severity": "medium",
                "title": prev.get("title", ""),
                "meta_description": "",
            }
        )

    return changes


async def run_competitor_scan(trigger: str = "manual") -> dict[str, Any]:
    sites = competitors_config()
    if not sites:
        return {"error": "Нет конкурентов в config", "changes": []}

    cfg = (load_config().get("competitors") or {})
    max_pages = int(cfg.get("max_pages_per_site") or 100)
    concurrency = int(cfg.get("concurrency") or 6)

    run_id = start_competitor_run(trigger)
    all_snapshots: list[dict[str, Any]] = []
    all_changes: list[dict[str, Any]] = []
    new_paths_total = 0

    async with httpx.AsyncClient(timeout=TIMEOUT, follow_redirects=True) as client:
        sem = asyncio.Semaphore(concurrency)

        for spec in sites:
            cid = spec["id"]
            name = spec.get("name") or cid
            logger.info("competitor scan: %s (up to %d pages)", name, max_pages)

            known_paths = get_known_competitor_paths(cid)
            urls = await _discover_urls(client, spec, max_pages)
            previous = get_previous_competitor_snapshots(cid)

            async def _cap(u: str) -> dict[str, Any]:
                async with sem:
                    page = await _capture_page(client, u)
                    page["competitor_id"] = cid
                    page["competitor_name"] = name
                    return page

            pages = list(await asyncio.gather(*[_cap(u) for u in urls]))
            changes = _diff_pages(cid, previous, known_paths, pages)
            new_paths_total += upsert_known_competitor_paths(cid, run_id, pages)
            for c in changes:
                c["competitor_name"] = name

            for p in pages:
                p["has_changes"] = any(c["path"] == p["path"] for c in changes)
            all_snapshots.extend(pages)
            all_changes.extend(changes)

    insert_competitor_snapshots(run_id, all_snapshots)
    insert_competitor_changes(run_id, all_changes)

    summary = {
        "status": "ok",
        "sites": len(sites),
        "pages_scanned": len(all_snapshots),
        "max_pages_per_site": max_pages,
        "changes_total": len(all_changes),
        "new_landings": sum(1 for c in all_changes if c["change_type"] == "new_landing"),
        "new_paths_registered": new_paths_total,
        "title_changes": sum(1 for c in all_changes if c["change_type"] == "title_changed"),
        "desc_changes": sum(1 for c in all_changes if c["change_type"] == "description_changed"),
        "content_changes": sum(1 for c in all_changes if c["change_type"] == "content_changed"),
    }
    finish_competitor_run(run_id, summary, all_changes)
    return {"run_id": run_id, "error": None, "summary": summary, "changes": all_changes}


def build_changes_csv(changes: list[dict[str, Any]]) -> str:
    import csv
    import io

    fields = [
        "competitor_id",
        "competitor_name",
        "change_type",
        "severity",
        "url",
        "path",
        "field",
        "before_val",
        "after_val",
        "title",
        "meta_description",
    ]
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    for row in changes:
        writer.writerow({k: row.get(k, "") for k in fields})
    return buf.getvalue()


def build_snapshots_csv(snapshots: list[dict[str, Any]]) -> str:
    import csv
    import io

    fields = [
        "competitor_id",
        "competitor_name",
        "url",
        "path",
        "http_status",
        "title",
        "meta_description",
        "h1",
        "word_count",
        "content_hash",
        "is_new",
        "has_changes",
    ]
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    for row in snapshots:
        writer.writerow({k: row.get(k, "") for k in fields})
    return buf.getvalue()
