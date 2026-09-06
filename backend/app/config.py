"""
All configuration comes from environment variables. Nothing here is a
hardcoded secret — see .env.example for the variables to set locally,
and docker-compose.yml for how they are injected in containers.
"""
from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    app_name: str = "TRACE-X"
    environment: str = os.environ.get("TRACEX_ENV", "development")

    database_url: str = os.environ.get(
        "TRACEX_DATABASE_URL",
        "postgresql+psycopg2://tracex:tracex@localhost:5432/tracex",
    )
    redis_url: str = os.environ.get("TRACEX_REDIS_URL", "redis://localhost:6379/0")

    jwt_secret: str = os.environ.get("TRACEX_JWT_SECRET", "")
    jwt_algorithm: str = "HS256"
    jwt_expiry_minutes: int = int(os.environ.get("TRACEX_JWT_EXPIRY_MINUTES", "120"))

    cors_allowed_origins: tuple[str, ...] = tuple(
        o.strip()
        for o in os.environ.get("TRACEX_CORS_ORIGINS", "http://localhost:3000").split(",")
        if o.strip()
    )

    rate_limit_per_minute: int = int(os.environ.get("TRACEX_RATE_LIMIT_PER_MINUTE", "60"))

    def require_jwt_secret(self) -> str:
        if not self.jwt_secret:
            raise RuntimeError(
                "TRACEX_JWT_SECRET is not set. Refusing to start with a "
                "default/hardcoded secret — set it via environment variable "
                "or a .env file (see .env.example)."
            )
        return self.jwt_secret


settings = Settings()
