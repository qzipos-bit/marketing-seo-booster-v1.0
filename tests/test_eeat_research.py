"""Tests for E-E-A-T research parse and ingest."""

import json

import pytest


SAMPLE_REVIEW = """
## Executive Summary
- Grade: C
- Weakest pillar: T
- BestChange delisted

```json
{
  "documents": [
    {
      "doc_id": "DOC-NEW-001",
      "tier": "T3_ugc",
      "type": "entity",
      "source_id": "NEW-TEST-ENTITY",
      "title": "Quickex test entity page",
      "url": "https://example.com/quickex-entity-test-unique-88421",
      "publisher": "Example",
      "published_date": "2026-01-01",
      "eeat_pillar": "A",
      "criteria_ids": ["EE13", "EE15"],
      "relevance_score": 3,
      "summary": "Test entity document for ingest",
      "supports_brand": true,
      "verification": "search_snippet"
    }
  ],
  "collection_stats": {"total": 1}
}
```

```json
{
  "criteria": [
    {
      "id": "EE99",
      "pillar": "T",
      "status": "fail",
      "evidence": "Test fail criterion",
      "gap": "Fix test gap",
      "fix_priority": "P0",
      "supporting_docs": ["EEAT-QX-AML"]
    }
  ],
  "summary": {"pass": 0, "fail": 1}
}
```
"""


@pytest.fixture()
def research_db():
    from app.eeat_library import seed_eeat_library
    from app.storage import connect, init_db

    init_db()
    with connect() as conn:
        conn.execute("DELETE FROM eeat_insights WHERE id LIKE 'INS-AI-%'")
        conn.execute("DELETE FROM eeat_documents WHERE origin = 'ai_research'")
    seed_eeat_library(force=True)
    yield


def test_parse_research_response():
    from app.eeat_research import parse_research_response

    parsed = parse_research_response(SAMPLE_REVIEW)
    assert len(parsed["registry"]["documents"]) == 1
    assert len(parsed["criteria"]["criteria"]) == 1
    assert "Grade: C" in parsed["executive_summary"]


def test_library_snapshot_for_prompt(research_db):
    from app.eeat_research import library_snapshot_for_prompt

    snap = library_snapshot_for_prompt(limit=5)
    assert len(snap) == 5
    assert snap[0]["id"].startswith("EEAT-")


def test_ingest_research_documents(research_db):
    from app.eeat_research import ingest_research_documents, parse_research_response

    parsed = parse_research_response(SAMPLE_REVIEW)
    stats = ingest_research_documents(parsed["registry"], research_run_id=99)
    assert stats["added"] == 1
    assert stats["skipped"] == 0

    stats2 = ingest_research_documents(parsed["registry"], research_run_id=100)
    assert stats2["skipped"] == 1


def test_ingest_research_insights(research_db):
    from app.eeat_research import ingest_research_insights, parse_research_response

    parsed = parse_research_response(SAMPLE_REVIEW)
    n = ingest_research_insights(parsed["criteria"], research_run_id=42)
    assert n == 1


def test_process_research_ingest(research_db):
    from app.eeat_research import process_research_ingest

    result = process_research_ingest(SAMPLE_REVIEW, research_run_id=7)
    assert result["documents"]["added"] == 1
    assert result["insights_added"] == 1


def test_build_eeat_user_message_includes_library(monkeypatch):
    monkeypatch.setenv("CONFIG_PROFILE", "quickex")
    from app.eeat_ai_reviewer import build_eeat_user_message

    msg = build_eeat_user_message(
        {
            "url": "https://quickex.io/",
            "summary": {"score": 70},
            "results": [],
            "site_corpus": {"/": "homepage text"},
            "footer_links": ["/docs/privacy-policy"],
        }
    )
    assert "LIBRARY_SNAPSHOT" in msg
    assert "SITE_CORPUS" in msg
    assert "EEAT-G-QRG" in msg or "documents" in msg


def test_research_run_storage(research_db):
    from app.storage import finish_eeat_research_run, latest_eeat_research_run, start_eeat_research_run

    rid = start_eeat_research_run("https://quickex.io/", "Home")
    finish_eeat_research_run(
        rid,
        {
            "status": "ok",
            "model": "sonar-pro",
            "latency_ms": 1200,
            "executive_summary": "Test summary",
            "raw_review": SAMPLE_REVIEW,
            "registry": {"documents": []},
            "criteria": {"criteria": []},
            "ingest": {"documents": {"added": 1}, "insights_added": 1},
        },
    )
    latest = latest_eeat_research_run()
    assert latest is not None
    assert latest["id"] == rid
    assert latest["ingest"]["insights_added"] == 1
