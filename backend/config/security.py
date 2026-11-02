"""Production secret and list-parsing helpers.

Settings call these at import. Tests call them directly so a weak key is rejected
without reloading Django.
"""

import os

from django.core.exceptions import ImproperlyConfigured

DEV_SECRET_PREFIX = "dev-only-"
MIN_SECRET_LENGTH = 50
MIN_UNIQUE_SECRET_CHARS = 8
DEFAULT_DEV_SECRET = (
    "dev-only-synfotalent-secret-key-change-before-any-shared-deployment-0001-local"
)


def resolve_secret_key(raw: str | None, *, debug: bool) -> str:
    """Return a usable secret, or refuse to start when debug is off."""
    secret = (raw or "").strip()
    if not secret:
        if debug:
            return DEFAULT_DEV_SECRET
        raise ImproperlyConfigured(
            "Set DJANGO_SECRET_KEY. SynfoTalent will not start with DEBUG off and no secret."
        )
    if debug:
        return secret
    if secret.startswith(DEV_SECRET_PREFIX):
        raise ImproperlyConfigured(
            "Refusing to start with the development secret while DJANGO_DEBUG is off."
        )
    if len(secret) < MIN_SECRET_LENGTH:
        raise ImproperlyConfigured(
            "DJANGO_SECRET_KEY must be at least "
            f"{MIN_SECRET_LENGTH} characters when DJANGO_DEBUG is off."
        )
    if len(set(secret)) < MIN_UNIQUE_SECRET_CHARS:
        raise ImproperlyConfigured(
            "DJANGO_SECRET_KEY does not have enough unique characters to start with DJANGO_DEBUG off."
        )
    return secret


def csv_setting(name: str, default: str = "") -> list[str]:
    raw = os.getenv(name, default)
    return [item.strip() for item in raw.split(",") if item.strip()]
