"""Production preflight checks (env + basic config sanity)."""
from __future__ import annotations

import os
import sys
from urllib.parse import urlparse

REQUIRED = [
    "SECRET_KEY",
    "ADMIN_PASSWORD_HASH",
    "DATABASE_URL",
    "REDIS_URL",
]


def _fail(msg: str) -> None:
    print(f"FAIL: {msg}")
    sys.exit(1)


def _warn(msg: str) -> None:
    print(f"WARN: {msg}")


def main() -> None:
    env_state = os.getenv("ENV_STATE", "development")
    debug = os.getenv("DEBUG", "false").lower() == "true"
    cors = os.getenv("CORS_ORIGINS", "")

    if env_state == "production" and debug:
        _fail("DEBUG must be false in production")

    if env_state == "production" and ("*" in cors or not cors.strip()):
        _fail("CORS_ORIGINS must be explicit in production")

    for key in REQUIRED:
        if not os.getenv(key):
            _fail(f"Missing env var: {key}")

    secret = os.getenv("SECRET_KEY", "")
    if len(secret) < 32:
        _warn("SECRET_KEY length < 32")

    admin_hash = os.getenv("ADMIN_PASSWORD_HASH", "")
    if not admin_hash.startswith("$2"):
        _warn("ADMIN_PASSWORD_HASH does not look like bcrypt")

    db = urlparse(os.getenv("DATABASE_URL", ""))
    if not db.scheme.startswith("postgres"):
        _warn("DATABASE_URL is not postgres")

    redis = urlparse(os.getenv("REDIS_URL", ""))
    if redis.scheme != "redis":
        _warn("REDIS_URL scheme is not redis")

    sentry = os.getenv("SENTRY_DSN")
    if not sentry:
        _warn("SENTRY_DSN not set")

    grafana = os.getenv("GF_SECURITY_ADMIN_PASSWORD")
    if not grafana:
        _warn("GF_SECURITY_ADMIN_PASSWORD not set")

    print("OK: preflight checks passed")


if __name__ == "__main__":
    main()
