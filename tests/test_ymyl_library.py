"""Tests for YMYL document library."""

import pytest


@pytest.fixture()
def ymyl_db():
    from app.storage import connect, init_db
    from app.ymyl_library import seed_ymyl_library

    init_db()
    with connect() as conn:
        conn.execute("DELETE FROM ymyl_insights WHERE id LIKE 'INS-AI-%'")
        conn.execute("DELETE FROM ymyl_documents WHERE origin = 'ai_research'")
    seed_ymyl_library(force=True)
    yield


def test_seed_ymyl_library(ymyl_db):
    from app.ymyl_library import DOCUMENTS, INSIGHTS, seed_ymyl_library

    second = seed_ymyl_library()
    assert second["seeded"] is False
    assert second["documents"] >= len(DOCUMENTS)

    forced = seed_ymyl_library(force=True)
    assert forced["seeded"] is True
    assert forced["documents"] == len(DOCUMENTS)
    assert forced["insights"] == len(INSIGHTS)


def test_list_ymyl_documents(ymyl_db):
    from app.ymyl_library import DOCUMENTS, get_document, list_documents

    docs = list_documents()
    assert len(docs) == len(DOCUMENTS)
    doc = get_document("YMYL-R-SEC-BITCOIN")
    assert doc is not None
    assert "YY06" in doc["criteria_ids"]
    assert doc.get("content_md")
    assert doc.get("harm_category") == "financial_loss"


def test_ymyl_insights(ymyl_db):
    from app.ymyl_library import list_insights

    insights = list_insights()
    assert len(insights) >= 8
    assert insights[0]["severity"] in ("critical", "high", "medium", "low")


def test_ymyl_library_snapshot(ymyl_db):
    from app.ymyl_library import library_snapshot_for_prompt

    snap = library_snapshot_for_prompt(5)
    assert len(snap) == 5
    assert snap[0]["id"].startswith("YMYL-")


def test_export_ymyl_markdown(ymyl_db):
    from app.ymyl_library import export_library_markdown

    md = export_library_markdown()
    assert "YMYL Document Library" in md
    assert "YMYL-R-ESMA-2024" in md
    assert "INS-Y-AML-GAP" in md


def test_harm_scenarios_and_enrich(ymyl_db):
    from app.specialist_catalog import load_ymyl_catalog
    from app.ymyl_library import HARM_SCENARIOS, documents_for_criterion, enrich_display_items

    assert len(HARM_SCENARIOS) >= 6
    docs = documents_for_criterion("YY10")
    assert any(d["id"] == "YMYL-QX-AML" for d in docs)
    items = enrich_display_items(load_ymyl_catalog(), {})
    assert all("library_docs" in i for i in items)
    yy06 = enrich_display_items(load_ymyl_catalog(), {"YY06": {"id": "YY06", "status": "fail"}})
    row = next(i for i in yy06 if i["id"] == "YY06")
    assert row["status"] == "fail"
    assert len(row["library_docs"]) >= 1
