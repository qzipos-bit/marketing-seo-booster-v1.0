"""Export service — CSV/JSON выгрузки как в Ahrefs/Screaming Frog."""

from __future__ import annotations

import csv
import io
import json
from datetime import datetime, timezone
from typing import Any

from app.config_loader import load_config
from app.storage import (
    connect,
    latest_checklist_run,
    latest_lab_run,
    latest_model_run,
    latest_pro_run,
    latest_seo_run,
    list_drift_baselines,
    scan_run_history,
)


def _site_slug() -> str:
    cfg = load_config()
    name = (cfg.get("seo") or {}).get("site_name") or "site"
    domain = (cfg.get("seo") or {}).get("domain") or name
    return domain.replace(".", "_").lower()


def _stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d_%H%M")


def _filename(module: str, ext: str) -> str:
    return f"{_site_slug()}_{module}_{_stamp()}.{ext}"


def log_export(module: str, fmt: str, rows: int) -> None:
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO export_log (created_at, module, format, row_count, site)
            VALUES (?, ?, ?, ?, ?)
            """,
            (datetime.now(timezone.utc).isoformat(), module, fmt, rows, _site_slug()),
        )


def export_history(limit: int = 30) -> list[dict[str, Any]]:
    with connect() as conn:
        rows = conn.execute(
            "SELECT * FROM export_log ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]


def _csv_response(rows: list[dict[str, Any]], fieldnames: list[str]) -> tuple[str, str]:
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        flat = {k: row.get(k, "") for k in fieldnames}
        for k, v in flat.items():
            if isinstance(v, (list, dict)):
                flat[k] = json.dumps(v, ensure_ascii=False)
        writer.writerow(flat)
    return buf.getvalue(), _filename("export", "csv")


# ── Checklist ─────────────────────────────────────────────────────────────


def export_checklist_csv() -> tuple[str, str, int]:
    run = latest_checklist_run()
    if not run or not run.get("results"):
        return "", _filename("checklist", "csv"), 0
    rows = []
    for r in run["results"]:
        rows.append(
            {
                "id": r.get("id"),
                "block": r.get("block"),
                "block_name": r.get("block_name"),
                "severity": r.get("severity"),
                "scope": r.get("scope"),
                "title": r.get("title"),
                "status": r.get("status"),
                "evidence": r.get("evidence"),
                "url": run.get("url"),
                "label": run.get("label"),
                "run_at": run.get("finished_at") or run.get("started_at"),
            }
        )
    fields = ["id", "block", "block_name", "severity", "scope", "title", "status", "evidence", "url", "label", "run_at"]
    content, _ = _csv_response(rows, fields)
    log_export("checklist", "csv", len(rows))
    return content, _filename("checklist", "csv"), len(rows)


def export_checklist_json() -> tuple[str, str, int]:
    run = latest_checklist_run() or {}
    payload = {
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "site": _site_slug(),
        "run": run,
    }
    n = len(run.get("results") or [])
    log_export("checklist", "json", n)
    return json.dumps(payload, ensure_ascii=False, indent=2), _filename("checklist", "json"), n


# ── Pro ───────────────────────────────────────────────────────────────────


def export_pro_json() -> tuple[str, str, int]:
    run = latest_pro_run() or {}
    payload = {
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "site": _site_slug(),
        "report": run.get("report") or {},
        "roadmap": run.get("roadmap") or [],
    }
    n = len(payload.get("roadmap") or [])
    log_export("pro", "json", n)
    return json.dumps(payload, ensure_ascii=False, indent=2), _filename("pro", "json"), n


def export_pro_csv() -> tuple[str, str, int]:
    run = latest_pro_run()
    if not run:
        return "", _filename("pro", "csv"), 0
    report = run.get("report") or {}
    rows: list[dict[str, Any]] = []
    for bot, st in (report.get("bot_access_flat") or {}).items():
        rows.append({"section": "bot_matrix", "key": bot, "value": st})
    for h, v in (report.get("security_headers") or {}).items():
        rows.append({"section": "security", "key": h, "value": v})
    for item in run.get("roadmap") or []:
        rows.append(
            {
                "section": "roadmap",
                "priority": item.get("priority"),
                "id": item.get("id"),
                "title": item.get("title"),
                "evidence": item.get("evidence"),
            }
        )
    fields = ["section", "key", "value", "priority", "id", "title", "evidence"]
    content, _ = _csv_response(rows, fields)
    log_export("pro", "csv", len(rows))
    return content, _filename("pro", "csv"), len(rows)


# ── Lab features ──────────────────────────────────────────────────────────


def export_lab_csv(feature: str) -> tuple[str, str, int]:
    run = latest_lab_run(feature)
    if not run or not run.get("payload"):
        return "", _filename(f"lab_{feature}", "csv"), 0
    payload = run["payload"]
    rows: list[dict[str, Any]] = []

    if feature == "bot_reality":
        for r in payload.get("results") or []:
            rows.append({**r, "url": payload.get("url")})
        fields = ["bot", "robots", "http_status", "verdict", "body_len", "latency_ms", "url"]
    elif feature == "citations":
        for r in payload.get("results") or []:
            rows.append(r)
        fields = ["query", "model_label", "family", "status", "cites_target_domain", "latency_ms", "response_preview"]
    elif feature == "geo":
        for r in payload.get("results") or []:
            rows.append(r)
        fields = ["label", "url", "score", "grade", "http_status"]
    elif feature == "drift":
        for c in payload.get("changes") or []:
            rows.append(c)
        fields = ["severity", "rule", "message", "before", "after"]
    elif feature == "render_gap":
        for r in payload.get("results") or []:
            for g in r.get("gaps") or []:
                rows.append({**g, "page_url": r.get("url"), "label": r.get("label")})
        fields = ["page_url", "label", "field", "severity", "message", "raw", "rendered"]
    else:
        rows = [{"json": json.dumps(payload, ensure_ascii=False)}]
        fields = ["json"]

    content, _ = _csv_response(rows, fields)
    log_export(f"lab_{feature}", "csv", len(rows))
    return content, _filename(f"lab_{feature}", "csv"), len(rows)


# ── Models & SEO ──────────────────────────────────────────────────────────


def export_models_csv() -> tuple[str, str, int]:
    run = latest_model_run()
    if not run or not run.get("results"):
        return "", _filename("models", "csv"), 0
    rows = []
    for r in run["results"]:
        rows.append(
            {
                "model_id": r.get("model_id"),
                "label": r.get("label"),
                "family": r.get("family"),
                "status": r.get("status"),
                "latency_ms": r.get("latency_ms"),
                "credits": r.get("credits"),
                "response_preview": (r.get("response_preview") or "")[:500],
                "error": r.get("error"),
                "run_at": run.get("finished_at") or run.get("started_at"),
            }
        )
    fields = ["model_id", "label", "family", "status", "latency_ms", "credits", "response_preview", "error", "run_at"]
    content, _ = _csv_response(rows, fields)
    log_export("models", "csv", len(rows))
    return content, _filename("models", "csv"), len(rows)


def export_seo_csv() -> tuple[str, str, int]:
    run = latest_seo_run()
    if not run or not run.get("results"):
        return "", _filename("seo", "csv"), 0
    rows = []
    for r in run["results"]:
        rows.append(
            {
                "url": r.get("url"),
                "label": r.get("label"),
                "status": r.get("status"),
                "score": r.get("score"),
                "http_status": r.get("http_status"),
                "latency_ms": r.get("latency_ms"),
                "issues": json.dumps(r.get("issues") or [], ensure_ascii=False),
                "run_at": run.get("finished_at") or run.get("started_at"),
            }
        )
    fields = ["url", "label", "status", "score", "http_status", "latency_ms", "issues", "run_at"]
    content, _ = _csv_response(rows, fields)
    log_export("seo", "csv", len(rows))
    return content, _filename("seo", "csv"), len(rows)


# ── Full snapshot ─────────────────────────────────────────────────────────


def export_snapshot_json() -> tuple[str, str, int]:
    payload = {
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "site": _site_slug(),
        "checklist": latest_checklist_run(),
        "pro": latest_pro_run(),
        "models": latest_model_run(),
        "seo": latest_seo_run(),
        "lab": {
            "bot_reality": latest_lab_run("bot_reality"),
            "drift": latest_lab_run("drift"),
            "citations": latest_lab_run("citations"),
            "geo": latest_lab_run("geo"),
            "render_gap": latest_lab_run("render_gap"),
        },
        "drift_baselines": list_drift_baselines(limit=50),
        "scan_history": scan_run_history(50),
    }
    n = sum(1 for k in ("checklist", "pro", "models", "seo") if payload.get(k))
    n += len(payload.get("scan_history") or [])
    log_export("snapshot", "json", n)
    return json.dumps(payload, ensure_ascii=False, indent=2, default=str), _filename("snapshot", "json"), n


def export_scan_history_csv() -> tuple[str, str, int]:
    runs = scan_run_history(200)
    rows = []
    for r in runs:
        m = r.get("metrics") or {}
        rows.append(
            {
                "scan_id": r.get("id"),
                "started_at": r.get("started_at"),
                "finished_at": r.get("finished_at"),
                "status": r.get("status"),
                "trigger": r.get("trigger"),
                "site": r.get("site"),
                "checklist_score": m.get("checklist_score"),
                "checklist_grade": m.get("checklist_grade"),
                "seo_avg_score": m.get("seo_avg_score"),
                "geo_avg_score": m.get("geo_avg_score"),
                "pass": m.get("pass"),
                "fail": m.get("fail"),
                "models_ok": m.get("models_ok"),
                "bot_mismatch": m.get("bot_mismatch"),
            }
        )
    fields = [
        "scan_id", "started_at", "finished_at", "status", "trigger", "site",
        "checklist_score", "checklist_grade", "seo_avg_score", "geo_avg_score",
        "pass", "fail", "models_ok", "bot_mismatch",
    ]
    content, _ = _csv_response(rows, fields)
    log_export("scan_history", "csv", len(rows))
    return content, _filename("scan_history", "csv"), len(rows)
