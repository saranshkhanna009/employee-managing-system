"""Daily task log model."""

import enum
import uuid
from typing import Optional

from sqlalchemy import (
    String, Text, ForeignKey, Enum, Date, DateTime, DECIMAL, Index, func
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, BYTEA
from sqlalchemy.ext.hybrid import hybrid_property

from app.models.base import BaseModel, EncryptionMixin
from app.models.employee import Employee
from app.models.task import Task


class DailyLogStatus(str, enum.Enum):
    """Daily log status."""

    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    BLOCKED = "blocked"
    ON_HOLD = "on_hold"


class DailyLog(BaseModel, EncryptionMixin):
    """Daily task tracking log."""

    __tablename__ = "daily_logs"

    _encrypted_fields = {
        "progress_notes": "notes",
    }

    employee_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("employees.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    task_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("tasks.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    log_date: Mapped[Date] = mapped_column(Date, nullable=False, index=True)
    hours_spent: Mapped[Optional[float]] = mapped_column(DECIMAL(4, 2), nullable=True)
    _progress_notes_encrypted: Mapped[Optional[bytes]] = mapped_column("progress_notes_encrypted", BYTEA, nullable=True)

    status: Mapped[DailyLogStatus] = mapped_column(
        Enum(DailyLogStatus, native_enum=False),
        default=DailyLogStatus.IN_PROGRESS,
        nullable=False,
    )

    # Relationships
    employee: Mapped[Employee] = relationship("Employee", back_populates="daily_logs", lazy="selectin")
    task: Mapped[Optional[Task]] = relationship("Task", back_populates="daily_logs", lazy="selectin")

    # Hybrid property for encrypted notes
    @hybrid_property
    def progress_notes(self) -> Optional[str]:
        return self._decrypt("progress_notes", self._progress_notes_encrypted)

    @progress_notes.setter
    def progress_notes(self, value: Optional[str]) -> None:
        self._progress_notes_encrypted = self._encrypt("progress_notes", value)

    @property
    def employee_name(self) -> str:
        """Return the employee name for response schemas."""
        employee = self.__dict__.get("employee")
        return employee.full_name if employee else ""

    @property
    def task_title(self) -> Optional[str]:
        """Return the related task title for response schemas."""
        task = self.__dict__.get("task")
        return task.title if task else None

    def __repr__(self) -> str:
        return f"<DailyLog(id={self.id}, employee_id={self.employee_id}, date={self.log_date}, hours={self.hours_spent})>"


# Indexes
Index("ix_daily_logs_employee_date", DailyLog.employee_id, DailyLog.log_date, unique=True)
Index("ix_daily_logs_task_date", DailyLog.task_id, DailyLog.log_date)
Index("ix_daily_logs_date_status", DailyLog.log_date, DailyLog.status)
