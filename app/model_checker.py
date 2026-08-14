"""Probe Kie chat models and return health results."""

from __future__ import annotations

import asyncio
import json
import time
from typing import Any

import httpx

from app.config_loader import kie_api_key, load_config, perplexity_api_key

KIE_BASE = "https://api.kie.ai"
PERPLEXITY_BASE = "https://api.perplexity.ai"
TIMEOUT_SEC = 120


def _extract_text(data: dict[str, Any]) -> str | None:
    if data.get("code") and data.get("code") != 200:
        return None
    if data.get("error"):
        err = data["error"]
        if isinstance(err, dict):
            return None
    texts: list[str] = []
    for item in data.get("output", []):
        if item.get("type") == "message":
            for block in item.get("content", []):
                if block.get("type") == "output_text":
                    texts.append(block.get("text", ""))
    if texts:
        return "\n".join(texts).strip()
    for block in data.get("content", []):
        if block.get("type") == "text":
            texts.append(block.get("text", ""))
        elif block.get("type") == "output_text":
            texts.append(block.get("text", ""))
    if texts:
        return "\n".join(texts).strip()
    for choice in data.get("choices", []):
        msg = choice.get("message") or {}
        content = msg.get("content")
        if content:
            if isinstance(content, list):
                parts = [c.get("text", "") for c in content if isinstance(c, dict)]
                joined = "\n".join(p for p in parts if p).strip()
                if joined:
                    return joined
            return str(content).strip()
    return None


def _error_message(data: dict[str, Any]) -> str:
    if data.get("msg"):
        return str(data["msg"])
    err = data.get("error")
    if isinstance(err, dict):
        return str(err.get("message") or err)
    if err:
        return str(err)
    return json.dumps(data, ensure_ascii=False)[:300]


def _build_request(
    family: str,
    model: str,
    prompt: str,
    spec: dict[str, Any] | None = None,
) -> tuple[str, dict[str, Any], str | None]:
    """Returns (url, payload, auth_key_type). auth_key_type: kie | perplexity."""
    spec = spec or {}
    api = spec.get("api") or family
    max_tokens = int(spec.get("max_tokens") or 1024)

    if family == "perplexity":
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
        }
        return (f"{PERPLEXITY_BASE}/chat/completions", payload, "perplexity")

    if api == "openai_compat":
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "max_tokens": max_tokens,
        }
        if spec.get("reasoning_effort"):
            payload["reasoning_effort"] = spec["reasoning_effort"]
        return (f"{KIE_BASE}/v1/chat/completions", payload, "kie")

    if api == "chat" or family == "openai":
        endpoint = spec.get("endpoint") or f"/{model}/v1/chat/completions"
        payload: dict[str, Any] = {
            "model": model,
            "messages": [
                {
                    "role": "user",
                    "content": [{"type": "text", "text": prompt}],
                }
            ],
            "stream": False,
        }
        if spec.get("web_search"):
            if family == "gemini":
                payload["tools"] = [
                    {"type": "function", "function": {"name": "googleSearch"}}
                ]
            else:
                payload["tools"] = [
                    {"type": "function", "function": {"name": "web_search"}}
                ]
        return (f"{KIE_BASE}{endpoint}", payload, "kie")

    if family == "codex":
        return (
            f"{KIE_BASE}/codex/v1/responses",
            {
                "model": model,
                "stream": False,
                "input": prompt,
                "reasoning": {"effort": "low"},
            },
            "kie",
        )
    if family == "grok":
        payload = {
            "model": model,
            "stream": False,
            "input": prompt,
            "reasoning": {"effort": spec.get("reasoning_effort", "low")},
        }
        if spec.get("web_search"):
            payload["tools"] = [{"type": "web_search"}]
        return (f"{KIE_BASE}/grok/v1/responses", payload, "kie")
    if family == "claude":
        payload: dict[str, Any] = {
            "model": model,
            "stream": False,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
        }
        if spec.get("thinking_flag"):
            payload["thinkingFlag"] = True
        return (f"{KIE_BASE}/claude/v1/messages", payload, "kie")
    if family == "gemini":
        endpoint = spec.get("endpoint") or f"/{model}/v1/chat/completions"
        payload = {
            "messages": [
                {
                    "role": "user",
                    "content": [{"type": "text", "text": prompt}],
                }
            ],
            "stream": False,
            "include_thoughts": False,
        }
        if spec.get("web_search"):
            payload["tools"] = [
                {"type": "function", "function": {"name": "googleSearch"}}
            ]
        return (f"{KIE_BASE}{endpoint}", payload, "kie")
    raise ValueError(f"Unknown model family: {family}")


async def fetch_kie_credit(client: httpx.AsyncClient, api_key: str) -> float | None:
    try:
        resp = await client.get(
            f"{KIE_BASE}/api/v1/chat/credit",
            headers={"Authorization": f"Bearer {api_key}"},
        )
        data = resp.json()
        if data.get("code") == 200:
            return float(data.get("data") or 0)
    except Exception:
        pass
    return None


async def probe_model(
    client: httpx.AsyncClient,
    api_key: str,
    spec: dict[str, str],
    prompt: str,
) -> dict[str, Any]:
    model_id = spec["id"]
    label = spec.get("label") or model_id
    family = spec["family"]
    model = spec["model"]

    pplx_key = perplexity_api_key()
    try:
        url, payload, auth_type = _build_request(family, model, prompt, spec)
    except ValueError as exc:
        return {
            "model_id": model_id,
            "label": label,
            "family": family,
            "status": "fail",
            "latency_ms": 0,
            "credits": None,
            "response_preview": None,
            "response_full": None,
            "error": str(exc),
        }

    if auth_type == "perplexity":
        if not pplx_key:
            return {
                "model_id": model_id,
                "label": label,
                "family": family,
                "status": "fail",
                "latency_ms": 0,
                "credits": None,
                "response_preview": None,
                "response_full": None,
                "error": "PERPLEXITY_API_KEY не задан в .env",
            }
        bearer = pplx_key
    else:
        if not api_key:
            return {
                "model_id": model_id,
                "label": label,
                "family": family,
                "status": "fail",
                "latency_ms": 0,
                "credits": None,
                "response_preview": None,
                "response_full": None,
                "error": "KIE_API_KEY не задан",
            }
        bearer = api_key

    started = time.perf_counter()
    try:
        resp = await client.post(
            url,
            json=payload,
            headers={
                "Authorization": f"Bearer {bearer}",
                "Content-Type": "application/json",
            },
        )
        latency_ms = round((time.perf_counter() - started) * 1000, 1)
        if resp.status_code >= 400:
            return {
                "model_id": model_id,
                "label": label,
                "family": family,
                "status": "fail",
                "latency_ms": latency_ms,
                "credits": None,
                "response_preview": None,
                "response_full": None,
                "error": f"HTTP {resp.status_code}: {resp.text[:200]}",
            }
        data = resp.json()
        text = _extract_text(data)
        if text:
            return {
                "model_id": model_id,
                "label": label,
                "family": family,
                "status": "ok",
                "latency_ms": latency_ms,
                "credits": data.get("credits_consumed"),
                "response_preview": text[:280],
                "response_full": text[:4000],
                "error": None,
            }
        return {
            "model_id": model_id,
            "label": label,
            "family": family,
            "status": "fail",
            "latency_ms": latency_ms,
            "credits": data.get("credits_consumed"),
            "response_preview": None,
            "response_full": None,
            "error": _error_message(data),
        }
    except Exception as exc:
        latency_ms = round((time.perf_counter() - started) * 1000, 1)
        return {
            "model_id": model_id,
            "label": label,
            "family": family,
            "status": "fail",
            "latency_ms": latency_ms,
            "credits": None,
            "response_preview": None,
            "response_full": None,
            "error": str(exc)[:300],
        }


async def run_model_check() -> dict[str, Any]:
    cfg = load_config()
    api_key = kie_api_key()
    pplx_key = perplexity_api_key()
    prompt = cfg.get("model_probe_prompt") or "Ответь одним словом: OK"
    models = cfg.get("models") or []

    if not api_key and not pplx_key:
        return {
            "error": "Задай KIE_API_KEY и/или PERPLEXITY_API_KEY в .env",
            "results": [],
            "credit": None,
        }

    async with httpx.AsyncClient(timeout=TIMEOUT_SEC) as client:
        credit = await fetch_kie_credit(client, api_key) if api_key else None
        sem = asyncio.Semaphore(4)

        async def _probe(spec: dict[str, str]) -> dict[str, Any]:
            async with sem:
                return await probe_model(client, api_key or "", spec, prompt)

        results = list(await asyncio.gather(*[_probe(spec) for spec in models]))

    return {"error": None, "results": results, "credit": credit, "prompt": prompt, "models_config": models}
