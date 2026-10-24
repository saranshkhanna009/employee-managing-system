"""Authentication schemas."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, ConfigDict
from pydantic.alias_generators import to_camel

from app.models.employee import EmployeeRole, EmployeeStatus


class TokenResponse(BaseModel):
    """Token response (session cookie is set separately)."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    employee_id: str
    role: EmployeeRole
    company_slug: str
    expires_at: datetime


class LoginRequest(BaseModel):
    """Login request."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    employee_id: str = Field(..., min_length=1, max_length=50, description="Admin ID")
    password: str = Field(..., min_length=1, max_length=128, description="Password")
    remember_me: bool = Field(default=False, description="Extend session to 30 days")


class LoginResponse(BaseModel):
    """Login response."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    success: bool = True
    employee: "EmployeeProfile"
    message: Optional[str] = None


class RegisterCompanyRequest(BaseModel):
    """Company registration request."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    company_name: str = Field(..., min_length=2, max_length=255, description="Company name")
    company_slug: str = Field(..., min_length=2, max_length=100, pattern=r"^[a-z0-9-]+$", description="URL-friendly slug")
    admin_email: EmailStr = Field(..., description="Super admin email")
    admin_password: str = Field(..., min_length=12, max_length=128, description="Super admin password")
    admin_first_name: str = Field(..., min_length=1, max_length=100, description="Super admin first name")
    admin_last_name: str = Field(..., min_length=1, max_length=100, description="Super admin last name")
    admin_phone: Optional[str] = Field(default=None, max_length=30, description="Super admin phone")


class RegisterCompanyResponse(BaseModel):
    """Company registration response."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    success: bool = True
    company_slug: str
    admin_employee_id: str
    message: str = "Company registered successfully. Please log in."


class ForgotPasswordRequest(BaseModel):
    """Forgot password request."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    employee_id: str = Field(..., min_length=1, max_length=50)
    email: EmailStr


class ForgotPasswordResponse(BaseModel):
    """Forgot password response."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    success: bool = True
    message: str = "If the account exists, a password reset link has been sent."


class ResetPasswordRequest(BaseModel):
    """Reset password request."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    token: str = Field(..., min_length=1, description="Reset token from email")
    password: str = Field(..., min_length=12, max_length=128)
    confirm_password: str = Field(..., min_length=12, max_length=128)


class ResetPasswordResponse(BaseModel):
    """Reset password response."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    success: bool = True
    message: str = "Password has been reset. Please log in."


class ChangePasswordRequest(BaseModel):
    """Change password request (authenticated)."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    current_password: str = Field(..., min_length=1, max_length=128)
    new_password: str = Field(..., min_length=12, max_length=128)
    confirm_password: str = Field(..., min_length=12, max_length=128)


class ChangePasswordResponse(BaseModel):
    """Change password response."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    success: bool = True
    message: str = "Password changed successfully. Please log in again."


class EmployeeProfile(BaseModel):
    """Employee profile for responses."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)

    id: UUID
    employee_id: str
    email: str
    first_name: str
    last_name: str
    full_name: str
    phone: Optional[str] = None
    role: EmployeeRole
    status: EmployeeStatus
    department_id: Optional[UUID] = None
    department_name: Optional[str] = None
    company_id: UUID
    company_slug: str
    last_login: Optional[datetime] = None
    created_at: datetime


class SessionInfo(BaseModel):
    """Session information."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    id: UUID
    device_fingerprint: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    created_at: datetime
    last_activity: datetime
    expires_at: datetime
    is_current: bool = False


class UpdateProfileRequest(BaseModel):
    """Update profile request."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    first_name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    phone: Optional[str] = Field(default=None, max_length=30)


class ExportDataResponse(BaseModel):
    """Export data response."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    success: bool = True
    data: dict
    exported_at: datetime
