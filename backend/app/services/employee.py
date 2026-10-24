"""Employee service."""

import uuid
from typing import Annotated, Optional, List
from uuid import UUID

from fastapi import Depends
from sqlalchemy import select, func, update, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.models.employee import Employee, EmployeeRole, EmployeeStatus
from app.models.company import Company
from app.models.department import Department
from app.models.audit import AuditLog, AuditAction
from app.schemas.employee import EmployeeCreate, EmployeeUpdate, EmployeePasswordReset
from app.services.auth import AuthService
from app.utils.passwords import validate_password_strength, hash_password
from app.services.encryption import get_encryption_service
from app.database import get_db


class EmployeeService:
    """Employee management service."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.encryption = get_encryption_service()

    def _generate_employee_id(self, company_slug: str, sequence: int) -> str:
        """Generate employee ID."""
        return settings.ADMIN_ID_FORMAT.format(
            prefix=settings.ADMIN_ID_PREFIX,
            company_slug=company_slug,
            sequence=sequence,
        )

    async def _get_next_sequence(self, company_id: UUID) -> int:
        """Get next employee sequence number for company."""
        stmt = select(func.max(Employee.id)).where(Employee.company_id == company_id)
        # This is a simplification - in production, use a dedicated sequence table
        stmt = select(func.count()).where(Employee.company_id == company_id)
        count = await self.db.scalar(stmt) or 0
        return count + 1

    async def create(self, company_id: UUID, data: EmployeeCreate, actor_id: UUID) -> Employee:
        """Create a new employee."""
        # Verify actor can create employees
        actor = await self.db.get(Employee, actor_id)
        if not actor or not actor.is_manager_or_above():
            raise ValueError("Insufficient permissions")

        # Verify company
        company = await self.db.get(Company, company_id)
        if not company:
            raise ValueError("Company not found")

        # Verify department if provided
        if data.department_id:
            dept = await self.db.get(Department, UUID(data.department_id))
            if not dept or dept.company_id != company_id:
                raise ValueError("Invalid department")

        # Check email uniqueness within company
        email_encrypted = self.encryption.encrypt(data.email, "email")
        existing = await self.db.execute(
            select(Employee).where(
                Employee.company_id == company_id,
                Employee._email_encrypted == email_encrypted,
            )
        )
        if existing.scalar_one_or_none():
            raise ValueError("Email already exists in this company")

        # Validate password
        errors = validate_password_strength(data.password)
        if errors:
            raise ValueError(f"Password validation failed: {', '.join(errors)}")

        # Generate employee ID
        sequence = await self._get_next_sequence(company_id)
        employee_id = self._generate_employee_id(company.slug, sequence)

        # Create employee
        employee = Employee(
            company_id=company_id,
            employee_id=employee_id,
            email=data.email,
            first_name=data.first_name,
            last_name=data.last_name,
            phone=data.phone,
            department_id=UUID(data.department_id) if data.department_id else None,
            role=data.role,
            status=EmployeeStatus.ACTIVE,
        )
        employee.set_password(data.password)
        self.db.add(employee)
        await self.db.flush()

        await self._log_audit(
            company_id=company_id,
            employee_id=actor_id,
            action=AuditAction.EMPLOYEE_CREATED,
            resource_type="employee",
            resource_id=employee.id,
            metadata={
                "employee_id": employee_id,
                "email": data.email,
                "role": data.role.value,
                "department_id": str(data.department_id) if data.department_id else None,
            },
        )

        await self.db.commit()
        await self.db.refresh(employee)
        return employee

    async def get_by_id(self, employee_id: UUID, company_id: UUID) -> Optional[Employee]:
        """Get employee by ID within company."""
        stmt = select(Employee).where(
            Employee.id == employee_id,
            Employee.company_id == company_id,
        ).options(selectinload(Employee.department), selectinload(Employee.company))
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_employee_id(self, employee_id: str) -> Optional[Employee]:
        """Get employee by admin ID (for login)."""
        stmt = select(Employee).where(Employee.employee_id == employee_id).options(
            selectinload(Employee.company), selectinload(Employee.department)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def update(self, employee: Employee, data: EmployeeUpdate, actor: Employee) -> Employee:
        """Update employee."""
        if not actor.can_manage(employee):
            raise ValueError("Insufficient permissions")

        update_data = data.model_dump(exclude_unset=True)
        old_data = {}

        for key, value in update_data.items():
            old_data[key] = getattr(employee, key)
            if key == "department_id" and value:
                dept = await self.db.get(Department, UUID(value))
                if not dept or dept.company_id != employee.company_id:
                    raise ValueError("Invalid department")
                setattr(employee, key, UUID(value))
            elif key == "role":
                # Prevent privilege escalation
                if not self._can_assign_role(actor, EmployeeRole(value)):
                    raise ValueError("Cannot assign this role")
                setattr(employee, key, EmployeeRole(value))
            elif key == "status":
                setattr(employee, key, EmployeeStatus(value))
            else:
                setattr(employee, key, value)

        await self._log_audit(
            company_id=employee.company_id,
            employee_id=actor.id,
            action=AuditAction.EMPLOYEE_UPDATED,
            resource_type="employee",
            resource_id=employee.id,
            metadata={"old": {k: str(v) for k, v in old_data.items()}, "new": {k: str(v) for k, v in update_data.items()}},
        )

        await self.db.commit()
        await self.db.refresh(employee)
        return employee

    async def reset_password(self, employee: Employee, data: EmployeePasswordReset, actor: Employee) -> None:
        """Admin reset employee password."""
        if not actor.can_manage(employee):
            raise ValueError("Insufficient permissions")

        errors = validate_password_strength(data.password)
        if errors:
            raise ValueError(f"Password validation failed: {', '.join(errors)}")

        employee.set_password(data.password)

        # Revoke all sessions
        from app.models.session import Session
        stmt = update(Session).where(
            Session.employee_id == employee.id,
            Session.revoked_at.is_(None),
        ).values(revoked_at=func.now())
        await self.db.execute(stmt)

        await self._log_audit(
            company_id=employee.company_id,
            employee_id=actor.id,
            action=AuditAction.EMPLOYEE_PASSWORD_RESET,
            resource_type="employee",
            resource_id=employee.id,
            metadata={"target_employee_id": employee.employee_id},
        )

        await self.db.commit()

    async def deactivate(self, employee: Employee, actor: Employee) -> None:
        """Deactivate employee (soft delete)."""
        if not actor.can_manage(employee):
            raise ValueError("Insufficient permissions")

        if employee.id == actor.id:
            raise ValueError("Cannot deactivate yourself")

        employee.status = EmployeeStatus.INACTIVE

        # Revoke all sessions
        from app.models.session import Session
        stmt = update(Session).where(
            Session.employee_id == employee.id,
            Session.revoked_at.is_(None),
        ).values(revoked_at=func.now())
        await self.db.execute(stmt)

        await self._log_audit(
            company_id=employee.company_id,
            employee_id=actor.id,
            action=AuditAction.EMPLOYEE_DEACTIVATED,
            resource_type="employee",
            resource_id=employee.id,
            metadata={"target_employee_id": employee.employee_id},
        )

        await self.db.commit()

    async def list_employees(
        self,
        company_id: UUID,
        actor: Employee,
        page: int = 1,
        page_size: int = 20,
        search: Optional[str] = None,
        department_id: Optional[UUID] = None,
        role: Optional[EmployeeRole] = None,
        status: Optional[EmployeeStatus] = None,
    ) -> tuple[List[Employee], int]:
        """List employees with pagination and filtering."""
        # Base query - scoped to company
        stmt = select(Employee).where(Employee.company_id == company_id)

        # Role-based filtering
        if not actor.is_admin_or_above():
            # Managers can only see their department
            if actor.department_id:
                stmt = stmt.where(Employee.department_id == actor.department_id)
            else:
                stmt = stmt.where(Employee.id == actor.id)  # Only themselves

        if search:
            # Search on encrypted fields is not directly possible
            # We'll search on employee_id and decrypted names in Python
            pass

        if department_id:
            stmt = stmt.where(Employee.department_id == department_id)

        if role:
            stmt = stmt.where(Employee.role == role)

        if status:
            stmt = stmt.where(Employee.status == status)

        # Count total
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = await self.db.scalar(count_stmt) or 0

        # Paginate
        stmt = stmt.order_by(Employee.created_at.desc())
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        stmt = stmt.options(selectinload(Employee.department))

        result = await self.db.execute(stmt)
        employees = result.scalars().all()

        # Filter by search in Python (since fields are encrypted)
        if search:
            search_lower = search.lower()
            filtered = []
            for emp in employees:
                if (
                    search_lower in emp.employee_id.lower()
                    or search_lower in emp.first_name.lower()
                    or search_lower in emp.last_name.lower()
                    or search_lower in emp.email.lower()
                ):
                    filtered.append(emp)
            employees = filtered
            total = len(employees)

        return list(employees), total

    def _can_assign_role(self, actor: Employee, target_role: EmployeeRole) -> bool:
        """Check if actor can assign target role."""
        if actor.role == EmployeeRole.SUPER_ADMIN:
            return True
        if actor.role == EmployeeRole.ADMIN:
            return target_role != EmployeeRole.SUPER_ADMIN
        if actor.role == EmployeeRole.MANAGER:
            return target_role == EmployeeRole.EMPLOYEE
        return False

    async def get_employee_summary(self, company_id: UUID, actor: Employee) -> List[dict]:
        """Get lightweight employee summaries for dropdowns."""
        employees, _ = await self.list_employees(company_id, actor, page_size=1000)
        return [
            {
                "id": str(e.id),
                "employee_id": e.employee_id,
                "full_name": e.full_name,
                "email": e.email,
                "role": e.role.value,
                "department_id": str(e.department_id) if e.department_id else None,
                "department_name": e.department.name if e.department else None,
            }
            for e in employees
        ]

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

    async def get_team_members(
        self,
        manager: Employee,
        page: int = 1,
        page_size: int = 20,
        search: Optional[str] = None,
        status: Optional[EmployeeStatus] = None,
    ) -> tuple[List[Employee], int]:
        """Get team members for a manager (direct reports + department)."""
        # Get all departments the manager manages
        managed_dept_ids = await self._get_managed_department_ids(manager)

        if not managed_dept_ids:
            return [], 0

        stmt = select(Employee).where(
            Employee.company_id == manager.company_id,
            Employee.department_id.in_(managed_dept_ids),
        )

        if manager.role == EmployeeRole.MANAGER:
            # Managers see their department but not other managers/admins
            stmt = stmt.where(Employee.role == EmployeeRole.EMPLOYEE)
        # Admins see everyone in managed departments

        if search:
            pass  # Filter in Python

        if status:
            stmt = stmt.where(Employee.status == status)

        # Count total
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = await self.db.scalar(count_stmt) or 0

        # Add task counts
        from app.models.task import Task
        from app.models.daily_log import DailyLog
        from app.models.leave import LeaveRequest

        stmt = stmt.order_by(Employee.created_at.desc())
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        stmt = stmt.options(selectinload(Employee.department))

        result = await self.db.execute(stmt)
        employees = result.scalars().all()

        # Filter by search in Python
        if search:
            search_lower = search.lower()
            filtered = []
            for emp in employees:
                if (
                    search_lower in emp.employee_id.lower()
                    or search_lower in emp.first_name.lower()
                    or search_lower in emp.last_name.lower()
                    or search_lower in emp.email.lower()
                ):
                    filtered.append(emp)
            employees = filtered
            total = len(employees)

        # Enrich with counts
        emp_ids = [e.id for e in employees]
        if emp_ids:
            # Task counts
            task_counts = await self.db.execute(
                select(Task.assigned_to_id, func.count(Task.id))
                .where(Task.assigned_to_id.in_(emp_ids))
                .group_by(Task.assigned_to_id)
            )
            task_count_map = {str(k): v for k, v in task_counts.all()}

            # Attach counts
            for emp in employees:
                emp.task_count = task_count_map.get(str(emp.id), 0)

        return list(employees), total

    async def get_team_summary(self, manager: Employee) -> dict:
        """Get team summary statistics."""
        managed_dept_ids = await self._get_managed_department_ids(manager)

        if not managed_dept_ids:
            return {
                "total_members": 0,
                "total_tasks": 0,
                "completed_this_week": 0,
                "hours_today": 0,
            }

        from app.models.task import Task, TaskStatus
        from app.models.daily_log import DailyLog
        from datetime import datetime, timezone, timedelta

        now = datetime.now(timezone.utc)
        week_ago = now - timedelta(days=7)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

        # Total members
        total_members = await self.db.scalar(
            select(func.count(Employee.id))
            .where(
                Employee.company_id == manager.company_id,
                Employee.department_id.in_(managed_dept_ids),
                Employee.status == EmployeeStatus.ACTIVE,
            )
        ) or 0

        # Total tasks
        total_tasks = await self.db.scalar(
            select(func.count(Task.id))
            .where(
                Task.company_id == manager.company_id,
                Task.department_id.in_(managed_dept_ids),
            )
        ) or 0

        # Completed this week
        completed_this_week = await self.db.scalar(
            select(func.count(Task.id))
            .where(
                Task.company_id == manager.company_id,
                Task.department_id.in_(managed_dept_ids),
                Task.status == TaskStatus.COMPLETED,
                Task.completed_at >= week_ago,
            )
        ) or 0

        # Hours today
        hours_today = await self.db.scalar(
            select(func.coalesce(func.sum(DailyLog.hours_spent), 0))
            .where(
                DailyLog.employee_id.in_(
                    select(Employee.id).where(
                        Employee.company_id == manager.company_id,
                        Employee.department_id.in_(managed_dept_ids),
                    )
                ),
                DailyLog.log_date == now.date(),
            )
        ) or 0

        return {
            "total_members": total_members,
            "total_tasks": total_tasks,
            "completed_this_week": completed_this_week,
            "hours_today": float(hours_today) if hours_today else 0,
        }

    async def _get_managed_department_ids(self, manager: Employee) -> List[UUID]:
        """Get department IDs that a manager can manage."""
        if manager.is_admin_or_above():
            # Admins can see all departments in company
            from app.models.department import Department
            depts = await self.db.execute(
                select(Department.id).where(Department.company_id == manager.company_id)
            )
            return list(depts.scalars().all())
        elif manager.role == EmployeeRole.MANAGER and manager.department_id:
            # Managers see their department and sub-departments
            from app.models.department import Department
            depts = await self.db.execute(
                select(Department.id).where(
                    (Department.id == manager.department_id) |
                    (Department.parent_id == manager.department_id)
                )
            )
            return list(depts.scalars().all())
        return []


async def get_employee_service(db: Annotated[AsyncSession, Depends(get_db)]) -> EmployeeService:
    """Get employee service instance."""
    return EmployeeService(db)
