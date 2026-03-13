"""
╔══════════════════════════════════════════════════════════════╗
║  PRODUCT ROUTER — Refactored with Dependency Injection       ║
║                                                              ║
║  Same DI patterns as user_router, applied to products.       ║
║  Notice: ZERO imports from mongo_product_repository.         ║
║  The router is completely database-agnostic.                 ║
╚══════════════════════════════════════════════════════════════╝
"""

from fastapi import APIRouter, Depends

from app.application.use_cases.create_product import CreateProduct
from app.application.use_cases.get_product import GetProduct
from app.application.use_cases.list_product import ListProducts
from app.application.use_cases.update_product import UpdateProduct

from app.adapters.api.dependencies import (
    ProductRepoDep,       # Pattern 2: Repository injection
    CurrentUserDep,       # Pattern 7: JWT Authentication
    log_request,          # Pattern 3: Request logging
)


router = APIRouter(
    prefix="/products",
    tags=["Products"],
    dependencies=[Depends(log_request)],  # Logs all product requests
)


# ── Public endpoints ──

@router.get("/")
async def list_products(repo: ProductRepoDep):
    use_case = ListProducts(repo)
    return await use_case.execute()


@router.get("/{product_id}")
async def get_product(product_id: str, repo: ProductRepoDep):
    use_case = GetProduct(repo)
    return await use_case.execute(product_id)


# ── Protected endpoints (require JWT Authentication) ──

@router.post("/")
async def create_product(
    name: str,
    price: float,
    repo: ProductRepoDep,
    current_user: CurrentUserDep, # Injects the User object if JWT is valid
    description: str = None,
):
    """
    Create a new product.
    Requires a valid JWT token (Authorization: Bearer <token>).
    """
    use_case = CreateProduct(repo)
    return await use_case.execute(name, price, description)


@router.put("/{product_id}")
async def update_product(
    product_id: str,
    name: str,
    price: float,
    repo: ProductRepoDep,
    current_user: CurrentUserDep, # Injects the User object if JWT is valid
    description: str = None,
):
    """
    Update a product.
    Requires a valid JWT token.
    """
    use_case = UpdateProduct(repo)
    return await use_case.execute(product_id, name, price, description)
