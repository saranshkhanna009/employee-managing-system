"""Company schemas."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, ConfigDict
from pydantic.alias_generators import to_camel


class CompanyBase(BaseModel):
    """Base company fields."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    name: str = Field(..., min_length=2, max_length=255)
    slug: str = Field(..., min_length=2, max_length=100, pattern=r"^[a-z0-9-]+$")
    email: EmailStr
    phone: Optional[str] = Field(default=None, max_length=30)
    address: Optional[str] = Field(default=None, max_length=500)


class CompanyCreate(CompanyBase):
    """Create company request (super admin only)."""
    pass


class CompanyUpdate(BaseModel):
    """Update company request."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    name: Optional[str] = Field(default=None, min_length=2, max_length=255)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(default=None, max_length=30)
    address: Optional[str] = Field(default=None, max_length=500)
    subscription_tier: Optional[str] = Field(default=None, max_length=50)
    is_active: Optional[bool] = None


class CompanyResponse(CompanyBase):
    """Company response."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)

    id: UUID
    subscription_tier: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


class CompanyListResponse(BaseModel):
    """Paginated company list response."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    items: list[CompanyResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
