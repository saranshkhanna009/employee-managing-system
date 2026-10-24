"""Department service."""

from typing import Annotated, Optional, List
from uuid import UUID

from fastapi import Depends
from sqlalchemy import select, func, delete, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.department import Department
from app.models.company import Company
from app.models.employee import Employee, EmployeeRole
from app.models.audit import AuditLog, AuditAction
from app.schemas.department import DepartmentCreate, DepartmentUpdate
from app.database import get_db


class DepartmentService:
    """Department management service."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, company_id: UUID, data: DepartmentCreate, actor_id: UUID) -> Department:
        """Create a new department."""
        # Verify company exists
        company = await self.db.get(Company, company_id)
        if not company:
            raise ValueError("Company not found")

        # Verify parent department if provided
        if data.parent_id:
            parent = await self.db.get(Department, UUID(data.parent_id))
            if not parent or parent.company_id != company_id:
                raise ValueError("Invalid parent department")

        department = Department(
            company_id=company_id,
            name=data.name,
            description=data.description,
            parent_id=UUID(data.parent_id) if data.parent_id else None,
            sort_order=data.sort_order,
        )
        self.db.add(department)
        await self.db.flush()

        await self._log_audit(
            company_id=company_id,
            employee_id=actor_id,
            action=AuditAction.DEPARTMENT_CREATED,
            resource_type="department",
            resource_id=department.id,
            metadata={"name": department.name, "parent_id": str(data.parent_id) if data.parent_id else None},
        )

        await self.db.commit()
        await self.db.refresh(department)
        return department

    async def get_by_id(self, department_id: UUID, company_id: UUID) -> Optional[Department]:
        """Get department by ID within company."""
        stmt = select(Department).where(
            Department.id == department_id,
            Department.company_id == company_id,
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_tree(self, company_id: UUID) -> List[Department]:
        """Get department tree for a company."""
        stmt = select(Department).where(
            Department.company_id == company_id,
        ).order_by(Department.sort_order, Department.name)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def update(self, department: Department, data: DepartmentUpdate, actor_id: UUID) -> Department:
        """Update department."""
        update_data = data.model_dump(exclude_unset=True)
        old_data = {k: getattr(department, k) for k in update_data.keys()}

        # Verify parent department if changing
        if "parent_id" in update_data and update_data["parent_id"]:
            parent = await self.db.get(Department, UUID(update_data["parent_id"]))
            if not parent or parent.company_id != department.company_id:
                raise ValueError("Invalid parent department")
            # Prevent circular reference
            if parent.id == department.id:
                raise ValueError("Department cannot be its own parent")
            # Check if parent is a descendant
            if await self._is_descendant(department.id, parent.id):
                raise ValueError("Cannot set descendant as parent")

        for key, value in update_data.items():
            if key == "parent_id" and value:
                setattr(department, key, UUID(value))
            else:
                setattr(department, key, value)

        await self._log_audit(
            company_id=department.company_id,
            employee_id=actor_id,
            action=AuditAction.DEPARTMENT_UPDATED,
            resource_type="department",
            resource_id=department.id,
            metadata={"old": {k: str(v) for k, v in old_data.items()}, "new": {k: str(v) for k, v in update_data.items()}},
        )

        await self.db.commit()
        await self.db.refresh(department)
        return department

    async def delete(self, department: Department, actor_id: UUID, reassign_to: Optional[UUID] = None) -> None:
        """
        Delete department.

        Args:
            department: Department to delete
            actor_id: Employee performing deletion
            reassign_to: Optional department ID to reassign employees to
        """
        # Reassign employees if specified
        if reassign_to:
            from app.models.employee import Employee
            stmt = (
                update(Employee)
                .where(Employee.department_id == department.id)
                .values(department_id=reassign_to)
            )
            await self.db.execute(stmt)

        # Delete children first (cascade)
        await self._delete_children(department.id)

        await self._log_audit(
            company_id=department.company_id,
            employee_id=actor_id,
            action=AuditAction.DEPARTMENT_DELETED,
            resource_type="department",
            resource_id=department.id,
            metadata={"name": department.name, "reassign_to": str(reassign_to) if reassign_to else None},
        )

        await self.db.delete(department)
        await self.db.commit()

    async def list_departments(
        self,
        company_id: UUID,
        page: int = 1,
        page_size: int = 50,
        parent_id: Optional[UUID] = None,
        search: Optional[str] = None,
        root_only: bool = False,
    ) -> tuple[List[Department], int]:
        """List departments with pagination."""
        stmt = select(Department).where(Department.company_id == company_id)

        if root_only:
            stmt = stmt.where(Department.parent_id.is_(None))
        elif parent_id is not None:
            stmt = stmt.where(Department.parent_id == parent_id)

        if search:
            stmt = stmt.where(Department.name.ilike(f"%{search}%"))

        # Count total
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = await self.db.scalar(count_stmt) or 0

        # Paginate
        stmt = stmt.order_by(Department.sort_order, Department.name)
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)

        result = await self.db.execute(stmt)
        departments = result.scalars().all()

        return list(departments), total

    async def _is_descendant(self, ancestor_id: UUID, descendant_id: UUID) -> bool:
        """Check if descendant_id is a descendant of ancestor_id."""
        current_id = descendant_id
        while current_id:
            dept = await self.db.get(Department, current_id)
            if not dept:
                break
            if dept.parent_id == ancestor_id:
                return True
            current_id = dept.parent_id
        return False

    async def _delete_children(self, department_id: UUID) -> None:
        """Recursively delete child departments."""
        stmt = select(Department).where(Department.parent_id == department_id)
        result = await self.db.execute(stmt)
        children = result.scalars().all()

        for child in children:
            await self._delete_children(child.id)
            await self.db.delete(child)

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


async def get_department_service(db: Annotated[AsyncSession, Depends(get_db)]) -> DepartmentService:
    """Get department service instance."""
    return DepartmentService(db)
