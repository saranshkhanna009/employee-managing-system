"""Daily log schemas."""

from datetime import date, datetime
from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict
from pydantic.alias_generators import to_camel

from app.models.daily_log import DailyLogStatus


class DailyLogBase(BaseModel):
    """Base daily log fields."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    task_id: Optional[str] = None
    log_date: date
    hours_spent: Optional[float] = Field(default=None, ge=0, le=24)
    progress_notes: Optional[str] = Field(default=None, max_length=5000)
    status: DailyLogStatus = DailyLogStatus.IN_PROGRESS


class DailyLogCreate(DailyLogBase):
    """Create daily log request."""

    pass


class DailyLogUpdate(BaseModel):
    """Update daily log request."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    task_id: Optional[str] = None
    hours_spent: Optional[float] = Field(default=None, ge=0, le=24)
    progress_notes: Optional[str] = Field(default=None, max_length=5000)
    status: Optional[DailyLogStatus] = None


class DailyLogResponse(DailyLogBase):
    """Daily log response."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)

    task_id: Optional[UUID] = None
    id: UUID
    employee_id: UUID
    employee_name: str
    task_title: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class DailyLogListResponse(BaseModel):
    """Paginated daily log list response."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    items: List[DailyLogResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class DailyLogSummary(BaseModel):
    """Daily log summary for an employee over a date range."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    employee_id: UUID
    employee_name: str
    period_start: date
    period_end: date
    total_hours: float
    tasks_count: int
    completed_tasks: int
    in_progress_tasks: int
    logs_count: int


class EmployeeDailySummary(BaseModel):
    """Daily log summary for one employee in a department report."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    employee_id: UUID
    employee_name: str
    hours_spent: float
    tasks_count: int


class DepartmentDailySummary(BaseModel):
    """Department daily summary for managers."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    date: date
    department_id: str
    department_name: str
    total_employees: int
    active_employees: int
    total_hours: float
    tasks_completed: int
    tasks_in_progress: int
    employee_summaries: List[EmployeeDailySummary]
