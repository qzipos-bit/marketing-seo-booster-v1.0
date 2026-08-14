"""Persistent full-site scan pipeline — history storage."""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any
from urllib.parse import urlparse

import httpx

from app.alerts import process_scan_alerts
from app.bot_reality_check import run_bot_reality_check
from app.checklist_runner import run_checklist_audit
from app.citability_scorer import score_pages_from_config
from app.config_loader import config_profile, kie_api_key, load_config, scan_skip_ai_review
from app.model_checker import run_model_check
from app.page_library import config_html_pages, get_scan_pages, scan_concurrency
from app.pro_seo_auditor import build_priority_roadmap, build_site_pro_context, run_pro_audit
from app.seo_checker import run_seo_check
from app.storage import (
    finish_checklist_run,
    finish_job_run,
    finish_model_run,
    finish_pro_run,
    finish_scan_run,
    finish_seo_run,
    start_checklist_run,
    start_job_run,
    start_model_run,
    start_pro_run,
    start_scan_run,
    start_seo_run,
    store_scan_page_snapshots,
)

logger = logging.getLogger(__name__)


async def _build_shared_pro_context(pages: list[dict[str, Any]]) -> Any | None:
    if not pages:
        return None
    parsed = urlparse(pages[0]["url"])
    base = f"{parsed.scheme}://{parsed.netloc}"
    page_urls = [p["url"] for p in pages]
    async with httpx.AsyncClient(timeout=25, follow_redirects=True) as client:
        robots = ""
        try:
            r = await client.get(f"{base}/robots.txt")
            if r.status_code == 200:
                robots = r.text
        except Exception:
            pass
        return await build_site_pro_context(client, base, page_urls, robots)


async def _run_checklist_for_page(
    page: dict[str, Any],
    pro_ctx: Any | None,
    seo_by_url: dict[str, dict],
    sem: asyncio.Semaphore,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None, str | None]:
    """Returns (page_snapshot, checklist_payload, error_message)."""
    async with sem:
        run_id = start_checklist_run(
            page["url"],
            page.get("label") or page["url"],
            page.get("pair") or "",
            page.get("lang") or "en",
        )
        cl = await run_checklist_audit(page, pro_ctx=pro_ctx)
        if cl.get("error"):
            finish_checklist_run(run_id, {"summary": {"status": "fail"}, "results": [], **cl})
            return None, None, f"checklist {page['url']}: {cl['error']}"

        finish_checklist_run(run_id, cl)
        summary = cl.get("summary") or {}
        counts = summary.get("counts") or {}
        seo_row = seo_by_url.get(page["url"], {})
        snap = {
            "url": page["url"],
            "label": page.get("label") or page["url"],
            "checklist_score": float(summary.get("score") or 0),
            "checklist_grade": summary.get("grade") or "—",
            "seo_score": seo_row.get("score"),
            "geo_score": None,
            "pass_count": counts.get("pass", 0),
            "warn_count": counts.get("warn", 0),
            "fail_count": counts.get("fail", 0),
        }
        return snap, cl, None


async def run_full_scan(trigger: str = "manual") -> dict[str, Any]:
    """Run complete audit cycle and persist to scan history."""
    started = time.perf_counter()
    job_id = start_job_run("full_scan", trigger)
    cfg = load_config()
    seo_cfg = cfg.get("seo") or {}
    site = seo_cfg.get("domain") or seo_cfg.get("site_name") or "site"
    scan_pages = get_scan_pages()
    pro_pages = config_html_pages() or scan_pages[:1]
    conc = scan_concurrency()
    checklist_concurrency = conc["checklist"]
    seo_concurrency = conc["seo"]

    scan_id = start_scan_run(site, config_profile(), trigger)
    refs: dict[str, int | None] = {
        "checklist_run_id": None,
        "seo_run_id": None,
        "model_run_id": None,
        "pro_run_id": None,
    }
    metrics: dict[str, Any] = {
        "site": site,
        "trigger": trigger,
        "pages_scanned": 0,
        "mandatory_pages": sum(1 for p in scan_pages if p.get("mandatory")),
    }
    page_snapshots: list[dict[str, Any]] = []
    errors: list[str] = []
    last_checklist_results: list[dict] = []

    logger.info("scan started scan_id=%s trigger=%s pages=%s", scan_id, trigger, len(scan_pages))

    # SEO pages check (skip slow AI review during scheduled scans)
    seo_run_id = start_seo_run()
    refs["seo_run_id"] = seo_run_id
    seo_payload = await run_seo_check(
        skip_ai_review=scan_skip_ai_review(),
        pages=scan_pages,
        concurrency=seo_concurrency,
    )
    if seo_payload.get("results"):
        seo_summary = finish_seo_run(seo_run_id, seo_payload["results"])
        metrics["seo_avg_score"] = seo_summary.get("avg_score", 0)
        metrics["seo_fail"] = seo_summary.get("fail", 0)
        seo_by_url = {r["url"]: r for r in seo_payload["results"]}
    else:
        finish_seo_run(seo_run_id, [])
        seo_by_url = {}
        if seo_payload.get("error"):
            errors.append(str(seo_payload["error"]))

    # Shared pro context once per scan (not per page)
    shared_pro_ctx = None
    try:
        shared_pro_ctx = await _build_shared_pro_context(pro_pages)
    except Exception as exc:
        errors.append(f"pro_context: {exc}")
        logger.warning("shared pro context failed: %s", exc)

    # Checklist pages in parallel (bounded)
    sem = asyncio.Semaphore(checklist_concurrency)
    checklist_tasks = [
        _run_checklist_for_page(page, shared_pro_ctx, seo_by_url, sem) for page in scan_pages
    ]
    checklist_outcomes = await asyncio.gather(*checklist_tasks) if checklist_tasks else []

    best_score = 0.0
    best_grade = "—"
    total_pass = total_warn = total_fail = 0

    for snap, cl, err in checklist_outcomes:
        if err:
            errors.append(err)
            continue
        if not snap or not cl:
            continue
        if refs["checklist_run_id"] is None:
            refs["checklist_run_id"] = cl.get("run_id")  # type: ignore[attr-defined]
        last_checklist_results = cl.get("results") or []
        score = snap["checklist_score"]
        if score > best_score:
            best_score = score
            best_grade = snap["checklist_grade"]
        total_pass += snap["pass_count"]
        total_warn += snap["warn_count"]
        total_fail += snap["fail_count"]
        page_snapshots.append(snap)

    metrics["checklist_score"] = best_score
    metrics["checklist_grade"] = best_grade
    metrics["pass"] = total_pass
    metrics["warn"] = total_warn
    metrics["fail"] = total_fail
    metrics["pages_scanned"] = len(page_snapshots)

    # GEO scores
    try:
        geo = await score_pages_from_config(scan_pages)
        if geo.get("results"):
            metrics["geo_avg_score"] = geo.get("summary", {}).get("avg_score", 0)
            geo_map = {r.get("url"): r.get("score") for r in geo["results"]}
            for snap in page_snapshots:
                snap["geo_score"] = geo_map.get(snap["url"])
    except Exception as exc:
        errors.append(f"geo: {exc}")

    # Models (Kie probes)
    if kie_api_key():
        m_run_id = start_model_run()
        refs["model_run_id"] = m_run_id
        m_payload = await run_model_check()
        if m_payload.get("results"):
            m_summary = finish_model_run(m_run_id, m_payload["results"], m_payload.get("credit"))
            metrics["models_ok"] = m_summary.get("ok", 0)
            metrics["models_total"] = m_summary.get("total", 0)
            metrics["kie_credit"] = m_payload.get("credit")
        else:
            finish_model_run(m_run_id, [])

    # Pro audit + bot matrix
    try:
        pro = await run_pro_audit(pro_pages)
        if not pro.get("error") and pro_pages:
            parsed = urlparse(pro_pages[0]["url"])
            base = f"{parsed.scheme}://{parsed.netloc}"
            pro_run_id = start_pro_run(base)
            refs["pro_run_id"] = pro_run_id
            roadmap = build_priority_roadmap(last_checklist_results)
            finish_pro_run(pro_run_id, pro, roadmap)
            br = pro.get("bot_reality") or {}
            metrics["bot_mismatch"] = (br.get("summary") or {}).get("mismatch", 0)
    except Exception as exc:
        errors.append(f"pro: {exc}")

    if scan_pages and "bot_mismatch" not in metrics:
        try:
            parsed = urlparse(scan_pages[0]["url"])
            base = f"{parsed.scheme}://{parsed.netloc}"
            robots = ""
            async with httpx.AsyncClient(timeout=15) as client:
                try:
                    r = await client.get(f"{base}/robots.txt")
                    if r.status_code == 200:
                        robots = r.text
                except Exception:
                    pass
            br = await run_bot_reality_check(scan_pages[0]["url"], robots)
            metrics["bot_mismatch"] = (br.get("summary") or {}).get("mismatch", 0)
            metrics["bot_critical"] = (br.get("summary") or {}).get("has_critical_mismatch", False)
        except Exception as exc:
            errors.append(f"bot_reality: {exc}")

    duration_ms = round((time.perf_counter() - started) * 1000, 1)
    metrics["duration_ms"] = duration_ms
    metrics["errors"] = errors
    status = "ok" if not errors else ("partial" if page_snapshots else "fail")

    store_scan_page_snapshots(scan_id, page_snapshots)
    finish_scan_run(scan_id, status, metrics, refs)
    finish_job_run(job_id, status, duration_ms=duration_ms, meta={"scan_id": scan_id})

    logger.info(
        "scan finished scan_id=%s status=%s duration_ms=%s errors=%s",
        scan_id,
        status,
        duration_ms,
        len(errors),
    )

    try:
        await process_scan_alerts(scan_id, metrics, status)
    except Exception as exc:
        logger.error("scan alerts failed: %s", exc)

    return {
        "scan_id": scan_id,
        "status": status,
        "metrics": metrics,
        "page_snapshots": page_snapshots,
        "errors": errors,
        "duration_ms": duration_ms,
    }
