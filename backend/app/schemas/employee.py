"""Employee schemas."""

from datetime import datetime
from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, ConfigDict, field_validator
from pydantic.alias_generators import to_camel

from app.models.employee import EmployeeRole, EmployeeStatus


class EmployeeBase(BaseModel):
    """Base employee fields."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    email: EmailStr
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    phone: Optional[str] = Field(default=None, max_length=30)
    department_id: Optional[str] = None
    role: EmployeeRole = EmployeeRole.EMPLOYEE


class EmployeeCreate(EmployeeBase):
    """Create employee request."""

    password: str = Field(..., min_length=12, max_length=128)
    confirm_password: str = Field(..., min_length=12, max_length=128)

    @field_validator("confirm_password")
    @classmethod
    def passwords_match(cls, v: str, info) -> str:
        if "password" in info.data and v != info.data["password"]:
            raise ValueError("Passwords do not match")
        return v


class EmployeeUpdate(BaseModel):
    """Update employee request."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    email: Optional[EmailStr] = None
    first_name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    phone: Optional[str] = Field(default=None, max_length=30)
    department_id: Optional[str] = None
    role: Optional[EmployeeRole] = None
    status: Optional[EmployeeStatus] = None


class EmployeePasswordReset(BaseModel):
    """Admin password reset for employee."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    password: str = Field(..., min_length=12, max_length=128)
    confirm_password: str = Field(..., min_length=12, max_length=128)

    @field_validator("confirm_password")
    @classmethod
    def passwords_match(cls, v: str, info) -> str:
        if "password" in info.data and v != info.data["password"]:
            raise ValueError("Passwords do not match")
        return v


class EmployeeResponse(EmployeeBase):
    """Employee response with all fields."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)

    id: UUID
    employee_id: str
    full_name: str
    status: EmployeeStatus
    company_id: UUID
    department_id: Optional[UUID] = None
    company_slug: str
    department_name: Optional[str] = None
    last_login: Optional[datetime] = None
    failed_login_attempts: int = 0
    locked_until: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class EmployeeListResponse(BaseModel):
    """Paginated employee list response."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    items: List[EmployeeResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class EmployeeSummary(BaseModel):
    """Lightweight employee summary for dropdowns/references."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)

    id: UUID
    employee_id: str
    full_name: str
    email: str
    role: EmployeeRole
    department_id: Optional[UUID] = None
    department_name: Optional[str] = None


class TeamMemberResponse(EmployeeResponse):
    """Team member response with additional fields."""
    task_count: int = 0


class TeamListResponse(BaseModel):
    """Paginated team list response."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    items: List[TeamMemberResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class TeamSummaryResponse(BaseModel):
    """Team summary statistics."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    total_members: int
    total_tasks: int
    completed_this_week: int
    hours_today: float
