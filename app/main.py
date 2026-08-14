"""FastAPI dashboard for Kie model + SEO monitoring."""

from __future__ import annotations

import asyncio
import json
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from zoneinfo import ZoneInfo
from typing import Any, Optional, Union

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.config_loader import (
    ROOT,
    ahrefs_api_key,
    ahrefs_cron_hour,
    ahrefs_enabled,
    app_env,
    auto_check_interval_min,
    competitor_cron_hour,
    competitor_enabled,
    is_production,
    kie_api_key,
    load_config,
    monitor_api_token,
    scan_automation_enabled,
    scan_cron_timezone,
    scan_interval_min,
    scan_schedule,
    scan_schedule_label,
    scan_stale_threshold_hours,
)
from app.ahrefs_service import run_ahrefs_weekly, week_period
from app.leak_library import (
    CATEGORY_LABELS,
    CREDIBILITY_LABELS,
    get_document,
    library_stats,
    list_documents,
    list_rules,
    render_doc_html,
    seed_leak_library,
)
from app.leak_recommendations import build_leak_recommendations, export_recommendations_markdown
from app.eeat_library import (
    CATEGORY_LABELS as EEAT_CATEGORY_LABELS,
    PILLAR_LABELS as EEAT_PILLAR_LABELS,
    SUPPORTS_LABELS as EEAT_SUPPORTS_LABELS,
    TIER_LABELS as EEAT_TIER_LABELS,
    export_library_markdown as export_eeat_library_markdown,
    get_document as get_eeat_document,
    library_stats as eeat_library_stats,
    list_documents as list_eeat_documents,
    list_insights as list_eeat_insights,
    seed_eeat_library,
)
from app.ymyl_library import (
    BLOCK_LABELS as YMYL_BLOCK_LABELS,
    CATEGORY_LABELS as YMYL_CATEGORY_LABELS,
    HARM_LABELS as YMYL_HARM_LABELS,
    HARM_SCENARIOS,
    SUPPORTS_LABELS as YMYL_SUPPORTS_LABELS,
    TIER_LABELS as YMYL_TIER_LABELS,
    block_audit_stats,
    criteria_document_map,
    critical_insights,
    enrich_display_items,
    export_library_markdown as export_ymyl_library_markdown,
    get_document as get_ymyl_document,
    library_stats as ymyl_library_stats,
    list_documents as list_ymyl_documents,
    list_insights as list_ymyl_insights,
    seed_ymyl_library,
)
from app.competitor_monitor import (
    build_changes_csv,
    build_snapshots_csv,
    competitors_config,
    run_competitor_scan,
)
from app.logging_config import setup_logging
from app.security import (
    ApiAuthMiddleware,
    release_ops,
    scan_rate_ok,
    try_acquire_ops,
)
from app.brand import PRODUCT_FULL, PRODUCT_NAME, PRODUCT_TAGLINE, PRODUCT_VERSION
from app.alerts import alert_delivery_status, send_test_alert
from app.command_center import build_command_center
from app.checklist_catalog import BLOCK_NAMES
from app.export_service import (
    export_checklist_csv,
    export_checklist_json,
    export_history,
    export_lab_csv,
    export_models_csv,
    export_pro_csv,
    export_pro_json,
    export_seo_csv,
    export_snapshot_json,
)
from app.i18n_ru import ru_severity, ru_status, ru_verdict
from app.checklist_runner import run_checklist_audit
from app.crypto_audit_runner import run_specialist_audit
from app.eeat_ai_reviewer import run_ai_eeat_research
from app.ymyl_ai_reviewer import run_ai_ymyl_research
from app.specialist_catalog import (
    block_names_for,
    load_eeat_catalog,
    load_sources_library,
    load_ymyl_catalog,
    render_sources_html,
)
from app.bot_reality_check import run_bot_reality_check
from app.citation_radar import run_citation_radar
from app.citability_scorer import score_pages_from_config
from app.drift_monitor import capture_seo_snapshot, compare_snapshots
from app.pro_seo_auditor import build_priority_roadmap, pro_report_markdown, run_pro_audit
from app.model_checker import run_model_check
from app.page_library import config_html_pages
from app.scan_service import run_full_scan
from app.seo_checker import run_seo_check
from app.storage import (
    abandon_stale_scan_runs,
    finish_checklist_run,
    finish_model_run,
    finish_seo_run,
    init_db,
    latest_checklist_run,
    latest_model_run,
    latest_seo_run,
    model_run_history,
    seo_run_history,
    start_checklist_run,
    start_pro_run,
    finish_pro_run,
    latest_pro_run,
    start_lab_run,
    finish_lab_run,
    latest_lab_run,
    save_drift_baseline,
    get_drift_baseline,
    list_drift_baselines,
    start_model_run,
    start_seo_run,
    scan_run_history,
    scan_trends,
    scan_stats,
    latest_scan_run,
    get_scan_run,
    connect,
    alert_log_history,
    start_specialist_run,
    finish_specialist_run,
    latest_specialist_run,
    list_eeat_research_runs,
    latest_eeat_research_run,
    latest_ahrefs_run,
    ahrefs_run_history,
    latest_competitor_run,
    competitor_run_history,
    competitor_changes_for_run,
    competitor_snapshots_for_run,
)

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler()
_check_lock = asyncio.Lock()


async def _run_models_and_store() -> dict[str, Any]:
    async with _check_lock:
        run_id = start_model_run()
        payload = await run_model_check()
        if payload.get("error") and not payload.get("results"):
            finish_model_run(run_id, [])
            return {"run_id": run_id, **payload}
        summary = finish_model_run(run_id, payload["results"], payload.get("credit"))
        return {"run_id": run_id, "summary": summary, **payload}


async def _run_seo_and_store(skip_ai_review: bool = True) -> dict[str, Any]:
    async with _check_lock:
        run_id = start_seo_run()
        payload = await run_seo_check(skip_ai_review=skip_ai_review)
        if payload.get("error") and not payload.get("results"):
            finish_seo_run(run_id, [])
            return {"run_id": run_id, **payload}
        summary = finish_seo_run(run_id, payload["results"])
        return {"run_id": run_id, "summary": summary, **payload}


def _scheduled_checks() -> None:
    if not try_acquire_ops():
        logger.warning("scheduled auto-check skipped: another job running")
        return
    try:
        asyncio.run(_run_models_and_store())
        asyncio.run(_run_seo_and_store())
    finally:
        release_ops()


def _scheduled_full_scan() -> None:
    if not try_acquire_ops():
        logger.warning("scheduled full-scan skipped: another job running")
        return
    try:
        asyncio.run(run_full_scan(trigger="scheduled"))
    finally:
        release_ops()


def _scheduled_ahrefs() -> None:
    if not ahrefs_enabled() or not ahrefs_api_key():
        return
    if not try_acquire_ops():
        logger.warning("scheduled ahrefs skipped: another job running")
        return
    try:
        asyncio.run(run_ahrefs_weekly(trigger="scheduled"))
        logger.info("ahrefs weekly report completed")
    except Exception:
        logger.exception("ahrefs weekly report failed")
    finally:
        release_ops()


def _scheduled_competitors() -> None:
    if not competitor_enabled():
        return
    if not try_acquire_ops():
        logger.warning("scheduled competitor scan skipped: another job running")
        return
    try:
        asyncio.run(run_competitor_scan(trigger="scheduled"))
        logger.info("competitor daily scan completed")
    except Exception:
        logger.exception("competitor daily scan failed")
    finally:
        release_ops()


_scan_lock_full = asyncio.Lock()


async def _run_scan_and_store(trigger: str = "manual") -> dict[str, Any]:
    if not try_acquire_ops():
        raise HTTPException(status_code=429, detail="Другая операция уже выполняется")
    if trigger == "manual" and not scan_rate_ok():
        release_ops()
        raise HTTPException(
            status_code=429,
            detail="Скан можно запускать не чаще одного раза в 5 минут",
        )
    try:
        async with _scan_lock_full:
            return await run_full_scan(trigger=trigger)
    finally:
        release_ops()


@asynccontextmanager
async def lifespan(_: FastAPI):
    setup_logging()
    init_db()
    stale = abandon_stale_scan_runs(max_age_minutes=0)
    if stale:
        logger.warning("marked %s stale scan(s) as failed on startup", stale)
    leak_seed = seed_leak_library()
    if leak_seed.get("seeded"):
        logger.info("google leak library seeded: %s docs, %s rules", leak_seed["documents"], leak_seed["rules"])
    eeat_seed = seed_eeat_library()
    if eeat_seed.get("seeded"):
        logger.info("eeat library seeded: %s docs, %s insights", eeat_seed["documents"], eeat_seed["insights"])
    ymyl_seed = seed_ymyl_library()
    if ymyl_seed.get("seeded"):
        logger.info("ymyl library seeded: %s docs, %s insights", ymyl_seed["documents"], ymyl_seed["insights"])
    interval = auto_check_interval_min()
    if interval > 0:
        scheduler.add_job(
            _scheduled_checks,
            "interval",
            minutes=interval,
            id="auto-check",
            max_instances=1,
            coalesce=True,
        )
    scan_iv = scan_interval_min()
    scan_times = scan_schedule()
    if scan_times:
        hours = ",".join(str(h) for h, _ in scan_times)
        minutes = scan_times[0][1]
        tz = ZoneInfo(scan_cron_timezone())
        scheduler.add_job(
            _scheduled_full_scan,
            CronTrigger(hour=hours, minute=minutes, timezone=tz),
            id="full-scan",
            max_instances=1,
            coalesce=True,
        )
        logger.info(
            "full-scan cron scheduled: %s (%s)",
            scan_schedule_label(),
            scan_cron_timezone(),
        )
    elif scan_iv > 0:
        scheduler.add_job(
            _scheduled_full_scan,
            "interval",
            minutes=scan_iv,
            id="full-scan",
            max_instances=1,
            coalesce=True,
        )
    if interval > 0 or scan_times or scan_iv > 0:
        scheduler.start()
        logger.info("scheduler started auto=%s scan=%s", interval, scan_schedule_label())
    if ahrefs_enabled() and ahrefs_api_key():
        hour = ahrefs_cron_hour()
        scheduler.add_job(
            _scheduled_ahrefs,
            CronTrigger(day_of_week="mon", hour=hour, minute=0),
            id="ahrefs-weekly",
            max_instances=1,
            coalesce=True,
        )
        if not scheduler.running:
            scheduler.start()
        logger.info("ahrefs weekly job scheduled: Monday %s:00", hour)
    if competitor_enabled():
        ch = competitor_cron_hour()
        scheduler.add_job(
            _scheduled_competitors,
            CronTrigger(hour=ch, minute=0),
            id="competitor-daily",
            max_instances=1,
            coalesce=True,
        )
        if not scheduler.running:
            scheduler.start()
        logger.info("competitor daily job scheduled: %s:00 UTC", ch)
    yield
    if scheduler.running:
        scheduler.shutdown(wait=True)
        logger.info("scheduler stopped")


app = FastAPI(
    title=PRODUCT_FULL,
    lifespan=lifespan,
    docs_url=None if is_production() else "/docs",
    redoc_url=None if is_production() else "/redoc",
    openapi_url=None if is_production() else "/openapi.json",
)
app.add_middleware(ApiAuthMiddleware)
app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")
templates = Jinja2Templates(directory=ROOT / "templates")
templates.env.globals["product_name"] = PRODUCT_NAME
templates.env.globals["product_version"] = PRODUCT_VERSION
templates.env.globals["product_full"] = PRODUCT_FULL
templates.env.globals["product_tagline"] = PRODUCT_TAGLINE
templates.env.globals["monitor_api_token"] = monitor_api_token() or ""
templates.env.filters["tojson"] = lambda v: __import__("json").dumps(v, ensure_ascii=False)
templates.env.filters["ru_status"] = ru_status
templates.env.filters["ru_verdict"] = ru_verdict
templates.env.filters["ru_severity"] = ru_severity


def _render(request: Request, template: str, **context: Any):
    return templates.TemplateResponse(request, template, context)


@app.get("/health")
async def health():
    db_ok = False
    try:
        with connect() as conn:
            conn.execute("SELECT 1")
        db_ok = True
    except Exception as exc:
        logger.error("health db check failed: %s", exc)
    return JSONResponse(
        {
            "status": "ok" if db_ok else "degraded",
            "db": db_ok,
            "scheduler": scheduler.running,
            "env": app_env(),
        }
    )


@app.get("/ready")
async def ready():
    db_ok = False
    try:
        with connect() as conn:
            conn.execute("SELECT 1")
        db_ok = True
    except Exception:
        pass

    stale_h = scan_stale_threshold_hours()
    last = latest_scan_run()
    scan_ok = True
    if scan_automation_enabled() and last and last.get("finished_at"):
        try:
            finished = datetime.fromisoformat(last["finished_at"])
            age_h = (datetime.now(timezone.utc) - finished).total_seconds() / 3600
            scan_ok = age_h <= stale_h
        except Exception:
            scan_ok = True
    elif scan_automation_enabled() and not last:
        scan_ok = False

    ready_state = db_ok and (not scan_automation_enabled() or scan_ok)
    return JSONResponse(
        {
            "ready": ready_state,
            "db": db_ok,
            "scan_fresh": scan_ok,
            "last_scan_id": last.get("id") if last else None,
        },
        status_code=200 if ready_state else 503,
    )


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    cfg = load_config()
    return _render(
        request,
        "dashboard.html",
        config=cfg,
        has_api_key=bool(kie_api_key()),
        model_run=latest_model_run(),
        seo_run=latest_seo_run(),
        model_history=model_run_history(10),
        seo_history=seo_run_history(10),
        auto_interval=auto_check_interval_min(),
        scan_interval=scan_interval_min(),
        scan_schedule=scan_schedule_label(),
        scan_stats=scan_stats(),
        models_list=cfg.get("models") or [],
    )


@app.get("/models", response_class=HTMLResponse)
async def models_market(request: Request):
    cfg = load_config()
    models = cfg.get("models") or []
    run = latest_model_run()
    results_map = {}
    if run and run.get("results"):
        results_map = {r["model_id"]: r for r in run["results"]}
    families = sorted({m.get("family", "?") for m in models})
    return _render(
        request,
        "models.html",
        models=models,
        results_map=results_map,
        run=run,
        families=families,
        probe_prompt=cfg.get("model_probe_prompt", ""),
        has_api_key=bool(kie_api_key()),
    )


@app.get("/api/status")
async def api_status():
    return {
        "has_api_key": bool(kie_api_key()),
        "model_run": latest_model_run(),
        "seo_run": latest_seo_run(),
    }


@app.post("/api/check/models")
async def api_check_models():
    result = await _run_models_and_store()
    return JSONResponse(result)


@app.post("/api/check/seo")
async def api_check_seo(skip_ai_review: bool = True):
    result = await _run_seo_and_store(skip_ai_review=skip_ai_review)
    return JSONResponse(result)


@app.post("/api/check/all")
async def api_check_all(skip_ai_review: bool = True):
    models = await _run_models_and_store()
    seo = await _run_seo_and_store(skip_ai_review=skip_ai_review)
    return JSONResponse({"models": models, "seo": seo})


def _html_pages_from_config() -> list[dict]:
    return config_html_pages()


async def _run_checklist_and_store(page_index: int = 0) -> dict[str, Any]:
    pages = _html_pages_from_config()
    if not pages:
        return {"error": "Нет HTML-страниц в config", "results": []}
    page = pages[min(page_index, len(pages) - 1)]
    run_id = start_checklist_run(
        page["url"],
        page.get("label") or page["url"],
        page.get("pair") or "",
        page.get("lang") or "en",
    )
    payload = await run_checklist_audit(page)
    if payload.get("error"):
        finish_checklist_run(run_id, {"summary": {"status": "fail"}, "results": [], **payload})
        return {"run_id": run_id, **payload}
    finish_checklist_run(run_id, payload)
    return {"run_id": run_id, **payload}


@app.get("/checklist", response_class=HTMLResponse)
async def checklist_dashboard(request: Request):
    run = latest_checklist_run()
    pages = _html_pages_from_config()
    return _render(
        request,
        "checklist.html",
        run=run,
        pages=pages,
        blocks=BLOCK_NAMES,
    )


@app.post("/api/check/checklist")
async def api_check_checklist(page_index: int = 0):
    result = await _run_checklist_and_store(page_index)
    return JSONResponse(result)


@app.get("/api/checklist/latest")
async def api_checklist_latest():
    return JSONResponse(latest_checklist_run() or {})


def _specialist_context(checklist_type: str, page_title: str, subtitle: str, api_path: str):
    pages = _html_pages_from_config()
    catalog = load_ymyl_catalog() if checklist_type == "ymyl" else load_eeat_catalog()
    run = latest_specialist_run(checklist_type)
    results_map = {}
    if run and run.get("results"):
        results_map = {r["id"]: r for r in run["results"]}
    display_items = []
    for item in catalog:
        evaluated = results_map.get(item["id"])
        if evaluated:
            display_items.append(evaluated)
        else:
            display_items.append({**item, "status": "pending", "evidence": ""})
    return {
        "checklist_type": checklist_type,
        "page_title": page_title,
        "page_subtitle": subtitle,
        "api_path": api_path,
        "item_count": len(catalog),
        "catalog": catalog,
        "display_items": display_items,
        "pages": pages,
        "blocks": block_names_for(checklist_type),
        "run": run,
    }


async def _run_specialist_and_store(checklist_type: str, page_index: int = 0) -> dict[str, Any]:
    pages = _html_pages_from_config()
    if not pages:
        return {"error": "Нет HTML-страниц в config", "results": []}
    page = pages[min(page_index, len(pages) - 1)]
    run_id = start_specialist_run(checklist_type, page["url"], page.get("label") or page["url"])
    payload = await run_specialist_audit(checklist_type, page_index)
    if payload.get("error"):
        finish_specialist_run(run_id, {"summary": {"status": "fail"}, "results": [], **payload})
        return {"run_id": run_id, **payload}
    finish_specialist_run(run_id, payload)
    return {"run_id": run_id, **payload}


@app.get("/eeat", response_class=HTMLResponse)
async def eeat_dashboard(request: Request):
    return _render(
        request,
        "specialist.html",
        **_specialist_context(
            "eeat",
            "E-E-A-T Audit — Crypto Exchange",
            "Experience · Expertise · Authoritativeness · Trust",
            "/api/check/eeat",
        ),
    )


@app.get("/ymyl", response_class=HTMLResponse)
async def ymyl_dashboard(request: Request):
    ctx = _specialist_context(
        "ymyl",
        "YMYL Audit — Financial Security",
        "Your Money or Your Life · harm prevention",
        "/api/check/ymyl",
    )
    run = ctx.get("run")
    results = (run or {}).get("results") or []
    results_map = {r["id"]: r for r in results}
    ctx["display_items"] = enrich_display_items(ctx["catalog"], results_map)
    ctx["lib_stats"] = ymyl_library_stats()
    ctx["critical_insights"] = critical_insights()
    ctx["harm_scenarios"] = HARM_SCENARIOS
    ctx["harm_labels"] = YMYL_HARM_LABELS
    ctx["block_stats"] = block_audit_stats(results)
    return _render(request, "ymyl.html", **ctx)


@app.get("/library", response_class=HTMLResponse)
async def library_page(request: Request):
    md = load_sources_library()
    return _render(
        request,
        "library.html",
        library_html=render_sources_html(md),
        eeat_count=len(load_eeat_catalog()),
        ymyl_count=len(load_ymyl_catalog()),
    )


@app.post("/api/check/eeat")
async def api_check_eeat(page_index: int = 0):
    result = await _run_specialist_and_store("eeat", page_index)
    return JSONResponse(result)


@app.post("/api/check/eeat/ai-research")
async def api_check_eeat_ai_research(page_index: int = 0):
    """Deep E-E-A-T analysis + document registry via AI (Perplexity/Kie)."""
    base = await _run_specialist_and_store("eeat", page_index)
    if base.get("error") and not base.get("results"):
        return JSONResponse(base, status_code=400)
    ai = await run_ai_eeat_research(base)
    return JSONResponse({**base, "ai_research": ai})


@app.get("/api/eeat-library/research-runs")
async def api_eeat_research_runs():
    return JSONResponse(list_eeat_research_runs())


@app.get("/api/eeat-library/research-runs/latest")
async def api_eeat_research_latest():
    return JSONResponse(latest_eeat_research_run() or {})


@app.post("/api/check/ymyl")
async def api_check_ymyl(page_index: int = 0):
    result = await _run_specialist_and_store("ymyl", page_index)
    return JSONResponse(result)


@app.post("/api/check/ymyl/ai-research")
async def api_check_ymyl_ai_research(page_index: int = 0):
    """Deep YMYL harm-prevention research + document collection via AI."""
    base = await _run_specialist_and_store("ymyl", page_index)
    if base.get("error") and not base.get("results"):
        return JSONResponse(base, status_code=400)
    ai = await run_ai_ymyl_research(base)
    return JSONResponse({**base, "ai_research": ai})


@app.get("/api/eeat/latest")
async def api_eeat_latest():
    return JSONResponse(latest_specialist_run("eeat") or {})


@app.get("/api/ymyl/latest")
async def api_ymyl_latest():
    return JSONResponse(latest_specialist_run("ymyl") or {})


async def _run_pro_and_store(page_index: int = 0) -> dict[str, Any]:
    checklist_result = await _run_checklist_and_store(page_index)
    pages = _html_pages_from_config()
    if not pages:
        return {"error": "Нет HTML-страниц в config", "report": {}, "checklist": checklist_result}
    from urllib.parse import urlparse

    parsed = urlparse(pages[min(page_index, len(pages) - 1)]["url"])
    base = f"{parsed.scheme}://{parsed.netloc}"
    run_id = start_pro_run(base)
    report = await run_pro_audit(pages)
    roadmap = checklist_result.get("roadmap") or build_priority_roadmap(checklist_result.get("results") or [])
    finish_pro_run(run_id, report, roadmap)
    return {"run_id": run_id, "report": report, "roadmap": roadmap, "checklist": checklist_result}


@app.get("/pro", response_class=HTMLResponse)
async def pro_dashboard(request: Request):
    run = latest_pro_run()
    checklist = latest_checklist_run()
    roadmap = run.get("roadmap") if run else []
    if not roadmap and checklist:
        roadmap = (checklist.get("summary") or {}).get("roadmap") or []
    return _render(
        request,
        "pro.html",
        run=run,
        checklist=checklist,
        roadmap=roadmap,
    )


@app.post("/api/check/pro")
async def api_check_pro(page_index: int = 0):
    result = await _run_pro_and_store(page_index)
    return JSONResponse(result)


@app.get("/api/pro/latest")
async def api_pro_latest():
    return JSONResponse(latest_pro_run() or {})


@app.get("/api/pro/export.md")
async def api_pro_export_md():
    from fastapi.responses import PlainTextResponse

    run = latest_pro_run()
    if not run:
        return PlainTextResponse("Pro-аудит ещё не запускался", status_code=404)
    md = pro_report_markdown(run.get("report") or {}, run.get("roadmap") or [])
    return PlainTextResponse(md, media_type="text/markdown; charset=utf-8")


# ── SEO Lab: 5 pro features ──────────────────────────────────────────────


@app.get("/lab", response_class=HTMLResponse)
async def lab_dashboard(request: Request):
    pages = _html_pages_from_config()
    return _render(
        request,
        "lab.html",
        pages=pages,
        has_api_key=bool(kie_api_key()),
        bot_reality=latest_lab_run("bot_reality"),
        drift=latest_lab_run("drift"),
        citations=latest_lab_run("citations"),
        geo=latest_lab_run("geo"),
        render_gap=latest_lab_run("render_gap"),
        drift_baselines=list_drift_baselines(limit=10),
    )


@app.post("/api/lab/bot-reality")
async def api_lab_bot_reality(page_index: int = 0):
    pages = _html_pages_from_config()
    if not pages:
        return JSONResponse({"error": "Нет страниц в конфиге"})
    page = pages[min(page_index, len(pages) - 1)]
    run_id = start_lab_run("bot_reality")
    from urllib.parse import urlparse
    import httpx

    parsed = urlparse(page["url"])
    base = f"{parsed.scheme}://{parsed.netloc}"
    robots = ""
    async with httpx.AsyncClient(timeout=20) as client:
        try:
            r = await client.get(f"{base}/robots.txt")
            if r.status_code == 200:
                robots = r.text
        except Exception:
            pass
    payload = await run_bot_reality_check(page["url"], robots)
    finish_lab_run(run_id, payload, "ok" if not payload.get("error") else "fail")
    return JSONResponse({"run_id": run_id, **payload})


@app.post("/api/lab/drift/baseline")
async def api_lab_drift_baseline(page_index: int = 0, tag: str = "default"):
    pages = _html_pages_from_config()
    if not pages:
        return JSONResponse({"error": "Нет страниц в конфиге"})
    page = pages[min(page_index, len(pages) - 1)]
    snapshot = await capture_seo_snapshot(page["url"])
    bid = save_drift_baseline(page["url"], page.get("label") or page["url"], tag, snapshot)
    run_id = start_lab_run("drift")
    finish_lab_run(run_id, {"action": "baseline", "baseline_id": bid, "snapshot": snapshot})
    return JSONResponse({"baseline_id": bid, "url": page["url"], "tag": tag, "snapshot": snapshot})


@app.post("/api/lab/drift/compare")
async def api_lab_drift_compare(page_index: int = 0, baseline_id: Union[int, None] = None, tag: str = "default"):
    pages = _html_pages_from_config()
    if not pages:
        return JSONResponse({"error": "Нет страниц в конфиге"})
    page = pages[min(page_index, len(pages) - 1)]
    baseline_row = get_drift_baseline(baseline_id=baseline_id, url=page["url"], tag=tag)
    if not baseline_row:
        return JSONResponse({"error": "Baseline не найден — сначала POST /api/lab/drift/baseline"})
    current = await capture_seo_snapshot(page["url"])
    diff = compare_snapshots(baseline_row["snapshot"], current)
    run_id = start_lab_run("drift")
    finish_lab_run(run_id, diff, "fail" if diff.get("critical_count") else "ok")
    return JSONResponse({"baseline_id": baseline_row["id"], **diff})


@app.get("/api/lab/drift/baselines")
async def api_lab_drift_baselines(url: Union[str, None] = None):
    return JSONResponse(list_drift_baselines(url))


@app.post("/api/lab/citations")
async def api_lab_citations():
    run_id = start_lab_run("citations")
    payload = await run_citation_radar()
    status = "fail" if payload.get("error") else "ok"
    finish_lab_run(run_id, payload, status)
    return JSONResponse({"run_id": run_id, **payload})


@app.post("/api/lab/geo")
async def api_lab_geo():
    run_id = start_lab_run("geo")
    payload = await score_pages_from_config()
    finish_lab_run(run_id, payload)
    return JSONResponse({"run_id": run_id, **payload})


@app.post("/api/lab/render-gap")
async def api_lab_render_gap(page_index: int = 0, batch: bool = False):
    run_id = start_lab_run("render_gap")
    if batch:
        payload = await run_render_gap_batch()
    else:
        pages = _html_pages_from_config()
        if not pages:
            return JSONResponse({"error": "Нет страниц в конфиге"})
        page = pages[min(page_index, len(pages) - 1)]
        single = await run_render_gap(page["url"])
        single["label"] = page.get("label")
        payload = {"error": None, "summary": single.get("summary"), "results": [single]}
    finish_lab_run(run_id, payload)
    return JSONResponse({"run_id": run_id, **payload})


@app.post("/api/lab/run-all")
async def api_lab_run_all(page_index: int = 0):
    """Run all 5 features sequentially."""
    pages = _html_pages_from_config()
    if not pages:
        return JSONResponse({"error": "Нет страниц в конфиге"})
    page = pages[min(page_index, len(pages) - 1)]
    results: dict[str, Any] = {}

    from urllib.parse import urlparse
    import httpx

    parsed = urlparse(page["url"])
    base = f"{parsed.scheme}://{parsed.netloc}"
    robots = ""
    async with httpx.AsyncClient(timeout=20) as client:
        try:
            r = await client.get(f"{base}/robots.txt")
            if r.status_code == 200:
                robots = r.text
        except Exception:
            pass

    run_id = start_lab_run("bot_reality")
    br = await run_bot_reality_check(page["url"], robots)
    finish_lab_run(run_id, br)
    results["bot_reality"] = br

    snapshot = await capture_seo_snapshot(page["url"])
    bid = save_drift_baseline(page["url"], page.get("label") or page["url"], "auto", snapshot)
    baseline_row = get_drift_baseline(baseline_id=bid)
    current = await capture_seo_snapshot(page["url"])
    diff = compare_snapshots(baseline_row["snapshot"], current)
    finish_lab_run(start_lab_run("drift"), diff)
    results["drift"] = diff

    if kie_api_key():
        run_id = start_lab_run("citations")
        cr = await run_citation_radar()
        finish_lab_run(run_id, cr, "ok" if not cr.get("error") else "fail")
        results["citations"] = cr
    else:
        results["citations"] = {"error": "KIE_API_KEY не задан"}

    run_id = start_lab_run("geo")
    gr = await score_pages_from_config()
    finish_lab_run(run_id, gr)
    results["geo"] = gr

    run_id = start_lab_run("render_gap")
    rg = await run_render_gap(page["url"])
    rg["label"] = page.get("label")
    finish_lab_run(run_id, {"results": [rg], "summary": rg.get("summary")})
    results["render_gap"] = rg

    return JSONResponse(results)


# ── Data Export (Ahrefs-style) ────────────────────────────────────────────


def _file_response(content: str, filename: str, media: str):
    from fastapi.responses import Response

    if not content:
        return JSONResponse({"error": "Нет данных для выгрузки"}, status_code=404)
    return Response(
        content=content,
        media_type=media,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.get("/api/export/checklist.csv")
async def api_export_checklist_csv():
    content, name, _ = export_checklist_csv()
    return _file_response(content, name, "text/csv; charset=utf-8")


@app.get("/api/export/checklist.json")
async def api_export_checklist_json():
    content, name, _ = export_checklist_json()
    return _file_response(content, name, "application/json; charset=utf-8")


@app.get("/api/export/pro.csv")
async def api_export_pro_csv():
    content, name, _ = export_pro_csv()
    return _file_response(content, name, "text/csv; charset=utf-8")


@app.get("/api/export/pro.json")
async def api_export_pro_json():
    content, name, _ = export_pro_json()
    return _file_response(content, name, "application/json; charset=utf-8")


@app.get("/api/export/models.csv")
async def api_export_models_csv():
    content, name, _ = export_models_csv()
    return _file_response(content, name, "text/csv; charset=utf-8")


@app.get("/api/export/seo.csv")
async def api_export_seo_csv():
    content, name, _ = export_seo_csv()
    return _file_response(content, name, "text/csv; charset=utf-8")


@app.get("/api/export/lab/{feature}.csv")
async def api_export_lab_csv(feature: str):
    allowed = {"bot_reality", "drift", "citations", "geo", "render_gap"}
    if feature not in allowed:
        return JSONResponse({"error": f"Неизвестный модуль: {feature}"}, status_code=400)
    content, name, _ = export_lab_csv(feature)
    return _file_response(content, name, "text/csv; charset=utf-8")


@app.get("/api/export/snapshot.json")
async def api_export_snapshot():
    content, name, _ = export_snapshot_json()
    return _file_response(content, name, "application/json; charset=utf-8")


@app.get("/api/export/history")
async def api_export_history():
    return JSONResponse(export_history())


@app.get("/exports", response_class=HTMLResponse)
async def exports_page(request: Request):
    cfg = load_config()
    return _render(
        request,
        "exports.html",
        site_name=(cfg.get("seo") or {}).get("site_name") or "Site",
        domain=(cfg.get("seo") or {}).get("domain") or "",
        history=export_history(20),
    )


# ── Ahrefs link intelligence ───────────────────────────────────────────


@app.get("/ahrefs", response_class=HTMLResponse)
async def ahrefs_dashboard(request: Request):
    cfg = load_config()
    run = latest_ahrefs_run()
    payload = (run or {}).get("payload") or {}
    date_from, date_to = week_period()
    return _render(
        request,
        "ahrefs.html",
        site_name=(cfg.get("seo") or {}).get("site_name") or "Site",
        domain=(cfg.get("seo") or {}).get("domain") or "",
        run=run,
        payload=payload,
        history=ahrefs_run_history(12),
        has_ahrefs_key=bool(ahrefs_api_key()),
        week_from=date_from,
        week_to=date_to,
        ahrefs_cron_hour=ahrefs_cron_hour(),
    )


@app.post("/api/ahrefs/run")
async def api_ahrefs_run():
    result = await run_ahrefs_weekly(trigger="manual")
    if result.get("error") and not result.get("summary"):
        return JSONResponse(result, status_code=400)
    return JSONResponse(result)


@app.get("/api/ahrefs/latest")
async def api_ahrefs_latest():
    return JSONResponse(latest_ahrefs_run() or {})


@app.get("/api/export/ahrefs-design.md")
async def api_export_ahrefs_design_md():
    run = latest_ahrefs_run()
    if not run:
        return JSONResponse({"error": "Нет Ahrefs-отчёта — запусти проверку"}, status_code=404)
    payload = run.get("payload") or {}
    files = payload.get("export_files") or {}
    md = payload.get("designer_brief_md")
    if not md and files.get("md"):
        from pathlib import Path

        p = Path(files["md"])
        if p.exists():
            md = p.read_text(encoding="utf-8")
    if not md:
        from app.ahrefs_service import build_designer_brief

        md = build_designer_brief(payload)
    name = files.get("md_name") or f"ahrefs_design_{run.get('period_to', 'report')}.md"
    return _file_response(md, name, "text/markdown; charset=utf-8")


@app.get("/api/export/ahrefs-links.csv")
async def api_export_ahrefs_links_csv():
    run = latest_ahrefs_run()
    if not run:
        return JSONResponse({"error": "Нет Ahrefs-отчёта"}, status_code=404)
    payload = run.get("payload") or {}
    from app.ahrefs_service import build_links_csv

    content = build_links_csv(payload.get("links") or [])
    files = payload.get("export_files") or {}
    name = files.get("csv_name") or f"ahrefs_links_{run.get('period_to', 'report')}.csv"
    return _file_response(content, name, "text/csv; charset=utf-8")


# ── Google leak library & audit recommendations ────────────────────────


@app.get("/leaks", response_class=HTMLResponse)
async def leaks_dashboard(request: Request):
    cfg = load_config()
    doc_id = request.query_params.get("doc")
    tab = request.query_params.get("tab", "recommendations")
    doc = get_document(doc_id) if doc_id else None
    rec_data = build_leak_recommendations()
    return _render(
        request,
        "leaks.html",
        site_name=(cfg.get("seo") or {}).get("site_name") or "Site",
        domain=(cfg.get("seo") or {}).get("domain") or "",
        tab=tab,
        documents=list_documents(),
        rules=list_rules(),
        stats=library_stats(),
        rec_data=rec_data,
        selected_doc=doc,
        doc_html=render_doc_html(doc["content_md"]) if doc and doc.get("content_md") else "",
        credibility_labels=CREDIBILITY_LABELS,
        category_labels=CATEGORY_LABELS,
    )


@app.get("/api/leaks/documents")
async def api_leaks_documents():
    return JSONResponse(list_documents())


@app.get("/api/leaks/documents/{doc_id}")
async def api_leaks_document(doc_id: str):
    doc = get_document(doc_id)
    if not doc:
        return JSONResponse({"error": "Document not found"}, status_code=404)
    return JSONResponse(doc)


@app.get("/api/leaks/rules")
async def api_leaks_rules():
    return JSONResponse(list_rules())


@app.get("/api/leaks/recommendations")
async def api_leaks_recommendations():
    return JSONResponse(build_leak_recommendations())


@app.get("/api/export/leaks-recommendations.md")
async def api_export_leaks_recommendations_md():
    content = export_recommendations_markdown()
    domain = (load_config().get("seo") or {}).get("domain") or "site"
    name = f"{domain.replace('.', '_')}_leak_recommendations.md"
    return _file_response(content, name, "text/markdown; charset=utf-8")


@app.post("/api/leaks/reseed")
async def api_leaks_reseed():
    result = seed_leak_library(force=True)
    return JSONResponse(result)


# ── E-E-A-T document library ───────────────────────────────────────────


@app.get("/eeat-library", response_class=HTMLResponse)
async def eeat_library_dashboard(request: Request):
    cfg = load_config()
    doc_id = request.query_params.get("doc")
    tab = request.query_params.get("tab", "insights")
    filter_tier = request.query_params.get("tier") or None
    filter_category = request.query_params.get("category") or None
    doc = get_eeat_document(doc_id) if doc_id else None
    return _render(
        request,
        "eeat_library.html",
        site_name=(cfg.get("seo") or {}).get("site_name") or "Site",
        domain=(cfg.get("seo") or {}).get("domain") or "",
        tab=tab,
        documents=list_eeat_documents(category=filter_category, tier=filter_tier),
        insights=list_eeat_insights(),
        stats=eeat_library_stats(),
        research_runs=list_eeat_research_runs(10),
        latest_research=latest_eeat_research_run(),
        filter_tier=filter_tier or "",
        filter_category=filter_category or "",
        selected_doc=doc,
        doc_html=render_doc_html(doc["content_md"]) if doc and doc.get("content_md") else "",
        tier_labels=EEAT_TIER_LABELS,
        category_labels=EEAT_CATEGORY_LABELS,
        supports_labels=EEAT_SUPPORTS_LABELS,
        pillar_labels=EEAT_PILLAR_LABELS,
    )


@app.get("/api/eeat-library/documents")
async def api_eeat_library_documents():
    return JSONResponse(list_eeat_documents())


@app.get("/api/eeat-library/documents/{doc_id}")
async def api_eeat_library_document(doc_id: str):
    doc = get_eeat_document(doc_id)
    if not doc:
        return JSONResponse({"error": "Document not found"}, status_code=404)
    return JSONResponse(doc)


@app.get("/api/eeat-library/insights")
async def api_eeat_library_insights():
    return JSONResponse(list_eeat_insights())


@app.get("/api/export/eeat-library.md")
async def api_export_eeat_library_md():
    content = export_eeat_library_markdown()
    domain = (load_config().get("seo") or {}).get("domain") or "site"
    name = f"{domain.replace('.', '_')}_eeat_library.md"
    return _file_response(content, name, "text/markdown; charset=utf-8")


@app.post("/api/eeat-library/reseed")
async def api_eeat_library_reseed():
    result = seed_eeat_library(force=True)
    return JSONResponse(result)


# ── YMYL document library ──────────────────────────────────────────────


@app.get("/ymyl-library", response_class=HTMLResponse)
async def ymyl_library_dashboard(request: Request):
    cfg = load_config()
    doc_id = request.query_params.get("doc")
    tab = request.query_params.get("tab", "overview")
    filter_harm = request.query_params.get("harm") or None
    filter_category = request.query_params.get("category") or None
    doc = get_ymyl_document(doc_id) if doc_id else None
    return _render(
        request,
        "ymyl_library.html",
        site_name=(cfg.get("seo") or {}).get("site_name") or "Site",
        domain=(cfg.get("seo") or {}).get("domain") or "",
        tab=tab,
        documents=list_ymyl_documents(category=filter_category, harm_category=filter_harm),
        insights=list_ymyl_insights(),
        stats=ymyl_library_stats(),
        harm_scenarios=HARM_SCENARIOS,
        criteria_map=criteria_document_map(),
        filter_harm=filter_harm or "",
        filter_category=filter_category or "",
        selected_doc=doc,
        doc_html=render_doc_html(doc["content_md"]) if doc and doc.get("content_md") else "",
        tier_labels=YMYL_TIER_LABELS,
        category_labels=YMYL_CATEGORY_LABELS,
        supports_labels=YMYL_SUPPORTS_LABELS,
        harm_labels=YMYL_HARM_LABELS,
        block_labels=YMYL_BLOCK_LABELS,
    )


@app.get("/api/ymyl-library/documents")
async def api_ymyl_library_documents():
    return JSONResponse(list_ymyl_documents())


@app.get("/api/ymyl-library/documents/{doc_id}")
async def api_ymyl_library_document(doc_id: str):
    doc = get_ymyl_document(doc_id)
    if not doc:
        return JSONResponse({"error": "Document not found"}, status_code=404)
    return JSONResponse(doc)


@app.get("/api/ymyl-library/insights")
async def api_ymyl_library_insights():
    return JSONResponse(list_ymyl_insights())


@app.get("/api/export/ymyl-library.md")
async def api_export_ymyl_library_md():
    content = export_ymyl_library_markdown()
    domain = (load_config().get("seo") or {}).get("domain") or "site"
    name = f"{domain.replace('.', '_')}_ymyl_library.md"
    return _file_response(content, name, "text/markdown; charset=utf-8")


@app.post("/api/ymyl-library/reseed")
async def api_ymyl_library_reseed():
    result = seed_ymyl_library(force=True)
    return JSONResponse(result)


# ── Competitor monitor ─────────────────────────────────────────────────


@app.get("/competitors", response_class=HTMLResponse)
async def competitors_dashboard(request: Request):
    cfg = load_config()
    run = latest_competitor_run()
    run_id = run["id"] if run else None
    filter_comp = request.query_params.get("competitor", "")
    changes = competitor_changes_for_run(run_id)
    if filter_comp:
        changes = [c for c in changes if c.get("competitor_id") == filter_comp]
    snapshots = competitor_snapshots_for_run(run_id, filter_comp or None)
    return _render(
        request,
        "competitors.html",
        site_name=(cfg.get("seo") or {}).get("site_name") or "Site",
        run=run,
        changes=changes,
        snapshots=snapshots,
        sites=competitors_config(),
        history=competitor_run_history(14),
        filter_comp=filter_comp,
        competitor_cron_hour=competitor_cron_hour(),
    )


@app.post("/api/competitors/run")
async def api_competitors_run():
    if not try_acquire_ops():
        return JSONResponse({"error": "Другая операция выполняется"}, status_code=429)
    try:
        result = await run_competitor_scan(trigger="manual")
        return JSONResponse(result)
    finally:
        release_ops()


@app.get("/api/competitors/latest")
async def api_competitors_latest():
    run = latest_competitor_run()
    if not run:
        return JSONResponse({})
    changes = competitor_changes_for_run(run["id"])
    return JSONResponse({**run, "changes": changes})


@app.get("/api/export/competitors-changes.csv")
async def api_export_competitors_csv():
    run = latest_competitor_run()
    if not run:
        return JSONResponse({"error": "Нет среза конкурентов"}, status_code=404)
    changes = competitor_changes_for_run(run["id"])
    sites = {s["id"]: s["name"] for s in competitors_config()}
    for c in changes:
        if not c.get("competitor_name"):
            c["competitor_name"] = sites.get(c.get("competitor_id", ""), "")
    content = build_changes_csv(changes)
    date = (run.get("started_at") or "")[:10] or "report"
    name = f"competitors_changes_{date}.csv"
    return _file_response(content, name, "text/csv; charset=utf-8")


@app.get("/api/export/competitors/{competitor_id}.csv")
async def api_export_competitor_snapshots_csv(competitor_id: str):
    run = latest_competitor_run()
    if not run:
        return JSONResponse({"error": "Нет среза конкурентов"}, status_code=404)
    snapshots = competitor_snapshots_for_run(run["id"], competitor_id)
    if not snapshots:
        return JSONResponse({"error": "Нет данных по конкуренту"}, status_code=404)
    sites = {s["id"]: s["name"] for s in competitors_config()}
    for s in snapshots:
        if not s.get("competitor_name"):
            s["competitor_name"] = sites.get(competitor_id, competitor_id)
    content = build_snapshots_csv(snapshots)
    date = (run.get("started_at") or "")[:10] or "report"
    name = f"competitor_{competitor_id}_{date}.csv"
    return _file_response(content, name, "text/csv; charset=utf-8")


@app.get("/api/export/competitors-all.csv")
async def api_export_all_competitor_snapshots_csv():
    run = latest_competitor_run()
    if not run:
        return JSONResponse({"error": "Нет среза конкурентов"}, status_code=404)
    snapshots = competitor_snapshots_for_run(run["id"])
    sites = {s["id"]: s["name"] for s in competitors_config()}
    for s in snapshots:
        if not s.get("competitor_name"):
            s["competitor_name"] = sites.get(s.get("competitor_id", ""), "")
    content = build_snapshots_csv(snapshots)
    date = (run.get("started_at") or "")[:10] or "report"
    name = f"competitors_all_pages_{date}.csv"
    return _file_response(content, name, "text/csv; charset=utf-8")


# ── Scan history & persistent screening ────────────────────────────────


@app.get("/command", response_class=HTMLResponse)
async def command_dashboard(request: Request):
    cfg = load_config()
    data = build_command_center()
    return _render(
        request,
        "command.html",
        site_name=(cfg.get("seo") or {}).get("site_name") or "Site",
        domain=(cfg.get("seo") or {}).get("domain") or "",
        cmd=data,
        alerts_status=alert_delivery_status(),
        scan_schedule=scan_schedule_label(),
        alerts=alert_log_history(15),
    )


@app.get("/api/command")
async def api_command():
    return JSONResponse(build_command_center())


@app.get("/api/alerts/history")
async def api_alerts_history(limit: int = 30):
    return JSONResponse(alert_log_history(limit))


@app.get("/api/alerts/status")
async def api_alerts_status():
    return JSONResponse(alert_delivery_status())


@app.post("/api/alerts/test")
async def api_alerts_test():
    result = await send_test_alert()
    return JSONResponse(result)


@app.get("/history", response_class=HTMLResponse)
async def history_dashboard(request: Request):
    cfg = load_config()
    return _render(
        request,
        "history.html",
        site_name=(cfg.get("seo") or {}).get("site_name") or "Site",
        domain=(cfg.get("seo") or {}).get("domain") or "",
        stats=scan_stats(),
        scans=scan_run_history(40),
        trends=scan_trends(30),
        scan_schedule=scan_schedule_label(),
    )


@app.post("/api/scan/run")
async def api_scan_run():
    try:
        result = await _run_scan_and_store(trigger="manual")
    except HTTPException:
        raise
    return JSONResponse(result)


@app.get("/api/scan/latest")
async def api_scan_latest():
    return JSONResponse(latest_scan_run() or {})


@app.get("/api/scan/history")
async def api_scan_history(limit: int = 50):
    return JSONResponse(scan_run_history(limit))


@app.get("/api/scan/trends")
async def api_scan_trends(limit: int = 30):
    return JSONResponse(scan_trends(limit))


@app.get("/api/scan/{scan_id}")
async def api_scan_detail(scan_id: int):
    run = get_scan_run(scan_id)
    if not run:
        return JSONResponse({"error": "Скан не найден"}, status_code=404)
    return JSONResponse(run)


@app.get("/api/export/scan-history.csv")
async def api_export_scan_history_csv():
    from app.export_service import export_scan_history_csv

    content, name, _ = export_scan_history_csv()
    return _file_response(content, name, "text/csv; charset=utf-8")
