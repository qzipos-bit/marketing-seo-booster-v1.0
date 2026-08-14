"""Tests for scan schedule configuration."""

import os

import pytest


def test_scan_schedule_from_env(monkeypatch):
    monkeypatch.setenv("CONFIG_PROFILE", "")
    monkeypatch.setenv("SCAN_CRON_TIMES", "7:00,12:00,21:00")
    from app.config_loader import scan_schedule, scan_schedule_label, scan_stale_threshold_hours

    assert scan_schedule() == [(7, 0), (12, 0), (21, 0)]
    assert "07:00" in scan_schedule_label()
    assert scan_stale_threshold_hours() == 12.0  # max gap 10h (21→7) + 2h buffer


def test_scan_schedule_off(monkeypatch):
    monkeypatch.setenv("SCAN_CRON_TIMES", "off")
    monkeypatch.setenv("SCAN_INTERVAL_MIN", "60")
    from app.config_loader import scan_schedule, scan_interval_min

    assert scan_schedule() is None
    assert scan_interval_min() == 60


def test_quickex_config_has_moscow_schedule(monkeypatch):
    monkeypatch.delenv("SCAN_CRON_TIMES", raising=False)
    monkeypatch.setenv("CONFIG_PROFILE", "quickex")
    monkeypatch.setenv("SCAN_INTERVAL_MIN", "0")
    from app.config_loader import scan_cron_timezone, scan_schedule, scan_schedule_label

    schedule = scan_schedule()
    assert schedule == [(7, 0), (12, 0), (21, 0)]
    assert scan_cron_timezone() == "Europe/Moscow"
    assert "МСК" in scan_schedule_label()
