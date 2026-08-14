"""Alert engine — Telegram + webhook notifications on scan events."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from app.config_loader import (
    alert_enabled,
    alert_score_drop_pct,
    alert_webhook_url,
    telegram_bot_token,
    telegram_chat_id,
)
from app.storage import log_alert, scan_run_history

logger = logging.getLogger(__name__)


def _fmt_scan_message(alert: dict[str, Any]) -> str:
    lines = [
        f"*{alert['title']}*",
        alert.get("message") or "",
    ]
    payload = alert.get("payload") or {}
    if payload.get("checklist_score") is not None:
        lines.append(f"Score: {payload['checklist_score']}% ({payload.get('checklist_grade', '—')})")
    if payload.get("delta") is not None:
        sign = "+" if payload["delta"] >= 0 else ""
        lines.append(f"Δ {sign}{payload['delta']}%")
    if payload.get("scan_id"):
        lines.append(f"Scan #{payload['scan_id']}")
    return "\n".join(line for line in lines if line)


async def _send_telegram(text: str) -> bool:
    token = telegram_bot_token()
    chat_id = telegram_chat_id()
    if not token or not chat_id:
        return False
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.post(
                url,
                json={
                    "chat_id": chat_id,
                    "text": text,
                    "parse_mode": "Markdown",
                    "disable_web_page_preview": True,
                },
            )
            if r.status_code != 200:
                logger.warning("telegram send failed: %s %s", r.status_code, r.text[:200])
                return False
            return True
    except Exception as exc:
        logger.error("telegram error: %s", exc)
        return False


async def _send_webhook(payload: dict[str, Any]) -> bool:
    url = alert_webhook_url()
    if not url:
        return False
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.post(url, json=payload)
            if r.status_code >= 400:
                logger.warning("webhook failed: %s %s", r.status_code, r.text[:200])
                return False
            return True
    except Exception as exc:
        logger.error("webhook error: %s", exc)
        return False


async def deliver_alert(alert: dict[str, Any]) -> dict[str, bool]:
    text = _fmt_scan_message(alert)
    tg = await _send_telegram(text)
    wh = await _send_webhook(
        {
            "event": alert.get("alert_type"),
            "severity": alert.get("severity"),
            "title": alert.get("title"),
            "message": alert.get("message"),
            "payload": alert.get("payload"),
            "scan_id": alert.get("scan_id"),
        }
    )
    return {"telegram": tg, "webhook": wh}


def evaluate_scan_alerts(
    scan_id: int,
    metrics: dict[str, Any],
    status: str,
) -> list[dict[str, Any]]:
    """Build alert objects from scan result vs previous scan."""
    if not alert_enabled():
        return []

    alerts: list[dict[str, Any]] = []
    prev_scans = scan_run_history(2)
    prev = prev_scans[1] if len(prev_scans) > 1 and prev_scans[0].get("id") == scan_id else (
        prev_scans[0] if len(prev_scans) > 1 else None
    )
    prev_metrics = (prev or {}).get("metrics") or {}

    base_payload = {
        "scan_id": scan_id,
        "status": status,
        "checklist_score": metrics.get("checklist_score"),
        "checklist_grade": metrics.get("checklist_grade"),
        "seo_avg_score": metrics.get("seo_avg_score"),
        "geo_avg_score": metrics.get("geo_avg_score"),
        "fail": metrics.get("fail"),
        "bot_mismatch": metrics.get("bot_mismatch"),
    }

    alerts.append(
        {
            "alert_type": "scan_complete",
            "severity": "info" if status == "ok" else ("warn" if status == "partial" else "critical"),
            "title": f"Скан завершён — {status.upper()}",
            "message": (
                f"Checklist {metrics.get('checklist_score', '—')}% · "
                f"fail {metrics.get('fail', 0)} · "
                f"{round((metrics.get('duration_ms') or 0) / 1000)}с"
            ),
            "payload": dict(base_payload),
            "scan_id": scan_id,
        }
    )

    current_score = metrics.get("checklist_score")
    prev_score = prev_metrics.get("checklist_score")
    if current_score is not None and prev_score is not None:
        delta = round(current_score - prev_score, 1)
        base_payload["delta"] = delta
        threshold = alert_score_drop_pct()
        if delta <= -threshold:
            alerts.append(
                {
                    "alert_type": "score_drop",
                    "severity": "high",
                    "title": f"Score упал на {abs(delta)}%",
                    "message": f"Было {prev_score}%, стало {current_score}% (порог {threshold}%)",
                    "payload": dict(base_payload),
                    "scan_id": scan_id,
                }
            )

    if metrics.get("bot_mismatch", 0) > 0:
        alerts.append(
            {
                "alert_type": "bot_mismatch",
                "severity": "critical" if metrics.get("bot_critical") else "high",
                "title": f"Bot mismatch: {metrics['bot_mismatch']}",
                "message": "robots.txt и HTTP-ответ расходятся — проверьте Bot Reality",
                "payload": dict(base_payload),
                "scan_id": scan_id,
            }
        )

    if metrics.get("fail", 0) >= 5:
        alerts.append(
            {
                "alert_type": "critical_fail",
                "severity": "high",
                "title": f"Много fail: {metrics['fail']}",
                "message": "Критичные проблемы в чеклисте — откройте Command Center",
                "payload": dict(base_payload),
                "scan_id": scan_id,
            }
        )

    geo = metrics.get("geo_avg_score")
    if geo is not None and geo < 35:
        alerts.append(
            {
                "alert_type": "geo_low",
                "severity": "medium",
                "title": f"GEO score низкий: {geo}",
                "message": "Улучшите FAQ, schema и citability на Tier-1 парах",
                "payload": dict(base_payload),
                "scan_id": scan_id,
            }
        )

    return alerts


async def process_scan_alerts(scan_id: int, metrics: dict[str, Any], status: str) -> list[dict[str, Any]]:
    """Evaluate, deliver and persist alerts for a completed scan."""
    alerts = evaluate_scan_alerts(scan_id, metrics, status)
    delivered: list[dict[str, Any]] = []

    for alert in alerts:
        # Skip noisy scan_complete on partial/ok if only info and no other channels need it
        if alert["alert_type"] == "scan_complete" and alert["severity"] == "info":
            if not telegram_bot_token() and not alert_webhook_url():
                continue

        channels = await deliver_alert(alert)
        aid = log_alert(
            alert_type=alert["alert_type"],
            severity=alert["severity"],
            title=alert["title"],
            message=alert.get("message"),
            payload=alert.get("payload"),
            scan_id=scan_id,
            delivered_telegram=channels["telegram"],
            delivered_webhook=channels["webhook"],
        )
        delivered.append({**alert, "id": aid, "delivered": channels})

    if delivered:
        logger.info("alerts sent scan_id=%s count=%s", scan_id, len(delivered))
    return delivered


async def send_test_alert() -> dict[str, Any]:
    """Manual test alert for Telegram/webhook setup."""
    alert = {
        "alert_type": "test",
        "severity": "info",
        "title": "Marketing SEO Booster — тест алерта",
        "message": "Если вы видите это — уведомления настроены верно.",
        "payload": {"test": True},
        "scan_id": None,
    }
    channels = await deliver_alert(alert)
    aid = log_alert(
        alert_type="test",
        severity="info",
        title=alert["title"],
        message=alert["message"],
        payload=alert["payload"],
        scan_id=None,
        delivered_telegram=channels["telegram"],
        delivered_webhook=channels["webhook"],
    )
    return {"id": aid, "delivered": channels, "configured": alert_delivery_status()}


def alert_delivery_status() -> dict[str, bool]:
    return {
        "enabled": alert_enabled(),
        "telegram": bool(telegram_bot_token() and telegram_chat_id()),
        "webhook": bool(alert_webhook_url()),
    }
