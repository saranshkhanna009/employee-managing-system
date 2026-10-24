"""Leave request API routes."""

from typing import Annotated
from uuid import UUID
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    DBSession,
    LeaveSvc,
    get_current_company,
    get_current_employee,
    RequireManager,
    PaginationParams,
    get_pagination,
)
from app.api.route import SnakeCaseAPIRoute
from app.schemas.leave import (
    LeaveRequestCreate,
    LeaveRequestUpdate,
    LeaveRequestReview,
    LeaveRequestResponse,
    LeaveRequestListResponse,
    LeaveBalanceResponse,
)
from app.models.leave import LeaveType, LeaveStatus
from app.models.employee import Employee, EmployeeRole


router = APIRouter(prefix="/leaves", tags=["Leave Requests"], route_class=SnakeCaseAPIRoute)


@router.post("", response_model=LeaveRequestResponse, status_code=status.HTTP_201_CREATED)
async def create_leave_request(
    data: LeaveRequestCreate,
    leave_service: LeaveSvc,
    employee: Annotated[Employee, Depends(get_current_employee)],
) -> LeaveRequestResponse:
    """Create a leave request."""
    try:
        leave = await leave_service.create(employee, data)
        return LeaveRequestResponse.model_validate(leave, from_attributes=True)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("", response_model=LeaveRequestListResponse)
async def list_leave_requests(
    pagination: Annotated[PaginationParams, Depends(get_pagination)],
    leave_service: LeaveSvc,
    company_id: Annotated[UUID, Depends(get_current_company)],
    actor: Annotated[Employee, Depends(get_current_employee)],
    employee_id: UUID | None = Query(None),
    status: LeaveStatus | None = Query(None),
    leave_type: LeaveType | None = Query(None),
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
) -> LeaveRequestListResponse:
    """List leave requests with pagination and filtering."""
    leaves, total = await leave_service.list_requests(
        company_id=company_id,
        actor=actor,
        page=pagination.page,
        page_size=pagination.page_size,
        employee_id=employee_id,
        status=status,
        leave_type=leave_type,
        start_date=start_date,
        end_date=end_date,
    )

    return LeaveRequestListResponse(
        items=[LeaveRequestResponse.model_validate(l, from_attributes=True) for l in leaves],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
        total_pages=(total + pagination.page_size - 1) // pagination.page_size,
    )


@router.get("/balance", response_model=LeaveBalanceResponse)
async def get_leave_balance(
    leave_service: LeaveSvc,
    employee: Annotated[Employee, Depends(get_current_employee)],
    year: int | None = Query(None),
) -> LeaveBalanceResponse:
    """Get leave balance for current employee."""
    balance = await leave_service.get_leave_balance(employee, year)
    return LeaveBalanceResponse(**balance)


@router.get("/{leave_id}", response_model=LeaveRequestResponse)
async def get_leave_request(
    leave_id: UUID,
    leave_service: LeaveSvc,
    company_id: Annotated[UUID, Depends(get_current_company)],
    actor: Annotated[Employee, Depends(get_current_employee)],
) -> LeaveRequestResponse:
    """Get leave request by ID."""
    leave = await leave_service.get_by_id(leave_id, company_id)
    if not leave:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Leave request not found")

    # Check permissions
    if actor.role == EmployeeRole.EMPLOYEE and leave.employee_id != actor.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")

    return LeaveRequestResponse.model_validate(leave, from_attributes=True)


@router.patch("/{leave_id}", response_model=LeaveRequestResponse)
async def update_leave_request(
    leave_id: UUID,
    data: LeaveRequestUpdate,
    leave_service: LeaveSvc,
    company_id: Annotated[UUID, Depends(get_current_company)],
    actor: Annotated[Employee, Depends(get_current_employee)],
) -> LeaveRequestResponse:
    """Update leave request."""
    leave = await leave_service.get_by_id(leave_id, company_id)
    if not leave:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Leave request not found")

    try:
        updated = await leave_service.update(leave, data, actor)
        return LeaveRequestResponse.model_validate(updated, from_attributes=True)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/{leave_id}/review", response_model=LeaveRequestResponse)
async def review_leave_request(
    leave_id: UUID,
    data: LeaveRequestReview,
    leave_service: LeaveSvc,
    company_id: Annotated[UUID, Depends(get_current_company)],
    actor: Annotated[Employee, Depends(get_current_employee)],
) -> LeaveRequestResponse:
    """Review (approve/reject) leave request."""
    leave = await leave_service.get_by_id(leave_id, company_id)
    if not leave:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Leave request not found")

    try:
        updated = await leave_service.review(leave, data, actor)
        return LeaveRequestResponse.model_validate(updated, from_attributes=True)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/{leave_id}/cancel", response_model=LeaveRequestResponse)
async def cancel_leave_request(
    leave_id: UUID,
    leave_service: LeaveSvc,
    company_id: Annotated[UUID, Depends(get_current_company)],
    actor: Annotated[Employee, Depends(get_current_employee)],
) -> LeaveRequestResponse:
    """Cancel leave request."""
    leave = await leave_service.get_by_id(leave_id, company_id)
    if not leave:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Leave request not found")

    try:
        updated = await leave_service.cancel(leave, actor)
        return LeaveRequestResponse.model_validate(updated, from_attributes=True)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete("/{leave_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_leave_request(
    leave_id: UUID,
    leave_service: LeaveSvc,
    company_id: Annotated[UUID, Depends(get_current_company)],
    actor: Annotated[Employee, Depends(get_current_employee)],
) -> None:
    """Delete leave request (admin only)."""
    leave = await leave_service.get_by_id(leave_id, company_id)
    if not leave:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Leave request not found")

    try:
        await leave_service.delete(leave, actor)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
