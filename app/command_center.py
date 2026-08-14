"""Command Center — aggregated SEO ops view and priority actions."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.config_loader import load_config, scan_schedule_label, scan_stale_threshold_hours
from app.page_library import config_html_pages
from app.pro_seo_auditor import build_priority_roadmap
from app.storage import (
    get_scan_run,
    latest_checklist_run,
    latest_lab_run,
    latest_pro_run,
    latest_scan_run,
    scan_run_history,
    scan_trends,
)


def _score_delta(current: float | None, previous: float | None) -> float | None:
    if current is None or previous is None:
        return None
    return round(current - previous, 1)


def _pages_from_config() -> list[dict[str, Any]]:
    return config_html_pages()


def _tier_label(page: dict[str, Any]) -> str:
    label = (page.get("label") or "").lower()
    if "tier-1" in label or page.get("tier") == 1:
        return "T1"
    if page.get("pair"):
        return "T2"
    return "—"


def _health_status(last_scan: dict[str, Any] | None, stale_hours: float) -> dict[str, Any]:
    if not last_scan or last_scan.get("status") == "running":
        return {"status": "unknown", "label": "Нет данных", "detail": "Скан ещё не выполнялся"}

    finished = last_scan.get("finished_at")
    stale = False
    if finished and stale_hours > 0:
        try:
            ts = datetime.fromisoformat(finished)
            age_h = (datetime.now(timezone.utc) - ts).total_seconds() / 3600
            stale = age_h > stale_hours
        except Exception:
            pass

    scan_status = last_scan.get("status", "ok")
    if stale:
        return {"status": "warn", "label": "Устарело", "detail": "Последний скан слишком давно"}
    if scan_status == "fail":
        return {"status": "bad", "label": "Проблемы", "detail": "Последний скан завершился с ошибкой"}
    if scan_status == "partial":
        return {"status": "warn", "label": "Частично", "detail": "Скан с предупреждениями"}
    return {"status": "ok", "label": "В норме", "detail": "Мониторинг активен"}


def build_command_center() -> dict[str, Any]:
    """Aggregate latest scan, lab, pro and checklist data into one ops payload."""
    stale_h = scan_stale_threshold_hours()
    cfg = load_config()
    seo_cfg = cfg.get("seo") or {}
    site_name = seo_cfg.get("site_name") or "Site"
    domain = seo_cfg.get("domain") or ""

    last_scan = latest_scan_run()
    prev_scans = scan_run_history(3)
    prev_scan = prev_scans[1] if len(prev_scans) > 1 else None

    last_metrics = (last_scan or {}).get("metrics") or {}
    prev_metrics = (prev_scan or {}).get("metrics") or {}

    checklist_score = last_metrics.get("checklist_score")
    prev_checklist = prev_metrics.get("checklist_score")
    delta = _score_delta(checklist_score, prev_checklist)

    scan_detail = None
    page_rows: list[dict[str, Any]] = []
    if last_scan and last_scan.get("id"):
        scan_detail = get_scan_run(last_scan["id"])
        if scan_detail:
            page_rows = scan_detail.get("pages") or []

    config_pages = _pages_from_config()
    snap_by_url = {p["url"]: p for p in page_rows}

    pairs: list[dict[str, Any]] = []
    for page in config_pages:
        snap = snap_by_url.get(page["url"], {})
        fail_n = snap.get("fail_count") or 0
        warn_n = snap.get("warn_count") or 0
        pairs.append(
            {
                "url": page["url"],
                "label": page.get("label") or page["url"],
                "pair": page.get("pair") or "",
                "tier": _tier_label(page),
                "keyword": page.get("top_keyword") or "",
                "checklist_score": snap.get("checklist_score"),
                "checklist_grade": snap.get("checklist_grade"),
                "seo_score": snap.get("seo_score"),
                "geo_score": snap.get("geo_score"),
                "fail_count": fail_n,
                "warn_count": warn_n,
                "issues": fail_n + warn_n,
                "status": "bad" if fail_n > 0 else ("warn" if warn_n > 0 else "ok"),
            }
        )
    pairs.sort(key=lambda x: (-(x.get("issues") or 0), x.get("checklist_score") or 0))

    # Priority actions from pro roadmap + latest checklist
    actions: list[dict[str, Any]] = []
    pro = latest_pro_run()
    if pro and pro.get("roadmap"):
        for item in pro["roadmap"][:15]:
            actions.append({**item, "source": "pro"})
    else:
        checklist = latest_checklist_run()
        if checklist and checklist.get("results"):
            for item in build_priority_roadmap(checklist["results"])[:15]:
                actions.append({**item, "source": "checklist"})

    p0 = [a for a in actions if a.get("priority") == "P0"][:5]
    p1 = [a for a in actions if a.get("priority") == "P1"][:5]
    today_actions = (p0 + p1)[:8]
    if not today_actions:
        today_actions = actions[:8]

    # Lab signals
    citations = latest_lab_run("citations")
    geo = latest_lab_run("geo")
    bot = latest_lab_run("bot_reality")

    cite_payload = (citations or {}).get("payload") or {}
    cite_summary = cite_payload.get("summary") or {}
    geo_summary = ((geo or {}).get("payload") or {}).get("summary") or {}
    bot_summary = ((bot or {}).get("payload") or {}).get("summary") or {}

    signals: list[dict[str, Any]] = []
    bot_mismatch = last_metrics.get("bot_mismatch") or bot_summary.get("mismatch") or 0
    if bot_mismatch:
        signals.append(
            {
                "type": "bot_mismatch",
                "severity": "critical" if last_metrics.get("bot_critical") else "high",
                "title": f"Bot mismatch: {bot_mismatch} ботов",
                "detail": "robots.txt и HTTP-ответ расходятся",
            }
        )
    if last_metrics.get("seo_fail", 0) > 0:
        signals.append(
            {
                "type": "seo_fail",
                "severity": "high",
                "title": f"SEO fail: {last_metrics['seo_fail']} страниц",
                "detail": "Проверьте SEO-чек на дашборде",
            }
        )
    geo_avg = last_metrics.get("geo_avg_score") or geo_summary.get("avg_score")
    if geo_avg is not None and geo_avg < 40:
        signals.append(
            {
                "type": "geo_low",
                "severity": "medium",
                "title": f"GEO score низкий: {geo_avg}",
                "detail": "Улучшите citability / FAQ / schema",
            }
        )
    if cite_summary.get("site_mentions", 0) == 0 and not cite_payload.get("error"):
        signals.append(
            {
                "type": "no_citations",
                "severity": "medium",
                "title": "AI citations: 0 упоминаний",
                "detail": "Запустите Citation Radar в SEO Lab",
            }
        )
    if delta is not None and delta <= -10:
        signals.append(
            {
                "type": "score_drop",
                "severity": "high",
                "title": f"Score упал на {abs(delta)}%",
                "detail": f"Было {prev_checklist}%, стало {checklist_score}%",
            }
        )

    trends = scan_trends(14)
    tier1 = [p for p in pairs if p["tier"] == "T1"]
    worst_pages = sorted(
        [p for p in pairs if p.get("issues", 0) > 0 or (p.get("checklist_score") or 100) < 70],
        key=lambda x: (-(x.get("issues") or 0), x.get("checklist_score") or 0),
    )[:5]

    return {
        "site_name": site_name,
        "domain": domain,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "health": _health_status(last_scan, stale_h),
        "scan_schedule": scan_schedule_label(),
        "kpis": {
            "checklist_score": checklist_score,
            "checklist_grade": last_metrics.get("checklist_grade"),
            "checklist_delta": delta,
            "seo_avg_score": last_metrics.get("seo_avg_score"),
            "geo_avg_score": geo_avg,
            "pass": last_metrics.get("pass"),
            "warn": last_metrics.get("warn"),
            "fail": last_metrics.get("fail"),
            "bot_mismatch": bot_mismatch,
            "models_ok": last_metrics.get("models_ok"),
            "models_total": last_metrics.get("models_total"),
            "ai_citations": cite_summary.get("site_mentions"),
            "pages_scanned": last_metrics.get("pages_scanned"),
        },
        "last_scan": {
            "id": last_scan.get("id") if last_scan else None,
            "status": last_scan.get("status") if last_scan else None,
            "finished_at": last_scan.get("finished_at") if last_scan else None,
            "trigger": last_scan.get("trigger") if last_scan else None,
            "duration_ms": last_metrics.get("duration_ms"),
        },
        "today_actions": today_actions,
        "signals": signals,
        "pairs": pairs,
        "tier1_pairs": tier1,
        "worst_pages": worst_pages,
        "trends": trends,
        "action_counts": {
            "p0": len(p0),
            "p1": len(p1),
            "total": len(actions),
        },
    }
