"""Basic SEO audit for configured pages."""

from __future__ import annotations

import asyncio
import re
import time
from typing import Any
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

from app.config_loader import load_config
from app.seo_ai_reviewer import run_ai_seo_review

TIMEOUT_SEC = 20


def _first_text(soup: BeautifulSoup, selector: str) -> str | None:
    el = soup.select_one(selector)
    if not el:
        return None
    text = el.get_text(strip=True)
    return text or None


def _meta_content(soup: BeautifulSoup, name: str | None = None, prop: str | None = None) -> str | None:
    if name:
        tag = soup.find("meta", attrs={"name": name})
        if tag and tag.get("content"):
            return str(tag["content"]).strip()
    if prop:
        tag = soup.find("meta", attrs={"property": prop})
        if tag and tag.get("content"):
            return str(tag["content"]).strip()
    return None


def _extract_snippets(html: str) -> tuple[str, str]:
    soup = BeautifulSoup(html, "lxml")
    head = soup.head
    head_text = head.get_text("\n", strip=True)[:4000] if head else ""
    if head:
        head_html = "".join(str(tag) for tag in head.find_all(["title", "meta", "link", "script"]))[:6000]
    else:
        head_html = head_text

    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    body = soup.body or soup
    visible = body.get_text("\n", strip=True)
    lines = [ln.strip() for ln in visible.splitlines() if ln.strip()]
    visible_text = "\n".join(lines[:120])
    return head_html, visible_text


def _hreflang_count(soup: BeautifulSoup) -> int:
    return len(soup.find_all("link", rel="alternate", hreflang=True))


def _count_json_ld(soup: BeautifulSoup) -> int:
    return len(soup.find_all("script", attrs={"type": "application/ld+json"}))


def _score_page(issues: list[str]) -> tuple[int, str]:
    if any(i.startswith("FAIL:") for i in issues):
        return 0, "fail"
    if issues:
        return max(40, 100 - len(issues) * 12), "warn"
    return 100, "ok"


def _audit_html(url: str, html: str, http_status: int) -> dict[str, Any]:
    issues: list[str] = []
    soup = BeautifulSoup(html, "lxml")

    title = _first_text(soup, "title")
    h1 = _first_text(soup, "h1")
    description = _meta_content(soup, name="description")
    canonical = soup.find("link", rel="canonical")
    canonical_href = canonical.get("href") if canonical else None
    og_title = _meta_content(soup, prop="og:title")
    og_desc = _meta_content(soup, prop="og:description")
    robots = _meta_content(soup, name="robots")
    json_ld_count = _count_json_ld(soup)
    hreflang_count = _hreflang_count(soup)

    if http_status != 200:
        issues.append(f"FAIL: HTTP {http_status}")
    if not title:
        issues.append("FAIL: нет <title>")
    elif len(title) < 20:
        issues.append("WARN: title слишком короткий (<20)")
    elif len(title) > 70:
        issues.append("WARN: title длинный (>70)")

    if not description:
        issues.append("WARN: нет meta description")
    elif len(description) < 50:
        issues.append("WARN: description короткий (<50)")
    elif len(description) > 170:
        issues.append("WARN: description длинный (>170)")

    if not h1:
        issues.append("WARN: нет H1")
    if not canonical_href:
        issues.append("WARN: нет canonical")
    if not og_title:
        issues.append("INFO: нет og:title")
    if not og_desc:
        issues.append("INFO: нет og:description")
    if json_ld_count == 0:
        issues.append("INFO: нет JSON-LD")
    if robots and "noindex" in robots.lower():
        issues.append("WARN: robots noindex")

    score, status = _score_page(issues)
    return {
        "status": status,
        "score": score,
        "issues": issues,
        "details": {
            "title": title,
            "h1": h1,
            "description": description,
            "canonical": canonical_href,
            "og_title": og_title,
            "og_description": og_desc,
            "robots": robots,
            "json_ld_blocks": json_ld_count,
            "hreflang_count": hreflang_count,
        },
    }


def _audit_sitemap(content: str, http_status: int) -> dict[str, Any]:
    issues: list[str] = []
    if http_status != 200:
        issues.append(f"FAIL: HTTP {http_status}")
    if "<urlset" not in content and "<sitemapindex" not in content:
        issues.append("FAIL: не похож на XML sitemap")
    urls = re.findall(r"<loc>([^<]+)</loc>", content)
    if not urls:
        issues.append("WARN: нет URL в sitemap")
    score, status = _score_page(issues)
    return {
        "status": status,
        "score": score,
        "issues": issues,
        "details": {"url_count": len(urls), "sample_urls": urls[:5]},
    }


def _audit_robots(content: str, http_status: int) -> dict[str, Any]:
    issues: list[str] = []
    if http_status != 200:
        issues.append(f"FAIL: HTTP {http_status}")
    if "User-agent:" not in content:
        issues.append("WARN: нет User-agent")
    if "Sitemap:" not in content:
        issues.append("WARN: нет Sitemap directive")
    if re.search(r"Disallow:\s*/\s*$", content, re.M):
        issues.append("WARN: Disallow: / блокирует всё")
    score, status = _score_page(issues)
    return {
        "status": status,
        "score": score,
        "issues": issues,
        "details": {"lines": len(content.splitlines())},
    }


async def audit_page(client: httpx.AsyncClient, page: dict[str, str]) -> dict[str, Any]:
    url = page["url"]
    label = page.get("label") or url
    page_type = page.get("type") or "html"

    started = time.perf_counter()
    try:
        resp = await client.get(url, follow_redirects=True)
        latency_ms = round((time.perf_counter() - started) * 1000, 1)
        content = resp.text
        http_status = resp.status_code

        if page_type == "xml":
            audit = _audit_sitemap(content, http_status)
        elif page_type == "text":
            audit = _audit_robots(content, http_status)
        else:
            audit = _audit_html(url, content, http_status)
            head_snippet, visible_snippet = _extract_snippets(content)
            stack = page.get("stack")
            if stack or "/_nuxt/" in content or "__NUXT" in content:
                from app.nuxt_auditor import analyze_nuxt_html, detect_nuxt
                nx = analyze_nuxt_html(content, url, BeautifulSoup(content, "lxml").get_text(strip=True))
                if detect_nuxt(content, stack):
                    audit.setdefault("issues", [])
                    if not nx["h1_in_html"]:
                        audit["issues"].append("FAIL NUXT: H1 нет в SSR HTML")
                    if not nx["title_in_html"]:
                        audit["issues"].append("FAIL NUXT: title нет в SSR HTML")
                    if nx["visible_len"] < 150:
                        audit["issues"].append("WARN NUXT: мало текста в shell — CSR?")
                    if nx["title_count"] > 1:
                        audit["issues"].append("WARN NUXT: несколько title tags")
                    audit.setdefault("details", {})["nuxt"] = nx
                    score, status = _score_page(audit["issues"])
                    audit["score"] = score
                    audit["status"] = status
        result = {
            "url": url,
            "label": label,
            "http_status": http_status,
            "latency_ms": latency_ms,
            **audit,
        }
        if page_type not in ("xml", "text"):
            result["_head_snippet"] = head_snippet
            result["_visible_snippet"] = visible_snippet
        return result
    except Exception as exc:
        latency_ms = round((time.perf_counter() - started) * 1000, 1)
        return {
            "url": url,
            "label": label,
            "status": "fail",
            "http_status": None,
            "latency_ms": latency_ms,
            "score": 0,
            "issues": [f"FAIL: {exc}"],
            "details": {},
        }


async def run_seo_check(
    skip_ai_review: bool = False,
    pages: list[dict[str, Any]] | None = None,
    concurrency: int = 12,
) -> dict[str, Any]:
    cfg = load_config()
    seo_cfg = cfg.get("seo") or {}
    page_list = pages if pages is not None else (seo_cfg.get("pages") or [])
    html_pages = [p for p in page_list if p.get("type", "html") == "html"]
    site_name = seo_cfg.get("site_name") or urlparse(html_pages[0]["url"]).netloc if html_pages else "site"

    if not html_pages:
        return {"error": "В config.yaml не заданы SEO pages", "results": [], "site_name": site_name}

    sem = asyncio.Semaphore(max(1, concurrency))

    async def _audit_one(client: httpx.AsyncClient, page: dict[str, Any]) -> dict[str, Any]:
        async with sem:
            return await audit_page(client, page)

    async with httpx.AsyncClient(timeout=TIMEOUT_SEC) as client:
        results = list(await asyncio.gather(*[_audit_one(client, p) for p in html_pages]))

    ai_cfg = seo_cfg.get("ai_review") or {}
    if not skip_ai_review and ai_cfg.get("enabled"):
        max_pages = int(ai_cfg.get("max_pages") or 3)
        ai_count = 0
        for page, result in zip(html_pages, results):
            if ai_count >= max_pages:
                break
            if page.get("type") in ("xml", "text"):
                continue
            if not page.get("pair") and page.get("page_type") not in (None, "exchange", "premium", "homepage"):
                continue
            ai = await run_ai_seo_review(
                page,
                result,
                result.get("_head_snippet"),
                result.get("_visible_snippet"),
            )
            result.setdefault("details", {})["ai_review"] = ai
            if ai.get("status") == "ok":
                ai_count += 1
            for key in ("_head_snippet", "_visible_snippet"):
                result.pop(key, None)

    for result in results:
        result.pop("_head_snippet", None)
        result.pop("_visible_snippet", None)

    return {"error": None, "results": results, "site_name": site_name}
