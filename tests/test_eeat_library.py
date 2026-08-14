"""Tests for E-E-A-T document library seed and API."""

import pytest


@pytest.fixture()
def eeat_db():
    from app.eeat_library import seed_eeat_library
    from app.storage import connect, init_db

    init_db()
    with connect() as conn:
        conn.execute("DELETE FROM eeat_insights WHERE id LIKE 'INS-AI-%'")
        conn.execute("DELETE FROM eeat_documents WHERE origin = 'ai_research'")
    seed_eeat_library(force=True)
    yield


def test_seed_eeat_library(eeat_db):
    from app.eeat_library import DOCUMENTS, INSIGHTS, seed_eeat_library

    second = seed_eeat_library()
    assert second["seeded"] is False
    assert second["documents"] >= len(DOCUMENTS)
    assert second["insights"] == len(INSIGHTS)

    forced = seed_eeat_library(force=True)
    assert forced["seeded"] is True
    assert forced["documents"] == len(DOCUMENTS)


def test_list_and_get_document(eeat_db):
    from app.eeat_library import get_document, list_documents

    docs = list_documents()
    assert len(docs) >= 35
    assert all("criteria_ids" in d for d in docs)

    doc = get_document("EEAT-G-QRG")
    assert doc is not None
    assert doc["publisher"] == "Google"
    assert "EE17" in doc["criteria_ids"]
    assert doc.get("content_md")


def test_list_insights(eeat_db):
    from app.eeat_library import list_insights

    insights = list_insights()
    assert len(insights) >= 5
    assert insights[0]["severity"] in ("critical", "high", "medium", "low")
    assert insights[0].get("document_title")


def test_export_markdown(eeat_db):
    from app.eeat_library import export_library_markdown

    md = export_library_markdown()
    assert "E-E-A-T Document Library" in md
    assert "EEAT-G-QRG" in md
    assert "INS-TRUST-001" in md


def test_library_stats(eeat_db):
    from app.eeat_library import library_stats

    stats = library_stats()
    assert stats["documents"] >= 35
    assert stats["insights"] >= 5
    assert "T1_official" in stats["by_tier"]
