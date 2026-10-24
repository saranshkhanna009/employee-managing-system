"""Leave request service."""

from typing import Annotated, Optional, List
from uuid import UUID
from datetime import date, datetime, timezone

from fastapi import Depends
from sqlalchemy import select, func, and_, or_, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.leave import LeaveRequest, LeaveType, LeaveStatus
from app.models.employee import Employee, EmployeeRole
from app.models.audit import AuditLog, AuditAction
from app.schemas.leave import LeaveRequestCreate, LeaveRequestUpdate, LeaveRequestReview
from app.database import get_db


class LeaveService:
    """Leave request service."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, employee: Employee, data: LeaveRequestCreate) -> LeaveRequest:
        """Create a leave request."""
        # Validate dates
        if data.end_date < data.start_date:
            raise ValueError("End date must be after start date")

        # Check for overlapping approved leaves
        overlapping = await self.db.execute(
            select(LeaveRequest).where(
                LeaveRequest.employee_id == employee.id,
                LeaveRequest.status.in_([LeaveStatus.APPROVED, LeaveStatus.PENDING]),
                LeaveRequest.start_date <= data.end_date,
                LeaveRequest.end_date >= data.start_date,
            )
        )
        if overlapping.scalar_one_or_none():
            raise ValueError("Overlapping leave request exists")

        leave = LeaveRequest(
            employee_id=employee.id,
            employee=employee,
            leave_type=data.leave_type,
            start_date=data.start_date,
            end_date=data.end_date,
            reason=data.reason,
            status=LeaveStatus.PENDING,
        )
        self.db.add(leave)
        await self.db.flush()

        await self._log_audit(
            company_id=employee.company_id,
            employee_id=employee.id,
            action=AuditAction.LEAVE_REQUESTED,
            resource_type="leave_request",
            resource_id=leave.id,
            metadata={
                "leave_type": data.leave_type.value,
                "start_date": data.start_date.isoformat(),
                "end_date": data.end_date.isoformat(),
                "duration_days": leave.duration_days,
            },
        )

        await self.db.commit()
        await self.db.refresh(leave)
        return leave

    async def get_by_id(self, leave_id: UUID, company_id: UUID) -> Optional[LeaveRequest]:
        """Get leave request by ID within company."""
        stmt = select(LeaveRequest).join(Employee).where(
            LeaveRequest.id == leave_id,
            Employee.company_id == company_id,
        ).options(
            selectinload(LeaveRequest.employee).selectinload(Employee.department),
            selectinload(LeaveRequest.reviewer),
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def update(self, leave: LeaveRequest, data: LeaveRequestUpdate, actor: Employee) -> LeaveRequest:
        """Update leave request."""
        # Employee can update their own pending requests
        # Managers can update any request in their scope
        if leave.employee_id == actor.id:
            if leave.status != LeaveStatus.PENDING:
                raise ValueError("Can only update pending requests")
            # Employees can only cancel
            if "status" in data.model_dump(exclude_unset=True):
                raise ValueError("Employees cannot change status directly")
        elif not actor.can_manage(leave.employee):
            raise ValueError("Insufficient permissions")

        update_data = data.model_dump(exclude_unset=True)
        old_data = {k: getattr(leave, k) for k in update_data.keys()}

        for key, value in update_data.items():
            if key == "status":
                # Only managers can change status
                if not actor.is_manager_or_above():
                    raise ValueError("Only managers can change leave status")
                if value not in (LeaveStatus.APPROVED, LeaveStatus.REJECTED):
                    raise ValueError("Invalid status transition")
                leave.status = value
                leave.reviewed_by_id = actor.id
                leave.reviewed_at = datetime.now(timezone.utc)
            else:
                setattr(leave, key, value)

        await self._log_audit(
            company_id=leave.employee.company_id,
            employee_id=actor.id,
            action=AuditAction.LEAVE_APPROVED if leave.status == LeaveStatus.APPROVED else AuditAction.LEAVE_REJECTED,
            resource_type="leave_request",
            resource_id=leave.id,
            metadata={"old": {k: str(v) for k, v in old_data.items()}, "new": {k: str(v) for k, v in update_data.items()}},
        )

        await self.db.commit()
        await self.db.refresh(leave)
        return leave

    async def review(self, leave: LeaveRequest, data: LeaveRequestReview, actor: Employee) -> LeaveRequest:
        """Review (approve/reject) leave request."""
        if not actor.can_manage(leave.employee):
            raise ValueError("Insufficient permissions")

        if leave.status != LeaveStatus.PENDING:
            raise ValueError("Can only review pending requests")

        leave.status = data.status
        leave.reviewed_by_id = actor.id
        leave.reviewed_at = datetime.now(timezone.utc)
        leave.review_notes = data.review_notes

        await self._log_audit(
            company_id=leave.employee.company_id,
            employee_id=actor.id,
            action=AuditAction.LEAVE_APPROVED if data.status == LeaveStatus.APPROVED else AuditAction.LEAVE_REJECTED,
            resource_type="leave_request",
            resource_id=leave.id,
            metadata={
                "leave_type": leave.leave_type.value,
                "status": data.status.value,
                "review_notes": data.review_notes,
            },
        )

        await self.db.commit()
        await self.db.refresh(leave)
        return leave

    async def cancel(self, leave: LeaveRequest, actor: Employee) -> LeaveRequest:
        """Cancel leave request."""
        if leave.employee_id != actor.id and not actor.can_manage(leave.employee):
            raise ValueError("Insufficient permissions")

        if leave.status not in (LeaveStatus.PENDING, LeaveStatus.APPROVED):
            raise ValueError("Can only cancel pending or approved requests")

        leave.status = LeaveStatus.CANCELLED

        await self._log_audit(
            company_id=leave.employee.company_id,
            employee_id=actor.id,
            action=AuditAction.LEAVE_CANCELLED,
            resource_type="leave_request",
            resource_id=leave.id,
            metadata={"previous_status": leave.status.value},
        )

        await self.db.commit()
        await self.db.refresh(leave)
        return leave

    async def delete(self, leave: LeaveRequest, actor: Employee) -> None:
        """Delete leave request (admin only)."""
        if not actor.is_admin_or_above():
            raise ValueError("Insufficient permissions")

        await self._log_audit(
            company_id=leave.employee.company_id,
            employee_id=actor.id,
            action=AuditAction.LEAVE_CANCELLED,
            resource_type="leave_request",
            resource_id=leave.id,
            metadata={"deleted": True},
        )

        await self.db.delete(leave)
        await self.db.commit()

    async def list_requests(
        self,
        company_id: UUID,
        actor: Employee,
        page: int = 1,
        page_size: int = 20,
        employee_id: Optional[UUID] = None,
        status: Optional[LeaveStatus] = None,
        leave_type: Optional[LeaveType] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> tuple[List[LeaveRequest], int]:
        """List leave requests with pagination and filtering."""
        # Base query
        stmt = select(LeaveRequest).join(Employee).where(Employee.company_id == company_id)

        # Role-based filtering
        if actor.role == EmployeeRole.EMPLOYEE:
            stmt = stmt.where(LeaveRequest.employee_id == actor.id)
        elif actor.role == EmployeeRole.MANAGER:
            if actor.department_id:
                stmt = stmt.where(Employee.department_id == actor.department_id)
            else:
                stmt = stmt.where(LeaveRequest.employee_id == actor.id)

        if employee_id:
            stmt = stmt.where(LeaveRequest.employee_id == employee_id)

        if status:
            stmt = stmt.where(LeaveRequest.status == status)

        if leave_type:
            stmt = stmt.where(LeaveRequest.leave_type == leave_type)

        if start_date:
            stmt = stmt.where(LeaveRequest.start_date >= start_date)

        if end_date:
            stmt = stmt.where(LeaveRequest.end_date <= end_date)

        # Count total
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = await self.db.scalar(count_stmt) or 0

        # Paginate
        stmt = stmt.order_by(LeaveRequest.created_at.desc())
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        stmt = stmt.options(
            selectinload(LeaveRequest.employee).selectinload(Employee.department),
            selectinload(LeaveRequest.reviewer),
        )

        result = await self.db.execute(stmt)
        leaves = result.scalars().all()

        return list(leaves), total

    async def get_leave_balance(self, employee: Employee, year: Optional[int] = None) -> dict:
        """Get leave balance for employee."""
        if year is None:
            year = date.today().year

        # Default allocations (could be configurable per company)
        default_allocations = {
            LeaveType.SICK: 10,
            LeaveType.VACATION: 20,
            LeaveType.PERSONAL: 5,
            LeaveType.EMERGENCY: 3,
            LeaveType.MATERNITY: 90,
            LeaveType.PATERNITY: 30,
            LeaveType.BEREAVEMENT: 5,
            LeaveType.UNPAID: 0,
            LeaveType.OTHER: 5,
        }

        # Get used days
        stmt = select(LeaveRequest).where(
            LeaveRequest.employee_id == employee.id,
            LeaveRequest.status == LeaveStatus.APPROVED,
            LeaveRequest.start_date >= date(year, 1, 1),
            LeaveRequest.end_date <= date(year, 12, 31),
        )
        result = await self.db.execute(stmt)
        used_leaves = result.scalars().all()

        used_by_type = {}
        for leave in used_leaves:
            used_by_type[leave.leave_type] = used_by_type.get(leave.leave_type, 0) + leave.duration_days

        # Get pending days
        stmt = select(LeaveRequest).where(
            LeaveRequest.employee_id == employee.id,
            LeaveRequest.status == LeaveStatus.PENDING,
        )
        result = await self.db.execute(stmt)
        pending_leaves = result.scalars().all()

        pending_by_type = {}
        for leave in pending_leaves:
            pending_by_type[leave.leave_type] = pending_by_type.get(leave.leave_type, 0) + leave.duration_days

        balances = []
        for leave_type, allocated in default_allocations.items():
            used = used_by_type.get(leave_type, 0)
            pending = pending_by_type.get(leave_type, 0)
            balances.append({
                "leave_type": leave_type,
                "allocated": allocated,
                "used": used,
                "pending": pending,
                "remaining": allocated - used - pending,
            })

        return {
            "employee_id": str(employee.id),
            "employee_name": employee.full_name,
            "year": year,
            "balances": balances,
        }

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


async def get_leave_service(db: Annotated[AsyncSession, Depends(get_db)]) -> LeaveService:
    """Get leave service instance."""
    return LeaveService(db)
