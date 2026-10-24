"""Daily log service."""

from typing import Annotated, Optional, List
from uuid import UUID
from datetime import date, datetime, timezone

from fastapi import Depends
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.daily_log import DailyLog, DailyLogStatus
from app.models.task import Task
from app.models.employee import Employee, EmployeeRole
from app.models.audit import AuditLog, AuditAction
from app.schemas.daily_log import DailyLogCreate, DailyLogUpdate
from app.database import get_db


class DailyLogService:
    """Daily task log service."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, employee: Employee, data: DailyLogCreate) -> DailyLog:
        """Create a daily log entry."""
        # Verify task if provided
        if data.task_id:
            task = await self.db.get(Task, UUID(data.task_id))
            if not task or task.company_id != employee.company_id:
                raise ValueError("Invalid task")
            # Employee can only log time on their assigned tasks
            if task.assigned_to_id != employee.id:
                raise ValueError("Can only log time on assigned tasks")

        # Check for existing log on same date
        existing = await self.db.execute(
            select(DailyLog).where(
                DailyLog.employee_id == employee.id,
                DailyLog.log_date == data.log_date,
            )
        )
        if existing.scalar_one_or_none():
            raise ValueError("Log entry already exists for this date")

        log = DailyLog(
            employee_id=employee.id,
            employee=employee,
            task_id=UUID(data.task_id) if data.task_id else None,
            log_date=data.log_date,
            hours_spent=data.hours_spent,
            progress_notes=data.progress_notes,
            status=data.status,
        )
        self.db.add(log)
        await self.db.flush()

        await self._log_audit(
            company_id=employee.company_id,
            employee_id=employee.id,
            action=AuditAction.DAILY_LOG_CREATED,
            resource_type="daily_log",
            resource_id=log.id,
            metadata={
                "log_date": data.log_date.isoformat(),
                "hours_spent": data.hours_spent,
                "task_id": data.task_id,
            },
        )

        await self.db.commit()
        await self.db.refresh(log)
        return log

    async def get_by_id(self, log_id: UUID, company_id: UUID) -> Optional[DailyLog]:
        """Get daily log by ID within company."""
        stmt = select(DailyLog).join(Employee).where(
            DailyLog.id == log_id,
            Employee.company_id == company_id,
        ).options(selectinload(DailyLog.task), selectinload(DailyLog.employee))
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_employee_and_date(self, employee_id: UUID, log_date: date) -> Optional[DailyLog]:
        """Get daily log for employee on specific date."""
        stmt = select(DailyLog).where(
            DailyLog.employee_id == employee_id,
            DailyLog.log_date == log_date,
        ).options(selectinload(DailyLog.task))
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def update(self, log: DailyLog, data: DailyLogUpdate, actor: Employee) -> DailyLog:
        """Update daily log."""
        # Employee can update their own logs, managers can update team logs
        if log.employee_id != actor.id:
            if not actor.is_manager_or_above():
                raise ValueError("Insufficient permissions")
            if actor.role == EmployeeRole.MANAGER and log.employee.department_id != actor.department_id:
                raise ValueError("Cannot modify logs from other departments")

        update_data = data.model_dump(exclude_unset=True)
        old_data = {k: getattr(log, k) for k in update_data.keys()}

        for key, value in update_data.items():
            if key == "task_id" and value:
                task = await self.db.get(Task, UUID(value))
                if not task or task.company_id != log.employee.company_id:
                    raise ValueError("Invalid task")
                setattr(log, key, UUID(value))
            else:
                setattr(log, key, value)

        await self._log_audit(
            company_id=log.employee.company_id,
            employee_id=actor.id,
            action=AuditAction.DAILY_LOG_UPDATED,
            resource_type="daily_log",
            resource_id=log.id,
            metadata={"old": {k: str(v) for k, v in old_data.items()}, "new": {k: str(v) for k, v in update_data.items()}},
        )

        await self.db.commit()
        await self.db.refresh(log)
        return log

    async def delete(self, log: DailyLog, actor: Employee) -> None:
        """Delete daily log."""
        if log.employee_id != actor.id and not actor.is_manager_or_above():
            raise ValueError("Insufficient permissions")

        await self._log_audit(
            company_id=log.employee.company_id,
            employee_id=actor.id,
            action=AuditAction.DAILY_LOG_DELETED,
            resource_type="daily_log",
            resource_id=log.id,
            metadata={"log_date": log.log_date.isoformat()},
        )

        await self.db.delete(log)
        await self.db.commit()

    async def list_logs(
        self,
        company_id: UUID,
        actor: Employee,
        page: int = 1,
        page_size: int = 20,
        employee_id: Optional[UUID] = None,
        task_id: Optional[UUID] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        status: Optional[DailyLogStatus] = None,
    ) -> tuple[List[DailyLog], int]:
        """List daily logs with pagination and filtering."""
        # Base query
        stmt = select(DailyLog).join(Employee).where(Employee.company_id == company_id)

        # Role-based filtering
        if actor.role == EmployeeRole.EMPLOYEE:
            stmt = stmt.where(DailyLog.employee_id == actor.id)
        elif actor.role == EmployeeRole.MANAGER:
            if actor.department_id:
                stmt = stmt.where(Employee.department_id == actor.department_id)
            else:
                stmt = stmt.where(DailyLog.employee_id == actor.id)

        if employee_id:
            stmt = stmt.where(DailyLog.employee_id == employee_id)

        if task_id:
            stmt = stmt.where(DailyLog.task_id == task_id)

        if start_date:
            stmt = stmt.where(DailyLog.log_date >= start_date)

        if end_date:
            stmt = stmt.where(DailyLog.log_date <= end_date)

        if status:
            stmt = stmt.where(DailyLog.status == status)

        # Count total
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = await self.db.scalar(count_stmt) or 0

        # Paginate
        stmt = stmt.order_by(DailyLog.log_date.desc(), DailyLog.created_at.desc())
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        stmt = stmt.options(selectinload(DailyLog.task), selectinload(DailyLog.employee))

        result = await self.db.execute(stmt)
        logs = result.scalars().all()

        return list(logs), total

    async def get_employee_summary(
        self,
        employee: Employee,
        start_date: date,
        end_date: date,
    ) -> dict:
        """Get daily log summary for an employee."""
        stmt = select(DailyLog).where(
            DailyLog.employee_id == employee.id,
            DailyLog.log_date >= start_date,
            DailyLog.log_date <= end_date,
        )
        result = await self.db.execute(stmt)
        logs = result.scalars().all()

        total_hours = sum(log.hours_spent or 0 for log in logs)
        tasks_count = len(set(log.task_id for log in logs if log.task_id))
        completed_tasks = sum(1 for log in logs if log.status == DailyLogStatus.COMPLETED)
        in_progress_tasks = sum(1 for log in logs if log.status == DailyLogStatus.IN_PROGRESS)

        return {
            "employee_id": employee.id,
            "employee_name": employee.full_name,
            "period_start": start_date,
            "period_end": end_date,
            "total_hours": total_hours,
            "tasks_count": tasks_count,
            "completed_tasks": completed_tasks,
            "in_progress_tasks": in_progress_tasks,
            "logs_count": len(logs),
        }

    async def get_department_summary(
        self,
        department_id: UUID,
        actor: Employee,
        log_date: date,
    ) -> dict:
        """Get department daily summary for managers."""
        if actor.role == EmployeeRole.MANAGER and actor.department_id != department_id:
            raise ValueError("Insufficient permissions")

        from app.models.employee import Employee as EmpModel
        stmt = select(DailyLog).join(EmpModel).where(
            EmpModel.department_id == department_id,
            DailyLog.log_date == log_date,
        ).options(selectinload(DailyLog.employee).selectinload(EmpModel.department), selectinload(DailyLog.task))

        result = await self.db.execute(stmt)
        logs = result.scalars().all()

        employees = set(log.employee for log in logs if log.employee)
        total_hours = sum(log.hours_spent or 0 for log in logs)
        tasks_completed = sum(1 for log in logs if log.status == DailyLogStatus.COMPLETED)
        tasks_in_progress = sum(1 for log in logs if log.status == DailyLogStatus.IN_PROGRESS)

        employee_summaries = []
        for emp in employees:
            emp_logs = [log for log in logs if log.employee_id == emp.id]
            employee_summaries.append({
                "employee_id": emp.id,
                "employee_name": emp.full_name,
                "hours_spent": sum(l.hours_spent or 0 for l in emp_logs),
                "tasks_count": len(emp_logs),
            })

        return {
            "date": log_date.isoformat(),
            "department_id": str(department_id),
            "department_name": logs[0].employee.department.name if logs and logs[0].employee.department else "Unknown",
            "total_employees": len(employees),
            "active_employees": len([e for e in employees if any(l.employee_id == e.id for l in logs)]),
            "total_hours": total_hours,
            "tasks_completed": tasks_completed,
            "tasks_in_progress": tasks_in_progress,
            "employee_summaries": employee_summaries,
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


async def get_daily_log_service(db: Annotated[AsyncSession, Depends(get_db)]) -> DailyLogService:
    """Get daily log service instance."""
    return DailyLogService(db)
