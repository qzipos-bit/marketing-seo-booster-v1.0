"""Tests for E-E-A-T research prompt loader."""

from pathlib import Path

import pytest

from app.config_loader import ROOT


def test_eeat_prompt_file_exists():
    path = ROOT / "prompts" / "eeat-research-prompt.md"
    assert path.exists()
    text = path.read_text(encoding="utf-8")
    assert "СИСТЕМНЫЙ ПРОМПТ" in text
    assert "DOCUMENT REGISTRY" in text
    assert "EE01" in text or "EE17" in text


def test_load_system_prompt():
    from app.eeat_ai_reviewer import load_system_prompt

    prompt = load_system_prompt()
    assert "E-E-A-T Researcher" in prompt or "E-E-A-T" in prompt
    assert "TIER 1" in prompt or "OFFICIAL" in prompt
    assert len(prompt) > 500


def test_build_eeat_user_message(monkeypatch):
    monkeypatch.setenv("CONFIG_PROFILE", "quickex")
    from app.eeat_ai_reviewer import build_eeat_user_message

    msg = build_eeat_user_message(
        {
            "page": {"url": "https://quickex.io/"},
            "summary": {"score": 80},
            "results": [{"id": "EE17", "status": "pass"}],
        }
    )
    assert "EEAT RESEARCH REQUEST" in msg
    assert "quickex.io" in msg
    assert "EE17" in msg
