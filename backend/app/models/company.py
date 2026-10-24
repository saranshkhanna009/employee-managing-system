"""Company model."""

from typing import TYPE_CHECKING, Optional

from sqlalchemy import String, Text, Boolean, Index
from sqlalchemy.dialects.postgresql import BYTEA
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.ext.hybrid import hybrid_property

from app.models.base import BaseModel, EncryptionMixin

if TYPE_CHECKING:
    from app.models.department import Department
    from app.models.employee import Employee
    from app.models.task import Task


class Company(BaseModel, EncryptionMixin):
    """Company/Organization model."""

    __tablename__ = "companies"

    # Encrypted fields configuration
    _encrypted_fields = {
        "email": "email",
        "phone": "phone",
        "address": "address",
    }

    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)

    # Encrypted PII
    _email_encrypted: Mapped[bytes] = mapped_column("email_encrypted", BYTEA, nullable=False)
    _phone_encrypted: Mapped[Optional[bytes]] = mapped_column("phone_encrypted", BYTEA, nullable=True)
    _address_encrypted: Mapped[Optional[bytes]] = mapped_column("address_encrypted", BYTEA, nullable=True)

    subscription_tier: Mapped[str] = mapped_column(String(50), default="free", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    departments: Mapped[list["Department"]] = relationship(
        "Department",
        back_populates="company",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )
    employees: Mapped[list["Employee"]] = relationship(
        "Employee",
        back_populates="company",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )
    tasks: Mapped[list["Task"]] = relationship(
        "Task",
        back_populates="company",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )

    # Hybrid properties for encrypted fields
    @hybrid_property
    def email(self) -> str:
        return self._decrypt("email", self._email_encrypted) or ""

    @email.setter
    def email(self, value: str) -> None:
        self._email_encrypted = self._encrypt("email", value)

    @hybrid_property
    def phone(self) -> Optional[str]:
        return self._decrypt("phone", self._phone_encrypted)

    @phone.setter
    def phone(self, value: Optional[str]) -> None:
        self._phone_encrypted = self._encrypt("phone", value)

    @hybrid_property
    def address(self) -> Optional[str]:
        return self._decrypt("address", self._address_encrypted)

    @address.setter
    def address(self, value: Optional[str]) -> None:
        self._address_encrypted = self._encrypt("address", value)

    def __repr__(self) -> str:
        return f"<Company(id={self.id}, name={self.name}, slug={self.slug})>"


# Indexes
Index("ix_companies_slug_active", Company.slug, Company.is_active)
Index("ix_companies_name_active", Company.name, Company.is_active)
