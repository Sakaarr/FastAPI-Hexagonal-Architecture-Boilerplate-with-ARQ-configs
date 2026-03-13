"""
╔══════════════════════════════════════════════════════════════╗
║  AUTH ROUTER — Registration & Login                          ║
║                                                              ║
║  Endpoints:                                                  ║
║  ┌──────────────────────────────────────────────────────────┐║
║  │  POST /auth/register  → Create account with password     │║
║  │  POST /auth/login     → Get JWT token                    │║
║  │  GET  /auth/me        → Get current user (requires JWT)  │║
║  └──────────────────────────────────────────────────────────┘║
║                                                              ║
║  All auth is handled via DI — the router doesn't know        ║
║  about bcrypt, JWT internals, or MongoDB.                    ║
╚══════════════════════════════════════════════════════════════╝
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel, EmailStr

from app.application.use_cases.register_user import RegisterUser
from app.application.use_cases.login_user import LoginUser

from app.adapters.api.dependencies import (
    UserRepoDep,
    TaskQueueDep,
    PasswordHasherDep,
    CurrentUserDep,
    log_request,
)


router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
    dependencies=[Depends(log_request)],
)


# ═══════════════════════════════════════════════════════════════
#  REQUEST/RESPONSE SCHEMAS
# ═══════════════════════════════════════════════════════════════

class RegisterRequest(BaseModel):
    """
    Request body for user registration.

    LEARNING POINT:
    ─────────────────
    Using a Pydantic model for the request body (instead of
    individual query params) gives us:
    - Automatic validation
    - JSON body parsing
    - OpenAPI schema documentation
    """
    name: str
    email: str
    password: str


class LoginRequest(BaseModel):
    """Request body for login."""
    email: str
    password: str


class TokenResponse(BaseModel):
    """Response after successful login."""
    access_token: str
    token_type: str
    user: dict


# ═══════════════════════════════════════════════════════════════
#  ENDPOINTS
# ═══════════════════════════════════════════════════════════════

@router.post("/register", response_model=dict)
async def register(
    body: RegisterRequest,
    repo: UserRepoDep,
    hasher: PasswordHasherDep,
    task_queue: TaskQueueDep,
):
    """
    Register a new user account.

    WHAT HAPPENS:
    1. RegisterUser use case validates the input
    2. Password is hashed via injected PasswordHasher (bcrypt)
    3. User is saved to the database
    4. Welcome email is enqueued (if Redis is available)
    5. User data is returned (WITHOUT password_hash)

    THREE injected dependencies:
    - repo: UserRepoDep → database access
    - hasher: PasswordHasherDep → password hashing
    - task_queue: TaskQueueDep → background email
    """
    use_case = RegisterUser(repo, hasher, task_queue)
    user = await use_case.execute(body.name, body.email, body.password)
    return user.to_public_dict()


@router.post("/login", response_model=TokenResponse)
async def login(
    body: LoginRequest,
    repo: UserRepoDep,
    hasher: PasswordHasherDep,
):
    """
    Login and receive a JWT token.

    WHAT HAPPENS:
    1. LoginUser use case looks up the user by email
    2. Password is verified against the stored bcrypt hash
    3. If valid, a JWT token is generated
    4. Token + user info is returned

    HOW TO USE THE TOKEN:
    Include in subsequent requests as:
        Authorization: Bearer <token>
    """
    use_case = LoginUser(repo, hasher)
    return await use_case.execute(body.email, body.password)


@router.get("/me")
async def get_current_user_info(current_user: CurrentUserDep):
    """
    Get the currently authenticated user's info.

    LEARNING POINT:
    ─────────────────
    `current_user: CurrentUserDep` triggers a dependency chain:

    1. FastAPI extracts the Bearer token from Authorization header
    2. get_current_user() decodes the JWT
    3. Extracts user_id from the "sub" claim
    4. Looks up the user in the database
    5. Returns the User object (or raises 401)

    All of this happens BEFORE this endpoint runs.
    If any step fails, the endpoint never executes.
    """
    return current_user.to_public_dict()
