"""AI-powered SEO review using Quickex audit prompt + Kie API."""

from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Any

import httpx

from app.config_loader import ROOT, kie_api_key, load_config
from app.model_checker import KIE_BASE, _extract_text

PROMPT_PATH = ROOT / "prompts" / "quickex-seo-audit.md"
TIMEOUT_SEC = 180


def load_system_prompt() -> str:
    text = PROMPT_PATH.read_text(encoding="utf-8")
    match = re.search(
        r"## СИСТЕМНЫЙ ПРОМПТ \(копировать отсюда\)\s*\n\n```\n(.*?)```",
        text,
        re.DOTALL,
    )
    if not match:
        raise ValueError(f"System prompt block not found in {PROMPT_PATH}")
    return match.group(1).strip()


def build_audit_user_message(
    page: dict[str, str],
    audit_result: dict[str, Any],
    html_head: str | None = None,
    visible_text: str | None = None,
) -> str:
    cfg = load_config()
    seo_cfg = cfg.get("seo") or {}
    ai_cfg = seo_cfg.get("ai_review") or {}
    mode = ai_cfg.get("mode") or "audit_only"

    auto_checker = {
        "url": audit_result.get("url"),
        "status": audit_result.get("status"),
        "score": audit_result.get("score"),
        "http_status": audit_result.get("http_status"),
        "latency_ms": audit_result.get("latency_ms"),
        "issues": audit_result.get("issues"),
        "details": audit_result.get("details"),
    }

    lines = [
        "AUDIT REQUEST",
        "site: quickex.io",
        f"page_type: {page.get('page_type') or 'exchange'}",
        f"pair: {page.get('pair') or ''}",
        f"lang: {page.get('lang') or 'en'}",
        f"url: {page.get('url')}",
        f"top_keyword: {page.get('top_keyword') or ''}",
        f"mode: {mode}",
        "",
        "AUTO_CHECKER:",
        json.dumps(auto_checker, ensure_ascii=False, indent=2),
    ]
    if html_head:
        lines.extend(["", "HTML_HEAD_SNIPPET:", html_head[:6000]])
    if visible_text:
        lines.extend(["", "VISIBLE_TEXT_SNIPPET:", visible_text[:8000]])
    lines.append("")
    lines.append("Начни аудит с Executive Summary.")
    return "\n".join(lines)


async def run_ai_seo_review(
    page: dict[str, str],
    audit_result: dict[str, Any],
    html_head: str | None = None,
    visible_text: str | None = None,
) -> dict[str, Any]:
    api_key = kie_api_key()
    if not api_key:
        return {"status": "skip", "error": "KIE_API_KEY не задан", "review": None}

    cfg = load_config()
    ai_cfg = (cfg.get("seo") or {}).get("ai_review") or {}
    if not ai_cfg.get("enabled"):
        return {"status": "skip", "error": "ai_review disabled", "review": None}

    model = ai_cfg.get("model") or "gpt-5-2"
    system_prompt = load_system_prompt()
    user_message = build_audit_user_message(page, audit_result, html_head, visible_text)

    spec = {
        "family": "openai",
        "model": model,
        "api": "chat",
        "web_search": False,
    }
    from app.model_checker import _build_request

    _, payload = _build_request(spec["family"], spec["model"], user_message, spec)
    payload["messages"] = [
        {
            "role": "developer",
            "content": [{"type": "text", "text": system_prompt}],
        },
        {
            "role": "user",
            "content": [{"type": "text", "text": user_message}],
        },
    ]

    started = time.perf_counter()
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT_SEC) as client:
            endpoint = f"{KIE_BASE}/{model}/v1/chat/completions"
            resp = await client.post(
                endpoint,
                json=payload,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
            )
            latency_ms = round((time.perf_counter() - started) * 1000, 1)
            if resp.status_code >= 400:
                return {
                    "status": "fail",
                    "error": f"HTTP {resp.status_code}: {resp.text[:200]}",
                    "review": None,
                    "latency_ms": latency_ms,
                    "model": model,
                }
            data = resp.json()
            text = _extract_text(data)
            if not text:
                return {
                    "status": "fail",
                    "error": str(data.get("error") or data.get("msg") or "empty response"),
                    "review": None,
                    "latency_ms": latency_ms,
                    "model": model,
                }
            return {
                "status": "ok",
                "error": None,
                "review": text,
                "latency_ms": latency_ms,
                "model": model,
                "credits": data.get("credits_consumed"),
            }
    except Exception as exc:
        return {
            "status": "fail",
            "error": str(exc)[:300],
            "review": None,
            "latency_ms": round((time.perf_counter() - started) * 1000, 1),
            "model": model,
        }
