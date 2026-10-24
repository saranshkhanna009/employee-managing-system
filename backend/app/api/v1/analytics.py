"""Company analytics API."""

from collections import Counter
from datetime import date, datetime, time, timedelta, timezone
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.deps import DBSession, RequireAdmin, get_current_company
from app.api.route import SnakeCaseAPIRoute
from app.models.daily_log import DailyLog
from app.models.department import Department
from app.models.employee import Employee, EmployeeStatus
from app.models.leave import LeaveRequest, LeaveStatus, LeaveType
from app.models.task import Task, TaskPriority, TaskStatus


router = APIRouter(prefix="/analytics", tags=["Analytics"], route_class=SnakeCaseAPIRoute)


def _period_start(range_name: str) -> date:
    days = {"7d": 7, "30d": 30, "90d": 90, "1y": 365}.get(range_name)
    if days is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="range must be one of: 7d, 30d, 90d, 1y",
        )
    return date.today() - timedelta(days=days - 1)


@router.get("")
async def get_analytics(
    db: DBSession,
    company_id: Annotated[UUID, Depends(get_current_company)],
    _: RequireAdmin,
    range: str = Query("30d"),
) -> dict:
    """Return company-level reporting data for the selected time period."""
    start_date = _period_start(range)
    start_datetime = datetime.combine(start_date, time.min, tzinfo=timezone.utc)

    employees = list(
        (
            await db.execute(
                select(Employee).where(Employee.company_id == company_id)
            )
        ).scalars().all()
    )
    tasks = list(
        (
            await db.execute(
                select(Task)
                .where(Task.company_id == company_id)
                .options(
                    selectinload(Task.assignee),
                    selectinload(Task.department),
                )
            )
        ).scalars().all()
    )
    logs = list(
        (
            await db.execute(
                select(DailyLog)
                .join(Employee, DailyLog.employee_id == Employee.id)
                .where(
                    Employee.company_id == company_id,
                    DailyLog.log_date >= start_date,
                )
            )
        ).scalars().all()
    )
    leaves = list(
        (
            await db.execute(
                select(LeaveRequest)
                .join(Employee, LeaveRequest.employee_id == Employee.id)
                .where(
                    Employee.company_id == company_id,
                    LeaveRequest.created_at >= start_datetime,
                )
            )
        ).scalars().all()
    )
    departments = list(
        (
            await db.execute(
                select(Department).where(Department.company_id == company_id)
            )
        ).scalars().all()
    )

    task_status_counts = Counter(task.status.value for task in tasks)
    task_priority_counts = Counter(task.priority.value for task in tasks)
    leave_type_counts = Counter(leave.leave_type.value for leave in leaves)
    leave_status_counts = Counter(leave.status.value for leave in leaves)

    daily_hours = Counter()
    daily_tasks = Counter()
    employee_hours = Counter()
    for log in logs:
        daily_hours[log.log_date.isoformat()] += float(log.hours_spent or 0)
        daily_tasks[log.log_date.isoformat()] += 1
        employee_hours[log.employee_id] += float(log.hours_spent or 0)

    completed_by_employee = Counter(
        task.assigned_to_id
        for task in tasks
        if task.status == TaskStatus.COMPLETED and task.assigned_to_id is not None
    )
    employee_by_id = {employee.id: employee for employee in employees}

    department_stats = []
    for department in departments:
        department_employees = [
            employee
            for employee in employees
            if employee.department_id == department.id
        ]
        department_tasks = [
            task for task in tasks if task.department_id == department.id
        ]
        department_hours = sum(
            employee_hours[employee.id] for employee in department_employees
        )
        department_stats.append(
            {
                "department": department.name,
                "employees": len(department_employees),
                "tasks": len(department_tasks),
                "hours": round(department_hours, 2),
            }
        )

    top_performers = []
    for employee_id, tasks_completed in completed_by_employee.most_common(10):
        employee = employee_by_id.get(employee_id)
        if employee is None:
            continue
        top_performers.append(
            {
                "employee_id": str(employee.id),
                "name": employee.full_name,
                "tasks_completed": tasks_completed,
                "hours": round(employee_hours[employee.id], 2),
            }
        )

    daily_activity = [
        {
            "date": (start_date + timedelta(days=offset)).isoformat(),
            "hours": round(daily_hours[(start_date + timedelta(days=offset)).isoformat()], 2),
            "tasks": daily_tasks[(start_date + timedelta(days=offset)).isoformat()],
        }
        for offset in range((date.today() - start_date).days + 1)
    ]

    return {
        "overview": {
            "total_employees": sum(
                employee.status == EmployeeStatus.ACTIVE for employee in employees
            ),
            "total_tasks": len(tasks),
            "completed_tasks": sum(
                task.status == TaskStatus.COMPLETED for task in tasks
            ),
            "total_hours": round(sum(daily_hours.values()), 2),
            "leave_requests": len(leaves),
            "approved_leaves": sum(leave.status == LeaveStatus.APPROVED for leave in leaves),
        },
        "tasks_by_status": [
            {"status": status.value, "count": task_status_counts[status.value]}
            for status in TaskStatus
        ],
        "tasks_by_priority": [
            {"priority": priority.value, "count": task_priority_counts[priority.value]}
            for priority in TaskPriority
        ],
        "leaves_by_type": [
            {"leave_type": leave_type.value, "count": leave_type_counts[leave_type.value]}
            for leave_type in LeaveType
        ],
        "leaves_by_status": [
            {"status": status.value, "count": leave_status_counts[status.value]}
            for status in LeaveStatus
        ],
        "daily_activity": daily_activity,
        "department_stats": department_stats,
        "top_performers": top_performers,
    }
