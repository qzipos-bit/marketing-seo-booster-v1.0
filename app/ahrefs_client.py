"""Ahrefs API v3 client — backlinks, refdomains, metrics."""

from __future__ import annotations

import logging
from datetime import date
from typing import Any
from urllib.parse import urlencode

import httpx

from app.config_loader import ahrefs_api_key

logger = logging.getLogger(__name__)

AHREFS_BASE = "https://api.ahrefs.com/v3/site-explorer"
TIMEOUT_SEC = 60


class AhrefsError(Exception):
    pass


async def _get(
    client: httpx.AsyncClient,
    path: str,
    params: dict[str, Any],
) -> dict[str, Any]:
    key = ahrefs_api_key()
    if not key:
        raise AhrefsError("AHREFS_API_KEY не задан в .env")

    url = f"{AHREFS_BASE}/{path}?{urlencode(params)}"
    resp = await client.get(url, headers={"Authorization": f"Bearer {key}"})
    if resp.status_code == 429:
        raise AhrefsError("Ahrefs rate limit — попробуй позже")
    if resp.status_code >= 400:
        raise AhrefsError(f"Ahrefs HTTP {resp.status_code}: {resp.text[:300]}")
    data = resp.json()
    if isinstance(data, dict) and data.get("error"):
        raise AhrefsError(str(data["error"]))
    return data


async def fetch_domain_rating(
    client: httpx.AsyncClient,
    target: str,
) -> dict[str, Any]:
    today = date.today().isoformat()
    data = await _get(client, "domain-rating", {"target": target, "date": today, "output": "json"})
    return data.get("domain_rating") or {}


async def fetch_backlinks_stats(
    client: httpx.AsyncClient,
    target: str,
    mode: str = "domain",
) -> dict[str, Any]:
    today = date.today().isoformat()
    data = await _get(
        client,
        "backlinks-stats",
        {"target": target, "mode": mode, "date": today, "output": "json"},
    )
    return data.get("metrics") or {}


async def fetch_organic_metrics(
    client: httpx.AsyncClient,
    target: str,
    mode: str = "domain",
) -> dict[str, Any]:
    today = date.today().isoformat()
    data = await _get(
        client,
        "metrics",
        {"target": target, "mode": mode, "date": today, "output": "json"},
    )
    return data.get("metrics") or {}


async def fetch_new_backlinks(
    client: httpx.AsyncClient,
    target: str,
    since: str,
    *,
    mode: str = "domain",
    limit: int = 200,
) -> list[dict[str, Any]]:
    """Backlinks first seen since `since` (YYYY-MM-DD)."""
    select = (
        "url_from,url_to,domain_rating_source,anchor,first_seen,is_dofollow,"
        "traffic,url_rating_source"
    )
    data = await _get(
        client,
        "all-backlinks",
        {
            "target": target,
            "mode": mode,
            "select": select,
            "history": f"since:{since}",
            "order_by": "first_seen:desc",
            "limit": limit,
            "output": "json",
        },
    )
    return data.get("backlinks") or []


async def fetch_new_refdomains(
    client: httpx.AsyncClient,
    target: str,
    since: str,
    *,
    mode: str = "domain",
    limit: int = 100,
) -> list[dict[str, Any]]:
    select = "domain,domain_rating,first_seen,links_to_target,dofollow_links"
    data = await _get(
        client,
        "refdomains",
        {
            "target": target,
            "mode": mode,
            "select": select,
            "history": f"since:{since}",
            "order_by": "first_seen:desc",
            "limit": limit,
            "output": "json",
        },
    )
    return data.get("refdomains") or []
