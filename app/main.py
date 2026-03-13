"""
╔══════════════════════════════════════════════════════════════╗
║  APPLICATION ENTRY POINT                                     ║
║                                                              ║
║  Demonstrates:                                               ║
║  - Global exception handler for ValueError (business logic)  ║
║  - Lifespan events (startup/shutdown)                        ║
║  - arq Redis pool creation on startup                        ║
║  - Config injection at the app level                         ║
╚══════════════════════════════════════════════════════════════╝
"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from arq import create_pool
from arq.connections import RedisSettings

from app.adapters.api.user_router import router as user_router
from app.adapters.api.product_router import router as product_router
from app.adapters.api.auth_router import router as auth_router
from app.infrastructure.config import get_settings


# ── Configure logging ──
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s │ %(levelname)-8s │ %(name)s │ %(message)s",
)
logger = logging.getLogger("app")


# ── Lifespan: runs on startup and shutdown ──
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    LEARNING POINT:
    ─────────────────
    Lifespan is where we create the arq Redis pool.
    We store it on app.state so dependencies can access it.

    app.state is FastAPI's built-in way to share objects
    across the application without globals.
    """
    settings = get_settings()
    logger.info(f"🚀 Starting {settings.app_name}")
    logger.info(f"📦 Database: {settings.mongo_db_name} @ {settings.mongo_url}")
    logger.info(f"🔧 Debug mode: {settings.debug}")

    # ── Create arq Redis pool for background tasks ──
    try:
        redis_pool = await create_pool(
            RedisSettings(
                host=settings.redis_host,
                port=settings.redis_port,
                password=settings.redis_password,
            )
        )
        app.state.arq_pool = redis_pool
        logger.info(
            f"📡 Redis connected: {settings.redis_host}:{settings.redis_port}"
        )
    except Exception as e:
        logger.warning(f"⚠️ Redis connection failed: {e}")
        logger.warning("   Background tasks will be disabled.")
        app.state.arq_pool = None

    yield

    # ── Cleanup: close Redis pool ──
    if hasattr(app.state, "arq_pool") and app.state.arq_pool:
        await app.state.arq_pool.close()
        logger.info("📡 Redis pool closed")

    logger.info("👋 Shutting down...")


# ── Create app with settings ──
settings = get_settings()
app = FastAPI(
    title=settings.app_name,
    debug=settings.debug,
    lifespan=lifespan,
)


# ── Global exception handler ──
# Catches ValueError from use cases and returns proper HTTP responses
@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    """
    LEARNING POINT:
    ─────────────────
    Our use cases raise ValueError for business rule violations
    (e.g. "duplicate email", "user not found"). This handler
    catches ALL of them and converts to a clean 400 response.

    Without this, FastAPI would return a generic 500 error.
    """
    return JSONResponse(
        status_code=400,
        content={"detail": str(exc)},
    )


# ── Register routers ──
app.include_router(user_router)
app.include_router(product_router)
app.include_router(auth_router)


# ── Health check endpoint ──
@app.get("/health", tags=["Health"])
async def health_check():
    redis_status = "connected" if (
        hasattr(app.state, "arq_pool") and app.state.arq_pool
    ) else "disconnected"
    return {
        "status": "healthy",
        "app": settings.app_name,
        "redis": redis_status,
    }