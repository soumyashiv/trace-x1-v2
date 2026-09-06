from __future__ import annotations

import logging
import time
import uuid

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.cache import RateLimiter
from app.api.routers import auth, cases, health, investigations, reports
from app.config import settings
from app.db.session import init_db

# --- structured logging -----------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format='{"timestamp":"%(asctime)s","level":"%(levelname)s","logger":"%(name)s","message":%(message)r}',
)
logger = logging.getLogger("tracex")

app = FastAPI(
    title="TRACE-X API",
    description=(
        "Real-time identification of fraud-linked cryptocurrency exchanges "
        "from victim-reported suspect wallet addresses."
    ),
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_allowed_origins),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)

_rate_limiter = RateLimiter()


@app.middleware("http")
async def request_logging_and_rate_limit(request: Request, call_next):
    request_id = str(uuid.uuid4())
    start = time.time()

    # Rate limit by client IP (per-user limiting also applied inside
    # authenticated routes via the same RateLimiter, keyed by username).
    client_ip = request.client.host if request.client else "unknown"
    if not _rate_limiter.check(client_ip):
        logger.warning(f"rate_limited ip={client_ip} path={request.url.path}")
        return JSONResponse(
            status_code=429, content={"detail": "Rate limit exceeded. Try again shortly."}
        )

    try:
        response = await call_next(request)
    except Exception:
        logger.exception(f"unhandled_error request_id={request_id} path={request.url.path}")
        return JSONResponse(
            status_code=500, content={"detail": "Internal server error", "request_id": request_id}
        )

    duration_ms = round((time.time() - start) * 1000, 2)
    # Privacy-conscious logging: log path/method/status/duration, never
    # request bodies (which could contain victim-identifying details).
    logger.info(
        f"request_id={request_id} method={request.method} path={request.url.path} "
        f"status={response.status_code} duration_ms={duration_ms}"
    )
    response.headers["X-Request-ID"] = request_id
    return response


@app.on_event("startup")
def on_startup():
    init_db()
    logger.info("TRACE-X API startup complete")


app.include_router(auth.router)
app.include_router(cases.router)
app.include_router(investigations.router)
app.include_router(reports.router)
app.include_router(health.router)


@app.get("/")
def root():
    return {"service": "TRACE-X", "status": "ok", "docs": "/docs"}
