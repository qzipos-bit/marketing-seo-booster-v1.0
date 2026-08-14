"""SQLite storage for check runs."""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any

from app.config_loader import DATA_DIR, DB_PATH


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def init_db() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS model_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                started_at TEXT NOT NULL,
                finished_at TEXT,
                status TEXT NOT NULL DEFAULT 'running',
                summary_json TEXT
            );

            CREATE TABLE IF NOT EXISTS model_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id INTEGER NOT NULL,
                model_id TEXT NOT NULL,
                label TEXT NOT NULL,
                family TEXT,
                status TEXT NOT NULL,
                latency_ms REAL,
                credits REAL,
                response_preview TEXT,
                response_full TEXT,
                error TEXT,
                FOREIGN KEY (run_id) REFERENCES model_runs(id)
            );

            CREATE TABLE IF NOT EXISTS seo_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                started_at TEXT NOT NULL,
                finished_at TEXT,
                status TEXT NOT NULL DEFAULT 'running',
                summary_json TEXT
            );

            CREATE TABLE IF NOT EXISTS seo_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id INTEGER NOT NULL,
                url TEXT NOT NULL,
                label TEXT NOT NULL,
                status TEXT NOT NULL,
                http_status INTEGER,
                latency_ms REAL,
                score INTEGER,
                issues_json TEXT,
                details_json TEXT,
                FOREIGN KEY (run_id) REFERENCES seo_runs(id)
            );

            CREATE TABLE IF NOT EXISTS checklist_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                started_at TEXT NOT NULL,
                finished_at TEXT,
                url TEXT NOT NULL,
                label TEXT,
                pair TEXT,
                lang TEXT,
                status TEXT NOT NULL DEFAULT 'running',
                summary_json TEXT,
                results_json TEXT
            );

            CREATE TABLE IF NOT EXISTS pro_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                started_at TEXT NOT NULL,
                finished_at TEXT,
                base TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'running',
                report_json TEXT,
                roadmap_json TEXT
            );

            CREATE TABLE IF NOT EXISTS lab_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                feature TEXT NOT NULL,
                started_at TEXT NOT NULL,
                finished_at TEXT,
                status TEXT NOT NULL DEFAULT 'running',
                payload_json TEXT
            );

            CREATE TABLE IF NOT EXISTS drift_baselines (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT NOT NULL,
                label TEXT,
                tag TEXT,
                created_at TEXT NOT NULL,
                snapshot_json TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS export_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                module TEXT NOT NULL,
                format TEXT NOT NULL,
                row_count INTEGER DEFAULT 0,
                site TEXT
            );

            CREATE TABLE IF NOT EXISTS scan_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                started_at TEXT NOT NULL,
                finished_at TEXT,
                status TEXT NOT NULL DEFAULT 'running',
                site TEXT NOT NULL,
                profile TEXT,
                trigger TEXT NOT NULL DEFAULT 'manual',
                checklist_run_id INTEGER,
                seo_run_id INTEGER,
                model_run_id INTEGER,
                pro_run_id INTEGER,
                metrics_json TEXT
            );

            CREATE TABLE IF NOT EXISTS scan_page_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                scan_run_id INTEGER NOT NULL,
                url TEXT NOT NULL,
                label TEXT,
                checklist_score REAL,
                checklist_grade TEXT,
                seo_score INTEGER,
                geo_score INTEGER,
                pass_count INTEGER DEFAULT 0,
                warn_count INTEGER DEFAULT 0,
                fail_count INTEGER DEFAULT 0,
                FOREIGN KEY (scan_run_id) REFERENCES scan_runs(id)
            );

            CREATE INDEX IF NOT EXISTS idx_scan_runs_started ON scan_runs(started_at DESC);
            CREATE INDEX IF NOT EXISTS idx_scan_pages_run ON scan_page_snapshots(scan_run_id);

            CREATE TABLE IF NOT EXISTS job_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_type TEXT NOT NULL,
                trigger TEXT,
                started_at TEXT NOT NULL,
                finished_at TEXT,
                status TEXT NOT NULL DEFAULT 'running',
                duration_ms REAL,
                error TEXT,
                meta_json TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_job_runs_started ON job_runs(started_at DESC);

            CREATE TABLE IF NOT EXISTS alert_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                alert_type TEXT NOT NULL,
                severity TEXT NOT NULL,
                title TEXT NOT NULL,
                message TEXT,
                payload_json TEXT,
                scan_id INTEGER,
                delivered_telegram INTEGER DEFAULT 0,
                delivered_webhook INTEGER DEFAULT 0
            );
            CREATE INDEX IF NOT EXISTS idx_alert_log_created ON alert_log(created_at DESC);

            CREATE TABLE IF NOT EXISTS specialist_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                checklist_type TEXT NOT NULL,
                started_at TEXT NOT NULL,
                finished_at TEXT,
                url TEXT NOT NULL,
                label TEXT,
                status TEXT NOT NULL DEFAULT 'running',
                summary_json TEXT,
                results_json TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_specialist_type ON specialist_runs(checklist_type, id DESC);

            CREATE TABLE IF NOT EXISTS ahrefs_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                target TEXT NOT NULL,
                period_from TEXT,
                period_to TEXT,
                trigger TEXT,
                started_at TEXT NOT NULL,
                finished_at TEXT,
                status TEXT,
                summary_json TEXT,
                payload_json TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_ahrefs_runs_started ON ahrefs_runs(started_at DESC);

            CREATE TABLE IF NOT EXISTS leak_documents (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                category TEXT,
                credibility TEXT,
                source_url TEXT,
                published TEXT,
                summary TEXT,
                content_md TEXT,
                file_name TEXT
            );

            CREATE TABLE IF NOT EXISTS leak_rules (
                id TEXT PRIMARY KEY,
                document_id TEXT NOT NULL,
                name TEXT NOT NULL,
                category TEXT,
                severity TEXT,
                leak_attributes TEXT,
                google_public TEXT,
                leak_evidence TEXT,
                recommendation TEXT,
                audit_triggers_json TEXT,
                FOREIGN KEY (document_id) REFERENCES leak_documents(id)
            );
            CREATE INDEX IF NOT EXISTS idx_leak_rules_doc ON leak_rules(document_id);
            CREATE INDEX IF NOT EXISTS idx_leak_rules_cat ON leak_rules(category);

            CREATE TABLE IF NOT EXISTS eeat_documents (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                tier TEXT,
                doc_type TEXT,
                source_id TEXT,
                category TEXT,
                credibility TEXT,
                source_url TEXT,
                published TEXT,
                publisher TEXT,
                language TEXT,
                eeat_pillar TEXT,
                criteria_ids_json TEXT,
                relevance_score INTEGER,
                supports_brand TEXT,
                summary TEXT,
                content_md TEXT,
                file_name TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_eeat_docs_tier ON eeat_documents(tier);
            CREATE INDEX IF NOT EXISTS idx_eeat_docs_cat ON eeat_documents(category);

            CREATE TABLE IF NOT EXISTS eeat_insights (
                id TEXT PRIMARY KEY,
                document_id TEXT,
                title TEXT NOT NULL,
                severity TEXT,
                eeat_pillar TEXT,
                criteria_ids_json TEXT,
                recommendation TEXT,
                FOREIGN KEY (document_id) REFERENCES eeat_documents(id)
            );

            CREATE TABLE IF NOT EXISTS eeat_research_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                page_url TEXT,
                page_label TEXT,
                started_at TEXT NOT NULL,
                finished_at TEXT,
                status TEXT,
                model TEXT,
                latency_ms REAL,
                executive_summary TEXT,
                raw_review TEXT,
                registry_json TEXT,
                criteria_json TEXT,
                ingest_json TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_eeat_research_started ON eeat_research_runs(started_at DESC);

            CREATE TABLE IF NOT EXISTS ymyl_documents (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                tier TEXT,
                doc_type TEXT,
                source_id TEXT,
                category TEXT,
                credibility TEXT,
                source_url TEXT,
                published TEXT,
                publisher TEXT,
                language TEXT,
                ymyl_block TEXT,
                harm_category TEXT,
                criteria_ids_json TEXT,
                relevance_score INTEGER,
                supports_brand TEXT,
                summary TEXT,
                content_md TEXT,
                file_name TEXT,
                origin TEXT,
                research_run_id INTEGER,
                accessed_date TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_ymyl_docs_tier ON ymyl_documents(tier);
            CREATE INDEX IF NOT EXISTS idx_ymyl_docs_harm ON ymyl_documents(harm_category);

            CREATE TABLE IF NOT EXISTS ymyl_insights (
                id TEXT PRIMARY KEY,
                document_id TEXT,
                title TEXT NOT NULL,
                severity TEXT,
                ymyl_block TEXT,
                harm_category TEXT,
                criteria_ids_json TEXT,
                recommendation TEXT,
                FOREIGN KEY (document_id) REFERENCES ymyl_documents(id)
            );

            CREATE TABLE IF NOT EXISTS competitor_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                trigger TEXT,
                started_at TEXT NOT NULL,
                finished_at TEXT,
                status TEXT,
                summary_json TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_competitor_runs_started ON competitor_runs(started_at DESC);

            CREATE TABLE IF NOT EXISTS competitor_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id INTEGER NOT NULL,
                competitor_id TEXT NOT NULL,
                competitor_name TEXT,
                url TEXT NOT NULL,
                path TEXT,
                http_status INTEGER,
                title TEXT,
                meta_description TEXT,
                h1 TEXT,
                word_count INTEGER,
                content_preview TEXT,
                content_hash TEXT,
                is_new INTEGER DEFAULT 0,
                has_changes INTEGER DEFAULT 0,
                FOREIGN KEY (run_id) REFERENCES competitor_runs(id)
            );
            CREATE INDEX IF NOT EXISTS idx_comp_snap_run ON competitor_snapshots(run_id);
            CREATE INDEX IF NOT EXISTS idx_comp_snap_comp ON competitor_snapshots(competitor_id, run_id);

            CREATE TABLE IF NOT EXISTS competitor_changes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id INTEGER NOT NULL,
                competitor_id TEXT NOT NULL,
                url TEXT,
                path TEXT,
                change_type TEXT,
                field TEXT,
                before_val TEXT,
                after_val TEXT,
                severity TEXT,
                title TEXT,
                meta_description TEXT,
                detected_at TEXT NOT NULL,
                FOREIGN KEY (run_id) REFERENCES competitor_runs(id)
            );
            CREATE INDEX IF NOT EXISTS idx_comp_changes_run ON competitor_changes(run_id);
            CREATE INDEX IF NOT EXISTS idx_comp_changes_type ON competitor_changes(change_type);

            CREATE TABLE IF NOT EXISTS competitor_known_paths (
                competitor_id TEXT NOT NULL,
                path TEXT NOT NULL,
                url TEXT,
                first_seen_at TEXT NOT NULL,
                first_seen_run_id INTEGER,
                PRIMARY KEY (competitor_id, path)
            );
            CREATE INDEX IF NOT EXISTS idx_comp_known ON competitor_known_paths(competitor_id);
            """
        )
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=5000")
        _migrate_schema(conn)

    from app.leak_library import seed_leak_library
    from app.eeat_library import seed_eeat_library
    from app.ymyl_library import seed_ymyl_library

    seed_leak_library()
    seed_eeat_library()
    seed_ymyl_library()


def _migrate_schema(conn) -> None:
    cols = {row[1] for row in conn.execute("PRAGMA table_info(model_results)").fetchall()}
    if cols and "response_full" not in cols:
        conn.execute("ALTER TABLE model_results ADD COLUMN response_full TEXT")
    if cols and "family" not in cols:
        conn.execute("ALTER TABLE model_results ADD COLUMN family TEXT")

    eeat_cols = {row[1] for row in conn.execute("PRAGMA table_info(eeat_documents)").fetchall()}
    if eeat_cols:
        for col, typ in (
            ("origin", "TEXT"),
            ("research_run_id", "INTEGER"),
            ("verification", "TEXT"),
            ("accessed_date", "TEXT"),
        ):
            if col not in eeat_cols:
                conn.execute(f"ALTER TABLE eeat_documents ADD COLUMN {col} {typ}")


@contextmanager
def connect():
    conn = sqlite3.connect(DB_PATH, timeout=5.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout=5000")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def start_model_run() -> int:
    with connect() as conn:
        cur = conn.execute(
            "INSERT INTO model_runs (started_at, status) VALUES (?, 'running')",
            (_utc_now(),),
        )
        return int(cur.lastrowid)


def finish_model_run(
    run_id: int,
    results: list[dict[str, Any]],
    credit: float | None = None,
) -> dict[str, Any]:
    ok = sum(1 for r in results if r["status"] == "ok")
    fail = len(results) - ok
    summary = {
        "total": len(results),
        "ok": ok,
        "fail": fail,
        "credit": credit,
        "avg_latency_ms": round(
            sum(r.get("latency_ms") or 0 for r in results) / max(len(results), 1),
            1,
        ),
    }
    status = "ok" if fail == 0 else ("partial" if ok else "fail")
    with connect() as conn:
        conn.execute(
            """
            UPDATE model_runs
            SET finished_at = ?, status = ?, summary_json = ?
            WHERE id = ?
            """,
            (_utc_now(), status, json.dumps(summary, ensure_ascii=False), run_id),
        )
        for r in results:
            conn.execute(
                """
                INSERT INTO model_results
                (run_id, model_id, label, family, status, latency_ms, credits, response_preview, response_full, error)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    r["model_id"],
                    r["label"],
                    r.get("family"),
                    r["status"],
                    r.get("latency_ms"),
                    r.get("credits"),
                    r.get("response_preview"),
                    r.get("response_full"),
                    r.get("error"),
                ),
            )
    return summary


def start_seo_run() -> int:
    with connect() as conn:
        cur = conn.execute(
            "INSERT INTO seo_runs (started_at, status) VALUES (?, 'running')",
            (_utc_now(),),
        )
        return int(cur.lastrowid)


def finish_seo_run(run_id: int, results: list[dict[str, Any]]) -> dict[str, Any]:
    ok = sum(1 for r in results if r["status"] == "ok")
    warn = sum(1 for r in results if r["status"] == "warn")
    fail = sum(1 for r in results if r["status"] == "fail")
    avg_score = round(
        sum(r.get("score") or 0 for r in results) / max(len(results), 1)
    )
    summary = {
        "total": len(results),
        "ok": ok,
        "warn": warn,
        "fail": fail,
        "avg_score": avg_score,
    }
    status = "ok" if fail == 0 and warn == 0 else ("partial" if ok else "fail")
    with connect() as conn:
        conn.execute(
            """
            UPDATE seo_runs
            SET finished_at = ?, status = ?, summary_json = ?
            WHERE id = ?
            """,
            (_utc_now(), status, json.dumps(summary, ensure_ascii=False), run_id),
        )
        for r in results:
            conn.execute(
                """
                INSERT INTO seo_results
                (run_id, url, label, status, http_status, latency_ms, score, issues_json, details_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    r["url"],
                    r["label"],
                    r["status"],
                    r.get("http_status"),
                    r.get("latency_ms"),
                    r.get("score"),
                    json.dumps(r.get("issues") or [], ensure_ascii=False),
                    json.dumps(r.get("details") or {}, ensure_ascii=False),
                ),
            )
    return summary


def latest_model_run() -> dict[str, Any] | None:
    with connect() as conn:
        row = conn.execute(
            "SELECT * FROM model_runs ORDER BY id DESC LIMIT 1"
        ).fetchone()
        if not row:
            return None
        run = dict(row)
        run["summary"] = json.loads(run.pop("summary_json") or "{}")
        run["results"] = [
            dict(r)
            for r in conn.execute(
                "SELECT * FROM model_results WHERE run_id = ? ORDER BY id",
                (run["id"],),
            ).fetchall()
        ]
        return run


def latest_seo_run() -> dict[str, Any] | None:
    with connect() as conn:
        row = conn.execute(
            "SELECT * FROM seo_runs ORDER BY id DESC LIMIT 1"
        ).fetchone()
        if not row:
            return None
        run = dict(row)
        run["summary"] = json.loads(run.pop("summary_json") or "{}")
        results = []
        for r in conn.execute(
            "SELECT * FROM seo_results WHERE run_id = ? ORDER BY id",
            (run["id"],),
        ).fetchall():
            item = dict(r)
            item["issues"] = json.loads(item.pop("issues_json") or "[]")
            item["details"] = json.loads(item.pop("details_json") or "{}")
            results.append(item)
        run["results"] = results
        return run


def model_run_history(limit: int = 20) -> list[dict[str, Any]]:
    with connect() as conn:
        rows = conn.execute(
            "SELECT * FROM model_runs ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
        out = []
        for row in rows:
            item = dict(row)
            item["summary"] = json.loads(item.pop("summary_json") or "{}")
            out.append(item)
        return out


def seo_run_history(limit: int = 20) -> list[dict[str, Any]]:
    with connect() as conn:
        rows = conn.execute(
            "SELECT * FROM seo_runs ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
        out = []
        for row in rows:
            item = dict(row)
            item["summary"] = json.loads(item.pop("summary_json") or "{}")
            out.append(item)
        return out


def start_checklist_run(url: str, label: str, pair: str, lang: str) -> int:
    with connect() as conn:
        cur = conn.execute(
            """
            INSERT INTO checklist_runs (started_at, url, label, pair, lang, status)
            VALUES (?, ?, ?, ?, ?, 'running')
            """,
            (_utc_now(), url, label, pair, lang),
        )
        return int(cur.lastrowid)


def finish_checklist_run(run_id: int, payload: dict[str, Any]) -> None:
    summary = dict(payload.get("summary") or {})
    summary["is_nuxt"] = payload.get("is_nuxt")
    summary["stack"] = payload.get("stack")
    summary["url"] = payload.get("url")
    summary["label"] = payload.get("label")
    summary["pair"] = payload.get("pair")
    summary["lang"] = payload.get("lang")
    summary["roadmap"] = payload.get("roadmap")
    summary["pro_summary"] = payload.get("pro_summary")
    status = summary.get("status") or "ok"
    with connect() as conn:
        conn.execute(
            """
            UPDATE checklist_runs
            SET finished_at = ?, status = ?, summary_json = ?, results_json = ?
            WHERE id = ?
            """,
            (
                _utc_now(),
                status,
                json.dumps(summary, ensure_ascii=False),
                json.dumps(payload.get("results") or [], ensure_ascii=False),
                run_id,
            ),
        )


def latest_checklist_run() -> dict[str, Any] | None:
    with connect() as conn:
        row = conn.execute(
            "SELECT * FROM checklist_runs ORDER BY id DESC LIMIT 1"
        ).fetchone()
        if not row:
            return None
        run = dict(row)
        run["summary"] = json.loads(run.pop("summary_json") or "{}")
        run["results"] = json.loads(run.pop("results_json") or "[]")
        return run


def checklist_run_history(limit: int = 15) -> list[dict[str, Any]]:
    with connect() as conn:
        rows = conn.execute(
            "SELECT id, started_at, finished_at, url, label, pair, lang, status, summary_json FROM checklist_runs ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
        out = []
        for row in rows:
            item = dict(row)
            item["summary"] = json.loads(item.pop("summary_json") or "{}")
            out.append(item)
        return out


def start_pro_run(base: str) -> int:
    with connect() as conn:
        cur = conn.execute(
            "INSERT INTO pro_runs (started_at, base, status) VALUES (?, ?, 'running')",
            (_utc_now(), base),
        )
        return int(cur.lastrowid)


def finish_pro_run(run_id: int, report: dict[str, Any], roadmap: list[dict[str, Any]]) -> None:
    status = "ok" if not report.get("error") else "fail"
    with connect() as conn:
        conn.execute(
            """
            UPDATE pro_runs
            SET finished_at = ?, status = ?, report_json = ?, roadmap_json = ?
            WHERE id = ?
            """,
            (
                _utc_now(),
                status,
                json.dumps(report, ensure_ascii=False),
                json.dumps(roadmap, ensure_ascii=False),
                run_id,
            ),
        )


def latest_pro_run() -> dict[str, Any] | None:
    with connect() as conn:
        row = conn.execute("SELECT * FROM pro_runs ORDER BY id DESC LIMIT 1").fetchone()
        if not row:
            return None
        run = dict(row)
        run["report"] = json.loads(run.pop("report_json") or "{}")
        run["roadmap"] = json.loads(run.pop("roadmap_json") or "[]")
        return run


def start_lab_run(feature: str) -> int:
    with connect() as conn:
        cur = conn.execute(
            "INSERT INTO lab_runs (feature, started_at, status) VALUES (?, ?, 'running')",
            (feature, _utc_now()),
        )
        return int(cur.lastrowid)


def finish_lab_run(run_id: int, payload: dict[str, Any], status: str = "ok") -> None:
    with connect() as conn:
        conn.execute(
            """
            UPDATE lab_runs SET finished_at = ?, status = ?, payload_json = ? WHERE id = ?
            """,
            (_utc_now(), status, json.dumps(payload, ensure_ascii=False), run_id),
        )


def latest_lab_run(feature: str) -> dict[str, Any] | None:
    with connect() as conn:
        row = conn.execute(
            "SELECT * FROM lab_runs WHERE feature = ? ORDER BY id DESC LIMIT 1",
            (feature,),
        ).fetchone()
        if not row:
            return None
        run = dict(row)
        run["payload"] = json.loads(run.pop("payload_json") or "{}")
        return run


def save_drift_baseline(url: str, label: str, tag: str, snapshot: dict[str, Any]) -> int:
    with connect() as conn:
        cur = conn.execute(
            """
            INSERT INTO drift_baselines (url, label, tag, created_at, snapshot_json)
            VALUES (?, ?, ?, ?, ?)
            """,
            (url, label, tag, _utc_now(), json.dumps(snapshot, ensure_ascii=False)),
        )
        return int(cur.lastrowid)


def get_drift_baseline(baseline_id: int | None = None, url: str | None = None, tag: str | None = None) -> dict[str, Any] | None:
    with connect() as conn:
        if baseline_id:
            row = conn.execute("SELECT * FROM drift_baselines WHERE id = ?", (baseline_id,)).fetchone()
        elif tag and url:
            row = conn.execute(
                "SELECT * FROM drift_baselines WHERE url = ? AND tag = ? ORDER BY id DESC LIMIT 1",
                (url, tag),
            ).fetchone()
        elif url:
            row = conn.execute(
                "SELECT * FROM drift_baselines WHERE url = ? ORDER BY id DESC LIMIT 1",
                (url,),
            ).fetchone()
        else:
            return None
        if not row:
            return None
        item = dict(row)
        item["snapshot"] = json.loads(item.pop("snapshot_json") or "{}")
        return item


def list_drift_baselines(url: str | None = None, limit: int = 20) -> list[dict[str, Any]]:
    with connect() as conn:
        if url:
            rows = conn.execute(
                "SELECT id, url, label, tag, created_at FROM drift_baselines WHERE url = ? ORDER BY id DESC LIMIT ?",
                (url, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT id, url, label, tag, created_at FROM drift_baselines ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [dict(r) for r in rows]


# ── Scan history (Marketing SEO Booster) ─────────────────────────────────


def abandon_stale_scan_runs(max_age_minutes: int = 120) -> int:
    """Mark orphaned running scans as failed (crash or parallel start)."""
    with connect() as conn:
        if max_age_minutes <= 0:
            cur = conn.execute(
                """
                UPDATE scan_runs
                SET status = 'fail', finished_at = ?
                WHERE status = 'running'
                """,
                (_utc_now(),),
            )
        else:
            cur = conn.execute(
                """
                UPDATE scan_runs
                SET status = 'fail', finished_at = ?
                WHERE status = 'running'
                  AND started_at < datetime(?, '-' || ? || ' minutes')
                """,
                (_utc_now(), _utc_now(), max_age_minutes),
            )
        return cur.rowcount


def start_scan_run(site: str, profile: str, trigger: str) -> int:
    abandon_stale_scan_runs(max_age_minutes=0)
    with connect() as conn:
        cur = conn.execute(
            """
            INSERT INTO scan_runs (started_at, site, profile, trigger, status)
            VALUES (?, ?, ?, ?, 'running')
            """,
            (_utc_now(), site, profile, trigger),
        )
        return int(cur.lastrowid)


def finish_scan_run(
    scan_id: int,
    status: str,
    metrics: dict[str, Any],
    refs: dict[str, Any],
) -> None:
    with connect() as conn:
        conn.execute(
            """
            UPDATE scan_runs
            SET finished_at = ?, status = ?, metrics_json = ?,
                checklist_run_id = ?, seo_run_id = ?, model_run_id = ?, pro_run_id = ?
            WHERE id = ?
            """,
            (
                _utc_now(),
                status,
                json.dumps(metrics, ensure_ascii=False),
                refs.get("checklist_run_id"),
                refs.get("seo_run_id"),
                refs.get("model_run_id"),
                refs.get("pro_run_id"),
                scan_id,
            ),
        )


def store_scan_page_snapshots(scan_id: int, snapshots: list[dict[str, Any]]) -> None:
    with connect() as conn:
        for s in snapshots:
            conn.execute(
                """
                INSERT INTO scan_page_snapshots
                (scan_run_id, url, label, checklist_score, checklist_grade,
                 seo_score, geo_score, pass_count, warn_count, fail_count)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    scan_id,
                    s.get("url"),
                    s.get("label"),
                    s.get("checklist_score"),
                    s.get("checklist_grade"),
                    s.get("seo_score"),
                    s.get("geo_score"),
                    s.get("pass_count", 0),
                    s.get("warn_count", 0),
                    s.get("fail_count", 0),
                ),
            )


def scan_run_history(limit: int = 50) -> list[dict[str, Any]]:
    with connect() as conn:
        rows = conn.execute(
            "SELECT * FROM scan_runs ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
        out = []
        for row in rows:
            item = dict(row)
            item["metrics"] = json.loads(item.pop("metrics_json") or "{}")
            out.append(item)
        return out


def latest_scan_run() -> dict[str, Any] | None:
    hist = scan_run_history(1)
    return hist[0] if hist else None


def get_scan_run(scan_id: int) -> dict[str, Any] | None:
    with connect() as conn:
        row = conn.execute("SELECT * FROM scan_runs WHERE id = ?", (scan_id,)).fetchone()
        if not row:
            return None
        item = dict(row)
        item["metrics"] = json.loads(item.pop("metrics_json") or "{}")
        item["pages"] = [
            dict(r)
            for r in conn.execute(
                "SELECT * FROM scan_page_snapshots WHERE scan_run_id = ? ORDER BY id",
                (scan_id,),
            ).fetchall()
        ]
        return item


def scan_trends(limit: int = 30) -> list[dict[str, Any]]:
    """Time series for charts — newest last."""
    runs = scan_run_history(limit)
    runs.reverse()
    series = []
    for r in runs:
        m = r.get("metrics") or {}
        series.append(
            {
                "scan_id": r["id"],
                "at": r.get("finished_at") or r.get("started_at"),
                "status": r.get("status"),
                "trigger": r.get("trigger"),
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
    return series


def scan_stats() -> dict[str, Any]:
    with connect() as conn:
        total = conn.execute("SELECT COUNT(*) FROM scan_runs WHERE status != 'running'").fetchone()[0]
        last = latest_scan_run()
        first_row = conn.execute(
            "SELECT started_at FROM scan_runs ORDER BY id ASC LIMIT 1"
        ).fetchone()
        return {
            "total_scans": total,
            "first_scan_at": first_row[0] if first_row else None,
            "last_scan": last,
        }


def start_job_run(job_type: str, trigger: str = "manual", meta: dict[str, Any] | None = None) -> int:
    with connect() as conn:
        cur = conn.execute(
            """
            INSERT INTO job_runs (job_type, trigger, started_at, status, meta_json)
            VALUES (?, ?, ?, 'running', ?)
            """,
            (job_type, trigger, _utc_now(), json.dumps(meta or {}, ensure_ascii=False)),
        )
        return int(cur.lastrowid)


def finish_job_run(
    job_id: int,
    status: str,
    duration_ms: float | None = None,
    error: str | None = None,
    meta: dict[str, Any] | None = None,
) -> None:
    with connect() as conn:
        conn.execute(
            """
            UPDATE job_runs
            SET finished_at = ?, status = ?, duration_ms = ?, error = ?,
                meta_json = COALESCE(?, meta_json)
            WHERE id = ?
            """,
            (
                _utc_now(),
                status,
                duration_ms,
                error,
                json.dumps(meta, ensure_ascii=False) if meta else None,
                job_id,
            ),
        )


def latest_job_run(job_type: str | None = None) -> dict[str, Any] | None:
    with connect() as conn:
        if job_type:
            row = conn.execute(
                "SELECT * FROM job_runs WHERE job_type = ? ORDER BY id DESC LIMIT 1",
                (job_type,),
            ).fetchone()
        else:
            row = conn.execute(
                "SELECT * FROM job_runs ORDER BY id DESC LIMIT 1"
            ).fetchone()
        if not row:
            return None
        item = dict(row)
        item["meta"] = json.loads(item.pop("meta_json") or "{}")
        return item


def log_alert(
    alert_type: str,
    severity: str,
    title: str,
    message: str | None = None,
    payload: dict[str, Any] | None = None,
    scan_id: int | None = None,
    delivered_telegram: bool = False,
    delivered_webhook: bool = False,
) -> int:
    with connect() as conn:
        cur = conn.execute(
            """
            INSERT INTO alert_log
            (created_at, alert_type, severity, title, message, payload_json, scan_id,
             delivered_telegram, delivered_webhook)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                _utc_now(),
                alert_type,
                severity,
                title,
                message,
                json.dumps(payload or {}, ensure_ascii=False),
                scan_id,
                1 if delivered_telegram else 0,
                1 if delivered_webhook else 0,
            ),
        )
        return int(cur.lastrowid)


def alert_log_history(limit: int = 30) -> list[dict[str, Any]]:
    with connect() as conn:
        rows = conn.execute(
            "SELECT * FROM alert_log ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
        out = []
        for row in rows:
            item = dict(row)
            item["payload"] = json.loads(item.pop("payload_json") or "{}")
            item["delivered_telegram"] = bool(item.get("delivered_telegram"))
            item["delivered_webhook"] = bool(item.get("delivered_webhook"))
            out.append(item)
        return out


def start_specialist_run(checklist_type: str, url: str, label: str) -> int:
    with connect() as conn:
        cur = conn.execute(
            """
            INSERT INTO specialist_runs (checklist_type, started_at, url, label, status)
            VALUES (?, ?, ?, ?, 'running')
            """,
            (checklist_type, _utc_now(), url, label),
        )
        return int(cur.lastrowid)


def finish_specialist_run(run_id: int, payload: dict[str, Any]) -> None:
    summary = payload.get("summary") or {}
    status = summary.get("status") or ("ok" if not payload.get("error") else "fail")
    with connect() as conn:
        conn.execute(
            """
            UPDATE specialist_runs
            SET finished_at = ?, status = ?, summary_json = ?, results_json = ?
            WHERE id = ?
            """,
            (
                _utc_now(),
                status,
                json.dumps(summary, ensure_ascii=False),
                json.dumps(payload.get("results") or [], ensure_ascii=False),
                run_id,
            ),
        )


def latest_specialist_run(checklist_type: str) -> dict[str, Any] | None:
    with connect() as conn:
        row = conn.execute(
            """
            SELECT * FROM specialist_runs
            WHERE checklist_type = ?
            ORDER BY id DESC LIMIT 1
            """,
            (checklist_type,),
        ).fetchone()
        if not row:
            return None
        run = dict(row)
        run["summary"] = json.loads(run.pop("summary_json") or "{}")
        run["results"] = json.loads(run.pop("results_json") or "[]")
        return run


def start_ahrefs_run(target: str, period_from: str, period_to: str, trigger: str) -> int:
    with connect() as conn:
        cur = conn.execute(
            """
            INSERT INTO ahrefs_runs (target, period_from, period_to, trigger, started_at, status)
            VALUES (?, ?, ?, ?, ?, 'running')
            """,
            (target, period_from, period_to, trigger, _utc_now()),
        )
        return int(cur.lastrowid)


def finish_ahrefs_run(run_id: int, payload: dict[str, Any]) -> None:
    summary = payload.get("summary") or {}
    status = summary.get("status") or ("ok" if not payload.get("error") else "fail")
    with connect() as conn:
        conn.execute(
            """
            UPDATE ahrefs_runs
            SET finished_at = ?, status = ?, summary_json = ?, payload_json = ?
            WHERE id = ?
            """,
            (
                _utc_now(),
                status,
                json.dumps(summary, ensure_ascii=False),
                json.dumps(payload, ensure_ascii=False),
                run_id,
            ),
        )


def latest_ahrefs_run() -> dict[str, Any] | None:
    with connect() as conn:
        row = conn.execute(
            "SELECT * FROM ahrefs_runs ORDER BY id DESC LIMIT 1",
        ).fetchone()
        if not row:
            return None
        run = dict(row)
        run["summary"] = json.loads(run.pop("summary_json") or "{}")
        run["payload"] = json.loads(run.pop("payload_json") or "{}")
        return run


def ahrefs_run_history(limit: int = 20) -> list[dict[str, Any]]:
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT id, target, period_from, period_to, trigger, started_at, finished_at, status, summary_json
            FROM ahrefs_runs ORDER BY id DESC LIMIT ?
            """,
            (limit,),
        ).fetchall()
        out = []
        for row in rows:
            item = dict(row)
            item["summary"] = json.loads(item.pop("summary_json") or "{}")
            out.append(item)
        return out


def start_competitor_run(trigger: str) -> int:
    with connect() as conn:
        cur = conn.execute(
            "INSERT INTO competitor_runs (trigger, started_at, status) VALUES (?, ?, 'running')",
            (trigger, _utc_now()),
        )
        return int(cur.lastrowid)


def finish_competitor_run(run_id: int, summary: dict[str, Any], changes: list[dict[str, Any]]) -> None:
    status = summary.get("status") or "ok"
    with connect() as conn:
        conn.execute(
            """
            UPDATE competitor_runs
            SET finished_at = ?, status = ?, summary_json = ?
            WHERE id = ?
            """,
            (_utc_now(), status, json.dumps(summary, ensure_ascii=False), run_id),
        )


def insert_competitor_snapshots(run_id: int, pages: list[dict[str, Any]]) -> None:
    with connect() as conn:
        for p in pages:
            conn.execute(
                """
                INSERT INTO competitor_snapshots
                (run_id, competitor_id, competitor_name, url, path, http_status, title,
                 meta_description, h1, word_count, content_preview, content_hash, is_new, has_changes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    p.get("competitor_id"),
                    p.get("competitor_name"),
                    p.get("url"),
                    p.get("path"),
                    p.get("http_status"),
                    p.get("title"),
                    p.get("meta_description"),
                    p.get("h1"),
                    p.get("word_count"),
                    p.get("content_preview"),
                    p.get("content_hash"),
                    1 if p.get("is_new") else 0,
                    1 if p.get("has_changes") else 0,
                ),
            )


def insert_competitor_changes(run_id: int, changes: list[dict[str, Any]]) -> None:
    now = _utc_now()
    with connect() as conn:
        for c in changes:
            conn.execute(
                """
                INSERT INTO competitor_changes
                (run_id, competitor_id, url, path, change_type, field, before_val, after_val,
                 severity, title, meta_description, detected_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    c.get("competitor_id"),
                    c.get("url"),
                    c.get("path"),
                    c.get("change_type"),
                    c.get("field"),
                    c.get("before_val"),
                    c.get("after_val"),
                    c.get("severity"),
                    c.get("title"),
                    c.get("meta_description"),
                    now,
                ),
            )


def get_previous_competitor_snapshots(competitor_id: str) -> dict[str, dict[str, Any]]:
    with connect() as conn:
        prev_run = conn.execute(
            """
            SELECT id FROM competitor_runs
            WHERE status = 'ok' AND finished_at IS NOT NULL
            ORDER BY id DESC LIMIT 1
            """,
        ).fetchone()
        if not prev_run:
            return {}
        rows = conn.execute(
            """
            SELECT * FROM competitor_snapshots
            WHERE run_id = ? AND competitor_id = ?
            """,
            (prev_run["id"], competitor_id),
        ).fetchall()
        return {row["path"]: dict(row) for row in rows}


def get_known_competitor_paths(competitor_id: str) -> set[str]:
    with connect() as conn:
        rows = conn.execute(
            "SELECT path FROM competitor_known_paths WHERE competitor_id = ?",
            (competitor_id,),
        ).fetchall()
        return {row["path"] for row in rows}


def get_known_competitor_urls(competitor_id: str) -> list[str]:
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT url FROM competitor_known_paths
            WHERE competitor_id = ? AND url IS NOT NULL AND url != ''
            """,
            (competitor_id,),
        ).fetchall()
        return [row["url"] for row in rows]


def upsert_known_competitor_paths(
    competitor_id: str,
    run_id: int,
    pages: list[dict[str, Any]],
) -> int:
    """Register paths; returns count of genuinely new paths."""
    now = _utc_now()
    new_count = 0
    with connect() as conn:
        for p in pages:
            path = p.get("path")
            if not path:
                continue
            cur = conn.execute(
                """
                INSERT OR IGNORE INTO competitor_known_paths
                (competitor_id, path, url, first_seen_at, first_seen_run_id)
                VALUES (?, ?, ?, ?, ?)
                """,
                (competitor_id, path, p.get("url"), now, run_id),
            )
            if cur.rowcount:
                new_count += 1
            else:
                conn.execute(
                    """
                    UPDATE competitor_known_paths SET url = ?
                    WHERE competitor_id = ? AND path = ?
                    """,
                    (p.get("url"), competitor_id, path),
                )
    return new_count


def get_competitor_urls_from_last_run(competitor_id: str) -> list[str]:
    """URLs from the most recent completed run for this competitor."""
    with connect() as conn:
        prev_run = conn.execute(
            """
            SELECT id FROM competitor_runs
            WHERE status = 'ok' AND finished_at IS NOT NULL
            ORDER BY id DESC LIMIT 1
            """,
        ).fetchone()
        if not prev_run:
            return []
        rows = conn.execute(
            "SELECT url FROM competitor_snapshots WHERE run_id = ? AND competitor_id = ?",
            (prev_run["id"], competitor_id),
        ).fetchall()
        return [row["url"] for row in rows if row["url"]]


def latest_competitor_run() -> dict[str, Any] | None:
    with connect() as conn:
        row = conn.execute(
            "SELECT * FROM competitor_runs ORDER BY id DESC LIMIT 1",
        ).fetchone()
        if not row:
            return None
        run = dict(row)
        run["summary"] = json.loads(run.pop("summary_json") or "{}")
        return run


def competitor_run_history(limit: int = 30) -> list[dict[str, Any]]:
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT id, trigger, started_at, finished_at, status, summary_json
            FROM competitor_runs ORDER BY id DESC LIMIT ?
            """,
            (limit,),
        ).fetchall()
        out = []
        for row in rows:
            item = dict(row)
            item["summary"] = json.loads(item.pop("summary_json") or "{}")
            out.append(item)
        return out


def competitor_changes_for_run(run_id: int | None = None, limit: int = 500) -> list[dict[str, Any]]:
    with connect() as conn:
        if run_id is None:
            row = conn.execute(
                "SELECT id FROM competitor_runs WHERE status = 'ok' ORDER BY id DESC LIMIT 1",
            ).fetchone()
            if not row:
                return []
            run_id = row["id"]
        rows = conn.execute(
            """
            SELECT c.*, s.competitor_name
            FROM competitor_changes c
            LEFT JOIN competitor_snapshots s
              ON s.run_id = c.run_id AND s.competitor_id = c.competitor_id AND s.path = c.path
            WHERE c.run_id = ?
            ORDER BY
              CASE c.severity WHEN 'high' THEN 0 WHEN 'warning' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END,
              c.competitor_id, c.change_type
            LIMIT ?
            """,
            (run_id, limit),
        ).fetchall()
        return [dict(r) for r in rows]


def competitor_snapshots_for_run(run_id: int | None = None, competitor_id: str | None = None) -> list[dict[str, Any]]:
    with connect() as conn:
        if run_id is None:
            row = conn.execute(
                "SELECT id FROM competitor_runs ORDER BY id DESC LIMIT 1",
            ).fetchone()
            if not row:
                return []
            run_id = row["id"]
        if competitor_id:
            rows = conn.execute(
                "SELECT * FROM competitor_snapshots WHERE run_id = ? AND competitor_id = ? ORDER BY path",
                (run_id, competitor_id),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM competitor_snapshots WHERE run_id = ? ORDER BY competitor_id, path",
                (run_id,),
            ).fetchall()
        return [dict(r) for r in rows]


def competitor_all_changes(limit: int = 200) -> list[dict[str, Any]]:
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT c.*, r.started_at AS run_date
            FROM competitor_changes c
            JOIN competitor_runs r ON r.id = c.run_id
            ORDER BY c.id DESC LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]


def start_eeat_research_run(page_url: str, page_label: str) -> int:
    with connect() as conn:
        cur = conn.execute(
            """
            INSERT INTO eeat_research_runs (page_url, page_label, started_at, status)
            VALUES (?, ?, ?, 'running')
            """,
            (page_url, page_label, _utc_now()),
        )
        return int(cur.lastrowid)


def finish_eeat_research_run(run_id: int, payload: dict[str, Any]) -> None:
    with connect() as conn:
        conn.execute(
            """
            UPDATE eeat_research_runs
            SET finished_at = ?, status = ?, model = ?, latency_ms = ?,
                executive_summary = ?, raw_review = ?, registry_json = ?,
                criteria_json = ?, ingest_json = ?
            WHERE id = ?
            """,
            (
                _utc_now(),
                payload.get("status"),
                payload.get("model"),
                payload.get("latency_ms"),
                payload.get("executive_summary"),
                payload.get("raw_review"),
                json.dumps(payload.get("registry"), ensure_ascii=False) if payload.get("registry") else None,
                json.dumps(payload.get("criteria"), ensure_ascii=False) if payload.get("criteria") else None,
                json.dumps(payload.get("ingest"), ensure_ascii=False) if payload.get("ingest") else None,
                run_id,
            ),
        )


def latest_eeat_research_run() -> dict[str, Any] | None:
    with connect() as conn:
        row = conn.execute(
            "SELECT * FROM eeat_research_runs ORDER BY id DESC LIMIT 1",
        ).fetchone()
        if not row:
            return None
        item = dict(row)
        for key in ("registry_json", "criteria_json", "ingest_json"):
            if item.get(key):
                try:
                    item[key.replace("_json", "")] = json.loads(item[key])
                except json.JSONDecodeError:
                    pass
        return item


def list_eeat_research_runs(limit: int = 20) -> list[dict[str, Any]]:
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT id, page_url, page_label, started_at, finished_at, status, model,
                   latency_ms, executive_summary, ingest_json
            FROM eeat_research_runs ORDER BY id DESC LIMIT ?
            """,
            (limit,),
        ).fetchall()
        out = []
        for row in rows:
            item = dict(row)
            if item.get("ingest_json"):
                try:
                    item["ingest"] = json.loads(item["ingest_json"])
                except json.JSONDecodeError:
                    item["ingest"] = {}
            out.append(item)
        return out
