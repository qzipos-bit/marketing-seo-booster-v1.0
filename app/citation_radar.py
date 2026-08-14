"""Feature 1: AI Citation Radar — probe buyer queries via Kie models."""

from __future__ import annotations

import re
import time
from typing import Any
from urllib.parse import urlparse

import httpx

from app.config_loader import kie_api_key, load_config, perplexity_api_key
from app.model_checker import _build_request, _error_message, _extract_text, fetch_kie_credit

KIE_BASE = "https://api.kie.ai"
TIMEOUT_SEC = 90

DEFAULT_QUERIES = [
    "What is the best non-custodial crypto exchange?",
    "How to swap BTC to XMR anonymously?",
    "Quickex vs ChangeNOW crypto exchange comparison",
]


def _extract_urls(text: str) -> list[str]:
    return re.findall(r"https?://[^\s\)\]\"\'<>]+", text)


def _domain_in_text(text: str, domain: str) -> bool:
    lower = text.lower()
    d = domain.lower().lstrip("www.")
    return d in lower or d.replace(".", " ") in lower


async def _ask_model(
    client: httpx.AsyncClient,
    api_key: str,
    spec: dict[str, str],
    prompt: str,
) -> dict[str, Any]:
    family = spec.get("family", "codex")
    model = spec["model"]
    url, payload, auth_type = _build_request(family, model, prompt, spec)

    if auth_type == "perplexity":
        bearer = perplexity_api_key()
        if not bearer:
            return {"status": "fail", "text": "", "latency_ms": 0, "error": "PERPLEXITY_API_KEY не задан"}
    else:
        bearer = api_key
    started = time.perf_counter()
    try:
        resp = await client.post(
            url,
            headers={"Authorization": f"Bearer {bearer}", "Content-Type": "application/json"},
            json=payload,
            timeout=TIMEOUT_SEC,
        )
        data = resp.json()
        latency = round((time.perf_counter() - started) * 1000, 1)
        text = _extract_text(data)
        if text:
            return {"status": "ok", "text": text, "latency_ms": latency, "error": None}
        return {"status": "fail", "text": "", "latency_ms": latency, "error": _error_message(data)}
    except Exception as exc:
        return {
            "status": "fail",
            "text": "",
            "latency_ms": round((time.perf_counter() - started) * 1000, 1),
            "error": str(exc)[:200],
        }


def _citation_models(cfg: dict) -> list[dict]:
    """Pick one model per family for citation probes."""
    models = cfg.get("models") or []
    citation_cfg = (cfg.get("seo") or {}).get("citation") or {}
    if citation_cfg.get("models"):
        ids = {m["id"] for m in citation_cfg["models"]}
        return [m for m in models if m["id"] in ids]
    picked: dict[str, dict] = {}
    for m in models:
        fam = m.get("family", "?")
        if fam not in picked:
            picked[fam] = m
    return list(picked.values())


async def run_citation_radar(
    domain: str | None = None,
    queries: list[str] | None = None,
) -> dict[str, Any]:
    api_key = kie_api_key()
    if not api_key and not perplexity_api_key():
        return {"error": "KIE_API_KEY или PERPLEXITY_API_KEY не задан", "results": []}

    cfg = load_config()
    seo = cfg.get("seo") or {}
    site_domain = domain or seo.get("domain") or ""
    if not site_domain:
        pages = seo.get("pages") or []
        if pages:
            site_domain = urlparse(pages[0]["url"]).netloc

    citation_cfg = seo.get("citation") or {}
    query_list = queries or citation_cfg.get("queries") or DEFAULT_QUERIES
    models = _citation_models(cfg)
    if not models:
        return {"error": "Нет моделей в config", "results": []}

    prompt_tpl = citation_cfg.get("prompt_template") or (
        "Answer briefly (3-5 sentences). List any websites or URLs you recommend as sources.\n\nQuery: {query}"
    )

    results: list[dict[str, Any]] = []
    async with httpx.AsyncClient(timeout=TIMEOUT_SEC) as client:
        credit = await fetch_kie_credit(client, api_key)
        for query in query_list:
            prompt = prompt_tpl.format(query=query)
            for spec in models:
                probe = await _ask_model(client, api_key, spec, prompt)
                text = probe.get("text") or ""
                urls = _extract_urls(text)
                cites_domain = _domain_in_text(text, site_domain) if site_domain else False
                domain_urls = [u for u in urls if site_domain and site_domain in u.lower()]
                results.append(
                    {
                        "query": query,
                        "model_id": spec["id"],
                        "model_label": spec.get("label", spec["id"]),
                        "family": spec.get("family"),
                        "status": probe["status"],
                        "latency_ms": probe["latency_ms"],
                        "error": probe.get("error"),
                        "response_preview": text[:500],
                        "response_full": text[:4000],
                        "urls_found": urls[:10],
                        "cites_target_domain": cites_domain,
                        "target_domain_urls": domain_urls,
                    }
                )

    total = len(results)
    cites = sum(1 for r in results if r.get("cites_target_domain"))
    ok = sum(1 for r in results if r["status"] == "ok")

    return {
        "error": None,
        "domain": site_domain,
        "credit": credit,
        "summary": {
            "queries": len(query_list),
            "models": len(models),
            "total_probes": total,
            "ok": ok,
            "cites_domain": cites,
            "cite_rate_pct": round(cites / max(total, 1) * 100, 1),
        },
        "results": results,
    }
