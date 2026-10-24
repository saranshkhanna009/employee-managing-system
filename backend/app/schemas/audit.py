"""Audit log schemas."""

from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict
from pydantic.alias_generators import to_camel


class AuditLogResponse(BaseModel):
    """Audit log response."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)

    id: UUID
    company_id: Optional[UUID] = None
    employee_id: Optional[UUID] = None
    employee_name: Optional[str] = None
    action: str
    resource_type: Optional[str] = None
    resource_id: Optional[UUID] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict, validation_alias="metadata_")
    previous_hash: Optional[str] = None
    current_hash: str
    created_at: datetime


class AuditLogListResponse(BaseModel):
    """Paginated audit log list response."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    items: List[AuditLogResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class AuditLogQuery(BaseModel):
    """Audit log query parameters."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    company_id: Optional[str] = None
    employee_id: Optional[str] = None
    action: Optional[str] = None
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, ge=1, le=200)
