"""Tests for YMYL research prompt loader."""

import pytest

from app.config_loader import ROOT


def test_ymyl_prompt_file_exists():
    path = ROOT / "prompts" / "ymyl-research-prompt.md"
    assert path.exists()
    text = path.read_text(encoding="utf-8")
    assert "СИСТЕМНЫЙ ПРОМПТ" in text
    assert "HARM SCENARIOS" in text
    assert "YY01" in text
    assert "YY28" in text


def test_load_ymyl_system_prompt():
    from app.ymyl_ai_reviewer import load_system_prompt

    prompt = load_system_prompt()
    assert "YMYL" in prompt
    assert "harm" in prompt.lower() or "HARM" in prompt
    assert "YY05" in prompt or "YY17" in prompt
    assert len(prompt) > 800


def test_build_ymyl_user_message(monkeypatch):
    monkeypatch.setenv("CONFIG_PROFILE", "quickex")
    from app.ymyl_ai_reviewer import build_ymyl_user_message

    msg = build_ymyl_user_message(
        {
            "url": "https://quickex.io/exchange-btc-xmr",
            "pair": "BTC-XMR",
            "summary": {"score": 75},
            "results": [{"id": "YY06", "status": "fail"}],
            "site_corpus": {"/docs/aml-policy": "AML text"},
        }
    )
    assert "YMYL RESEARCH REQUEST" in msg
    assert "privacy_pair: true" in msg
    assert "YY06" in msg
    assert "YMYL_LIBRARY_SNAPSHOT" in msg
    assert "YMYL-R-SEC" in msg or "documents" in msg


def test_privacy_pair_detection():
    from app.ymyl_ai_reviewer import _is_privacy_pair

    assert _is_privacy_pair("https://quickex.io/exchange-btc-xmr", "BTC-XMR") is True
    assert _is_privacy_pair("https://quickex.io/exchange-btc-usdt", "BTC-USDT") is False
