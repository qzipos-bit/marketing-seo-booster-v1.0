"""AI-powered E-E-A-T research using eeat-research-prompt + Kie/Perplexity API."""

from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Any

import httpx

from app.config_loader import ROOT, kie_api_key, load_config, perplexity_api_key
from app.eeat_research import (
    insights_snapshot_for_prompt,
    library_snapshot_for_prompt,
    process_research_ingest,
)
from app.model_checker import KIE_BASE, _extract_text
from app.storage import finish_eeat_research_run, start_eeat_research_run

DEFAULT_PROMPT = ROOT / "prompts" / "eeat-research-prompt.md"
TIMEOUT_SEC = 240


def _eeat_ai_config() -> dict[str, Any]:
    cfg = load_config()
    return (cfg.get("eeat") or {}).get("ai_research") or {}


def load_system_prompt(prompt_path: Path | None = None) -> str:
    path = prompt_path or Path(_eeat_ai_config().get("prompt_file") or DEFAULT_PROMPT)
    if not path.is_absolute():
        path = ROOT / path
    text = path.read_text(encoding="utf-8")
    match = re.search(
        r"## СИСТЕМНЫЙ ПРОМПТ \(копировать отсюда\)\s*\n\n```\n(.*?)```",
        text,
        re.DOTALL,
    )
    if not match:
        raise ValueError(f"System prompt block not found in {path}")
    return match.group(1).strip()


def build_eeat_user_message(
    audit_payload: dict[str, Any],
    *,
    site_corpus: dict[str, str] | None = None,
    json_ld: list[str] | None = None,
    footer_links: list[str] | None = None,
) -> str:
    ai_cfg = _eeat_ai_config()
    mode = ai_cfg.get("mode") or "audit_and_collect"
    web_search = ai_cfg.get("web_search", True)
    output_lang = ai_cfg.get("output_lang") or "ru"
    ingest_existing = ai_cfg.get("ingest_existing_library", True)

    page = audit_payload.get("page") or {}
    if not page.get("url"):
        page = {
            "url": audit_payload.get("url"),
            "label": audit_payload.get("label"),
        }

    lines = [
        "EEAT RESEARCH REQUEST",
        f"site: {(load_config().get('seo') or {}).get('domain') or 'quickex.io'}",
        f"brand: {(load_config().get('seo') or {}).get('site_name') or 'Quickex'}",
        f"scope: {ai_cfg.get('scope') or 'full_site'}",
        f"page_url: {page.get('url') or ''}",
        f"mode: {mode}",
        f"web_search: {str(web_search).lower()}",
        f"output_lang: {output_lang}",
        "",
        "AUTO_CHECKER (EEAT automated run):",
        json.dumps(
            {
                "summary": audit_payload.get("summary"),
                "results": audit_payload.get("results"),
                "site_pages_found": audit_payload.get("site_pages_found"),
            },
            ensure_ascii=False,
            indent=2,
        )[:12000],
    ]

    if ingest_existing:
        lines.append("")
        lines.append("LIBRARY_SNAPSHOT (уже в базе — НЕ дублируй, только NEW если нашёл новое):")
        lines.append(
            json.dumps(
                {
                    "documents": library_snapshot_for_prompt(),
                    "open_insights": insights_snapshot_for_prompt(),
                },
                ensure_ascii=False,
                indent=2,
            )[:14000],
        )

    corpus = site_corpus or audit_payload.get("site_corpus")
    if corpus:
        lines.append("")
        lines.append("SITE_CORPUS:")
        for path, text in corpus.items():
            lines.append(f"--- {path} ---")
            lines.append((text or "")[:4000])

    ld = json_ld or audit_payload.get("json_ld_corpus")
    if ld:
        lines.append("")
        lines.append("JSON_LD:")
        lines.append(json.dumps(ld[:8], ensure_ascii=False)[:6000])

    fl = footer_links or audit_payload.get("footer_links")
    if fl:
        lines.append("")
        lines.append("FOOTER_LINKS:")
        lines.append(json.dumps(fl[:40], ensure_ascii=False))

    if audit_payload.get("llms_txt"):
        lines.append("")
        lines.append("LLMS_TXT:")
        lines.append(audit_payload["llms_txt"][:2000])

    lines.append("")
    lines.append(
        "Начни с Executive Summary, затем JSON Document Registry (только NEW документы + not_found_mandatory), "
        "затем Criteria Audit. Для документов из LIBRARY_SNAPSHOT указывай существующий id, не создавай дубликаты."
    )
    return "\n".join(lines)


async def run_ai_eeat_research(audit_payload: dict[str, Any]) -> dict[str, Any]:
    """Run deep E-E-A-T research + document collection via configured model."""
    ai_cfg = _eeat_ai_config()
    if not ai_cfg.get("enabled"):
        return {"status": "skip", "error": "eeat.ai_research disabled", "review": None}

    model = ai_cfg.get("model") or "sonar-pro"
    web_search = bool(ai_cfg.get("web_search", True))
    use_perplexity = model.startswith("sonar") or ai_cfg.get("provider") == "perplexity"
    persist = ai_cfg.get("persist_to_library", True)

    api_key = perplexity_api_key() if use_perplexity else kie_api_key()
    if not api_key:
        return {
            "status": "skip",
            "error": "PERPLEXITY_API_KEY or KIE_API_KEY не задан",
            "review": None,
        }

    try:
        system_prompt = load_system_prompt()
    except ValueError as exc:
        return {"status": "fail", "error": str(exc), "review": None}

    page_url = audit_payload.get("url") or (audit_payload.get("page") or {}).get("url") or ""
    page_label = audit_payload.get("label") or (audit_payload.get("page") or {}).get("label") or page_url
    run_id: int | None = None
    if persist:
        run_id = start_eeat_research_run(page_url, page_label)

    user_message = build_eeat_user_message(audit_payload)
    started = time.perf_counter()

    try:
        async with httpx.AsyncClient(timeout=TIMEOUT_SEC) as client:
            if use_perplexity:
                resp = await client.post(
                    "https://api.perplexity.ai/chat/completions",
                    json={
                        "model": model,
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_message},
                        ],
                        "temperature": 0.2,
                        "max_tokens": 8000,
                    },
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                    },
                )
            else:
                from app.model_checker import _build_request

                spec = {
                    "family": "openai",
                    "model": model,
                    "api": "chat",
                    "web_search": web_search,
                }
                _, payload = _build_request(spec["family"], spec["model"], user_message, spec)
                payload["messages"] = [
                    {"role": "developer", "content": [{"type": "text", "text": system_prompt}]},
                    {"role": "user", "content": [{"type": "text", "text": user_message}]},
                ]
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
                result = {
                    "status": "fail",
                    "error": f"HTTP {resp.status_code}: {resp.text[:300]}",
                    "review": None,
                    "latency_ms": latency_ms,
                    "model": model,
                    "run_id": run_id,
                }
                if run_id:
                    finish_eeat_research_run(run_id, {**result, "raw_review": None})
                return result

            data = resp.json()
            text = _extract_text(data)
            if not text:
                result = {
                    "status": "fail",
                    "error": str(data.get("error") or data.get("msg") or "empty response"),
                    "review": None,
                    "latency_ms": latency_ms,
                    "model": model,
                    "run_id": run_id,
                }
                if run_id:
                    finish_eeat_research_run(run_id, {**result, "raw_review": None})
                return result

            ingest: dict[str, Any] = {}
            if persist and ai_cfg.get("auto_ingest", True):
                ingest = process_research_ingest(text, research_run_id=run_id)

            result = {
                "status": "ok",
                "error": None,
                "review": text,
                "latency_ms": latency_ms,
                "model": model,
                "credits": data.get("credits_consumed") or data.get("usage"),
                "run_id": run_id,
                "ingest": ingest,
                "executive_summary": ingest.get("executive_summary"),
            }
            if run_id:
                finish_eeat_research_run(
                    run_id,
                    {
                        "status": "ok",
                        "model": model,
                        "latency_ms": latency_ms,
                        "executive_summary": ingest.get("executive_summary"),
                        "raw_review": text,
                        "registry": ingest.get("registry"),
                        "criteria": ingest.get("criteria"),
                        "ingest": {
                            "documents": ingest.get("documents"),
                            "insights_added": ingest.get("insights_added"),
                            "parsed": ingest.get("parsed"),
                        },
                    },
                )
            return result
    except Exception as exc:
        latency_ms = round((time.perf_counter() - started) * 1000, 1)
        result = {
            "status": "fail",
            "error": str(exc)[:300],
            "review": None,
            "latency_ms": latency_ms,
            "model": model,
            "run_id": run_id,
        }
        if run_id:
            finish_eeat_research_run(run_id, {**result, "raw_review": None})
        return result
