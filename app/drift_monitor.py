"""Feature 2: SEO Drift Guard — baseline snapshots and regression diffs."""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any

import httpx
from bs4 import BeautifulSoup

TIMEOUT = 25

CRITICAL_RULES = (
    ("robots_noindex", "meta robots содержит noindex"),
    ("canonical_removed", "canonical удалён"),
    ("canonical_changed", "canonical URL изменился"),
    ("title_removed", "title удалён или пустой"),
    ("schema_removed", "JSON-LD schema удалена"),
    ("http_not_ok", "HTTP статус не 2xx"),
)

WARNING_RULES = (
    ("title_changed", "title изменился"),
    ("h1_changed", "H1 изменился"),
    ("desc_changed", "meta description изменился"),
    ("schema_hash_changed", "содержимое JSON-LD изменилось"),
    ("og_removed", "Open Graph теги удалены"),
    ("word_count_drop", "объём текста упал >25%"),
)

INFO_RULES = (
    ("h2_count_changed", "количество H2 изменилось"),
    ("internal_links_changed", "внутренние ссылки изменились >20%"),
)


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


async def capture_seo_snapshot(url: str) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=TIMEOUT, follow_redirects=True) as client:
        resp = await client.get(url)
        html = resp.text

    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    visible = soup.get_text("\n", strip=True)

    title_tag = soup.find("title")
    title = title_tag.get_text(strip=True) if title_tag else ""
    desc_tag = soup.find("meta", attrs={"name": "description"})
    desc = str(desc_tag["content"]).strip() if desc_tag and desc_tag.get("content") else ""
    robots_tag = soup.find("meta", attrs={"name": "robots"})
    robots = str(robots_tag["content"]).strip() if robots_tag and robots_tag.get("content") else ""
    canon_tag = soup.find("link", rel="canonical")
    canonical = str(canon_tag["href"]).strip() if canon_tag and canon_tag.get("href") else ""

    h1s = [h.get_text(strip=True) for h in soup.find_all("h1")]
    h2s = [h.get_text(strip=True) for h in soup.find_all("h2")]

    schemas = [
        s.get_text(strip=True)
        for s in BeautifulSoup(html, "lxml").find_all("script", type="application/ld+json")
    ]
    schema_joined = "\n".join(schemas)

    og: dict[str, str] = {}
    for tag in BeautifulSoup(html, "lxml").find_all("meta", property=re.compile("^og:", re.I)):
        prop = tag.get("property")
        if prop and tag.get("content"):
            og[str(prop)] = str(tag["content"])

    from urllib.parse import urljoin, urlparse

    parsed = urlparse(url)
    base_host = parsed.netloc.lower()
    internal = 0
    for a in BeautifulSoup(html, "lxml").find_all("a", href=True):
        href = str(a["href"])
        if href.startswith(("#", "mailto:", "tel:", "javascript:")):
            continue
        if urlparse(urljoin(url, href)).netloc.lower() == base_host:
            internal += 1

    return {
        "url": url,
        "final_url": str(resp.url),
        "http_status": resp.status_code,
        "title": title,
        "meta_description": desc,
        "robots_meta": robots,
        "canonical": canonical,
        "h1": h1s,
        "h2_count": len(h2s),
        "h2_sample": h2s[:5],
        "word_count": len(visible.split()),
        "internal_links": internal,
        "schema_count": len(schemas),
        "schema_hash": _hash(schema_joined) if schema_joined else "",
        "og_keys": sorted(og.keys()),
        "og": og,
        "html_hash": _hash(html),
    }


def compare_snapshots(baseline: dict[str, Any], current: dict[str, Any]) -> dict[str, Any]:
    """Diff two snapshots; return triggered rules with severity."""
    changes: list[dict[str, Any]] = []

    def add(severity: str, rule: str, message: str, before: Any = None, after: Any = None) -> None:
        changes.append(
            {
                "severity": severity,
                "rule": rule,
                "message": message,
                "before": before,
                "after": after,
            }
        )

    if current.get("http_status", 0) >= 400 or current.get("http_status", 0) < 200:
        add("critical", "http_not_ok", f"HTTP {current.get('http_status')}", baseline.get("http_status"), current.get("http_status"))

    robots_now = (current.get("robots_meta") or "").lower()
    robots_was = (baseline.get("robots_meta") or "").lower()
    if "noindex" in robots_now and "noindex" not in robots_was:
        add("critical", "robots_noindex", "добавлен noindex", robots_was, robots_now)

    if baseline.get("canonical") and not current.get("canonical"):
        add("critical", "canonical_removed", "canonical удалён", baseline["canonical"], None)
    elif baseline.get("canonical") != current.get("canonical") and current.get("canonical"):
        add("critical", "canonical_changed", "canonical изменился", baseline.get("canonical"), current.get("canonical"))

    if baseline.get("title") and not current.get("title"):
        add("critical", "title_removed", "title удалён", baseline["title"], "")
    elif baseline.get("title") != current.get("title"):
        add("warning", "title_changed", "title изменился", baseline.get("title"), current.get("title"))

    if baseline.get("schema_count", 0) > 0 and current.get("schema_count", 0) == 0:
        add("critical", "schema_removed", "JSON-LD удалена", baseline.get("schema_count"), 0)
    elif baseline.get("schema_hash") != current.get("schema_hash") and baseline.get("schema_hash"):
        add("warning", "schema_hash_changed", "содержимое schema изменилось", baseline.get("schema_hash"), current.get("schema_hash"))

    if baseline.get("h1") != current.get("h1"):
        add("warning", "h1_changed", "H1 изменился", baseline.get("h1"), current.get("h1"))

    if baseline.get("meta_description") != current.get("meta_description"):
        add("warning", "desc_changed", "meta description изменился", baseline.get("meta_description", "")[:80], current.get("meta_description", "")[:80])

    if baseline.get("og_keys") and not current.get("og_keys"):
        add("warning", "og_removed", "OG-теги удалены", baseline.get("og_keys"), [])

    bw = baseline.get("word_count") or 1
    cw = current.get("word_count") or 0
    if cw < bw * 0.75:
        add("warning", "word_count_drop", f"текст −{round((1 - cw/bw)*100)}%", bw, cw)

    if baseline.get("h2_count") != current.get("h2_count"):
        add("info", "h2_count_changed", "количество H2 изменилось", baseline.get("h2_count"), current.get("h2_count"))

    bi = baseline.get("internal_links") or 1
    ci = current.get("internal_links") or 0
    if abs(ci - bi) / max(bi, 1) > 0.2:
        add("info", "internal_links_changed", "внутренние ссылки изменились", bi, ci)

    critical = sum(1 for c in changes if c["severity"] == "critical")
    warning = sum(1 for c in changes if c["severity"] == "warning")
    info = sum(1 for c in changes if c["severity"] == "info")

    return {
        "url": current.get("url"),
        "baseline_url": baseline.get("url"),
        "has_drift": len(changes) > 0,
        "critical_count": critical,
        "warning_count": warning,
        "info_count": info,
        "exit_code": 1 if critical > 0 else 0,
        "changes": changes,
        "baseline": baseline,
        "current": current,
    }
