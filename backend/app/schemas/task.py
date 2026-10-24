"""Task schemas."""

from datetime import date, datetime
from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict
from pydantic.alias_generators import to_camel

from app.models.task import TaskStatus, TaskPriority


class TaskBase(BaseModel):
    """Base task fields."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(default=None, max_length=5000)
    department_id: Optional[str] = None
    priority: TaskPriority = TaskPriority.MEDIUM
    due_date: Optional[date] = None
    estimated_hours: Optional[float] = Field(default=None, ge=0, le=999.99)
    sort_order: int = 0


class TaskCreate(TaskBase):
    """Create task request."""

    assigned_to_id: Optional[str] = None


class TaskUpdate(BaseModel):
    """Update task request."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    title: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = Field(default=None, max_length=5000)
    department_id: Optional[str] = None
    priority: Optional[TaskPriority] = None
    due_date: Optional[date] = None
    estimated_hours: Optional[float] = Field(default=None, ge=0, le=999.99)
    sort_order: Optional[int] = None


class TaskAssign(BaseModel):
    """Assign task request."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    assigned_to_id: str = Field(..., min_length=1)


class TaskStatusUpdate(BaseModel):
    """Update task status request."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    status: TaskStatus


class TaskResponse(TaskBase):
    """Task response."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)

    id: UUID
    company_id: UUID
    department_id: Optional[UUID] = None
    assigned_to_id: Optional[UUID] = None
    assigned_to_name: Optional[str] = None
    created_by_id: UUID
    created_by_name: str
    status: TaskStatus
    actual_hours: float = 0.0
    completed_at: Optional[datetime] = None
    is_overdue: bool = False
    department_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class TaskListResponse(BaseModel):
    """Paginated task list response."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    items: List[TaskResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class TaskSummary(BaseModel):
    """Lightweight task summary."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)

    id: UUID
    title: str
    status: TaskStatus
    priority: TaskPriority
    due_date: Optional[date] = None
    assigned_to_name: Optional[str] = None
    department_name: Optional[str] = None
    is_overdue: bool = False
