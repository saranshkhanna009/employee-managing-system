"""Employee model with authentication and encrypted PII."""

import enum
import uuid
from datetime import datetime
from typing import Optional, List

from sqlalchemy import (
    String, Text, Boolean, ForeignKey, Enum, Integer, DateTime, Index, func
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, BYTEA, INET
from sqlalchemy.ext.hybrid import hybrid_property

from app.models.base import BaseModel, EncryptionMixin
from app.models.company import Company
from app.models.department import Department
from app.services.encryption import get_encryption_service
from app.utils.passwords import hash_password, verify_password


class EmployeeRole(str, enum.Enum):
    """Employee roles with increasing permissions."""

    EMPLOYEE = "employee"
    MANAGER = "manager"
    ADMIN = "admin"
    SUPER_ADMIN = "super_admin"


class EmployeeStatus(str, enum.Enum):
    """Employee status."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    LOCKED = "locked"
    PENDING = "pending"


class Employee(BaseModel, EncryptionMixin):
    """Employee model with encrypted PII and authentication."""

    __tablename__ = "employees"

    # Encrypted fields configuration
    _encrypted_fields = {
        "email": "email",
        "first_name": "name",
        "last_name": "name",
        "phone": "phone",
    }

    company_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    department_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("departments.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Admin ID - human readable, not encrypted (used for login)
    employee_id: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
    )

    # Encrypted PII
    _email_encrypted: Mapped[bytes] = mapped_column("email_encrypted", BYTEA, nullable=False)
    _password_hash: Mapped[bytes] = mapped_column("password_hash", BYTEA, nullable=False)
    _first_name_encrypted: Mapped[bytes] = mapped_column("first_name_encrypted", BYTEA, nullable=False)
    _last_name_encrypted: Mapped[bytes] = mapped_column("last_name_encrypted", BYTEA, nullable=False)
    _phone_encrypted: Mapped[Optional[bytes]] = mapped_column("phone_encrypted", BYTEA, nullable=True)

    role: Mapped[EmployeeRole] = mapped_column(
        Enum(EmployeeRole, native_enum=False),
        default=EmployeeRole.EMPLOYEE,
        nullable=False,
    )
    status: Mapped[EmployeeStatus] = mapped_column(
        Enum(EmployeeStatus, native_enum=False),
        default=EmployeeStatus.ACTIVE,
        nullable=False,
    )

    # Security fields
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    failed_login_attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    locked_until: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    company: Mapped[Company] = relationship("Company", back_populates="employees", lazy="selectin")
    department: Mapped[Optional[Department]] = relationship(
        "Department",
        back_populates="employees",
        lazy="selectin",
    )
    assigned_tasks: Mapped[List["Task"]] = relationship(
        "Task",
        foreign_keys="Task.assigned_to_id",
        back_populates="assignee",
        lazy="dynamic",
    )
    created_tasks: Mapped[List["Task"]] = relationship(
        "Task",
        foreign_keys="Task.created_by_id",
        back_populates="creator",
        lazy="dynamic",
    )
    daily_logs: Mapped[List["DailyLog"]] = relationship(
        "DailyLog",
        back_populates="employee",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )
    leave_requests: Mapped[List["LeaveRequest"]] = relationship(
        "LeaveRequest",
        foreign_keys="LeaveRequest.employee_id",
        back_populates="employee",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )
    reviewed_leaves: Mapped[List["LeaveRequest"]] = relationship(
        "LeaveRequest",
        foreign_keys="LeaveRequest.reviewed_by_id",
        back_populates="reviewer",
        lazy="dynamic",
    )
    sessions: Mapped[List["Session"]] = relationship(
        "Session",
        back_populates="employee",
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
    def first_name(self) -> str:
        return self._decrypt("first_name", self._first_name_encrypted) or ""

    @first_name.setter
    def first_name(self, value: str) -> None:
        self._first_name_encrypted = self._encrypt("first_name", value)

    @hybrid_property
    def last_name(self) -> str:
        return self._decrypt("last_name", self._last_name_encrypted) or ""

    @last_name.setter
    def last_name(self, value: str) -> None:
        self._last_name_encrypted = self._encrypt("last_name", value)

    @hybrid_property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()

    @hybrid_property
    def phone(self) -> Optional[str]:
        return self._decrypt("phone", self._phone_encrypted)

    @phone.setter
    def phone(self, value: Optional[str]) -> None:
        self._phone_encrypted = self._encrypt("phone", value)

    @property
    def company_slug(self) -> str:
        """Return the related company's slug for response schemas."""
        company = self.__dict__.get("company")
        return company.slug if company else ""

    @property
    def department_name(self) -> Optional[str]:
        """Return the related department name for response schemas."""
        department = self.__dict__.get("department")
        return department.name if department else None

    # Password methods (not using hybrid_property for security)
    def set_password(self, password: str) -> None:
        """Hash and set password."""
        self._password_hash = hash_password(password)

    def check_password(self, password: str) -> bool:
        """Verify password against hash."""
        return verify_password(password, self._password_hash)

    def get_decrypted_data(self) -> dict:
        """Get all decrypted PII data (for authorized access only)."""
        return {
            "email": self.email,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "full_name": self.full_name,
            "phone": self.phone,
        }

    def is_admin_or_above(self) -> bool:
        """Check if employee has admin or super_admin role."""
        return self.role in (EmployeeRole.ADMIN, EmployeeRole.SUPER_ADMIN)

    def is_manager_or_above(self) -> bool:
        """Check if employee has manager, admin, or super_admin role."""
        return self.role in (EmployeeRole.MANAGER, EmployeeRole.ADMIN, EmployeeRole.SUPER_ADMIN)

    def can_manage(self, other: "Employee") -> bool:
        """Check if this employee can manage another employee."""
        if self.role == EmployeeRole.SUPER_ADMIN:
            return True
        if self.role == EmployeeRole.ADMIN:
            return other.company_id == self.company_id
        if self.role == EmployeeRole.MANAGER:
            return (
                other.company_id == self.company_id
                and other.department_id == self.department_id
                and other.role == EmployeeRole.EMPLOYEE
            )
        return False

    def __repr__(self) -> str:
        return f"<Employee(id={self.id}, employee_id={self.employee_id}, role={self.role})>"


# Indexes
Index("ix_employees_company_dept", Employee.company_id, Employee.department_id)
Index("ix_employees_company_role", Employee.company_id, Employee.role)
Index("ix_employees_email_company", Employee._email_encrypted, Employee.company_id)  # For login lookup
Index("ix_employees_status_active", Employee.status)


# Import at the end to avoid circular imports
from app.models.task import Task
from app.models.daily_log import DailyLog
from app.models.leave import LeaveRequest
from app.models.session import Session
