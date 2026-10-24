"""Department model."""

import uuid
from typing import TYPE_CHECKING, Optional, List

from sqlalchemy import String, Text, ForeignKey, Index, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from app.models.base import BaseModel
from app.models.company import Company

if TYPE_CHECKING:
    from app.models.employee import Employee
    from app.models.task import Task


class Department(BaseModel):
    """Department model with hierarchical structure."""

    __tablename__ = "departments"

    company_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    parent_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("departments.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Relationships
    company: Mapped[Company] = relationship("Company", back_populates="departments", lazy="selectin")
    parent: Mapped[Optional["Department"]] = relationship(
        "Department",
        remote_side="Department.id",
        back_populates="children",
        lazy="selectin",
    )
    children: Mapped[List["Department"]] = relationship(
        "Department",
        back_populates="parent",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    employees: Mapped[List["Employee"]] = relationship(
        "Employee",
        back_populates="department",
        lazy="selectin",
    )
    tasks: Mapped[List["Task"]] = relationship(
        "Task",
        back_populates="department",
        lazy="dynamic",
    )

    def __repr__(self) -> str:
        return f"<Department(id={self.id}, name={self.name}, company_id={self.company_id})>"

    def get_full_path(self) -> str:
        """Get full department path (e.g., 'Engineering > Backend > API')."""
        path = [self.name]
        current = self.parent
        while current:
            path.insert(0, current.name)
            current = current.parent
        return " > ".join(path)

    @property
    def full_path(self) -> str:
        """Expose the department path expected by response schemas."""
        return self.get_full_path()


# Indexes
Index("ix_departments_company_parent", Department.company_id, Department.parent_id)
Index("ix_departments_company_sort", Department.company_id, Department.sort_order)
