"""Authentication API routes."""

from datetime import datetime, timezone
from typing import Annotated
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    DBSession,
    AuthSvc,
    EmployeeSvc,
    get_current_session,
    get_current_employee,
    get_current_company,
    RequireAdmin,
    RequireSuperAdmin,
)
from app.api.route import SnakeCaseAPIRoute
from app.schemas.auth import (
    LoginRequest,
    LoginResponse,
    RegisterCompanyRequest,
    RegisterCompanyResponse,
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    ResetPasswordRequest,
    ResetPasswordResponse,
    ChangePasswordRequest,
    ChangePasswordResponse,
    EmployeeProfile,
    SessionInfo,
    TokenResponse,
    UpdateProfileRequest,
    ExportDataResponse,
)
from app.models.employee import Employee, EmployeeRole
from app.models.session import Session
from app.services.auth import AuthError, InvalidCredentialsError, AccountLockedError
from app.config import settings


router = APIRouter(prefix="/auth", tags=["Authentication"], route_class=SnakeCaseAPIRoute)


@router.post("/register", response_model=RegisterCompanyResponse, status_code=status.HTTP_201_CREATED)
async def register_company(
    data: RegisterCompanyRequest,
    db: DBSession,
    auth_service: AuthSvc,
) -> RegisterCompanyResponse:
    """Register a new company with super admin account."""
    try:
        company, admin = await auth_service.register_company(data.model_dump())
        return RegisterCompanyResponse(
            company_slug=company.slug,
            admin_employee_id=admin.employee_id,
        )
    except AuthError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/login", response_model=LoginResponse)
async def login(
    response: Response,
    data: LoginRequest,
    request: Request,
    db: DBSession,
    auth_service: AuthSvc,
) -> LoginResponse:
    """Authenticate employee and create session."""
    try:
        ip = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent")

        employee, session, session_token = await auth_service.authenticate(
            employee_id=data.employee_id,
            password=data.password,
            ip_address=ip,
            user_agent=user_agent,
            remember_me=data.remember_me,
        )

        # Set secure session cookie
        cookie_max_age = settings.SESSION_TTL_SECONDS * (30 * 24 * 60 * 60 // settings.SESSION_TTL_SECONDS) if data.remember_me else settings.SESSION_TTL_SECONDS

        response.set_cookie(
            key=settings.SESSION_COOKIE_NAME,
            value=session_token,
            max_age=cookie_max_age,
            httponly=settings.SESSION_COOKIE_HTTPONLY,
            secure=settings.SESSION_COOKIE_SECURE,
            samesite=settings.SESSION_COOKIE_SAMESITE,
            domain=settings.SESSION_COOKIE_DOMAIN,
            path="/",
        )

        return LoginResponse(
            employee=EmployeeProfile.model_validate(employee, from_attributes=True),
        )
    except InvalidCredentialsError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    except AccountLockedError:
        raise HTTPException(status_code=status.HTTP_423_LOCKED, detail="Account temporarily locked")
    except AuthError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    response: Response,
    session: Annotated[Session, Depends(get_current_session)],
    auth_service: AuthSvc,
    revoke_all: bool = False,
) -> None:
    """Logout and revoke session."""
    await auth_service.logout(session, revoke_all=revoke_all)

    response.delete_cookie(
        key=settings.SESSION_COOKIE_NAME,
        path="/",
        domain=settings.SESSION_COOKIE_DOMAIN,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_session(
    session: Annotated[Session, Depends(get_current_session)],
    auth_service: AuthSvc,
) -> TokenResponse:
    """Refresh session expiry."""
    refreshed = await auth_service.refresh_session(session)
    return TokenResponse(
        employee_id=session.employee.employee_id,
        role=session.employee.role,
        company_slug=session.employee.company.slug,
        expires_at=refreshed.expires_at,
    )


@router.get("/me", response_model=EmployeeProfile)
async def get_profile(
    employee: Annotated[Employee, Depends(get_current_employee)],
) -> EmployeeProfile:
    """Get current employee profile."""
    return EmployeeProfile.model_validate(employee, from_attributes=True)


@router.patch("/me", response_model=EmployeeProfile)
async def update_profile(
    data: UpdateProfileRequest,
    employee: Annotated[Employee, Depends(get_current_employee)],
    auth_service: AuthSvc,
    request: Request,
) -> EmployeeProfile:
    """Update the authenticated employee's profile."""
    ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    updated = await auth_service.update_profile(
        employee=employee,
        first_name=data.first_name,
        last_name=data.last_name,
        phone=data.phone,
        ip_address=ip,
        user_agent=user_agent,
    )
    return EmployeeProfile.model_validate(updated, from_attributes=True)


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def delete_my_account(
    response: Response,
    employee: Annotated[Employee, Depends(get_current_employee)],
    auth_service: AuthSvc,
    request: Request,
) -> None:
    """Permanently delete the authenticated employee account."""
    ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    await auth_service.delete_account(employee, ip_address=ip, user_agent=user_agent)
    response.delete_cookie(
        key=settings.SESSION_COOKIE_NAME,
        path="/",
        domain=settings.SESSION_COOKIE_DOMAIN,
    )


@router.get("/me/export", response_model=ExportDataResponse)
async def export_my_data(
    employee: Annotated[Employee, Depends(get_current_employee)],
    auth_service: AuthSvc,
) -> ExportDataResponse:
    """Export personal data for the authenticated employee."""
    data = await auth_service.export_employee_data(employee)
    return ExportDataResponse(data=data, exported_at=datetime.now(timezone.utc))


@router.get("/sessions", response_model=list[SessionInfo])
async def get_sessions(
    employee: Annotated[Employee, Depends(get_current_employee)],
    auth_service: AuthSvc,
) -> list[SessionInfo]:
    """Get all active sessions for current employee."""
    sessions = await auth_service.get_active_sessions(employee.id)
    current_session_id = None  # Would need to track this

    return [
        SessionInfo(
            id=str(s.id),
            device_fingerprint=s.device_fingerprint,
            ip_address=s.ip_address,
            user_agent=s.user_agent,
            created_at=s.created_at,
            last_activity=s.last_activity,
            expires_at=s.expires_at,
            is_current=s.id == current_session_id,
        )
        for s in sessions
    ]


@router.post("/sessions/{session_id}/revoke", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_session(
    session_id: UUID,
    employee: Annotated[Employee, Depends(get_current_employee)],
    auth_service: AuthSvc,
    request: Request,
) -> None:
    """Revoke one active session belonging to the current employee."""
    ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    revoked = await auth_service.revoke_session(employee, session_id, ip_address=ip, user_agent=user_agent)
    if not revoked:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")


@router.post("/sessions/revoke-all", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_all_sessions(
    employee: Annotated[Employee, Depends(get_current_employee)],
    auth_service: AuthSvc,
    request: Request,
) -> None:
    """Revoke all active sessions for the current employee."""
    ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    await auth_service.revoke_all_sessions(employee, ip_address=ip, user_agent=user_agent)


@router.post("/forgot-password", response_model=ForgotPasswordResponse)
async def forgot_password(
    data: ForgotPasswordRequest,
    db: DBSession,
    auth_service: AuthSvc,
) -> ForgotPasswordResponse:
    """Request password reset (always returns success for security)."""
    # Implementation would send email with reset token
    # For now, just return success
    return ForgotPasswordResponse()


@router.post("/reset-password", response_model=ResetPasswordResponse)
async def reset_password(
    data: ResetPasswordRequest,
    db: DBSession,
    auth_service: AuthSvc,
) -> ResetPasswordResponse:
    """Reset password with token from email."""
    # Implementation would verify token and reset password
    return ResetPasswordResponse()


@router.post("/change-password", response_model=ChangePasswordResponse)
async def change_password(
    response: Response,
    data: ChangePasswordRequest,
    employee: Annotated[Employee, Depends(get_current_employee)],
    auth_service: AuthSvc,
    request: Request,
) -> ChangePasswordResponse:
    """Change password for authenticated employee."""
    try:
        ip = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent")

        await auth_service.change_password(
            employee=employee,
            current_password=data.current_password,
            new_password=data.new_password,
            ip_address=ip,
            user_agent=user_agent,
        )

        # Delete session cookie to force re-login
        response.delete_cookie(
            key=settings.SESSION_COOKIE_NAME,
            path="/",
            domain=settings.SESSION_COOKIE_DOMAIN,
        )

        return ChangePasswordResponse()
    except InvalidCredentialsError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Current password is incorrect")
    except AuthError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/admin/reset-password/{employee_id}", response_model=ChangePasswordResponse)
async def admin_reset_password(
    employee_id: str,
    data: ChangePasswordRequest,
    admin: RequireAdmin,
    auth_service: AuthSvc,
    employee_service: EmployeeSvc,
    request: Request,
) -> ChangePasswordResponse:
    """Admin reset employee password."""
    # Get target employee
    target = await employee_service.get_by_employee_id(employee_id)
    if not target or target.company_id != admin.company_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found")

    try:
        ip = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent")

        await auth_service.admin_reset_password(
            admin=admin,
            target_employee=target,
            new_password=data.new_password,
            ip_address=ip,
            user_agent=user_agent,
        )

        return ChangePasswordResponse(message=f"Password reset for {target.employee_id}")
    except AuthError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
