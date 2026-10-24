"""API dependencies."""

from typing import Optional, Annotated
from uuid import UUID

from fastapi import Depends, Header, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.config import settings
from app.services.auth import AuthService, get_auth_service
from app.services.company import CompanyService, get_company_service
from app.services.department import DepartmentService, get_department_service
from app.services.employee import EmployeeService, get_employee_service
from app.services.task import TaskService, get_task_service
from app.services.daily_log import DailyLogService, get_daily_log_service
from app.services.leave import LeaveService, get_leave_service
from app.services.audit import AuditService, get_audit_service
from app.models.employee import Employee, EmployeeRole
from app.models.session import Session


# Type aliases for dependency injection
DBSession = Annotated[AsyncSession, Depends(get_db)]
AuthSvc = Annotated[AuthService, Depends(get_auth_service)]
CompanySvc = Annotated[CompanyService, Depends(get_company_service)]
DepartmentSvc = Annotated[DepartmentService, Depends(get_department_service)]
EmployeeSvc = Annotated[EmployeeService, Depends(get_employee_service)]
TaskSvc = Annotated[TaskService, Depends(get_task_service)]
DailyLogSvc = Annotated[DailyLogService, Depends(get_daily_log_service)]
LeaveSvc = Annotated[LeaveService, Depends(get_leave_service)]
AuditSvc = Annotated[AuditService, Depends(get_audit_service)]


async def get_current_session(
    request: Request,
    auth_service: AuthSvc,
) -> Session:
    """Get current session from cookie."""
    session_cookie = request.cookies.get(settings.SESSION_COOKIE_NAME)
    if not session_cookie:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    session = await auth_service.validate_session(session_cookie)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session",
        )

    return session


async def get_current_employee(
    session: Annotated[Session, Depends(get_current_session)],
) -> Employee:
    """Get current authenticated employee."""
    return session.employee


async def get_current_company(
    employee: Annotated[Employee, Depends(get_current_employee)],
) -> UUID:
    """Get current employee's company ID."""
    return employee.company_id


def require_role(
    *allowed_roles: EmployeeRole,
) -> Employee:
    """Dependency factory for role-based access control."""
    async def role_checker(
        employee: Annotated[Employee, Depends(get_current_employee)],
    ) -> Employee:
        if employee.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return employee
    return role_checker


# Common role dependencies
RequireAdmin = Annotated[Employee, Depends(require_role(EmployeeRole.ADMIN, EmployeeRole.SUPER_ADMIN))]
RequireManager = Annotated[Employee, Depends(require_role(EmployeeRole.MANAGER, EmployeeRole.ADMIN, EmployeeRole.SUPER_ADMIN))]
RequireSuperAdmin = Annotated[Employee, Depends(require_role(EmployeeRole.SUPER_ADMIN))]


async def get_pagination_params(
    page: int = 1,
    page_size: int = 20,
) -> dict:
    """Get pagination parameters."""
    if page < 1:
        page = 1
    if page_size < 1:
        page_size = 1
    if page_size > 100:
        page_size = 100
    return {"page": page, "page_size": page_size}


class PaginationParams:
    """Pagination parameters class for dependency injection."""

    def __init__(self, page: int = 1, page_size: int = 20):
        self.page = max(1, page)
        self.page_size = min(max(1, page_size), 100)

    def offset(self) -> int:
        return (self.page - 1) * self.page_size

    def limit(self) -> int:
        return self.page_size


async def get_pagination(
    page: int = 1,
    page_size: int = 20,
) -> PaginationParams:
    """Get pagination parameters as object."""
    return PaginationParams(page, page_size)
