"""
╔══════════════════════════════════════════════════════════════╗
║  UPDATED: Database connection now uses injected Settings     ║
║                                                              ║
║  Before: MONGO_URL was hardcoded here.                       ║
║  After:  We read from Settings (which reads from .env).      ║
║                                                              ║
║  The get_database() function is a dependency that other      ║
║  dependencies can depend on (DEPENDENCY CHAIN — Pattern 5).  ║
╚══════════════════════════════════════════════════════════════╝
"""

from motor.motor_asyncio import AsyncIOMotorClient
from app.infrastructure.config import get_settings


settings = get_settings()

client = AsyncIOMotorClient(settings.mongo_url)
db = client[settings.mongo_db_name]

user_collection = db["users"]


def get_database():
    """
    Dependency that provides the database instance.

    LEARNING POINT:
    ─────────────────
    This is a DEPENDENCY CHAIN building block. Other dependencies
    (like repository providers) can depend on this function to
    get the database — so if you ever change HOW you connect to
    the DB, you only change this one place.
    """
    return db
