"""Audit log model for immutable audit trail."""

import uuid
from typing import Optional, Dict, Any

from sqlalchemy import (
    String, Text, ForeignKey, DateTime, Index, func, JSON
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, INET, JSONB
from sqlalchemy.event import listens_for

from app.models.base import BaseModel
from app.models.company import Company
from app.models.employee import Employee


class AuditLog(BaseModel):
    """
    Immutable audit log for security and compliance.

    Features:
    - Append-only (no updates/deletes via ORM)
    - Hash chaining for tamper evidence
    - Structured metadata for querying
    """

    __tablename__ = "audit_logs"

    company_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    employee_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("employees.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    action: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    resource_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    resource_id: Mapped[Optional[uuid.UUID]] = mapped_column(PG_UUID(as_uuid=True), nullable=True, index=True)

    ip_address: Mapped[Optional[str]] = mapped_column(INET, nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Structured metadata for flexible querying
    metadata_: Mapped[Dict[str, Any]] = mapped_column("metadata", JSONB, default=dict, nullable=False)

    def __init__(self, **kwargs: Any) -> None:
        """Accept the public ``metadata`` name while avoiding SQLAlchemy's reserved attribute."""
        if "metadata" in kwargs:
            kwargs["metadata_"] = kwargs.pop("metadata")
        super().__init__(**kwargs)

    # Hash chain for tamper evidence
    previous_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    current_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    # Relationships (read-only)
    company: Mapped[Optional[Company]] = relationship("Company", lazy="selectin")
    employee: Mapped[Optional[Employee]] = relationship("Employee", lazy="selectin")

    def __repr__(self) -> str:
        return f"<AuditLog(id={self.id}, action={self.action}, resource={self.resource_type}:{self.resource_id})>"

    @property
    def employee_name(self) -> Optional[str]:
        """Return the related employee name for response schemas."""
        return self.employee.full_name if self.employee else None


# Indexes
Index("ix_audit_logs_company_action", AuditLog.company_id, AuditLog.action)
Index("ix_audit_logs_employee_action", AuditLog.employee_id, AuditLog.action)
Index("ix_audit_logs_resource", AuditLog.resource_type, AuditLog.resource_id)
Index("ix_audit_logs_created", AuditLog.created_at.desc())


import hashlib
import json


def _compute_hash(log: AuditLog) -> str:
    """Compute hash for audit log entry."""
    data = {
        "id": str(log.id),
        "company_id": str(log.company_id) if log.company_id else None,
        "employee_id": str(log.employee_id) if log.employee_id else None,
        "action": log.action,
        "resource_type": log.resource_type,
        "resource_id": str(log.resource_id) if log.resource_id else None,
        "ip_address": log.ip_address,
        "user_agent": log.user_agent,
        "metadata": log.metadata_,
        "previous_hash": log.previous_hash,
        "created_at": log.created_at.isoformat() if log.created_at else None,
    }
    serialized = json.dumps(data, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode()).hexdigest()


@listens_for(AuditLog, "before_insert")
def _audit_log_before_insert(mapper, connection, target: AuditLog) -> None:
    """Set hash chain before insert."""
    # Get previous log's hash for this company
    if target.company_id:
        from sqlalchemy import select
        stmt = (
            select(AuditLog.current_hash)
            .where(AuditLog.company_id == target.company_id)
            .order_by(AuditLog.created_at.desc())
            .limit(1)
        )
        result = connection.execute(stmt).scalar_one_or_none()
        target.previous_hash = result

    # Compute current hash
    target.current_hash = _compute_hash(target)


# Prevent updates and deletes on audit logs
@listens_for(AuditLog, "before_update")
def _audit_log_before_update(mapper, connection, target: AuditLog) -> None:
    """Prevent updates to audit logs."""
    raise RuntimeError("Audit logs are immutable and cannot be updated")


@listens_for(AuditLog, "before_delete")
def _audit_log_before_delete(mapper, connection, target: AuditLog) -> None:
    """Prevent deletion of audit logs."""
    raise RuntimeError("Audit logs are immutable and cannot be deleted")


class AuditAction:
    """Standard audit action names."""

    # Auth
    LOGIN = "login"
    LOGOUT = "logout"
    LOGIN_FAILED = "login_failed"
    PASSWORD_CHANGED = "password_changed"
    PASSWORD_RESET_REQUESTED = "password_reset_requested"
    PASSWORD_RESET_COMPLETED = "password_reset_completed"
    SESSION_REVOKED = "session_revoked"
    SESSION_EXPIRED = "session_expired"

    # Company
    COMPANY_CREATED = "company_created"
    COMPANY_UPDATED = "company_updated"
    COMPANY_DELETED = "company_deleted"

    # Department
    DEPARTMENT_CREATED = "department_created"
    DEPARTMENT_UPDATED = "department_updated"
    DEPARTMENT_DELETED = "department_deleted"

    # Employee
    EMPLOYEE_CREATED = "employee_created"
    EMPLOYEE_UPDATED = "employee_updated"
    EMPLOYEE_DEACTIVATED = "employee_deactivated"
    EMPLOYEE_ROLE_CHANGED = "employee_role_changed"
    EMPLOYEE_PASSWORD_RESET = "employee_password_reset"
    EMPLOYEE_DELETED = "employee_deleted"
    PROFILE_UPDATED = "profile_updated"

    # Task
    TASK_CREATED = "task_created"
    TASK_UPDATED = "task_updated"
    TASK_DELETED = "task_deleted"
    TASK_ASSIGNED = "task_assigned"
    TASK_STATUS_CHANGED = "task_status_changed"

    # Daily Log
    DAILY_LOG_CREATED = "daily_log_created"
    DAILY_LOG_UPDATED = "daily_log_updated"
    DAILY_LOG_DELETED = "daily_log_deleted"

    # Leave
    LEAVE_REQUESTED = "leave_requested"
    LEAVE_APPROVED = "leave_approved"
    LEAVE_REJECTED = "leave_rejected"
    LEAVE_CANCELLED = "leave_cancelled"

    # Data Access
    DATA_EXPORTED = "data_exported"
    DATA_ACCESSED = "data_accessed"

    # Security
    PERMISSION_DENIED = "permission_denied"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
