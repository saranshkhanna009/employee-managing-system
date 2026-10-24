"""Task service."""

from typing import Annotated, Optional, List
from uuid import UUID
from datetime import date, datetime, timezone

from fastapi import Depends
from sqlalchemy import select, func, update, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.task import Task, TaskStatus, TaskPriority
from app.models.employee import Employee, EmployeeRole
from app.models.department import Department
from app.models.company import Company
from app.models.audit import AuditLog, AuditAction
from app.schemas.task import TaskCreate, TaskUpdate, TaskAssign, TaskStatusUpdate
from app.database import get_db


class TaskService:
    """Task management service."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, company_id: UUID, data: TaskCreate, actor: Employee) -> Task:
        """Create a new task."""
        # Verify actor can create tasks
        if not actor.is_manager_or_above():
            raise ValueError("Insufficient permissions")

        # Verify department if provided
        if data.department_id:
            dept = await self.db.get(Department, UUID(data.department_id))
            if not dept or dept.company_id != company_id:
                raise ValueError("Invalid department")

        # Verify assignee if provided
        if data.assigned_to_id:
            assignee = await self.db.get(Employee, UUID(data.assigned_to_id))
            if not assignee or assignee.company_id != company_id:
                raise ValueError("Invalid assignee")
            # Managers can only assign to their department
            if actor.role == EmployeeRole.MANAGER:
                if assignee.department_id != actor.department_id:
                    raise ValueError("Can only assign to employees in your department")

        task = Task(
            company_id=company_id,
            creator=actor,
            department_id=UUID(data.department_id) if data.department_id else None,
            assigned_to_id=UUID(data.assigned_to_id) if data.assigned_to_id else None,
            created_by_id=actor.id,
            title=data.title,
            description=data.description,
            priority=data.priority,
            due_date=data.due_date,
            estimated_hours=data.estimated_hours,
            sort_order=data.sort_order,
        )
        self.db.add(task)
        await self.db.flush()

        await self._log_audit(
            company_id=company_id,
            employee_id=actor.id,
            action=AuditAction.TASK_CREATED,
            resource_type="task",
            resource_id=task.id,
            metadata={
                "title": task.title,
                "priority": task.priority.value,
                "assigned_to": str(data.assigned_to_id) if data.assigned_to_id else None,
                "department_id": str(data.department_id) if data.department_id else None,
            },
        )

        await self.db.commit()
        await self.db.refresh(task)
        return task

    async def get_by_id(self, task_id: UUID, company_id: UUID) -> Optional[Task]:
        """Get task by ID within company."""
        stmt = select(Task).where(
            Task.id == task_id,
            Task.company_id == company_id,
        ).options(
            selectinload(Task.assignee).selectinload(Employee.department),
            selectinload(Task.creator),
            selectinload(Task.department),
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def update(self, task: Task, data: TaskUpdate, actor: Employee) -> Task:
        """Update task."""
        if not task.can_be_modified_by(actor):
            raise ValueError("Insufficient permissions")

        update_data = data.model_dump(exclude_unset=True)
        old_data = {k: getattr(task, k) for k in update_data.keys()}

        for key, value in update_data.items():
            if key in ("department_id", "assigned_to_id") and value:
                setattr(task, key, UUID(value))
            else:
                setattr(task, key, value)

        await self._log_audit(
            company_id=task.company_id,
            employee_id=actor.id,
            action=AuditAction.TASK_UPDATED,
            resource_type="task",
            resource_id=task.id,
            metadata={"old": {k: str(v) for k, v in old_data.items()}, "new": {k: str(v) for k, v in update_data.items()}},
        )

        await self.db.commit()
        await self.db.refresh(task)
        return task

    async def assign(self, task: Task, data: TaskAssign, actor: Employee) -> Task:
        """Assign task to employee."""
        if not task.can_be_modified_by(actor):
            raise ValueError("Insufficient permissions")

        assignee = await self.db.get(Employee, UUID(data.assigned_to_id))
        if not assignee or assignee.company_id != task.company_id:
            raise ValueError("Invalid assignee")

        # Managers can only assign to their department
        if actor.role == EmployeeRole.MANAGER:
            if assignee.department_id != actor.department_id:
                raise ValueError("Can only assign to employees in your department")

        old_assignee = task.assigned_to_id
        task.assigned_to_id = assignee.id

        await self._log_audit(
            company_id=task.company_id,
            employee_id=actor.id,
            action=AuditAction.TASK_ASSIGNED,
            resource_type="task",
            resource_id=task.id,
            metadata={"old_assignee": str(old_assignee) if old_assignee else None, "new_assignee": str(assignee.id)},
        )

        await self.db.commit()
        await self.db.refresh(task)
        return task

    async def update_status(self, task: Task, data: TaskStatusUpdate, actor: Employee) -> Task:
        """Update task status."""
        # Assignee can update status, creators and managers can too
        if not task.can_be_modified_by(actor):
            raise ValueError("Insufficient permissions")

        old_status = task.status
        task.status = data.status

        if data.status == TaskStatus.COMPLETED and old_status != TaskStatus.COMPLETED:
            task.completed_at = datetime.now(timezone.utc)

        await self._log_audit(
            company_id=task.company_id,
            employee_id=actor.id,
            action=AuditAction.TASK_STATUS_CHANGED,
            resource_type="task",
            resource_id=task.id,
            metadata={"old_status": old_status.value, "new_status": data.status.value},
        )

        await self.db.commit()
        await self.db.refresh(task)
        return task

    async def delete(self, task: Task, actor: Employee) -> None:
        """Delete task."""
        if not actor.is_manager_or_above():
            raise ValueError("Insufficient permissions")
        if actor.role == EmployeeRole.MANAGER and task.department_id != actor.department_id:
            raise ValueError("Cannot delete tasks from other departments")

        await self._log_audit(
            company_id=task.company_id,
            employee_id=actor.id,
            action=AuditAction.TASK_DELETED,
            resource_type="task",
            resource_id=task.id,
            metadata={"title": task.title},
        )

        await self.db.delete(task)
        await self.db.commit()

    async def list_tasks(
        self,
        company_id: UUID,
        actor: Employee,
        page: int = 1,
        page_size: int = 20,
        status: Optional[TaskStatus] = None,
        department_id: Optional[UUID] = None,
        assignee_id: Optional[UUID] = None,
        priority: Optional[TaskPriority] = None,
        search: Optional[str] = None,
    ) -> tuple[List[Task], int]:
        """List tasks with pagination and filtering."""
        # Base query scoped to company
        stmt = select(Task).where(Task.company_id == company_id)

        # Role-based filtering
        if actor.role == EmployeeRole.EMPLOYEE:
            # Employees see only their assigned tasks
            stmt = stmt.where(Task.assigned_to_id == actor.id)
        elif actor.role == EmployeeRole.MANAGER:
            # Managers see tasks in their department
            if actor.department_id:
                stmt = stmt.where(Task.department_id == actor.department_id)
            else:
                stmt = stmt.where(Task.assigned_to_id == actor.id)

        if status:
            stmt = stmt.where(Task.status == status)

        if department_id:
            stmt = stmt.where(Task.department_id == department_id)

        if assignee_id:
            stmt = stmt.where(Task.assigned_to_id == assignee_id)

        if priority:
            stmt = stmt.where(Task.priority == priority)

        # Count total
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = await self.db.scalar(count_stmt) or 0

        # Paginate
        stmt = stmt.order_by(Task.sort_order, Task.created_at.desc())
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        stmt = stmt.options(
            selectinload(Task.assignee).selectinload(Employee.department),
            selectinload(Task.creator),
            selectinload(Task.department),
        )

        result = await self.db.execute(stmt)
        tasks = result.scalars().all()

        # Filter by search in Python
        if search:
            search_lower = search.lower()
            filtered = []
            for task in tasks:
                if (
                    search_lower in task.title.lower()
                    or (task.description and search_lower in task.description.lower())
                ):
                    filtered.append(task)
            tasks = filtered
            total = len(tasks)

        return list(tasks), total

    async def get_my_tasks(self, employee: Employee, status: Optional[TaskStatus] = None) -> List[Task]:
        """Get tasks assigned to current employee."""
        stmt = select(Task).where(
            Task.company_id == employee.company_id,
            Task.assigned_to_id == employee.id,
        )
        if status:
            stmt = stmt.where(Task.status == status)
        stmt = stmt.order_by(Task.sort_order, Task.due_date.asc().nullslast())
        stmt = stmt.options(selectinload(Task.department))

        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_department_tasks(
        self,
        department_id: UUID,
        actor: Employee,
        status: Optional[TaskStatus] = None,
    ) -> List[Task]:
        """Get all tasks for a department (manager view)."""
        if actor.role == EmployeeRole.MANAGER and actor.department_id != department_id:
            raise ValueError("Insufficient permissions")

        stmt = select(Task).where(Task.department_id == department_id)
        if status:
            stmt = stmt.where(Task.status == status)
        stmt = stmt.order_by(Task.sort_order, Task.created_at.desc())
        stmt = stmt.options(
            selectinload(Task.assignee).selectinload(Employee.department),
            selectinload(Task.creator),
        )

        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def _log_audit(
        self,
        action: str,
        company_id: UUID,
        employee_id: UUID,
        resource_type: Optional[str] = None,
        resource_id: Optional[UUID] = None,
        metadata: Optional[dict] = None,
    ) -> None:
        """Create audit log entry."""
        audit = AuditLog(
            company_id=company_id,
            employee_id=employee_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            metadata=metadata or {},
        )
        self.db.add(audit)


async def get_task_service(db: Annotated[AsyncSession, Depends(get_db)]) -> TaskService:
    """Get task service instance."""
    return TaskService(db)
