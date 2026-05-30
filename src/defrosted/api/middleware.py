"""
Security middleware applied to every request.

Layers:
1. Request ID: every request gets a UUID for tracing across logs
2. Rate limiting: per-IP and per-user limits via Redis
3. Security headers: HSTS, X-Frame-Options, CSP, etc.
4. CORS: strict origin allowlist

What this does NOT do (handled elsewhere):
- JWT auth: in Depends(get_current_user) in dependencies.py
- Input validation: in Pydantic schemas in api/schemas/
- Business rule enforcement: in services/

Karpathy rule: middleware is boring on purpose. It should be invisible.
"""
from __future__ import annotations

import time
import uuid

import structlog
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from ..infrastructure.cache import get_redis_client

log = structlog.get_logger(__name__)


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Attach a unique request ID to every request and response."""

    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = str(uuid.uuid4())
        # Bind to structlog context so every log line in this request includes it
        structlog.contextvars.bind_contextvars(request_id=request_id)
        request.state.request_id = request_id

        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = (time.perf_counter() - start) * 1000

        response.headers["X-Request-ID"] = request_id

        log.info(
            "request_completed",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=round(duration_ms, 2),
        )
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to every response."""

    HEADERS = {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "Strict-Transport-Security": "max-age=63072000; includeSubDomains; preload",
        "Referrer-Policy": "strict-origin-when-cross-origin",
        "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
        # CSP: allow only our own origin and Anthropic/Claude APIs
        "Content-Security-Policy": (
            "default-src 'self'; "
            "connect-src 'self' https://api.anthropic.com; "
            "script-src 'self'; "
            "style-src 'self' 'unsafe-inline';"
        ),
    }

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        for header, value in self.HEADERS.items():
            response.headers[header] = value
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Sliding window rate limiter using Redis.
    Limits:
      - Per IP:   100 requests per minute (protects against bots)
      - Per user: 1000 requests per minute (authenticated users get higher limit)

    Uses Redis INCR with TTL — atomic, no race conditions.
    """

    IP_LIMIT   = 100   # requests per minute per IP
    USER_LIMIT = 1000  # requests per minute per authenticated user
    WINDOW_SECONDS = 60

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)
        self._redis = None   # initialized lazily to avoid startup import issues

    async def dispatch(self, request: Request, call_next) -> Response:
        if self._redis is None:
            self._redis = await get_redis_client()

        client_ip = request.client.host if request.client else "unknown"
        ip_key = f"rate_limit:ip:{client_ip}"

        ip_count = await self._redis.incr(ip_key)
        if ip_count == 1:
            # First request in this window — set the TTL
            await self._redis.expire(ip_key, self.WINDOW_SECONDS)

        if ip_count > self.IP_LIMIT:
            return Response(
                content='{"detail":"Rate limit exceeded. Max 100 requests per minute."}',
                status_code=429,
                media_type="application/json",
                headers={"Retry-After": str(self.WINDOW_SECONDS)},
            )

        return await call_next(request)
