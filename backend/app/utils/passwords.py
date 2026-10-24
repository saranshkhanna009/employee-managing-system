"""Password hashing utilities using Argon2id."""

import argon2
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError

from app.config import settings


# Configure Argon2id hasher
ph = PasswordHasher(
    time_cost=settings.ARGON2_TIME_COST,
    memory_cost=settings.ARGON2_MEMORY_COST,
    parallelism=settings.ARGON2_PARALLELISM,
    hash_len=32,
    salt_len=16,
    type=argon2.Type.ID,
)


def hash_password(password: str) -> bytes:
    """
    Hash a password using Argon2id.

    Args:
        password: Plain text password

    Returns:
        Argon2id hash as bytes
    """
    if not password:
        raise ValueError("Password cannot be empty")
    return ph.hash(password).encode("utf-8")


def verify_password(password: str, password_hash: bytes) -> bool:
    """
    Verify a password against its hash.

    Args:
        password: Plain text password to verify
        password_hash: Stored Argon2id hash

    Returns:
        True if password matches, False otherwise
    """
    if not password or not password_hash:
        return False
    try:
        ph.verify(password_hash.decode("utf-8"), password)
        return True
    except (VerifyMismatchError, VerificationError, UnicodeDecodeError):
        return False


def needs_rehash(password_hash: bytes) -> bool:
    """
    Check if password hash needs rehashing (parameters changed).

    Args:
        password_hash: Current password hash

    Returns:
        True if rehash needed, False otherwise
    """
    try:
        return ph.check_needs_rehash(password_hash.decode("utf-8"))
    except Exception:
        return True


def validate_password_strength(password: str) -> list[str]:
    """
    Validate password meets strength requirements.

    Args:
        password: Password to validate

    Returns:
        List of error messages (empty if valid)
    """
    errors = []

    if len(password) < settings.PASSWORD_MIN_LENGTH:
        errors.append(f"Password must be at least {settings.PASSWORD_MIN_LENGTH} characters")

    if settings.PASSWORD_REQUIRE_UPPER and not any(c.isupper() for c in password):
        errors.append("Password must contain at least one uppercase letter")

    if settings.PASSWORD_REQUIRE_LOWER and not any(c.islower() for c in password):
        errors.append("Password must contain at least one lowercase letter")

    if settings.PASSWORD_REQUIRE_DIGIT and not any(c.isdigit() for c in password):
        errors.append("Password must contain at least one digit")

    if settings.PASSWORD_REQUIRE_SPECIAL and not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
        errors.append("Password must contain at least one special character")

    # Check for common weak patterns
    if password.lower() in ("password", "admin", "employee", "company"):
        errors.append("Password is too common")

    return errors