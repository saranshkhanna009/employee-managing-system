"""Leave request model."""

import enum
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    String, Text, ForeignKey, Enum, Date, DateTime, Index, func
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, BYTEA
from sqlalchemy.ext.hybrid import hybrid_property

from app.models.base import BaseModel, EncryptionMixin
from app.models.employee import Employee


class LeaveType(str, enum.Enum):
    """Types of leave."""

    SICK = "sick"
    VACATION = "vacation"
    PERSONAL = "personal"
    EMERGENCY = "emergency"
    MATERNITY = "maternity"
    PATERNITY = "paternity"
    BEREAVEMENT = "bereavement"
    UNPAID = "unpaid"
    OTHER = "other"


class LeaveStatus(str, enum.Enum):
    """Leave request status."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class LeaveRequest(BaseModel, EncryptionMixin):
    """Leave request model with encrypted reason and review notes."""

    __tablename__ = "leave_requests"

    _encrypted_fields = {
        "reason": "reason",
        "review_notes": "notes",
    }

    employee_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("employees.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    leave_type: Mapped[LeaveType] = mapped_column(
        Enum(LeaveType, native_enum=False),
        nullable=False,
        index=True,
    )
    start_date: Mapped[Date] = mapped_column(Date, nullable=False, index=True)
    end_date: Mapped[Date] = mapped_column(Date, nullable=False, index=True)

    _reason_encrypted: Mapped[Optional[bytes]] = mapped_column("reason_encrypted", BYTEA, nullable=True)

    status: Mapped[LeaveStatus] = mapped_column(
        Enum(LeaveStatus, native_enum=False),
        default=LeaveStatus.PENDING,
        nullable=False,
        index=True,
    )

    reviewed_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("employees.id", ondelete="SET NULL"),
        nullable=True,
    )
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    _review_notes_encrypted: Mapped[Optional[bytes]] = mapped_column("review_notes_encrypted", BYTEA, nullable=True)

    # Relationships
    employee: Mapped[Employee] = relationship(
        "Employee",
        foreign_keys=[employee_id],
        back_populates="leave_requests",
        lazy="selectin",
    )
    reviewer: Mapped[Optional[Employee]] = relationship(
        "Employee",
        foreign_keys=[reviewed_by_id],
        back_populates="reviewed_leaves",
        lazy="selectin",
    )

    # Hybrid properties for encrypted fields
    @hybrid_property
    def reason(self) -> Optional[str]:
        return self._decrypt("reason", self._reason_encrypted)

    @reason.setter
    def reason(self, value: Optional[str]) -> None:
        self._reason_encrypted = self._encrypt("reason", value)

    @hybrid_property
    def review_notes(self) -> Optional[str]:
        return self._decrypt("review_notes", self._review_notes_encrypted)

    @review_notes.setter
    def review_notes(self, value: Optional[str]) -> None:
        self._review_notes_encrypted = self._encrypt("review_notes", value)

    @property
    def employee_name(self) -> str:
        """Return the employee name for response schemas."""
        employee = self.__dict__.get("employee")
        return employee.full_name if employee else ""

    @property
    def employee_email(self) -> str:
        """Return the employee email for response schemas."""
        employee = self.__dict__.get("employee")
        return employee.email if employee else ""

    @property
    def department_name(self) -> Optional[str]:
        """Return the employee's department name for response schemas."""
        employee = self.__dict__.get("employee")
        department = employee.__dict__.get("department") if employee else None
        return department.name if department else None

    @property
    def reviewed_by_name(self) -> Optional[str]:
        """Return the reviewer name for response schemas."""
        reviewer = self.__dict__.get("reviewer")
        return reviewer.full_name if reviewer else None

    @property
    def duration_days(self) -> int:
        """Calculate leave duration in days (inclusive)."""
        return (self.end_date - self.start_date).days + 1

    @property
    def is_active(self) -> bool:
        """Check if leave is currently active."""
        from datetime import date
        today = date.today()
        return (
            self.status == LeaveStatus.APPROVED
            and self.start_date <= today <= self.end_date
        )

    @property
    def is_upcoming(self) -> bool:
        """Check if leave is upcoming."""
        from datetime import date
        return self.status == LeaveStatus.APPROVED and self.start_date > date.today()

    @property
    def is_past(self) -> bool:
        """Check if leave is in the past."""
        from datetime import date
        return self.end_date < date.today()

    def can_be_reviewed_by(self, employee: Employee) -> bool:
        """Check if employee can review this leave request."""
        # Employee can cancel their own pending request
        if self.employee_id == employee.id and self.status == LeaveStatus.PENDING:
            return True
        # Managers/Admins can approve/reject
        if employee.is_manager_or_above():
            if employee.role == EmployeeRole.SUPER_ADMIN:
                return True
            if employee.role == EmployeeRole.ADMIN:
                return employee.company_id == self.employee.company_id
            if employee.role == EmployeeRole.MANAGER:
                return (
                    employee.company_id == self.employee.company_id
                    and employee.department_id == self.employee.department_id
                )
        return False

    def __repr__(self) -> str:
        return f"<LeaveRequest(id={self.id}, employee_id={self.employee_id}, type={self.leave_type}, status={self.status})>"


# Indexes
Index("ix_leave_requests_employee_status", LeaveRequest.employee_id, LeaveRequest.status)
Index("ix_leave_requests_dates", LeaveRequest.start_date, LeaveRequest.end_date)
Index("ix_leave_requests_company_status", LeaveRequest.employee_id, LeaveRequest.status)  # Via employee join


# Import at the end to avoid circular imports
from app.models.employee import EmployeeRole
