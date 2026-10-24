"""Company API routes."""

from typing import Annotated
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    DBSession,
    CompanySvc,
    get_current_employee,
    get_current_company,
    RequireSuperAdmin,
    RequireAdmin,
    PaginationParams,
    get_pagination,
)
from app.api.route import SnakeCaseAPIRoute
from app.schemas.company import CompanyCreate, CompanyUpdate, CompanyResponse, CompanyListResponse
from app.models.employee import Employee, EmployeeRole


router = APIRouter(prefix="/company", tags=["Company"], route_class=SnakeCaseAPIRoute)


@router.post("", response_model=CompanyResponse, status_code=status.HTTP_201_CREATED)
async def create_company(
    data: CompanyCreate,
    company_service: CompanySvc,
    admin: RequireSuperAdmin,
) -> CompanyResponse:
    """Create a new company (super admin only)."""
    company = await company_service.create(data, admin.id)
    return CompanyResponse.model_validate(company, from_attributes=True)


@router.get("/me", response_model=CompanyResponse)
async def get_my_company(
    company_id: Annotated[UUID, Depends(get_current_company)],
    company_service: CompanySvc,
) -> CompanyResponse:
    """Get current employee's company profile."""
    company = await company_service.get_by_id(company_id)
    if not company:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")
    return CompanyResponse.model_validate(company, from_attributes=True)


@router.get("/{company_id}", response_model=CompanyResponse)
async def get_company(
    company_id: UUID,
    company_service: CompanySvc,
    admin: RequireAdmin,
) -> CompanyResponse:
    """Get company by ID (admin only)."""
    if admin.role == EmployeeRole.ADMIN and admin.company_id != company_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")

    company = await company_service.get_by_id(company_id)
    if not company:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")
    return CompanyResponse.model_validate(company, from_attributes=True)


@router.patch("/me", response_model=CompanyResponse)
async def update_my_company(
    data: CompanyUpdate,
    company_id: Annotated[UUID, Depends(get_current_company)],
    company_service: CompanySvc,
    admin: RequireAdmin,
) -> CompanyResponse:
    """Update current company (admin only)."""
    if admin.role == EmployeeRole.ADMIN and admin.company_id != company_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")

    company = await company_service.get_by_id(company_id)
    if not company:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")

    updated = await company_service.update(company, data, admin.id)
    return CompanyResponse.model_validate(updated, from_attributes=True)


@router.delete("/{company_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_company(
    company_id: UUID,
    company_service: CompanySvc,
    admin: RequireSuperAdmin,
) -> None:
    """Delete company (super admin only - GDPR)."""
    company = await company_service.get_by_id(company_id)
    if not company:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")

    await company_service.delete(company, admin.id)


@router.get("", response_model=CompanyListResponse)
async def list_companies(
    pagination: Annotated[PaginationParams, Depends(get_pagination)],
    company_service: CompanySvc,
    admin: RequireSuperAdmin,
    search: str | None = Query(None),
    is_active: bool | None = Query(None),
) -> CompanyListResponse:
    """List all companies (super admin only)."""
    companies, total = await company_service.list_companies(
        page=pagination.page,
        page_size=pagination.page_size,
        search=search,
        is_active=is_active,
    )

    return CompanyListResponse(
        items=[CompanyResponse.model_validate(c, from_attributes=True) for c in companies],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
        total_pages=(total + pagination.page_size - 1) // pagination.page_size,
    )
