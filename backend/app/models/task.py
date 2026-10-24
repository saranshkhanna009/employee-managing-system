"""Task model."""

import enum
import uuid
from datetime import datetime
from typing import Optional, List

from sqlalchemy import (
    String, Text, ForeignKey, Enum, Date, DateTime, Index, Integer, DECIMAL, func
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, BYTEA
from sqlalchemy.ext.hybrid import hybrid_property

from app.models.base import BaseModel, EncryptionMixin
from app.models.company import Company
from app.models.department import Department
from app.models.employee import Employee, EmployeeRole


class TaskStatus(str, enum.Enum):
    """Task status."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    IN_REVIEW = "in_review"
    COMPLETED = "completed"
    BLOCKED = "blocked"
    CANCELLED = "cancelled"


class TaskPriority(str, enum.Enum):
    """Task priority."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class Task(BaseModel, EncryptionMixin):
    """Task model with encrypted description."""

    __tablename__ = "tasks"

    _encrypted_fields = {
        "description": "description",
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
    assigned_to_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("employees.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    created_by_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("employees.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    _description_encrypted: Mapped[Optional[bytes]] = mapped_column("description_encrypted", BYTEA, nullable=True)

    status: Mapped[TaskStatus] = mapped_column(
        Enum(TaskStatus, native_enum=False),
        default=TaskStatus.PENDING,
        nullable=False,
        index=True,
    )
    priority: Mapped[TaskPriority] = mapped_column(
        Enum(TaskPriority, native_enum=False),
        default=TaskPriority.MEDIUM,
        nullable=False,
    )
    due_date: Mapped[Optional[Date]] = mapped_column(Date, nullable=True, index=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    estimated_hours: Mapped[Optional[float]] = mapped_column(DECIMAL(5, 2), nullable=True)
    actual_hours: Mapped[Optional[float]] = mapped_column(DECIMAL(5, 2), nullable=True, default=0)

    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Relationships
    company: Mapped[Company] = relationship("Company", back_populates="tasks", lazy="selectin")
    department: Mapped[Optional[Department]] = relationship("Department", back_populates="tasks", lazy="selectin")
    assignee: Mapped[Optional[Employee]] = relationship(
        "Employee",
        foreign_keys=[assigned_to_id],
        back_populates="assigned_tasks",
        lazy="selectin",
    )
    creator: Mapped[Employee] = relationship(
        "Employee",
        foreign_keys=[created_by_id],
        back_populates="created_tasks",
        lazy="selectin",
    )
    daily_logs: Mapped[List["DailyLog"]] = relationship(
        "DailyLog",
        back_populates="task",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )

    # Hybrid property for encrypted description
    @hybrid_property
    def description(self) -> Optional[str]:
        return self._decrypt("description", self._description_encrypted)

    @description.setter
    def description(self, value: Optional[str]) -> None:
        self._description_encrypted = self._encrypt("description", value)

    @property
    def is_overdue(self) -> bool:
        """Check if task is overdue."""
        if self.due_date and self.status not in (TaskStatus.COMPLETED, TaskStatus.CANCELLED):
            from datetime import date
            return date.today() > self.due_date
        return False

    @property
    def assigned_to_name(self) -> Optional[str]:
        """Return the assignee name for response schemas."""
        assignee = self.__dict__.get("assignee")
        return assignee.full_name if assignee else None

    @property
    def created_by_name(self) -> str:
        """Return the creator name for response schemas."""
        creator = self.__dict__.get("creator")
        return creator.full_name if creator else ""

    @property
    def department_name(self) -> Optional[str]:
        """Return the department name for response schemas."""
        department = self.__dict__.get("department")
        return department.name if department else None

    def can_be_modified_by(self, employee: Employee) -> bool:
        """Check if employee can modify this task."""
        # Creator can always modify
        if self.created_by_id == employee.id:
            return True
        # Assignee can update status and add logs
        if self.assigned_to_id == employee.id:
            return True
        # Managers/Admins of the department can modify
        if employee.is_manager_or_above():
            if employee.role == EmployeeRole.SUPER_ADMIN:
                return True
            if employee.role == EmployeeRole.ADMIN:
                return employee.company_id == self.company_id
            if employee.role == EmployeeRole.MANAGER:
                return (
                    employee.company_id == self.company_id
                    and employee.department_id == self.department_id
                )
        return False

    def __repr__(self) -> str:
        return f"<Task(id={self.id}, title={self.title}, status={self.status})>"


# Indexes
Index("ix_tasks_company_dept_status", Task.company_id, Task.department_id, Task.status)
Index("ix_tasks_assignee_status", Task.assigned_to_id, Task.status)
Index("ix_tasks_due_date_status", Task.due_date, Task.status)
Index("ix_tasks_created_by", Task.created_by_id)


# Import at the end to avoid circular imports
from app.models.daily_log import DailyLog
