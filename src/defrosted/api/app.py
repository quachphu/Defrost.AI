"""
FastAPI application entrypoint.

Run with: uvicorn defrosted.api.app:app

Startup wires the process-wide engine and Redis client; shutdown disposes them.
Middleware order matters: request-id outermost (so every log line is tagged),
then security headers, then rate limiting closest to the routes.
"""
from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ..config import get_settings
from ..infrastructure.cache import close_redis, init_redis
from ..infrastructure.database import dispose_engine, init_engine
from .middleware import (
    RateLimitMiddleware,
    RequestIDMiddleware,
    SecurityHeadersMiddleware,
)
from .routers import approvals, leases, listings, searches

# Tighten this allowlist per environment; never use "*" with credentials.
ALLOWED_ORIGINS = ["https://app.defrosted.ai", "http://localhost:3000"]


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    init_engine(settings)
    await init_redis(settings)
    try:
        yield
    finally:
        await close_redis()
        await dispose_engine()


app = FastAPI(title="Defrosted.ai", version="0.1.0", lifespan=lifespan)

app.add_middleware(RateLimitMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestIDMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
)

app.include_router(searches.router)
app.include_router(listings.router)
app.include_router(approvals.router)
app.include_router(leases.router)


@app.get("/health", tags=["meta"], summary="Liveness probe")
async def health() -> dict[str, str]:
    return {"status": "ok"}
