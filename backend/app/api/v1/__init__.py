"""API v1 routes."""

from app.api.v1 import auth, company, departments, employees, tasks, daily_logs, leaves, audit, analytics

__all__ = ["auth", "company", "departments", "employees", "tasks", "daily_logs", "leaves", "audit", "analytics"]
