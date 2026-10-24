"""Department API routes."""

from typing import Annotated, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    DBSession,
    DepartmentSvc,
    get_current_company,
    get_current_employee,
    RequireAdmin,
    RequireManager,
    PaginationParams,
    get_pagination,
)
from app.api.route import SnakeCaseAPIRoute
from app.schemas.department import (
    DepartmentCreate,
    DepartmentUpdate,
    DepartmentResponse,
    DepartmentTreeResponse,
    DepartmentListResponse,
)
from app.models.employee import Employee, EmployeeRole


router = APIRouter(prefix="/departments", tags=["Departments"], route_class=SnakeCaseAPIRoute)


@router.post("", response_model=DepartmentResponse, status_code=status.HTTP_201_CREATED)
async def create_department(
    data: DepartmentCreate,
    department_service: DepartmentSvc,
    company_id: Annotated[UUID, Depends(get_current_company)],
    admin: RequireAdmin,
) -> DepartmentResponse:
    """Create a new department."""
    department = await department_service.create(company_id, data, admin.id)
    return DepartmentResponse.model_validate(department, from_attributes=True)


@router.get("/tree", response_model=list[DepartmentTreeResponse])
async def get_department_tree(
    department_service: DepartmentSvc,
    company_id: Annotated[UUID, Depends(get_current_company)],
    employee: Annotated[Employee, Depends(get_current_employee)],
) -> list[DepartmentTreeResponse]:
    """Get department tree for company."""
    departments = await department_service.get_tree(company_id)

    # Build tree structure
    dept_map = {d.id: DepartmentTreeResponse.model_validate(d, from_attributes=True) for d in departments}
    roots = []

    for dept in departments:
        tree_dept = dept_map[dept.id]
        if dept.parent_id and dept.parent_id in dept_map:
            parent = dept_map[dept.parent_id]
            parent.children.append(tree_dept)
        else:
            roots.append(tree_dept)

    return roots


@router.get("", response_model=DepartmentListResponse)
async def list_departments(
    pagination: Annotated[PaginationParams, Depends(get_pagination)],
    department_service: DepartmentSvc,
    company_id: Annotated[UUID, Depends(get_current_company)],
    employee: Annotated[Employee, Depends(get_current_employee)],
    parent_id: UUID | None = Query(None),
    search: str | None = Query(None),
    root_only: bool = Query(False),
) -> DepartmentListResponse:
    """List departments with pagination."""
    departments, total = await department_service.list_departments(
        company_id=company_id,
        page=pagination.page,
        page_size=pagination.page_size,
        parent_id=parent_id,
        search=search,
        root_only=root_only,
    )

    # Add counts
    items = []
    for dept in departments:
        item = DepartmentResponse.model_validate(dept, from_attributes=True)
        item.children_count = len(dept.children) if hasattr(dept, 'children') else 0
        item.employees_count = len(dept.employees) if hasattr(dept, 'employees') else 0
        items.append(item)

    return DepartmentListResponse(
        items=items,
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
        total_pages=(total + pagination.page_size - 1) // pagination.page_size,
    )


@router.get("/{department_id}", response_model=DepartmentResponse)
async def get_department(
    department_id: UUID,
    department_service: DepartmentSvc,
    company_id: Annotated[UUID, Depends(get_current_company)],
    employee: Annotated[Employee, Depends(get_current_employee)],
) -> DepartmentResponse:
    """Get department by ID."""
    department = await department_service.get_by_id(department_id, company_id)
    if not department:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Department not found")

    response = DepartmentResponse.model_validate(department, from_attributes=True)
    response.children_count = len(department.children) if hasattr(department, 'children') else 0
    response.employees_count = len(department.employees) if hasattr(department, 'employees') else 0
    return response


@router.patch("/{department_id}", response_model=DepartmentResponse)
async def update_department(
    department_id: UUID,
    data: DepartmentUpdate,
    department_service: DepartmentSvc,
    company_id: Annotated[UUID, Depends(get_current_company)],
    admin: RequireAdmin,
) -> DepartmentResponse:
    """Update department."""
    department = await department_service.get_by_id(department_id, company_id)
    if not department:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Department not found")

    updated = await department_service.update(department, data, admin.id)
    return DepartmentResponse.model_validate(updated, from_attributes=True)


@router.delete("/{department_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_department(
    department_id: UUID,
    department_service: DepartmentSvc,
    company_id: Annotated[UUID, Depends(get_current_company)],
    admin: RequireAdmin,
    reassign_to: UUID | None = Query(None),
) -> None:
    """Delete department."""
    department = await department_service.get_by_id(department_id, company_id)
    if not department:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Department not found")

    await department_service.delete(department, admin.id, reassign_to)
