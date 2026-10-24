"""Base model classes and encryption mixin."""

import uuid
from datetime import datetime, timezone
from typing import Any, Optional, TypeVar

from sqlalchemy import DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, declared_attr
from sqlalchemy.ext.hybrid import hybrid_property

from app.database import Base
from app.services.encryption import get_encryption_service


class TimestampMixin:
    """Mixin for created_at and updated_at timestamps."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class UUIDMixin:
    """Mixin for UUID primary key."""

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )


class EncryptionMixin:
    """
    Mixin for transparent field-level encryption.

    Usage:
        class MyModel(Base, EncryptionMixin):
            _encrypted_fields = {
                "email": "email",
                "phone": "phone",
                "first_name": "name",
                "last_name": "name",
            }

            _email_encrypted: Mapped[bytes] = mapped_column("email_encrypted", LargeBinary, nullable=False)
            _phone_encrypted: Mapped[Optional[bytes]] = mapped_column("phone_encrypted", LargeBinary, nullable=True)

            @hybrid_property
            def email(self) -> str:
                return self._decrypt("email", self._email_encrypted)

            @email.setter
            def email(self, value: str) -> None:
                self._email_encrypted = self._encrypt("email", value)
    """

    _encrypted_fields: dict[str, str] = {}  # property_name -> field_type

    def _encrypt(self, field_name: str, value: Optional[str]) -> Optional[bytes]:
        """Encrypt a field value."""
        if value is None or value == "":
            return None
        field_type = self._encrypted_fields.get(field_name, "default")
        return get_encryption_service().encrypt(value, field_type)

    def _decrypt(self, field_name: str, encrypted_value: Optional[bytes]) -> Optional[str]:
        """Decrypt a field value."""
        if encrypted_value is None or encrypted_value == b"":
            return None
        field_type = self._encrypted_fields.get(field_name, "default")
        try:
            return get_encryption_service().decrypt(encrypted_value, field_type)
        except Exception:
            # Return placeholder for corrupted data
            return "[DECRYPTION_FAILED]"

    def _encrypt_bytes(self, field_name: str, value: Optional[bytes]) -> Optional[bytes]:
        """Encrypt bytes value."""
        if value is None or value == b"":
            return None
        field_type = self._encrypted_fields.get(field_name, "default")
        return get_encryption_service().encrypt_bytes(value, field_type)

    def _decrypt_bytes(self, field_name: str, encrypted_value: Optional[bytes]) -> Optional[bytes]:
        """Decrypt bytes value."""
        if encrypted_value is None or encrypted_value == b"":
            return None
        field_type = self._encrypted_fields.get(field_name, "default")
        try:
            return get_encryption_service().decrypt_bytes(encrypted_value, field_type)
        except Exception:
            return b"[DECRYPTION_FAILED]"


class BaseModel(Base, UUIDMixin, TimestampMixin):
    """Base model with UUID and timestamps."""

    __abstract__ = True

    @declared_attr.directive
    def __tablename__(cls) -> str:
        return cls.__name__.lower() + "s"


# Type variable for generic repositories
ModelType = TypeVar("ModelType", bound=BaseModel)