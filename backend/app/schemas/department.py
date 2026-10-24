"""Department schemas."""

from datetime import datetime
from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict
from pydantic.alias_generators import to_camel


class DepartmentBase(BaseModel):
    """Base department fields."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(default=None, max_length=1000)
    parent_id: Optional[str] = None
    sort_order: int = 0


class DepartmentCreate(DepartmentBase):
    """Create department request."""

    pass


class DepartmentUpdate(BaseModel):
    """Update department request."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = Field(default=None, max_length=1000)
    parent_id: Optional[str] = None
    sort_order: Optional[int] = None


class DepartmentResponse(DepartmentBase):
    """Department response."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)

    id: UUID
    company_id: UUID
    parent_id: Optional[UUID] = None
    full_path: str
    children_count: int = 0
    employees_count: int = 0
    created_at: datetime
    updated_at: datetime


class DepartmentTreeResponse(DepartmentResponse):
    """Department response with nested children."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)

    children: List["DepartmentTreeResponse"] = []


class DepartmentListResponse(BaseModel):
    """Paginated department list response."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    items: List[DepartmentResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
