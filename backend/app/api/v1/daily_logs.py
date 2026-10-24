"""Daily log API routes."""

from typing import Annotated
from uuid import UUID
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    DBSession,
    DailyLogSvc,
    get_current_company,
    get_current_employee,
    RequireManager,
    PaginationParams,
    get_pagination,
)
from app.api.route import SnakeCaseAPIRoute
from app.schemas.daily_log import (
    DailyLogCreate,
    DailyLogUpdate,
    DailyLogResponse,
    DailyLogListResponse,
    DailyLogSummary,
    DepartmentDailySummary,
)
from app.models.daily_log import DailyLogStatus
from app.models.employee import Employee, EmployeeRole


router = APIRouter(prefix="/daily-logs", tags=["Daily Logs"], route_class=SnakeCaseAPIRoute)


@router.post("", response_model=DailyLogResponse, status_code=status.HTTP_201_CREATED)
async def create_daily_log(
    data: DailyLogCreate,
    daily_log_service: DailyLogSvc,
    employee: Annotated[Employee, Depends(get_current_employee)],
) -> DailyLogResponse:
    """Create a daily log entry."""
    try:
        log = await daily_log_service.create(employee, data)
        return DailyLogResponse.model_validate(log, from_attributes=True)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("", response_model=DailyLogListResponse)
async def list_daily_logs(
    pagination: Annotated[PaginationParams, Depends(get_pagination)],
    daily_log_service: DailyLogSvc,
    company_id: Annotated[UUID, Depends(get_current_company)],
    actor: Annotated[Employee, Depends(get_current_employee)],
    employee_id: UUID | None = Query(None),
    task_id: UUID | None = Query(None),
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    status: DailyLogStatus | None = Query(None),
) -> DailyLogListResponse:
    """List daily logs with pagination and filtering."""
    logs, total = await daily_log_service.list_logs(
        company_id=company_id,
        actor=actor,
        page=pagination.page,
        page_size=pagination.page_size,
        employee_id=employee_id,
        task_id=task_id,
        start_date=start_date,
        end_date=end_date,
        status=status,
    )

    return DailyLogListResponse(
        items=[DailyLogResponse.model_validate(l, from_attributes=True) for l in logs],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
        total_pages=(total + pagination.page_size - 1) // pagination.page_size,
    )


@router.get("/my/summary", response_model=DailyLogSummary)
async def get_my_daily_summary(
    daily_log_service: DailyLogSvc,
    employee: Annotated[Employee, Depends(get_current_employee)],
    start_date: date = Query(...),
    end_date: date = Query(...),
) -> DailyLogSummary:
    """Get daily log summary for current employee."""
    summary = await daily_log_service.get_employee_summary(employee, start_date, end_date)
    return DailyLogSummary(**summary)


@router.get("/department/{department_id}/summary", response_model=DepartmentDailySummary)
async def get_department_daily_summary(
    department_id: UUID,
    daily_log_service: DailyLogSvc,
    actor: Annotated[Employee, Depends(get_current_employee)],
    log_date: date = Query(...),
) -> DepartmentDailySummary:
    """Get department daily summary (manager view)."""
    try:
        summary = await daily_log_service.get_department_summary(department_id, actor, log_date)
        return DepartmentDailySummary(**summary)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.get("/{log_id}", response_model=DailyLogResponse)
async def get_daily_log(
    log_id: UUID,
    daily_log_service: DailyLogSvc,
    company_id: Annotated[UUID, Depends(get_current_company)],
    actor: Annotated[Employee, Depends(get_current_employee)],
) -> DailyLogResponse:
    """Get daily log by ID."""
    log = await daily_log_service.get_by_id(log_id, company_id)
    if not log:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Daily log not found")

    # Check permissions
    if actor.role == EmployeeRole.EMPLOYEE and log.employee_id != actor.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")

    return DailyLogResponse.model_validate(log, from_attributes=True)


@router.patch("/{log_id}", response_model=DailyLogResponse)
async def update_daily_log(
    log_id: UUID,
    data: DailyLogUpdate,
    daily_log_service: DailyLogSvc,
    company_id: Annotated[UUID, Depends(get_current_company)],
    actor: Annotated[Employee, Depends(get_current_employee)],
) -> DailyLogResponse:
    """Update daily log."""
    log = await daily_log_service.get_by_id(log_id, company_id)
    if not log:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Daily log not found")

    try:
        updated = await daily_log_service.update(log, data, actor)
        return DailyLogResponse.model_validate(updated, from_attributes=True)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete("/{log_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_daily_log(
    log_id: UUID,
    daily_log_service: DailyLogSvc,
    company_id: Annotated[UUID, Depends(get_current_company)],
    actor: Annotated[Employee, Depends(get_current_employee)],
) -> None:
    """Delete daily log."""
    log = await daily_log_service.get_by_id(log_id, company_id)
    if not log:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Daily log not found")

    try:
        await daily_log_service.delete(log, actor)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
