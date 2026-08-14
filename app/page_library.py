"""Mandatory Quickex exchange pages — always included in every scan pass."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from app.config_loader import ROOT, load_config


def _pair_from_url(url: str) -> str:
    path = urlparse(url).path.rstrip("/")
    if "/exchange-" in path:
        return path.split("/exchange-", 1)[-1]
    return ""


def _label_from_pair(pair: str) -> str:
    if not pair:
        return ""
    if "-" in pair:
        left, right = pair.split("-", 1)
        return f"{left.upper()}→{right.upper()}"
    return pair.upper()


def page_entry_from_url(url: str, *, mandatory: bool = False, **extra: Any) -> dict[str, Any]:
    pair = _pair_from_url(url)
    entry: dict[str, Any] = {
        "url": url,
        "label": extra.get("label") or _label_from_pair(pair) or url,
        "lang": extra.get("lang") or "en",
        "stack": extra.get("stack") or "nuxt",
        "type": "html",
    }
    if pair:
        entry["pair"] = pair
        entry["page_type"] = "exchange"
    if mandatory:
        entry["mandatory"] = True
    entry.update({k: v for k, v in extra.items() if k not in entry})
    return entry


@lru_cache(maxsize=8)
def _load_mandatory_urls(file_path: str) -> tuple[str, ...]:
    path = Path(file_path)
    if not path.is_file():
        return ()
    urls: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        raw = line.strip()
        if not raw or raw.startswith("#"):
            continue
        token = raw.split()[0]
        if token.startswith("http"):
            urls.append(token)
        elif token.startswith("/exchange-"):
            urls.append(f"https://quickex.io{token}")
        elif token.startswith("exchange-"):
            urls.append(f"https://quickex.io/{token}")
        else:
            urls.append(f"https://quickex.io/exchange-{token}")
    return tuple(urls)


def mandatory_pages_config() -> dict[str, Any]:
    return (load_config().get("scan") or {}).get("mandatory_pages") or {}


def mandatory_pages_file_path() -> Path:
    mp = mandatory_pages_config()
    rel = mp.get("file") or "data/quickex/mandatory-exchange-pages.txt"
    path = Path(rel)
    if not path.is_absolute():
        path = ROOT / rel
    return path


def mandatory_page_urls() -> list[str]:
    mp = mandatory_pages_config()
    if mp.get("enabled") is False:
        return []
    return list(_load_mandatory_urls(str(mandatory_pages_file_path())))


def config_html_pages() -> list[dict[str, Any]]:
    pages = (load_config().get("seo") or {}).get("pages") or []
    return [dict(p) for p in pages if p.get("type", "html") == "html"]


def get_scan_pages(*, include_mandatory: bool = True) -> list[dict[str, Any]]:
    """Config pages + mandatory exchange library (deduped by URL)."""
    by_url: dict[str, dict[str, Any]] = {}
    for page in config_html_pages():
        by_url[page["url"]] = page
    if include_mandatory:
        for url in mandatory_page_urls():
            if url in by_url:
                merged = dict(by_url[url])
                merged["mandatory"] = True
                by_url[url] = merged
            else:
                by_url[url] = page_entry_from_url(url, mandatory=True)
    return list(by_url.values())


def scan_concurrency() -> dict[str, int]:
    scan_cfg = load_config().get("scan") or {}
    return {
        "checklist": int(scan_cfg.get("checklist_concurrency") or 8),
        "seo": int(scan_cfg.get("seo_concurrency") or 12),
    }
