"""Task API routes."""

from typing import Annotated
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    DBSession,
    TaskSvc,
    get_current_company,
    get_current_employee,
    RequireManager,
    PaginationParams,
    get_pagination,
)
from app.api.route import SnakeCaseAPIRoute
from app.schemas.task import (
    TaskCreate,
    TaskUpdate,
    TaskAssign,
    TaskStatusUpdate,
    TaskResponse,
    TaskListResponse,
    TaskSummary,
)
from app.models.task import TaskStatus, TaskPriority
from app.models.employee import Employee, EmployeeRole


router = APIRouter(prefix="/tasks", tags=["Tasks"], route_class=SnakeCaseAPIRoute)


@router.post("", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    data: TaskCreate,
    task_service: TaskSvc,
    company_id: Annotated[UUID, Depends(get_current_company)],
    actor: RequireManager,
) -> TaskResponse:
    """Create a new task."""
    try:
        task = await task_service.create(company_id, data, actor)
        return TaskResponse.model_validate(task, from_attributes=True)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("", response_model=TaskListResponse)
async def list_tasks(
    pagination: Annotated[PaginationParams, Depends(get_pagination)],
    task_service: TaskSvc,
    company_id: Annotated[UUID, Depends(get_current_company)],
    actor: Annotated[Employee, Depends(get_current_employee)],
    status: TaskStatus | None = Query(None),
    department_id: UUID | None = Query(None),
    assignee_id: UUID | None = Query(None),
    priority: TaskPriority | None = Query(None),
    search: str | None = Query(None),
) -> TaskListResponse:
    """List tasks with pagination and filtering."""
    tasks, total = await task_service.list_tasks(
        company_id=company_id,
        actor=actor,
        page=pagination.page,
        page_size=pagination.page_size,
        status=status,
        department_id=department_id,
        assignee_id=assignee_id,
        priority=priority,
        search=search,
    )

    return TaskListResponse(
        items=[TaskResponse.model_validate(t, from_attributes=True) for t in tasks],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
        total_pages=(total + pagination.page_size - 1) // pagination.page_size,
    )


@router.get("/my", response_model=list[TaskSummary])
async def get_my_tasks(
    task_service: TaskSvc,
    employee: Annotated[Employee, Depends(get_current_employee)],
    status: TaskStatus | None = Query(None),
) -> list[TaskSummary]:
    """Get tasks assigned to current employee."""
    tasks = await task_service.get_my_tasks(employee, status)
    return [TaskSummary.model_validate(t, from_attributes=True) for t in tasks]


@router.get("/department/{department_id}", response_model=list[TaskSummary])
async def get_department_tasks(
    department_id: UUID,
    task_service: TaskSvc,
    actor: Annotated[Employee, Depends(get_current_employee)],
    status: TaskStatus | None = Query(None),
) -> list[TaskSummary]:
    """Get all tasks for a department (manager view)."""
    try:
        tasks = await task_service.get_department_tasks(department_id, actor, status)
        return [TaskSummary.model_validate(t, from_attributes=True) for t in tasks]
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: UUID,
    task_service: TaskSvc,
    company_id: Annotated[UUID, Depends(get_current_company)],
    actor: Annotated[Employee, Depends(get_current_employee)],
) -> TaskResponse:
    """Get task by ID."""
    task = await task_service.get_by_id(task_id, company_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    # Check permissions
    if actor.role == EmployeeRole.EMPLOYEE:
        if task.assigned_to_id != actor.id and task.created_by_id != actor.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")

    return TaskResponse.model_validate(task, from_attributes=True)


@router.patch("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: UUID,
    data: TaskUpdate,
    task_service: TaskSvc,
    company_id: Annotated[UUID, Depends(get_current_company)],
    actor: Annotated[Employee, Depends(get_current_employee)],
) -> TaskResponse:
    """Update task."""
    task = await task_service.get_by_id(task_id, company_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    try:
        updated = await task_service.update(task, data, actor)
        return TaskResponse.model_validate(updated, from_attributes=True)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/{task_id}/assign", response_model=TaskResponse)
async def assign_task(
    task_id: UUID,
    data: TaskAssign,
    task_service: TaskSvc,
    company_id: Annotated[UUID, Depends(get_current_company)],
    actor: Annotated[Employee, Depends(get_current_employee)],
) -> TaskResponse:
    """Assign task to employee."""
    task = await task_service.get_by_id(task_id, company_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    try:
        updated = await task_service.assign(task, data, actor)
        return TaskResponse.model_validate(updated, from_attributes=True)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/{task_id}/status", response_model=TaskResponse)
async def update_task_status(
    task_id: UUID,
    data: TaskStatusUpdate,
    task_service: TaskSvc,
    company_id: Annotated[UUID, Depends(get_current_company)],
    actor: Annotated[Employee, Depends(get_current_employee)],
) -> TaskResponse:
    """Update task status."""
    task = await task_service.get_by_id(task_id, company_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    try:
        updated = await task_service.update_status(task, data, actor)
        return TaskResponse.model_validate(updated, from_attributes=True)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    task_id: UUID,
    task_service: TaskSvc,
    company_id: Annotated[UUID, Depends(get_current_company)],
    actor: Annotated[Employee, Depends(get_current_employee)],
) -> None:
    """Delete task."""
    task = await task_service.get_by_id(task_id, company_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    try:
        await task_service.delete(task, actor)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
