"""
╔══════════════════════════════════════════════════════════════╗
║  PATTERN 1: Configuration as a Dependency                    ║
║                                                              ║
║  Instead of hardcoding values like MONGO_URL everywhere,     ║
║  we define a Settings class that loads from environment      ║
║  variables / .env file. Then we inject it via Depends().     ║
║                                                              ║
║  WHY?  If you want to switch databases, change the app       ║
║  name, or toggle debug mode, you change ONE .env file —      ║
║  not scattered hardcoded strings.                            ║
╚══════════════════════════════════════════════════════════════╝
"""

from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    All app configuration lives here.
    Values are loaded from environment variables or a .env file.
    """

    # ── App Settings ──
    app_name: str = "FastAPI Hexagonal Boilerplate"
    debug: bool = True

    # ── Database ──
    mongo_url: str = "mongodb://localhost:27017"
    mongo_db_name: str = "hexagonal_db"

    # ── Security ──
    api_key: str = "dev-secret-key-change-in-production"

    # ── Rate Limiting ──
    max_requests_per_minute: int = 60

    # ── Redis (for arq task queue) ──
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_password: str | None = None

    # ── Email (SMTP) ──
    smtp_host: str = "localhost"
    smtp_port: int = 1025         # Default MailHog/MailCatcher dev port
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_sender: str = "noreply@hexagonal-app.com"
    smtp_use_tls: bool = False    # Set True for production (Gmail, etc.)

    class Config:
        env_file = ".env"  # Automatically reads from .env if it exists


@lru_cache()
def get_settings() -> Settings:
    """
    Singleton factory for Settings.

    @lru_cache ensures this is only created ONCE, no matter how
    many times it's called. FastAPI's Depends(get_settings) will
    call this function and inject the result into your endpoint.

    LEARNING POINT:
    ─────────────────
    This is the simplest DI pattern — a function that returns
    an object. FastAPI calls it for you and passes the result
    as a parameter to your endpoint function.
    """
    return Settings()
