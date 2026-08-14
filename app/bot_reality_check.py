"""Feature 3: Bot Access Reality Test — robots.txt vs actual HTTP response."""

from __future__ import annotations

import time
from typing import Any

import httpx

from app.pro_seo_auditor import AI_BOTS, SEARCH_BOTS, parse_robots_access

TIMEOUT = 20
CHROME_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)

CF_CHALLENGE_MARKERS = (
    "cf-browser-verification",
    "challenge-platform",
    "just a moment",
    "checking your browser",
    "cloudflare",
)


def _detect_challenge(body: str, headers: dict[str, str]) -> bool:
    lower = body[:8000].lower()
    if any(m in lower for m in CF_CHALLENGE_MARKERS):
        return True
    if headers.get("cf-mitigated") == "challenge":
        return True
    server = headers.get("server", "").lower()
    if "cloudflare" in server and len(body) < 5000 and "html" in lower:
        return True
    return False


async def _fetch_as(
    client: httpx.AsyncClient, url: str, user_agent: str
) -> dict[str, Any]:
    started = time.perf_counter()
    try:
        resp = await client.get(
            url,
            headers={"User-Agent": user_agent, "Accept": "text/html,*/*"},
            follow_redirects=True,
        )
        latency = round((time.perf_counter() - started) * 1000, 1)
        body = resp.text
        hdrs = {k.lower(): v for k, v in resp.headers.items()}
        challenge = _detect_challenge(body, hdrs)
        return {
            "status": resp.status_code,
            "latency_ms": latency,
            "body_len": len(body),
            "final_url": str(resp.url),
            "challenge": challenge,
            "error": None,
        }
    except Exception as exc:
        return {
            "status": 0,
            "latency_ms": round((time.perf_counter() - started) * 1000, 1),
            "body_len": 0,
            "final_url": url,
            "challenge": False,
            "error": str(exc)[:200],
        }


def _verdict(robots: str, http: dict[str, Any]) -> str:
    """ok | mismatch | blocked | challenge | error"""
    if http.get("error"):
        return "error"
    st = http.get("status", 0)
    if http.get("challenge"):
        return "challenge"
    if st in (403, 401, 429, 503):
        return "blocked"
    if robots == "allowed" and st >= 400:
        return "mismatch"
    if robots == "blocked" and st == 200 and http.get("body_len", 0) > 1000:
        return "mismatch"
    return "ok"


async def run_bot_reality_check(
    url: str,
    robots_text: str = "",
) -> dict[str, Any]:
    """Compare robots policy vs real HTTP for each bot UA + Chrome baseline."""
    bots = [(name, desc) for name, desc in AI_BOTS + SEARCH_BOTS]
    chrome = await _probe_all(url, robots_text, bots, include_chrome=True)
    mismatches = [r for r in chrome["results"] if r["verdict"] in ("mismatch", "blocked", "challenge")]
    return {
        "error": None,
        "url": url,
        "robots_text_len": len(robots_text),
        "summary": {
            "total_bots": len(bots),
            "ok": sum(1 for r in chrome["results"] if r["verdict"] == "ok"),
            "mismatch": len(mismatches),
            "has_critical_mismatch": any(
                r["robots"] == "allowed" and r["verdict"] in ("blocked", "challenge", "mismatch")
                for r in chrome["results"]
            ),
        },
        "results": chrome["results"],
        "chrome_baseline": chrome.get("chrome_baseline"),
    }


async def _probe_all(
    url: str,
    robots_text: str,
    bots: list[tuple[str, str]],
    include_chrome: bool = True,
) -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    chrome_baseline: dict[str, Any] | None = None

    async with httpx.AsyncClient(timeout=TIMEOUT, follow_redirects=True) as client:
        if include_chrome:
            chrome_baseline = await _fetch_as(client, url, CHROME_UA)
            chrome_baseline["user_agent"] = "Chrome (baseline)"

        for bot_name, desc in bots:
            robots_st = parse_robots_access(robots_text, bot_name)
            http = await _fetch_as(client, url, bot_name)
            verdict = _verdict(robots_st, http)
            results.append(
                {
                    "bot": bot_name,
                    "description": desc,
                    "robots": robots_st,
                    "http_status": http["status"],
                    "body_len": http["body_len"],
                    "latency_ms": http["latency_ms"],
                    "challenge": http["challenge"],
                    "error": http["error"],
                    "verdict": verdict,
                    "final_url": http["final_url"],
                }
            )

    return {"results": results, "chrome_baseline": chrome_baseline}
