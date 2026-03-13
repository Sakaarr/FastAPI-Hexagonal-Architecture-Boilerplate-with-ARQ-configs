"""
Business Logic Tests
=====================
These tests verify all business rules WITHOUT touching MongoDB.
They use FakeUserRepository and FakeProductRepository (in-memory).

Run with:  pytest tests/test_business_logic.py -v
"""

import pytest
from tests.fake_repositories import FakeUserRepository, FakeProductRepository, FakeTaskQueue

from app.application.use_cases.create_user import CreateUser
from app.application.use_cases.get_user import GetUser
from app.application.use_cases.list_users import ListUsers

from app.application.use_cases.create_product import CreateProduct
from app.application.use_cases.get_product import GetProduct
from app.application.use_cases.list_product import ListProducts
from app.application.use_cases.update_product import UpdateProduct


# ═══════════════════════════════════════════════════════════════
#  USER ENTITY VALIDATION TESTS
# ═══════════════════════════════════════════════════════════════

class TestUserEntityValidation:
    """Tests for domain-level validation rules on the User entity."""

    @pytest.mark.asyncio
    async def test_valid_user_creation(self):
        repo = FakeUserRepository()
        use_case = CreateUser(repo)
        user = await use_case.execute("John Doe", "john@example.com")

        assert user.id is not None
        assert user.name == "John Doe"
        assert user.email == "john@example.com"

    @pytest.mark.asyncio
    async def test_email_is_lowercased(self):
        repo = FakeUserRepository()
        use_case = CreateUser(repo)
        user = await use_case.execute("Jane Doe", "JANE@EXAMPLE.COM")

        assert user.email == "jane@example.com"

    @pytest.mark.asyncio
    async def test_invalid_email_format_rejected(self):
        repo = FakeUserRepository()
        use_case = CreateUser(repo)

        with pytest.raises(Exception):  # Pydantic ValidationError
            await use_case.execute("John", "not-an-email")

    @pytest.mark.asyncio
    async def test_empty_email_rejected(self):
        repo = FakeUserRepository()
        use_case = CreateUser(repo)

        with pytest.raises(Exception):
            await use_case.execute("John", "")

    @pytest.mark.asyncio
    async def test_name_too_short_rejected(self):
        repo = FakeUserRepository()
        use_case = CreateUser(repo)

        with pytest.raises(Exception):
            await use_case.execute("J", "john@example.com")

    @pytest.mark.asyncio
    async def test_name_whitespace_only_rejected(self):
        repo = FakeUserRepository()
        use_case = CreateUser(repo)

        with pytest.raises(Exception):
            await use_case.execute("   ", "john@example.com")

    @pytest.mark.asyncio
    async def test_name_too_long_rejected(self):
        repo = FakeUserRepository()
        use_case = CreateUser(repo)

        with pytest.raises(Exception):
            await use_case.execute("A" * 101, "john@example.com")


# ═══════════════════════════════════════════════════════════════
#  USER BUSINESS LOGIC TESTS (USE CASE LEVEL)
# ═══════════════════════════════════════════════════════════════

class TestUserBusinessLogic:
    """Tests for use-case-level business rules."""

    @pytest.mark.asyncio
    async def test_duplicate_email_rejected(self):
        """The core business rule: no two users with the same email."""
        repo = FakeUserRepository()
        use_case = CreateUser(repo)

        # First creation should succeed
        await use_case.execute("Alice", "alice@example.com")

        # Second creation with same email should fail
        with pytest.raises(ValueError, match="already exists"):
            await use_case.execute("Bob", "alice@example.com")

    @pytest.mark.asyncio
    async def test_duplicate_email_case_insensitive(self):
        """Email duplicates should be caught regardless of case."""
        repo = FakeUserRepository()
        use_case = CreateUser(repo)

        await use_case.execute("Alice", "alice@example.com")

        with pytest.raises(ValueError, match="already exists"):
            await use_case.execute("Bob", "ALICE@EXAMPLE.COM")

    @pytest.mark.asyncio
    async def test_get_nonexistent_user_raises(self):
        repo = FakeUserRepository()
        use_case = GetUser(repo)

        with pytest.raises(ValueError, match="not found"):
            await use_case.execute("nonexistent-id")

    @pytest.mark.asyncio
    async def test_list_users_empty(self):
        repo = FakeUserRepository()
        use_case = ListUsers(repo)

        users = await use_case.execute()
        assert users == []

    @pytest.mark.asyncio
    async def test_list_users_returns_all(self):
        repo = FakeUserRepository()
        create = CreateUser(repo)
        list_uc = ListUsers(repo)

        await create.execute("Alice", "alice@example.com")
        await create.execute("Bob", "bob@example.com")

        users = await list_uc.execute()
        assert len(users) == 2


# ═══════════════════════════════════════════════════════════════
#  PRODUCT ENTITY VALIDATION TESTS
# ═══════════════════════════════════════════════════════════════

class TestProductEntityValidation:
    """Tests for domain-level validation rules on the Product entity."""

    @pytest.mark.asyncio
    async def test_valid_product_creation(self):
        repo = FakeProductRepository()
        use_case = CreateProduct(repo)
        product = await use_case.execute("Widget", 29.99, "A great widget")

        assert product.id is not None
        assert product.name == "Widget"
        assert product.price == 29.99
        assert product.description == "A great widget"

    @pytest.mark.asyncio
    async def test_negative_price_rejected(self):
        repo = FakeProductRepository()
        use_case = CreateProduct(repo)

        with pytest.raises(Exception):
            await use_case.execute("Widget", -10.0)

    @pytest.mark.asyncio
    async def test_price_too_high_rejected(self):
        repo = FakeProductRepository()
        use_case = CreateProduct(repo)

        with pytest.raises(Exception):
            await use_case.execute("Expensive Thing", 2_000_000)

    @pytest.mark.asyncio
    async def test_price_rounded_to_2_decimals(self):
        repo = FakeProductRepository()
        use_case = CreateProduct(repo)
        product = await use_case.execute("Widget", 29.999)

        assert product.price == 30.0

    @pytest.mark.asyncio
    async def test_product_name_too_short_rejected(self):
        repo = FakeProductRepository()
        use_case = CreateProduct(repo)

        with pytest.raises(Exception):
            await use_case.execute("X", 10.0)

    @pytest.mark.asyncio
    async def test_product_name_too_long_rejected(self):
        repo = FakeProductRepository()
        use_case = CreateProduct(repo)

        with pytest.raises(Exception):
            await use_case.execute("A" * 201, 10.0)

    @pytest.mark.asyncio
    async def test_empty_description_becomes_none(self):
        repo = FakeProductRepository()
        use_case = CreateProduct(repo)
        product = await use_case.execute("Widget", 10.0, "   ")

        assert product.description is None

    @pytest.mark.asyncio
    async def test_description_too_long_rejected(self):
        repo = FakeProductRepository()
        use_case = CreateProduct(repo)

        with pytest.raises(Exception):
            await use_case.execute("Widget", 10.0, "A" * 1001)


# ═══════════════════════════════════════════════════════════════
#  PRODUCT BUSINESS LOGIC TESTS (USE CASE LEVEL)
# ═══════════════════════════════════════════════════════════════

class TestProductBusinessLogic:
    """Tests for use-case-level business rules."""

    @pytest.mark.asyncio
    async def test_duplicate_product_name_rejected(self):
        """No two products with the same name."""
        repo = FakeProductRepository()
        use_case = CreateProduct(repo)

        await use_case.execute("Widget", 29.99)

        with pytest.raises(ValueError, match="already exists"):
            await use_case.execute("Widget", 49.99)

    @pytest.mark.asyncio
    async def test_get_nonexistent_product_raises(self):
        repo = FakeProductRepository()
        use_case = GetProduct(repo)

        with pytest.raises(ValueError, match="not found"):
            await use_case.execute("nonexistent-id")

    @pytest.mark.asyncio
    async def test_list_products_empty(self):
        repo = FakeProductRepository()
        use_case = ListProducts(repo)

        products = await use_case.execute()
        assert products == []

    @pytest.mark.asyncio
    async def test_list_products_returns_all(self):
        repo = FakeProductRepository()
        create = CreateProduct(repo)
        list_uc = ListProducts(repo)

        await create.execute("Widget A", 10.0)
        await create.execute("Widget B", 20.0)

        products = await list_uc.execute()
        assert len(products) == 2

    @pytest.mark.asyncio
    async def test_update_product(self):
        repo = FakeProductRepository()
        create = CreateProduct(repo)
        update = UpdateProduct(repo)

        product = await create.execute("Widget", 10.0, "Old description")
        updated = await update.execute(product.id, "Widget V2", 15.0, "New description")

        assert updated.name == "Widget V2"
        assert updated.price == 15.0
        assert updated.description == "New description"

    @pytest.mark.asyncio
    async def test_product_creation_without_description(self):
        repo = FakeProductRepository()
        use_case = CreateProduct(repo)
        product = await use_case.execute("Widget", 10.0)

        assert product.description is None


# ═══════════════════════════════════════════════════════════════
#  BACKGROUND TASK TESTS (Task Queue integration)
# ═══════════════════════════════════════════════════════════════

class TestBackgroundTasks:
    """Tests that verify background tasks are enqueued correctly."""

    @pytest.mark.asyncio
    async def test_welcome_email_enqueued_on_user_creation(self):
        """When a user is created WITH a task queue, a welcome email is enqueued."""
        repo = FakeUserRepository()
        task_queue = FakeTaskQueue()
        use_case = CreateUser(repo, task_queue)

        user = await use_case.execute("Alice", "alice@example.com")

        # Verify the task was enqueued
        assert len(task_queue.enqueued_tasks) == 1
        task = task_queue.enqueued_tasks[0]
        assert task["task_name"] == "send_welcome_email"
        assert task["kwargs"]["email"] == "alice@example.com"
        assert task["kwargs"]["name"] == "Alice"

    @pytest.mark.asyncio
    async def test_no_task_enqueued_without_task_queue(self):
        """When task_queue is None (Redis down), user creation still works."""
        repo = FakeUserRepository()
        use_case = CreateUser(repo, task_queue=None)

        user = await use_case.execute("Alice", "alice@example.com")
        assert user.name == "Alice"  # User was still created

    @pytest.mark.asyncio
    async def test_no_task_enqueued_on_failed_creation(self):
        """If user creation fails (duplicate), no email task is enqueued."""
        repo = FakeUserRepository()
        task_queue = FakeTaskQueue()
        use_case = CreateUser(repo, task_queue)

        await use_case.execute("Alice", "alice@example.com")
        task_queue.enqueued_tasks.clear()  # Reset after first creation

        with pytest.raises(ValueError, match="already exists"):
            await use_case.execute("Bob", "alice@example.com")

        # No task should have been enqueued for the failed creation
        assert len(task_queue.enqueued_tasks) == 0

    @pytest.mark.asyncio
    async def test_multiple_users_enqueue_multiple_emails(self):
        """Each user creation enqueues its own welcome email."""
        repo = FakeUserRepository()
        task_queue = FakeTaskQueue()
        use_case = CreateUser(repo, task_queue)

        await use_case.execute("Alice", "alice@example.com")
        await use_case.execute("Bob", "bob@example.com")

        assert len(task_queue.enqueued_tasks) == 2
        assert task_queue.enqueued_tasks[0]["kwargs"]["email"] == "alice@example.com"
        assert task_queue.enqueued_tasks[1]["kwargs"]["email"] == "bob@example.com"
