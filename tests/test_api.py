import os
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(tmp_path, monkeypatch):
    db = tmp_path / "test.db"
    monkeypatch.setenv("SCAN_INTERVAL_MIN", "0")
    monkeypatch.setenv("SCAN_CRON_TIMES", "off")
    monkeypatch.setenv("AUTO_CHECK_INTERVAL_MIN", "0")
    monkeypatch.setenv("SCAN_SKIP_AI_REVIEW", "true")
    monkeypatch.setenv("MONITOR_API_TOKEN", "")
    monkeypatch.setattr("app.storage.DB_PATH", db)
    monkeypatch.setattr("app.config_loader.DB_PATH", db)
    monkeypatch.setattr("app.config_loader.DATA_DIR", tmp_path)

    from app.storage import init_db

    init_db()
    from app.main import app

    with TestClient(app) as c:
        yield c


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    data = r.json()
    assert data["db"] is True
    assert "scheduler" in data


def test_ready_no_scans(client):
    r = client.get("/ready")
    assert r.status_code in (200, 503)


def test_scan_auth_required(tmp_path, monkeypatch):
    db = tmp_path / "auth.db"
    monkeypatch.setenv("SCAN_INTERVAL_MIN", "0")
    monkeypatch.setenv("SCAN_CRON_TIMES", "off")
    monkeypatch.setenv("AUTO_CHECK_INTERVAL_MIN", "0")
    monkeypatch.setenv("MONITOR_API_TOKEN", "secret-token")
    monkeypatch.setattr("app.storage.DB_PATH", db)
    monkeypatch.setattr("app.config_loader.DB_PATH", db)
    monkeypatch.setattr("app.config_loader.DATA_DIR", tmp_path)

    from app.storage import init_db

    init_db()
    from app.main import app

    with TestClient(app) as c:
        r = c.post("/api/scan/run")
        assert r.status_code == 401


def test_history_page(client):
    r = client.get("/history")
    assert r.status_code == 200
    assert "История сканов" in r.text or "скрининг" in r.text.lower()


def test_seo_skip_ai_review_param(client):
    from unittest.mock import AsyncMock, patch

    with patch("app.main.run_seo_check", new_callable=AsyncMock) as mock_seo:
        mock_seo.return_value = {"error": None, "results": [], "site_name": "test"}
        r = client.post("/api/check/seo?skip_ai_review=true")
        assert r.status_code == 200
        mock_seo.assert_called_once_with(skip_ai_review=True)


def test_abandon_stale_scan_runs(client):
    from app.storage import abandon_stale_scan_runs, connect, start_scan_run

    sid = start_scan_run("test.io", "test", "unit")
    with connect() as conn:
        row = conn.execute("SELECT status FROM scan_runs WHERE id=?", (sid,)).fetchone()
        assert row[0] == "running"
    n = abandon_stale_scan_runs(max_age_minutes=0)
    assert n >= 1


def test_command_page(client):
    r = client.get("/command")
    assert r.status_code == 200
    assert "Command Center" in r.text


def test_command_api(client):
    r = client.get("/api/command")
    assert r.status_code == 200
    data = r.json()
    assert "kpis" in data
    assert "today_actions" in data
    assert "pairs" in data


def test_evaluate_scan_alerts_score_drop():
    from app.alerts import evaluate_scan_alerts
    from app.storage import finish_scan_run, init_db, start_scan_run

    init_db()
    sid1 = start_scan_run("test.io", "test", "unit")
    finish_scan_run(sid1, "ok", {"checklist_score": 80.0}, {})
    sid2 = start_scan_run("test.io", "test", "unit")
    finish_scan_run(sid2, "ok", {"checklist_score": 65.0, "fail": 0}, {})

    alerts = evaluate_scan_alerts(sid2, {"checklist_score": 65.0, "fail": 0}, "ok")
    types = [a["alert_type"] for a in alerts]
    assert "score_drop" in types


def test_alert_log(client):
    from app.storage import log_alert, alert_log_history

    aid = log_alert("test", "info", "Test alert", message="hello")
    assert aid > 0
    hist = alert_log_history(5)
    assert any(h["id"] == aid for h in hist)

    r = client.get("/api/alerts/history")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_eeat_page(client):
    r = client.get("/eeat")
    assert r.status_code == 200
    assert "E-E-A-T" in r.text


def test_ymyl_page(client):
    r = client.get("/ymyl")
    assert r.status_code == 200
    assert "YMYL" in r.text
    assert "Harm Scenarios" in r.text
    assert "YY01" in r.text or "card-YY" in r.text


def test_ymyl_library_overview(client):
    r = client.get("/ymyl-library?tab=overview")
    assert r.status_code == 200
    assert "Overview" in r.text or "overview" in r.text.lower()
    assert "HS-AML-FREEZE" in r.text or "AML" in r.text


def test_library_page(client):
    r = client.get("/library")
    assert r.status_code == 200
    assert "Google QRG" in r.text or "G-QRG" in r.text


def test_specialist_catalog_counts():
    from app.specialist_catalog import load_eeat_catalog, load_ymyl_catalog

    assert len(load_eeat_catalog()) >= 25
    assert len(load_ymyl_catalog()) >= 25


def test_ahrefs_page(client):
    r = client.get("/ahrefs")
    assert r.status_code == 200
    assert "Ahrefs" in r.text
    assert "бриф для дизайна" in r.text.lower() or "Бриф для дизайна" in r.text


def test_ahrefs_classify_link():
    from app.ahrefs_service import classify_link

    spam = classify_link(
        {
            "url_from": "https://spam-backlink.shop/page",
            "url_to": "https://quickex.io/",
            "domain_rating_source": 0,
            "anchor": "Black Hat SEO Telegram:@spam",
            "is_dofollow": True,
        },
        "quickex.io",
    )
    assert spam["is_spam"] is True
    assert spam["is_quality"] is False

    quality = classify_link(
        {
            "url_from": "https://coindesk.com/article",
            "url_to": "https://quickex.io/",
            "domain_rating_source": 92,
            "anchor": "Quickex",
            "is_dofollow": True,
        },
        "quickex.io",
    )
    assert quality["is_quality"] is True
    assert quality["bucket"] == "homepage"


def test_ahrefs_run_mock(client, monkeypatch):
    from unittest.mock import AsyncMock

    mock_result = {
        "run_id": 1,
        "error": None,
        "summary": {"new_links": 5, "quality_links": 1, "spam_links": 2},
        "metrics": {"domain_rating": 62},
        "export_files": {"md_name": "test.md", "csv_name": "test.csv"},
    }
    monkeypatch.setattr("app.main.run_ahrefs_weekly", AsyncMock(return_value=mock_result))
    r = client.post("/api/ahrefs/run")
    assert r.status_code == 200
    assert r.json()["summary"]["new_links"] == 5


def test_leaks_page(client):
    r = client.get("/leaks")
    assert r.status_code == 200
    assert "Google Leaks" in r.text
    assert "Рекомендации" in r.text


def test_leaks_library_seed(client):
    r = client.get("/api/leaks/documents")
    assert r.status_code == 200
    docs = r.json()
    assert len(docs) >= 6
    assert any(d["id"] == "DOC-CW-2024" for d in docs)


def test_eeat_library_page(client):
    r = client.get("/eeat-library")
    assert r.status_code == 200
    assert "E-E-A-T Library" in r.text or "Библиотека E-E-A-T" in r.text


def test_eeat_library_api(client):
    r = client.get("/api/eeat-library/documents")
    assert r.status_code == 200
    docs = r.json()
    assert len(docs) >= 35


def test_ymyl_library_page(client):
    r = client.get("/ymyl-library")
    assert r.status_code == 200
    assert "YMYL Library" in r.text or "Библиотека YMYL" in r.text


def test_ymyl_library_api(client):
    r = client.get("/api/ymyl-library/documents")
    assert r.status_code == 200
    docs = r.json()
    assert len(docs) >= 23
    assert any(d["id"] == "YMYL-R-SEC-BITCOIN" for d in docs)
    r2 = client.get("/api/ymyl-library/insights")
    assert r2.status_code == 200
    assert len(r2.json()) >= 8


def test_leaks_rules_api(client):
    r = client.get("/api/leaks/rules")
    assert r.status_code == 200
    rules = r.json()
    assert len(rules) >= 10
    assert any(rule["id"] == "LK-NAV-001" for rule in rules)


def test_leak_recommendations_engine(client):
    from app.leak_recommendations import build_leak_recommendations

    data = build_leak_recommendations()
    assert "recommendations" in data
    assert "audit_summary" in data


def test_competitors_page(client):
    r = client.get("/competitors")
    assert r.status_code == 200
    assert "Конкуренты" in r.text
    assert "ChangeNOW" in r.text or "changenow" in r.text


def test_competitors_page_null_snapshot_fields(client, monkeypatch):
    monkeypatch.setattr(
        "app.main.latest_competitor_run",
        lambda: {"id": 1, "started_at": "2026-01-01T00:00:00", "summary": {"pages_scanned": 1, "changes_total": 0}},
    )
    monkeypatch.setattr(
        "app.main.competitor_snapshots_for_run",
        lambda *a, **k: [
            {
                "competitor_name": "Test",
                "url": "https://example.com/page",
                "path": "/page",
                "title": None,
                "meta_description": None,
                "word_count": 0,
                "is_new": False,
                "has_changes": False,
            }
        ],
    )
    monkeypatch.setattr("app.main.competitor_changes_for_run", lambda *a, **k: [])
    monkeypatch.setattr("app.main.competitor_run_history", lambda *a, **k: [])
    r = client.get("/competitors")
    assert r.status_code == 200
    assert "example.com" in r.text


def test_all_intel_pages_load(client):
    paths = [
        "/ahrefs",
        "/eeat-library",
        "/eeat-library?tab=library",
        "/ymyl-library",
        "/ymyl-library?tab=criteria",
        "/leaks",
        "/leaks?tab=library",
        "/competitors",
        "/models",
    ]
    for path in paths:
        r = client.get(path)
        assert r.status_code == 200, f"{path} returned {r.status_code}"


def test_competitor_scan_mock(client, monkeypatch):
    from unittest.mock import AsyncMock

    mock_result = {
        "run_id": 1,
        "error": None,
        "summary": {
            "pages_scanned": 10,
            "changes_total": 2,
            "new_landings": 1,
            "title_changes": 1,
            "max_pages_per_site": 100,
        },
        "changes": [
            {
                "competitor_id": "changenow",
                "competitor_name": "ChangeNOW",
                "change_type": "title_changed",
                "url": "https://changenow.io/",
                "before_val": "Old",
                "after_val": "New",
            }
        ],
    }
    monkeypatch.setattr("app.main.run_competitor_scan", AsyncMock(return_value=mock_result))
    r = client.post("/api/competitors/run")
    assert r.status_code == 200
    assert r.json()["summary"]["changes_total"] == 2


def test_competitor_export_routes_404_without_run(client):
    r = client.get("/api/export/competitors/changenow.csv")
    assert r.status_code == 404
    r2 = client.get("/api/export/competitors-all.csv")
    assert r2.status_code == 404
