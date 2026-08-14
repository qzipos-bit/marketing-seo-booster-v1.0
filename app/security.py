"""API auth and simple rate limits."""

from __future__ import annotations

import threading
import time
from typing import Callable

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.config_loader import monitor_api_token, scan_rate_limit_sec

# Global ops lock: one heavy job at a time (scan, auto-check, model batch).
ops_lock = threading.Lock()

# Rate limit: full scan
_scan_last_at = 0.0
_scan_rate_lock = threading.Lock()


def _scan_min_interval() -> int:
    return scan_rate_limit_sec()


def try_acquire_ops() -> bool:
    return ops_lock.acquire(blocking=False)


def release_ops() -> None:
    if ops_lock.locked():
        ops_lock.release()


def scan_rate_ok() -> bool:
    global _scan_last_at
    limit = _scan_min_interval()
    if limit <= 0:
        return True
    with _scan_rate_lock:
        now = time.monotonic()
        if now - _scan_last_at < _scan_min_interval():
            return False
        _scan_last_at = now
        return True


def _extract_bearer(request: Request) -> str | None:
    auth = request.headers.get("Authorization", "")
    if auth.lower().startswith("bearer "):
        return auth[7:].strip()
    return None


class ApiAuthMiddleware(BaseHTTPMiddleware):
    """Require Bearer token on mutating API routes when MONITOR_API_TOKEN is set."""

    _PUBLIC = frozenset({"/health", "/ready", "/docs", "/openapi.json", "/redoc"})

    async def dispatch(self, request: Request, call_next: Callable):
        token = monitor_api_token()
        path = request.url.path

        if path.startswith("/static"):
            return await call_next(request)

        if token and request.method in ("POST", "PUT", "DELETE", "PATCH"):
            if path.startswith("/api/"):
                bearer = _extract_bearer(request)
                if bearer != token:
                    return JSONResponse(
                        {"error": "Unauthorized", "detail": "Bearer token required"},
                        status_code=401,
                    )

        return await call_next(request)
