"""Kie + SEO monitor — shared utilities."""

from __future__ import annotations

import os
from pathlib import Path

import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
DB_PATH = DATA_DIR / "monitor.db"

load_dotenv(ROOT / ".env")


def load_config() -> dict:
    profile = os.getenv("CONFIG_PROFILE", "").strip()
    if profile:
        profile_path = ROOT / f"config.{profile}.yaml"
        if profile_path.exists():
            with open(profile_path, encoding="utf-8") as f:
                return yaml.safe_load(f)
    with open(ROOT / "config.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def config_profile() -> str:
    return os.getenv("CONFIG_PROFILE", "").strip() or "default"


def kie_api_key() -> str | None:
    key = os.getenv("KIE_API_KEY", "").strip()
    return key or None


def perplexity_api_key() -> str | None:
    key = os.getenv("PERPLEXITY_API_KEY", "").strip()
    return key or None


def monitor_host() -> str:
    return os.getenv("MONITOR_HOST", "127.0.0.1")


def monitor_port() -> int:
    return int(os.getenv("MONITOR_PORT", "8787"))


def auto_check_interval_min() -> int:
    return int(os.getenv("AUTO_CHECK_INTERVAL_MIN", "30"))


def scan_interval_min() -> int:
    """Full audit scan interval (0 = disabled). Default 60 min. Ignored when cron schedule is set."""
    if scan_schedule():
        return 0
    return int(os.getenv("SCAN_INTERVAL_MIN", "60"))


def _parse_cron_time(value: str) -> tuple[int, int]:
    raw = value.strip()
    if not raw:
        raise ValueError("empty time")
    if ":" in raw:
        h, m = raw.split(":", 1)
        return int(h), int(m)
    return int(raw), 0


def scan_schedule() -> list[tuple[int, int]] | None:
    """Cron times (hour, minute) in scan timezone. None = use SCAN_INTERVAL_MIN instead."""
    env = os.getenv("SCAN_CRON_TIMES", "").strip()
    if env.lower() in ("off", "0", "false", "disable", "disabled"):
        return None
    if env:
        return [_parse_cron_time(part) for part in env.split(",") if part.strip()]

    cfg = load_config()
    cron = (cfg.get("scan") or {}).get("cron") or {}
    times = cron.get("times") or []
    if not times:
        return None
    return [_parse_cron_time(str(t)) for t in times]


def scan_cron_timezone() -> str:
    env = os.getenv("SCAN_CRON_TIMEZONE", "").strip()
    if env:
        return env
    cfg = load_config()
    return (cfg.get("scan") or {}).get("cron", {}).get("timezone") or "Europe/Moscow"


def scan_schedule_label() -> str:
    schedule = scan_schedule()
    if schedule:
        tz = scan_cron_timezone()
        tz_label = "МСК" if "Moscow" in tz else tz
        times = ", ".join(f"{h:02d}:{m:02d}" for h, m in schedule)
        return f"{times} {tz_label}"
    iv = int(os.getenv("SCAN_INTERVAL_MIN", "60"))
    if iv > 0:
        return f"каждые {iv} мин"
    return "выкл"


def scan_stale_threshold_hours() -> float:
    """Hours after last scan before health is marked stale."""
    schedule = scan_schedule()
    if schedule:
        hours_sorted = sorted(h for h, _ in schedule)
        max_gap = 0.0
        for i, h in enumerate(hours_sorted):
            next_h = hours_sorted[(i + 1) % len(hours_sorted)]
            gap = float(next_h - h)
            if gap <= 0:
                gap += 24.0
            max_gap = max(max_gap, gap)
        return max_gap + 2.0
    iv = int(os.getenv("SCAN_INTERVAL_MIN", "60"))
    return (iv / 60.0) * 2 if iv > 0 else 0.0


def scan_automation_enabled() -> bool:
    return bool(scan_schedule()) or int(os.getenv("SCAN_INTERVAL_MIN", "60")) > 0


def app_env() -> str:
    return os.getenv("ENV", "development").strip().lower()


def is_production() -> bool:
    return app_env() == "production"


def monitor_api_token() -> str | None:
    token = os.getenv("MONITOR_API_TOKEN", "").strip()
    return token or None


def log_level() -> str:
    return os.getenv("LOG_LEVEL", "INFO").strip().upper()


def log_format() -> str:
    return os.getenv("LOG_FORMAT", "text").strip().lower()


def scan_skip_ai_review() -> bool:
    return os.getenv("SCAN_SKIP_AI_REVIEW", "true").strip().lower() in (
        "1",
        "true",
        "yes",
    )


def scan_rate_limit_sec() -> int:
    return int(os.getenv("SCAN_RATE_LIMIT_SEC", "300"))


def alert_enabled() -> bool:
    return os.getenv("ALERT_ENABLED", "true").strip().lower() in ("1", "true", "yes")


def telegram_bot_token() -> str | None:
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    return token or None


def telegram_chat_id() -> str | None:
    chat = os.getenv("TELEGRAM_CHAT_ID", "").strip()
    return chat or None


def alert_webhook_url() -> str | None:
    url = os.getenv("ALERT_WEBHOOK_URL", "").strip()
    return url or None


def alert_score_drop_pct() -> float:
    try:
        return float(os.getenv("ALERT_SCORE_DROP_PCT", "10"))
    except ValueError:
        return 10.0


def ahrefs_api_key() -> str | None:
    key = os.getenv("AHREFS_API_KEY", "").strip()
    return key or None


def ahrefs_enabled() -> bool:
    return os.getenv("AHREFS_ENABLED", "true").strip().lower() in ("1", "true", "yes")


def ahrefs_cron_hour() -> int:
    try:
        return int(os.getenv("AHREFS_CRON_HOUR", "9"))
    except ValueError:
        return 9


def competitor_enabled() -> bool:
    return os.getenv("COMPETITOR_ENABLED", "true").strip().lower() in ("1", "true", "yes")


def competitor_cron_hour() -> int:
    try:
        return int(os.getenv("COMPETITOR_CRON_HOUR", "7"))
    except ValueError:
        return 7
