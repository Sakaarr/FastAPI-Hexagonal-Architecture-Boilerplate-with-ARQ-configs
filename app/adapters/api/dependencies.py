"""
╔══════════════════════════════════════════════════════════════════╗
║  CENTRAL DEPENDENCY INJECTION HUB                                ║
║                                                                  ║
║  This file contains ALL the dependency providers for the app.    ║
║  Each function below is a "provider" — FastAPI calls it via      ║
║  Depends() and injects the return value into your endpoint.      ║
║                                                                  ║
║  PATTERNS DEMONSTRATED:                                          ║
║  ┌─────┬───────────────────────────────────────────────────────┐  ║
║  │  1  │  Config injection         (get_settings)             │  ║
║  │  2  │  Repository providers     (get_user_repo, etc.)      │  ║
║  │  3  │  Request logging          (log_request)              │  ║
║  │  4  │  API key auth             (verify_api_key)           │  ║
║  │  5  │  Dependency chains        (repo → db → settings)     │  ║
║  │  6  │  Overrides for testing    (shown in test file)       │  ║
║  └─────┴───────────────────────────────────────────────────────┘  ║
╚══════════════════════════════════════════════════════════════════╝
"""

import time
import logging
from fastapi import Depends, Request, HTTPException, Header
from typing import Annotated

from app.infrastructure.config import Settings, get_settings
from app.infrastructure.database.mongodb import get_database
from app.adapters.repositories.mongo_user_repository import MongoUserRepository
from app.adapters.repositories.mongo_product_repository import MongoProductRepository
from app.domain.repositories.user_repository import UserRepository
from app.domain.repositories.product_repository import ProductRepository
from app.domain.task_queue import TaskQueue
from app.adapters.task_queue.arq_task_queue import ArqTaskQueue

logger = logging.getLogger("app")


# ═══════════════════════════════════════════════════════════════
#  PATTERN 2: Repository Providers
# ═══════════════════════════════════════════════════════════════
#
#  Instead of doing `repo = MongoUserRepository()` at the top of
#  your router (HARDCODED), we create provider functions.
#
#  WHY THIS MATTERS:
#  - The router never knows WHICH repository it's using
#  - You can swap MongoDB for PostgreSQL by changing ONE function
#  - In tests, you override this to return FakeUserRepository
# ═══════════════════════════════════════════════════════════════

def get_user_repo() -> UserRepository:
    """
    Provides a UserRepository implementation.

    CURRENT: Returns MongoUserRepository
    TO SWAP: Just change the return to PostgresUserRepository()
             or any other implementation of UserRepository.

    In tests, this gets overridden to return FakeUserRepository.
    """
    return MongoUserRepository()


def get_product_repo() -> ProductRepository:
    """
    Provides a ProductRepository implementation.
    Same pattern as get_user_repo — easy to swap implementations.
    """
    return MongoProductRepository()


def get_task_queue(request: Request) -> TaskQueue | None:
    """
    Provides a TaskQueue implementation (arq + Redis).

    LEARNING POINT — Accessing app.state:
    ───────────────────────────────────────
    The arq Redis pool is created in main.py's lifespan and
    stored on app.state.arq_pool. This dependency reads it
    from the Request object (request.app.state).

    Returns None if Redis is not connected, so the app still
    works — just without background emails.

    In tests, this gets overridden to return FakeTaskQueue.
    """
    pool = getattr(request.app.state, "arq_pool", None)
    if pool:
        return ArqTaskQueue(pool)
    return None


# ═══════════════════════════════════════════════════════════════
#  PATTERN 3: Request Logging Dependency (Cross-Cutting Concern)
# ═══════════════════════════════════════════════════════════════
#
#  This dependency doesn't return a "service" — instead it
#  performs a SIDE EFFECT (logging) before the endpoint runs.
#
#  WHY?
#  - Keeps logging logic out of every endpoint
#  - Can be applied per-router or globally
#  - Easy to add timing, request IDs, etc.
# ═══════════════════════════════════════════════════════════════

async def log_request(request: Request):
    """
    Logs every incoming request with method, path, and client IP.

    LEARNING POINT:
    ─────────────────
    FastAPI auto-injects the `Request` object — you don't need
    to declare it in your endpoint. This dependency receives it
    automatically because FastAPI recognizes the type hint.

    This is a "fire-and-forget" dependency — it doesn't return
    anything useful, it just performs a side effect.
    """
    start_time = time.time()
    logger.info(
        f"📥 {request.method} {request.url.path} "
        f"from {request.client.host if request.client else 'unknown'}"
    )

    # We yield to let the dependency be used as a context manager
    # but since we don't need cleanup, we just return
    return {"start_time": start_time, "path": request.url.path}


# ═══════════════════════════════════════════════════════════════
#  PATTERN 4: API Key Authentication (Security Guard)
# ═══════════════════════════════════════════════════════════════
#
#  This dependency checks the request for a valid API key.
#  If missing or invalid, it raises HTTPException (401/403).
#
#  DEPENDENCY CHAIN (Pattern 5):
#     verify_api_key → depends on → get_settings
#  The settings are injected INTO this dependency automatically!
# ═══════════════════════════════════════════════════════════════

async def verify_api_key(
    x_api_key: str = Header(default=None, description="API key for authentication"),
    settings: Settings = Depends(get_settings)
):
    """
    Validates the API key from the X-API-Key header.

    LEARNING POINT — DEPENDENCY CHAIN:
    ────────────────────────────────────
    Notice that this dependency ITSELF depends on `get_settings`.
    FastAPI resolves the chain automatically:

        endpoint
           ↓ Depends(verify_api_key)
        verify_api_key
           ↓ Depends(get_settings)
        get_settings → returns Settings object

    So when your endpoint uses Depends(verify_api_key), FastAPI:
    1. First calls get_settings() to get the Settings
    2. Then calls verify_api_key(settings=...) with that result
    3. Then calls your endpoint if auth passes

    This is Pattern 5 (Dependency Chains) in action!
    """
    if x_api_key is None:
        raise HTTPException(
            status_code=401,
            detail="Missing API key. Include 'X-API-Key' header."
        )

    if x_api_key != settings.api_key:
        raise HTTPException(
            status_code=403,
            detail="Invalid API key."
        )

    return {"authenticated": True, "api_key": x_api_key[:8] + "..."}


# ═══════════════════════════════════════════════════════════════
#  PATTERN 5: Dependency Chains (Composed Dependencies)
# ═══════════════════════════════════════════════════════════════
#
#  A dependency can depend on OTHER dependencies. FastAPI
#  resolves the entire chain automatically and caches results
#  within a single request.
#
#  Example chain:  get_current_request_info
#                     ↓ depends on
#                  log_request  +  get_settings
#                     ↓                ↓
#                  Request          @lru_cache
# ═══════════════════════════════════════════════════════════════

async def get_current_request_info(
    request: Request,
    settings: Settings = Depends(get_settings),
    log_data: dict = Depends(log_request),
):
    """
    A composed dependency that combines multiple other dependencies.

    LEARNING POINT:
    ─────────────────
    This single dependency triggers a chain:
    1. get_settings() is called  → returns Settings
    2. log_request() is called   → logs the request and returns timing data
    3. This function combines everything into a rich context object

    Your endpoint receives all this context with a single Depends() call.

    CACHING WITHIN A REQUEST:
    FastAPI caches dependency results within a single request.
    If two dependencies both Depends(get_settings), it's only
    called ONCE — the same Settings instance is reused.
    """
    elapsed = time.time() - log_data["start_time"]
    return {
        "app_name": settings.app_name,
        "debug": settings.debug,
        "request_path": log_data["path"],
        "method": request.method,
        "elapsed_ms": round(elapsed * 1000, 2),
    }


# ═══════════════════════════════════════════════════════════════
#  TYPE ALIASES (Annotated dependencies for cleaner signatures)
# ═══════════════════════════════════════════════════════════════
#
#  Instead of writing Depends(...) in every endpoint, you can
#  create type aliases. This keeps endpoint signatures clean.
# ═══════════════════════════════════════════════════════════════

# Use these in endpoint signatures for cleaner code:
#   async def create_user(repo: UserRepoDep, name: str, email: str):
UserRepoDep = Annotated[UserRepository, Depends(get_user_repo)]
ProductRepoDep = Annotated[ProductRepository, Depends(get_product_repo)]
TaskQueueDep = Annotated[TaskQueue | None, Depends(get_task_queue)]
SettingsDep = Annotated[Settings, Depends(get_settings)]
RequestInfoDep = Annotated[dict, Depends(get_current_request_info)]
