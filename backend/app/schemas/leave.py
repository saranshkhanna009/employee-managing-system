"""Leave request schemas."""

from datetime import date, datetime
from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict, field_validator
from pydantic.alias_generators import to_camel

from app.models.leave import LeaveType, LeaveStatus


class LeaveRequestBase(BaseModel):
    """Base leave request fields."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    leave_type: LeaveType
    start_date: date
    end_date: date
    reason: Optional[str] = Field(default=None, max_length=2000)

    @field_validator("end_date")
    @classmethod
    def end_after_start(cls, v: date, info) -> date:
        if "start_date" in info.data and v < info.data["start_date"]:
            raise ValueError("End date must be after or equal to start date")
        return v


class LeaveRequestCreate(LeaveRequestBase):
    """Create leave request."""

    pass


class LeaveRequestUpdate(BaseModel):
    """Update leave request (employee can cancel, manager can approve/reject)."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    leave_type: Optional[LeaveType] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    reason: Optional[str] = Field(default=None, max_length=2000)
    status: Optional[LeaveStatus] = None
    review_notes: Optional[str] = Field(default=None, max_length=1000)


class LeaveRequestReview(BaseModel):
    """Review leave request (approve/reject)."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    status: LeaveStatus = Field(..., description="Must be 'approved' or 'rejected'")
    review_notes: Optional[str] = Field(default=None, max_length=1000)


class LeaveRequestResponse(LeaveRequestBase):
    """Leave request response."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)

    id: UUID
    employee_id: UUID
    employee_name: str
    employee_email: str
    department_name: Optional[str] = None
    status: LeaveStatus
    duration_days: int
    reviewed_by_id: Optional[UUID] = None
    reviewed_by_name: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    review_notes: Optional[str] = None
    is_active: bool = False
    is_upcoming: bool = False
    is_past: bool = False
    created_at: datetime
    updated_at: datetime


class LeaveRequestListResponse(BaseModel):
    """Paginated leave request list response."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    items: List[LeaveRequestResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class LeaveBalance(BaseModel):
    """Leave balance for an employee."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    leave_type: LeaveType
    allocated: int
    used: int
    pending: int
    remaining: int


class LeaveBalanceResponse(BaseModel):
    """Leave balance response."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    employee_id: str
    employee_name: str
    balances: List[LeaveBalance]
    year: int
