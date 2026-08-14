"""Detect Nuxt/SPA stack signals and run block-N audit checks."""

from __future__ import annotations

import json
import re
from typing import Any
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

NUXT_MARKERS = (
    "__NUXT__",
    "__NUXT_DATA__",
    "window.__NUXT__",
    "/_nuxt/",
    "id=\"__nuxt\"",
    "id='__nuxt'",
    "data-server-rendered",
    "buildAssetsDir",
)


def detect_nuxt(html: str, config_stack: str | None = None) -> bool:
    if config_stack and config_stack.lower() in ("nuxt", "nuxt3", "nuxt2"):
        return True
    lower = html.lower()
    return any(m.lower() in lower for m in NUXT_MARKERS)


def analyze_nuxt_html(html: str, url: str, visible_text: str) -> dict[str, Any]:
    soup = BeautifulSoup(html, "lxml")
    head_html = str(soup.head) if soup.head else ""
    titles = soup.find_all("title")
    imgs = soup.find_all("img")
    scripts_head = soup.head.find_all("script") if soup.head else []
    blocking_scripts = [
        s for s in scripts_head if not s.get("defer") and not s.get("async") and s.get("src")
    ]
    imgs_no_dim = sum(1 for img in imgs if not img.get("width") and not img.get("height"))
    html_tag = soup.find("html")
    lang = html_tag.get("lang") if html_tag else None
    nuxt_div = soup.find(id="__nuxt") or soup.find(id="app")
    preload = soup.find_all("link", rel=re.compile(r"preload|modulepreload|prefetch", re.I))
    refresh = soup.find("meta", attrs={"http-equiv": re.compile("refresh", re.I)})

    nuxt_js_urls = re.findall(r'(?:src|href)=["\']([^"\']/_nuxt/[^"\']+\.js)["\']', html)
    parsed = urlparse(url)
    base = f"{parsed.scheme}://{parsed.netloc}"

    return {
        "is_nuxt": detect_nuxt(html),
        "visible_len": len(visible_text),
        "has_nuxt_payload": any(m in html for m in ("__NUXT__", "__NUXT_DATA__", "window.__NUXT__")),
        "h1_in_html": bool(soup.find("h1")),
        "title_in_html": bool(titles and titles[0].string),
        "title_count": len(titles),
        "desc_in_html": bool(soup.find("meta", attrs={"name": "description"})),
        "canonical_in_html": bool(soup.find("link", rel="canonical")),
        "og_in_html": bool(soup.find("meta", property=re.compile("^og:", re.I))),
        "json_ld_in_html": bool(soup.find("script", type="application/ld+json")),
        "lang": lang,
        "nuxt_div_text_len": len(nuxt_div.get_text(strip=True)) if nuxt_div else 0,
        "imgs_total": len(imgs),
        "imgs_no_dim": imgs_no_dim,
        "blocking_scripts_head": len(blocking_scripts),
        "has_refresh_meta": bool(refresh),
        "preload_count": len(preload),
        "nuxt_js_urls": [urljoin(base, u) for u in nuxt_js_urls[:3]],
        "robots_meta": _meta_robots(soup),
        "ssr_marker": bool(soup.find(attrs={"data-server-rendered": True})),
    }


def _meta_robots(soup: BeautifulSoup) -> str | None:
    tag = soup.find("meta", attrs={"name": "robots"})
    return str(tag["content"]).strip() if tag and tag.get("content") else None


async def check_nuxt_assets(client: httpx.AsyncClient, js_urls: list[str]) -> tuple[bool, str]:
    if not js_urls:
        return False, "Не найден /_nuxt/*.js в HTML"
    url = js_urls[0]
    try:
        r = await client.head(url, follow_redirects=True)
        if r.status_code == 200:
            return True, f"{url} → 200"
        return False, f"{url} → HTTP {r.status_code}"
    except Exception as e:
        return False, str(e)[:120]


def evaluate_nuxt_item(item_id: str, nx: dict[str, Any], asset_ok: bool, asset_note: str, url: str) -> dict[str, Any]:
    def ok(msg: str = "") -> dict[str, Any]:
        return {"status": "pass", "evidence": msg}

    def warn(msg: str) -> dict[str, Any]:
        return {"status": "warn", "evidence": msg}

    def fail(msg: str) -> dict[str, Any]:
        return {"status": "fail", "evidence": msg}

    def na(msg: str = "Не Nuxt / не применимо") -> dict[str, Any]:
        return {"status": "na", "evidence": msg}

    if not nx.get("is_nuxt"):
        return na()

    if item_id == "101":
        return ok(f"{nx['visible_len']} chars") if nx["visible_len"] >= 150 else fail(f"Мало текста: {nx['visible_len']} chars — возможен CSR shell")
    if item_id == "102":
        return ok() if nx["has_nuxt_payload"] or "/_nuxt/" in str(nx) else warn("Payload __NUXT__ не найден — возможен static generate или CSR")
    if item_id == "103":
        return ok() if nx["h1_in_html"] else fail("H1 отсутствует в исходном HTML")
    if item_id == "104":
        return ok() if nx["title_in_html"] else fail("Title отсутствует в SSR HTML")
    if item_id == "105":
        return ok() if nx["desc_in_html"] else fail("meta description только client-side?")
    if item_id == "106":
        return ok() if nx["canonical_in_html"] else warn("canonical не в initial HTML")
    if item_id == "107":
        return ok(asset_note) if asset_ok else fail(asset_note)
    if item_id == "108":
        if not nx["lang"]:
            return fail("html lang не задан")
        if "/ru/" in url and not str(nx["lang"]).lower().startswith("ru"):
            return warn(f"lang={nx['lang']} но URL /ru/")
        return ok(nx["lang"])
    if item_id == "109":
        if nx["visible_len"] < 200 and nx["nuxt_div_text_len"] < 50:
            return fail(f"Пустой #__nuxt shell: {nx['visible_len']} chars")
        return ok(f"{nx['visible_len']} chars")
    if item_id == "110":
        return ok() if nx["og_in_html"] else warn("OG только после гидрации")
    if item_id == "111":
        return ok() if nx["json_ld_in_html"] else warn("JSON-LD не в initial HTML")
    if item_id == "112":
        if nx["imgs_total"] == 0:
            return ok("Нет img")
        ratio = nx["imgs_no_dim"] / nx["imgs_total"]
        return warn(f"{nx['imgs_no_dim']}/{nx['imgs_total']} без width/height") if ratio >= 0.5 else ok()
    if item_id == "113":
        n = nx["blocking_scripts_head"]
        return warn(f"{n} blocking scripts в head") if n > 10 else ok(f"{n} blocking")
    if item_id == "114":
        return fail("meta refresh найден") if nx["has_refresh_meta"] else ok()
    if item_id == "115":
        return fail(f"{nx['title_count']} title tags") if nx["title_count"] > 1 else ok()
    if item_id == "116":
        if "/ru/" in url:
            return ok() if nx["lang"] and str(nx["lang"]).lower().startswith("ru") else warn(f"lang={nx['lang']}")
        return ok()
    if item_id == "117":
        return ok(f"{nx['preload_count']} preload/prefetch") if nx["preload_count"] else warn("Нет preload критичных ресурсов")
    if item_id == "118":
        return ok() if nx["preload_count"] else warn("Нет modulepreload/prefetch")
    if item_id == "119":
        if nx["visible_len"] < 100 and not nx["ssr_marker"] and not nx["has_nuxt_payload"]:
            return fail("Признаки CSR-only: пустой body без SSR marker")
        return ok()
    if item_id == "120":
        rob = nx.get("robots_meta") or ""
        return fail(f"robots: {rob}") if "noindex" in rob.lower() else ok(rob or "index по умолчанию")

    return {"status": "manual", "evidence": "Nuxt handler missing"}
