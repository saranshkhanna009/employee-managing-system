"""Employee API routes."""

from typing import Annotated
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    DBSession,
    EmployeeSvc,
    AuthSvc,
    get_current_company,
    get_current_employee,
    RequireAdmin,
    RequireManager,
    PaginationParams,
    get_pagination,
)
from app.api.route import SnakeCaseAPIRoute
from app.schemas.employee import (
    EmployeeCreate,
    EmployeeUpdate,
    EmployeePasswordReset,
    EmployeeResponse,
    EmployeeListResponse,
    EmployeeSummary,
    TeamMemberResponse,
    TeamListResponse,
    TeamSummaryResponse,
)
from app.models.employee import Employee, EmployeeRole, EmployeeStatus


router = APIRouter(prefix="/employees", tags=["Employees"], route_class=SnakeCaseAPIRoute)


@router.post("", response_model=EmployeeResponse, status_code=status.HTTP_201_CREATED)
async def create_employee(
    data: EmployeeCreate,
    employee_service: EmployeeSvc,
    company_id: Annotated[UUID, Depends(get_current_company)],
    admin: RequireManager,
) -> EmployeeResponse:
    """Create a new employee."""
    try:
        employee = await employee_service.create(company_id, data, admin.id)
        return EmployeeResponse.model_validate(employee, from_attributes=True)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("", response_model=EmployeeListResponse)
async def list_employees(
    pagination: Annotated[PaginationParams, Depends(get_pagination)],
    employee_service: EmployeeSvc,
    company_id: Annotated[UUID, Depends(get_current_company)],
    actor: Annotated[Employee, Depends(get_current_employee)],
    search: str | None = Query(None),
    department_id: UUID | None = Query(None),
    role: EmployeeRole | None = Query(None),
    status: EmployeeStatus | None = Query(None),
) -> EmployeeListResponse:
    """List employees with pagination and filtering."""
    employees, total = await employee_service.list_employees(
        company_id=company_id,
        actor=actor,
        page=pagination.page,
        page_size=pagination.page_size,
        search=search,
        department_id=department_id,
        role=role,
        status=status,
    )

    return EmployeeListResponse(
        items=[EmployeeResponse.model_validate(e, from_attributes=True) for e in employees],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
        total_pages=(total + pagination.page_size - 1) // pagination.page_size,
    )


@router.get("/summary", response_model=list[EmployeeSummary])
async def get_employee_summaries(
    employee_service: EmployeeSvc,
    company_id: Annotated[UUID, Depends(get_current_company)],
    actor: Annotated[Employee, Depends(get_current_employee)],
) -> list[EmployeeSummary]:
    """Get lightweight employee summaries for dropdowns."""
    summaries = await employee_service.get_employee_summary(company_id, actor)
    return [EmployeeSummary(**s) for s in summaries]


@router.get("/{employee_id:uuid}", response_model=EmployeeResponse)
async def get_employee(
    employee_id: UUID,
    employee_service: EmployeeSvc,
    company_id: Annotated[UUID, Depends(get_current_company)],
    actor: Annotated[Employee, Depends(get_current_employee)],
) -> EmployeeResponse:
    """Get employee by ID."""
    # Check permissions
    if actor.role == EmployeeRole.EMPLOYEE and actor.id != employee_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")

    employee = await employee_service.get_by_id(employee_id, company_id)
    if not employee:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found")

    return EmployeeResponse.model_validate(employee, from_attributes=True)


@router.patch("/{employee_id:uuid}", response_model=EmployeeResponse)
async def update_employee(
    employee_id: UUID,
    data: EmployeeUpdate,
    employee_service: EmployeeSvc,
    company_id: Annotated[UUID, Depends(get_current_company)],
    actor: Annotated[Employee, Depends(get_current_employee)],
) -> EmployeeResponse:
    """Update employee."""
    employee = await employee_service.get_by_id(employee_id, company_id)
    if not employee:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found")

    try:
        updated = await employee_service.update(employee, data, actor)
        return EmployeeResponse.model_validate(updated, from_attributes=True)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/{employee_id:uuid}/reset-password", status_code=status.HTTP_204_NO_CONTENT)
async def reset_employee_password(
    employee_id: UUID,
    data: EmployeePasswordReset,
    employee_service: EmployeeSvc,
    auth_service: AuthSvc,
    company_id: Annotated[UUID, Depends(get_current_company)],
    admin: RequireAdmin,
    request: Request,
) -> None:
    """Admin reset employee password."""
    employee = await employee_service.get_by_id(employee_id, company_id)
    if not employee:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found")

    try:
        ip = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent")

        await auth_service.admin_reset_password(
            admin=admin,
            target_employee=employee,
            new_password=data.password,
            ip_address=ip,
            user_agent=user_agent,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete("/{employee_id:uuid}", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_employee(
    employee_id: UUID,
    employee_service: EmployeeSvc,
    company_id: Annotated[UUID, Depends(get_current_company)],
    admin: RequireAdmin,
) -> None:
    """Deactivate employee (soft delete)."""
    if admin.id == employee_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot deactivate yourself")

    employee = await employee_service.get_by_id(employee_id, company_id)
    if not employee:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found")

    try:
        await employee_service.deactivate(employee, admin)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# Team endpoints (Manager+)
@router.get("/team", response_model=TeamListResponse)
async def get_team_members(
    pagination: Annotated[PaginationParams, Depends(get_pagination)],
    employee_service: EmployeeSvc,
    company_id: Annotated[UUID, Depends(get_current_company)],
    manager: RequireManager,
    search: str | None = Query(None),
    status: EmployeeStatus | None = Query(None),
) -> TeamListResponse:
    """Get team members for a manager."""
    employees, total = await employee_service.get_team_members(
        manager=manager,
        page=pagination.page,
        page_size=pagination.page_size,
        search=search,
        status=status,
    )

    return TeamListResponse(
        items=[TeamMemberResponse.model_validate(e, from_attributes=True) for e in employees],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
        total_pages=(total + pagination.page_size - 1) // pagination.page_size,
    )


@router.get("/team/summary", response_model=TeamSummaryResponse)
async def get_team_summary(
    employee_service: EmployeeSvc,
    company_id: Annotated[UUID, Depends(get_current_company)],
    manager: RequireManager,
) -> TeamSummaryResponse:
    """Get team summary statistics."""
    summary = await employee_service.get_team_summary(manager)
    return TeamSummaryResponse(**summary)
