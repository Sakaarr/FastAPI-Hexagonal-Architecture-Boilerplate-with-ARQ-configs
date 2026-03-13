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
║  │  7  │  JWT auth + current user  (get_current_user)         │  ║
║  │  8  │  Password hasher          (get_password_hasher)      │  ║
║  └─────┴───────────────────────────────────────────────────────┘  ║
╚══════════════════════════════════════════════════════════════════╝
"""

import time
import logging
from fastapi import Depends, Request, HTTPException, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Annotated

from app.infrastructure.config import Settings, get_settings
from app.infrastructure.database.mongodb import get_database
from app.adapters.repositories.mongo_user_repository import MongoUserRepository
from app.adapters.repositories.mongo_product_repository import MongoProductRepository
from app.domain.repositories.user_repository import UserRepository
from app.domain.repositories.product_repository import ProductRepository
from app.domain.task_queue import TaskQueue
from app.domain.password_hasher import PasswordHasher
from app.domain.entities.user import User
from app.adapters.task_queue.arq_task_queue import ArqTaskQueue
from app.infrastructure.security.password_hasher import BcryptPasswordHasher
from app.infrastructure.security.jwt_handler import decode_access_token

logger = logging.getLogger("app")


# ── HTTP Bearer scheme for JWT ──
# This tells FastAPI/OpenAPI that we expect a Bearer token
# in the Authorization header. Enables the 🔒 button in /docs.
bearer_scheme = HTTPBearer(auto_error=False)


# ═══════════════════════════════════════════════════════════════
#  PATTERN 2: Repository Providers
# ═══════════════════════════════════════════════════════════════

def get_user_repo() -> UserRepository:
    """
    Provides a UserRepository implementation.
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
    Returns None if Redis is not connected.
    """
    pool = getattr(request.app.state, "arq_pool", None)
    if pool:
        return ArqTaskQueue(pool)
    return None


# ═══════════════════════════════════════════════════════════════
#  PATTERN 8: Password Hasher Provider
# ═══════════════════════════════════════════════════════════════

def get_password_hasher() -> PasswordHasher:
    """
    Provides a PasswordHasher implementation.

    CURRENT: Returns BcryptPasswordHasher (production-grade)
    IN TESTS: Override to return FakePasswordHasher (fast, no bcrypt)

    LEARNING POINT:
    ─────────────────
    Same pattern as repositories. The use case depends on
    the abstract PasswordHasher port. In production it gets
    bcrypt, in tests it gets a fast fake.
    """
    return BcryptPasswordHasher()


# ═══════════════════════════════════════════════════════════════
#  PATTERN 3: Request Logging (Cross-Cutting Concern)
# ═══════════════════════════════════════════════════════════════

async def log_request(request: Request):
    """Logs every incoming request with method, path, and client IP."""
    start_time = time.time()
    logger.info(
        f"📥 {request.method} {request.url.path} "
        f"from {request.client.host if request.client else 'unknown'}"
    )
    return {"start_time": start_time, "path": request.url.path}


# ═══════════════════════════════════════════════════════════════
#  PATTERN 4: API Key Authentication (Security Guard)
# ═══════════════════════════════════════════════════════════════

async def verify_api_key(
    x_api_key: str = Header(default=None, description="API key for authentication"),
    settings: Settings = Depends(get_settings)
):
    """
    Validates the API key from the X-API-Key header.
    Dependency chain: verify_api_key → get_settings
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
#  PATTERN 7: JWT Authentication — get_current_user
# ═══════════════════════════════════════════════════════════════
#
#  This is the most complex dependency chain:
#
#     get_current_user
#        ↓ depends on
#     bearer_scheme (extracts Bearer token from header)
#        ↓ depends on
#     get_user_repo (to look up the user by ID)
#
#  The result is the full User object — injected into any
#  endpoint that declares `current_user: CurrentUserDep`.
# ═══════════════════════════════════════════════════════════════

async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    repo: UserRepository = Depends(get_user_repo),
) -> User:
    """
    Extracts, verifies the JWT token, and returns the current user.

    DEPENDENCY CHAIN:
    ─────────────────
    1. bearer_scheme extracts token from: Authorization: Bearer <token>
    2. decode_access_token verifies the JWT signature + expiry
    3. user_id is extracted from the "sub" claim
    4. User is looked up in the database via the injected repo
    5. The User object is returned — or 401 is raised

    LEARNING POINT:
    ─────────────────
    This dependency combines MULTIPLE patterns:
    - Pattern 2: Repository injection (to look up the user)
    - Pattern 5: Dependency chain (bearer → decode → repo)
    - Pattern 7: JWT authentication (new!)

    If ANY step fails, HTTPException(401) is raised and the
    endpoint never executes. This is the guard pattern.
    """
    # ── Step 1: Check for token ──
    if credentials is None:
        raise HTTPException(
            status_code=401,
            detail="Not authenticated. Include 'Authorization: Bearer <token>' header.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials

    # ── Step 2: Decode and verify JWT ──
    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # ── Step 3: Extract user_id from token ──
    user_id: str = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=401,
            detail="Token payload is invalid (missing 'sub').",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # ── Step 4: Look up user in database ──
    user = await repo.get(user_id)
    if user is None:
        raise HTTPException(
            status_code=401,
            detail="User not found. Token may be for a deleted account.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


# ═══════════════════════════════════════════════════════════════
#  PATTERN 5: Dependency Chains (Composed Dependencies)
# ═══════════════════════════════════════════════════════════════

async def get_current_request_info(
    request: Request,
    settings: Settings = Depends(get_settings),
    log_data: dict = Depends(log_request),
):
    """A composed dependency that combines multiple other dependencies."""
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

UserRepoDep = Annotated[UserRepository, Depends(get_user_repo)]
ProductRepoDep = Annotated[ProductRepository, Depends(get_product_repo)]
TaskQueueDep = Annotated[TaskQueue | None, Depends(get_task_queue)]
PasswordHasherDep = Annotated[PasswordHasher, Depends(get_password_hasher)]
CurrentUserDep = Annotated[User, Depends(get_current_user)]
SettingsDep = Annotated[Settings, Depends(get_settings)]
RequestInfoDep = Annotated[dict, Depends(get_current_request_info)]
