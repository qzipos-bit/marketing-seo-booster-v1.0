"""Русские подписи для статусов и UI."""

STATUS_RU = {
    "pass": "пройдено",
    "warn": "предупреждение",
    "fail": "ошибка",
    "manual": "вручную",
    "na": "н/д",
    "ok": "ок",
    "partial": "частично",
    "pending": "ожидание",
    "allowed": "разрешён",
    "blocked": "заблокирован",
    "unknown": "неизвестно",
    "mismatch": "расхождение",
    "challenge": "CDN/challenge",
    "error": "ошибка",
    "critical": "критично",
    "warning": "предупреждение",
    "info": "инфо",
    "raw_only": "только raw",
}

VERDICT_RU = {
    "ok": "ок",
    "mismatch": "расхождение",
    "blocked": "заблокирован",
    "challenge": "CDN challenge",
    "error": "ошибка",
}

SEVERITY_RU = {
    "critical": "критично",
    "high": "высокий",
    "medium": "средний",
    "low": "низкий",
}

PRIORITY_RU = {
    "P0": "P0 срочно",
    "P1": "P1 высокий",
    "P2": "P2 средний",
    "P3": "P3 низкий",
}


def ru_status(value: str) -> str:
    return STATUS_RU.get(str(value).lower(), value)


def ru_verdict(value: str) -> str:
    return VERDICT_RU.get(str(value).lower(), value)


def ru_severity(value: str) -> str:
    return SEVERITY_RU.get(str(value).lower(), value)
