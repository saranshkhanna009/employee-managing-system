"""Session model for authentication."""

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (
    String, Text, ForeignKey, DateTime, Index, func
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, BYTEA, INET
from sqlalchemy.ext.hybrid import hybrid_property

from app.models.base import BaseModel
from app.models.employee import Employee
from app.services.encryption import get_encryption_service
import hashlib
import secrets


class Session(BaseModel):
    """Session model for tracking active sessions."""

    __tablename__ = "sessions"

    employee_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("employees.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Store hash of session token (not the token itself)
    _session_token_hash: Mapped[bytes] = mapped_column("session_token_hash", BYTEA, nullable=False)

    # Session metadata
    ip_address: Mapped[Optional[str]] = mapped_column(INET, nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    device_fingerprint: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)

    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_activity: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    employee: Mapped[Employee] = relationship("Employee", back_populates="sessions", lazy="selectin")

    @hybrid_property
    def session_token_hash(self) -> bytes:
        return self._session_token_hash

    @session_token_hash.setter
    def session_token_hash(self, token: str) -> None:
        """Hash and store session token."""
        self._session_token_hash = hashlib.sha256(token.encode()).digest()

    def verify_token(self, token: str) -> bool:
        """Verify a session token against stored hash."""
        token_hash = hashlib.sha256(token.encode()).digest()
        return secrets.compare_digest(token_hash, self._session_token_hash)

    def generate_token(self) -> str:
        """Generate a new secure session token and store its hash."""
        token = secrets.token_urlsafe(32)
        self.session_token_hash = token
        return token

    def is_expired(self) -> bool:
        """Check if session is expired."""
        from datetime import datetime, timezone
        return datetime.now(timezone.utc) >= self.expires_at

    def is_revoked(self) -> bool:
        """Check if session is revoked."""
        return self.revoked_at is not None

    def is_valid(self) -> bool:
        """Check if session is valid (not expired, not revoked)."""
        return not self.is_expired() and not self.is_revoked()

    def revoke(self) -> None:
        """Revoke the session."""
        from datetime import datetime, timezone
        self.revoked_at = datetime.now(timezone.utc)

    def extend(self, ttl_seconds: int) -> None:
        """Extend session expiry."""
        from datetime import datetime, timezone, timedelta
        self.expires_at = datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)

    def update_activity(self) -> None:
        """Update last activity timestamp."""
        from datetime import datetime, timezone
        self.last_activity = datetime.now(timezone.utc)

    def __repr__(self) -> str:
        return f"<Session(id={self.id}, employee_id={self.employee_id}, expires={self.expires_at})>"


# Indexes
Index("ix_sessions_employee_expires", Session.employee_id, Session.expires_at)
Index("ix_sessions_device_active", Session.device_fingerprint, Session.revoked_at)
Index("ix_sessions_cleanup", Session.expires_at, Session.revoked_at)

