"""
╔══════════════════════════════════════════════════════════════════╗
║  PATTERN 6: Dependency Overrides for Testing                     ║
║                                                                  ║
║  This is the MOST POWERFUL DI pattern in FastAPI.                ║
║                                                                  ║
║  app.dependency_overrides lets you replace ANY dependency        ║
║  with a different implementation at runtime. This means you      ║
║  can test your ENTIRE API (routers, auth, everything) without    ║
║  a database — and without changing a single line of app code.    ║
║                                                                  ║
║  Run with:  pytest tests/test_api_with_di.py -v                 ║
╚══════════════════════════════════════════════════════════════════╝
"""

import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.adapters.api.dependencies import (
    get_user_repo,
    get_product_repo,
    get_task_queue,
    verify_api_key,
)
from tests.fake_repositories import (
    FakeUserRepository,
    FakeProductRepository,
    FakeTaskQueue,
)


# ═══════════════════════════════════════════════════════════════
#  FIXTURES — Set up dependency overrides
# ═══════════════════════════════════════════════════════════════

# Shared fake repos (reset for each test)
_fake_user_repo = FakeUserRepository()
_fake_product_repo = FakeProductRepository()


@pytest.fixture(autouse=True)
def override_dependencies():
    """
    LEARNING POINT — dependency_overrides:
    ────────────────────────────────────────
    app.dependency_overrides is a dictionary where:
      - KEY   = the original dependency function
      - VALUE = the replacement function

    When FastAPI sees Depends(get_user_repo), it checks if
    get_user_repo is in dependency_overrides. If so, it calls
    the override function INSTEAD.

    This means your routers, auth, logging — everything works
    exactly as in production, but with fake data.
    """
    global _fake_user_repo, _fake_product_repo
    _fake_user_repo = FakeUserRepository()       # Fresh for each test
    _fake_product_repo = FakeProductRepository()  # Fresh for each test
    _fake_task_queue = FakeTaskQueue()            # Fresh for each test

    # ── OVERRIDE: Swap real repos → fake repos ──
    app.dependency_overrides[get_user_repo] = lambda: _fake_user_repo
    app.dependency_overrides[get_product_repo] = lambda: _fake_product_repo
    app.dependency_overrides[get_task_queue] = lambda: _fake_task_queue

    # ── OVERRIDE: Skip auth for most tests ──
    # This replaces verify_api_key with a no-op, so tests don't
    # need to pass API keys. See test_auth_required() for how
    # to test auth specifically.
    app.dependency_overrides[verify_api_key] = lambda: {"authenticated": True}

    yield

    # ── CLEANUP: Remove all overrides after each test ──
    app.dependency_overrides.clear()


@pytest.fixture
async def client():
    """Async HTTP client that talks to the app in-memory (no server needed)."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# ═══════════════════════════════════════════════════════════════
#  USER API TESTS (Full HTTP layer, zero database)
# ═══════════════════════════════════════════════════════════════

class TestUserAPI:
    """Test the user endpoints through the full HTTP stack."""

    @pytest.mark.asyncio
    async def test_create_user_via_api(self, client):
        """
        This sends a real HTTP POST to the FastAPI app.
        But get_user_repo returns FakeUserRepository.
        So it's hitting the full router → use case → repo chain,
        just with an in-memory repo instead of MongoDB.
        """
        response = await client.post("/users/?name=Alice&email=alice@example.com")

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Alice"
        assert data["email"] == "alice@example.com"
        assert data["id"] is not None

    @pytest.mark.asyncio
    async def test_list_users_via_api(self, client):
        # Create two users first
        await client.post("/users/?name=Alice&email=alice@example.com")
        await client.post("/users/?name=Bob&email=bob@example.com")

        response = await client.get("/users/")
        assert response.status_code == 200
        assert len(response.json()) == 2

    @pytest.mark.asyncio
    async def test_get_user_via_api(self, client):
        # Create a user
        create_resp = await client.post("/users/?name=Alice&email=alice@example.com")
        user_id = create_resp.json()["id"]

        # Retrieve it
        response = await client.get(f"/users/{user_id}")
        assert response.status_code == 200
        assert response.json()["name"] == "Alice"

    @pytest.mark.asyncio
    async def test_get_nonexistent_user_returns_400(self, client):
        """
        Business logic (ValueError) should be caught by the
        global exception handler and returned as HTTP 400.
        """
        response = await client.get("/users/nonexistent-id")
        assert response.status_code == 400
        assert "not found" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_duplicate_email_returns_400(self, client):
        await client.post("/users/?name=Alice&email=alice@example.com")

        response = await client.post("/users/?name=Bob&email=alice@example.com")
        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_invalid_email_returns_error(self, client):
        response = await client.post("/users/?name=Alice&email=not-an-email")
        assert response.status_code != 200


# ═══════════════════════════════════════════════════════════════
#  PRODUCT API TESTS
# ═══════════════════════════════════════════════════════════════

class TestProductAPI:
    """Test the product endpoints through the full HTTP stack."""

    @pytest.mark.asyncio
    async def test_create_product_via_api(self, client):
        response = await client.post(
            "/products/?name=Widget&price=29.99&description=A+great+widget"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Widget"
        assert data["price"] == 29.99

    @pytest.mark.asyncio
    async def test_list_products_via_api(self, client):
        await client.post("/products/?name=Widget+A&price=10.0")
        await client.post("/products/?name=Widget+B&price=20.0")

        response = await client.get("/products/")
        assert response.status_code == 200
        assert len(response.json()) == 2

    @pytest.mark.asyncio
    async def test_negative_price_rejected(self, client):
        response = await client.post("/products/?name=Widget&price=-5.0")
        assert response.status_code != 200

    @pytest.mark.asyncio
    async def test_duplicate_product_name_rejected(self, client):
        await client.post("/products/?name=Widget&price=10.0")

        response = await client.post("/products/?name=Widget&price=20.0")
        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]


# ═══════════════════════════════════════════════════════════════
#  AUTH TESTS — Testing the auth dependency itself
# ═══════════════════════════════════════════════════════════════

class TestAuthentication:
    """
    LEARNING POINT:
    ─────────────────
    To test auth, we REMOVE the verify_api_key override so the
    real auth dependency runs. Then we test with/without headers.
    """

    @pytest.mark.asyncio
    async def test_protected_endpoint_rejects_no_api_key(self, client):
        # Remove the auth override so real auth runs
        app.dependency_overrides.pop(verify_api_key, None)

        response = await client.post("/users/?name=Alice&email=alice@example.com")
        assert response.status_code == 401
        assert "Missing API key" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_protected_endpoint_rejects_wrong_api_key(self, client):
        app.dependency_overrides.pop(verify_api_key, None)

        response = await client.post(
            "/users/?name=Alice&email=alice@example.com",
            headers={"X-API-Key": "wrong-key"},
        )
        assert response.status_code == 403
        assert "Invalid API key" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_protected_endpoint_accepts_valid_api_key(self, client):
        app.dependency_overrides.pop(verify_api_key, None)

        response = await client.post(
            "/users/?name=Alice&email=alice@example.com",
            headers={"X-API-Key": "dev-secret-key-change-in-production"},
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_public_endpoint_needs_no_api_key(self, client):
        """GET endpoints are public — no auth override needed."""
        app.dependency_overrides.pop(verify_api_key, None)

        response = await client.get("/users/")
        assert response.status_code == 200


# ═══════════════════════════════════════════════════════════════
#  HEALTH CHECK TEST
# ═══════════════════════════════════════════════════════════════

class TestHealthCheck:

    @pytest.mark.asyncio
    async def test_health_endpoint(self, client):
        response = await client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
