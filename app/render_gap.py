"""Feature 5: Render Gap Lab — raw HTML vs rendered DOM diff."""

from __future__ import annotations

import re
from typing import Any

import httpx
from bs4 import BeautifulSoup

TIMEOUT = 30


def _extract_signals(html: str, url: str) -> dict[str, Any]:
    soup = BeautifulSoup(html, "lxml")
    title = soup.find("title")
    h1 = soup.find("h1")
    desc = soup.find("meta", attrs={"name": "description"})
    schemas = soup.find_all("script", type="application/ld+json")
    from urllib.parse import urljoin, urlparse

    internal = 0
    base_host = urlparse(url).netloc.lower()
    for a in soup.find_all("a", href=True):
        href = str(a["href"])
        if href.startswith(("#", "mailto:", "tel:", "javascript:")):
            continue
        if urlparse(urljoin(url, href)).netloc.lower() == base_host:
            internal += 1

    visible = soup.get_text("\n", strip=True)
    return {
        "title": title.get_text(strip=True) if title else "",
        "h1": h1.get_text(strip=True) if h1 else "",
        "meta_description": str(desc["content"]).strip() if desc and desc.get("content") else "",
        "schema_count": len(schemas),
        "internal_links": internal,
        "word_count": len(visible.split()),
        "has_canonical": bool(soup.find("link", rel="canonical")),
    }


async def _fetch_raw(url: str) -> tuple[str, dict[str, Any]]:
    async with httpx.AsyncClient(timeout=TIMEOUT, follow_redirects=True) as client:
        resp = await client.get(url)
        return resp.text, {"http_status": resp.status_code, "final_url": str(resp.url)}


async def _fetch_rendered(url: str) -> tuple[str | None, str | None]:
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        return None, "Playwright не установлен: pip install playwright && playwright install chromium"

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto(url, wait_until="networkidle", timeout=45000)
            html = await page.content()
            await browser.close()
            return html, None
    except Exception as exc:
        return None, str(exc)[:200]


def _diff_signals(raw: dict[str, Any], rendered: dict[str, Any]) -> list[dict[str, Any]]:
    gaps: list[dict[str, Any]] = []
    checks = (
        ("title", "critical"),
        ("h1", "critical"),
        ("meta_description", "high"),
        ("word_count", "high"),
        ("internal_links", "medium"),
        ("schema_count", "medium"),
    )
    for field, severity in checks:
        rv, rend = raw.get(field), rendered.get(field)
        if field == "word_count":
            if rend > rv * 1.3 and rv < 200:
                gaps.append(
                    {
                        "field": field,
                        "severity": severity,
                        "raw": rv,
                        "rendered": rend,
                        "message": f"Слов: {rv} → {rend} (контент только после JS)",
                    }
                )
            elif rv > 0 and rend < rv * 0.5:
                gaps.append(
                    {
                        "field": field,
                        "severity": "warning",
                        "raw": rv,
                        "rendered": rend,
                        "message": f"После рендера меньше слов ({rend} vs {rv})",
                    }
                )
        elif field in ("internal_links", "schema_count"):
            if rend > rv + 2:
                gaps.append(
                    {
                        "field": field,
                        "severity": severity,
                        "raw": rv,
                        "rendered": rend,
                        "message": f"{field}: {rv} → {rend} (только через JS)",
                    }
                )
        elif rv != rend:
            if not rv and rend:
                gaps.append(
                    {
                        "field": field,
                        "severity": severity,
                        "raw": rv or "(empty)",
                        "rendered": rend,
                        "message": f"{field} нет в исходном HTML, появляется после рендера",
                    }
                )
            elif rv and not rend:
                gaps.append(
                    {
                        "field": field,
                        "severity": severity,
                        "raw": rv,
                        "rendered": "(пусто)",
                        "message": f"{field} пропал после рендера",
                    }
                )
            elif rv != rend:
                gaps.append(
                    {
                        "field": field,
                        "severity": severity,
                        "raw": rv,
                        "rendered": rend,
                        "message": f"{field} отличается",
                    }
                )
    return gaps


async def run_render_gap(url: str) -> dict[str, Any]:
    raw_html, meta = await _fetch_raw(url)
    raw_signals = _extract_signals(raw_html, url)

    rendered_html, render_err = await _fetch_rendered(url)
    if render_err:
        return {
            "error": None,
            "url": url,
            "playwright_available": False,
            "playwright_error": render_err,
            "raw": raw_signals,
            "rendered": None,
            "gaps": [],
            "summary": {
                "gap_count": 0,
                "status": "raw_only",
                "note": "Установи Playwright для полного diff",
            },
            **meta,
        }

    rendered_signals = _extract_signals(rendered_html or "", url)
    gaps = _diff_signals(raw_signals, rendered_signals)
    critical = sum(1 for g in gaps if g["severity"] == "critical")

    return {
        "error": None,
        "url": url,
        "playwright_available": True,
        "playwright_error": None,
        "raw": raw_signals,
        "rendered": rendered_signals,
        "gaps": gaps,
        "summary": {
            "gap_count": len(gaps),
            "critical": critical,
            "status": "fail" if critical > 0 else ("warn" if gaps else "ok"),
            "js_dependent_seo": critical > 0 or any(g["field"] == "h1" for g in gaps),
        },
        **meta,
    }


async def run_render_gap_batch(pages: list[dict] | None = None) -> dict[str, Any]:
    from app.config_loader import load_config

    cfg = load_config()
    page_list = pages or [
        p for p in (cfg.get("seo") or {}).get("pages") or [] if p.get("type", "html") == "html"
    ]
    results = []
    for p in page_list[:5]:
        r = await run_render_gap(p["url"])
        r["label"] = p.get("label") or p["url"]
        results.append(r)

    return {
        "error": None,
        "summary": {
            "pages": len(results),
            "with_gaps": sum(1 for r in results if r.get("gaps")),
            "playwright_ok": any(r.get("playwright_available") for r in results),
        },
        "results": results,
    }
