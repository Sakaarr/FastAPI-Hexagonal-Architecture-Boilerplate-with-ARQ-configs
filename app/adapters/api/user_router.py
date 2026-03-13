"""
╔══════════════════════════════════════════════════════════════════╗
║  USER ROUTER — Refactored with Dependency Injection              ║
║                                                                  ║
║  BEFORE (hardcoded):                                             ║
║      repo = MongoUserRepository()    ← tight coupling!          ║
║      use_case = CreateUser(repo)                                 ║
║                                                                  ║
║  AFTER (DI):                                                     ║
║      repo: UserRepoDep               ← injected by FastAPI      ║
║      use_case = CreateUser(repo)     ← same use case, any repo  ║
║                                                                  ║
║  The router no longer knows or cares which database it uses.     ║
╚══════════════════════════════════════════════════════════════════╝
"""

from fastapi import APIRouter, Depends

from app.application.use_cases.create_user import CreateUser
from app.application.use_cases.get_user import GetUser
from app.application.use_cases.list_users import ListUsers
from app.application.use_cases.update_user import UpdateUser
from app.application.use_cases.delete_user import DeleteUser

from app.adapters.api.dependencies import (
    UserRepoDep,          # Pattern 2: Repository injection
    TaskQueueDep,         # Background task queue injection
    SettingsDep,          # Pattern 1: Config injection
    RequestInfoDep,       # Pattern 5: Chained dependency
    log_request,          # Pattern 3: Request logging
    verify_api_key,       # Pattern 4: API key auth
    get_current_user,     # Pattern 7: JWT auth + current user
)

# ── The router itself can have dependencies! ──
# log_request runs for EVERY endpoint in this router automatically
router = APIRouter(
    prefix="/users",
    tags=["Users"],
    dependencies=[Depends(log_request)],  # Pattern 3: applied to ALL routes
)


# ─────────────────────────────────────────────────────────────────
#  PUBLIC ENDPOINTS (no auth required)
# ─────────────────────────────────────────────────────────────────

@router.get("/")
async def list_users(repo: UserRepoDep):
    """
    List all users.

    NOTICE: `repo: UserRepoDep` is all it takes!
    FastAPI calls get_user_repo() automatically and passes the
    result as `repo`. The endpoint doesn't know it's MongoDB.

    UserRepoDep = Annotated[UserRepository, Depends(get_user_repo)]
    """
    use_case = ListUsers(repo)
    return await use_case.execute()


@router.get("/{user_id}")
async def get_user(user_id: str, repo: UserRepoDep):
    """
    Get a specific user by ID.
    repo is injected — the endpoint is database-agnostic.
    """
    use_case = GetUser(repo)
    return await use_case.execute(user_id)


# ─────────────────────────────────────────────────────────────────
#  PROTECTED ENDPOINTS (API key required — Pattern 4)
# ─────────────────────────────────────────────────────────────────

@router.post("/", dependencies=[Depends(verify_api_key)])
async def create_user(name: str, email: str, repo: UserRepoDep, task_queue: TaskQueueDep):
    """
    Create a new user. Requires API key.
    Enqueues a welcome email as a background task via arq.

    THREE DI patterns at work here:
    1. dependencies=[Depends(verify_api_key)] → Auth guard (run, don't inject)
    2. repo: UserRepoDep → Repository injection
    3. task_queue: TaskQueueDep → Background task queue injection

    The task_queue can be None if Redis is down — user creation
    still succeeds, just without the welcome email.
    """
    use_case = CreateUser(repo, task_queue)
    return await use_case.execute(name, email)


@router.put("/{user_id}", dependencies=[Depends(verify_api_key)])
async def update_user(user_id: str, name: str, email: str, repo: UserRepoDep):
    """Update a user. Requires API key."""
    use_case = UpdateUser(repo)
    return await use_case.execute(user_id, name, email)


@router.delete("/{user_id}", dependencies=[Depends(verify_api_key)])
async def delete_user(user_id: str, repo: UserRepoDep):
    """Delete a user. Requires API key."""
    use_case = DeleteUser(repo)
    await use_case.execute(user_id)
    return {"message": "deleted"}


# ─────────────────────────────────────────────────────────────────
#  DEBUG ENDPOINT — Demonstrates Pattern 1 + Pattern 5
# ─────────────────────────────────────────────────────────────────

@router.get("/debug/info")
async def debug_info(settings: SettingsDep, request_info: RequestInfoDep):
    """
    Shows injected settings and request info.

    DEMONSTRATES:
    - Pattern 1: `settings: SettingsDep` injects the Settings object
    - Pattern 5: `request_info: RequestInfoDep` triggers a chain:
      get_current_request_info → log_request → request
                               → get_settings → @lru_cache

    All resolved automatically by FastAPI!
    """
    return {
        "app_name": settings.app_name,
        "debug_mode": settings.debug,
        "database": settings.mongo_db_name,
        "request_context": request_info,
    }
