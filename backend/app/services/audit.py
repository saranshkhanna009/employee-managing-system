"""Audit log service."""

from typing import Annotated, Optional, List
from uuid import UUID
from datetime import datetime

from fastapi import Depends
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog, AuditAction
from app.models.employee import Employee, EmployeeRole
from app.schemas.audit import AuditLogQuery
from app.database import get_db


class AuditService:
    """Audit log query service."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def query(
        self,
        actor: Employee,
        query: AuditLogQuery,
    ) -> tuple[List[AuditLog], int]:
        """Query audit logs with filters."""
        # Only admins can query audit logs
        if not actor.is_admin_or_above():
            raise ValueError("Insufficient permissions")

        # Build base query
        stmt = select(AuditLog)

        # Company scope
        if actor.role == EmployeeRole.ADMIN:
            stmt = stmt.where(AuditLog.company_id == actor.company_id)
        elif actor.role == EmployeeRole.SUPER_ADMIN:
            # Super admin can see all, but filter by company if specified
            if query.company_id:
                stmt = stmt.where(AuditLog.company_id == UUID(query.company_id))
        else:
            raise ValueError("Insufficient permissions")

        if query.employee_id:
            stmt = stmt.where(AuditLog.employee_id == UUID(query.employee_id))

        if query.action:
            stmt = stmt.where(AuditLog.action == query.action)

        if query.resource_type:
            stmt = stmt.where(AuditLog.resource_type == query.resource_type)

        if query.resource_id:
            stmt = stmt.where(AuditLog.resource_id == UUID(query.resource_id))

        if query.start_date:
            stmt = stmt.where(AuditLog.created_at >= query.start_date)

        if query.end_date:
            stmt = stmt.where(AuditLog.created_at <= query.end_date)

        # Count total
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = await self.db.scalar(count_stmt) or 0

        # Paginate
        stmt = stmt.order_by(AuditLog.created_at.desc())
        stmt = stmt.offset((query.page - 1) * query.page_size).limit(query.page_size)

        result = await self.db.execute(stmt)
        logs = result.scalars().all()

        return list(logs), total

    async def get_actions(self, company_id: UUID) -> List[str]:
        """Get distinct audit actions for a company."""
        stmt = select(AuditLog.action).where(AuditLog.company_id == company_id).distinct()
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_resource_types(self, company_id: UUID) -> List[str]:
        """Get distinct resource types for a company."""
        stmt = select(AuditLog.resource_type).where(
            AuditLog.company_id == company_id,
            AuditLog.resource_type.is_not(None),
        ).distinct()
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def verify_integrity(self, company_id: UUID) -> dict:
        """Verify audit log hash chain integrity."""
        stmt = select(AuditLog).where(AuditLog.company_id == company_id).order_by(AuditLog.created_at)
        result = await self.db.execute(stmt)
        logs = result.scalars().all()

        import hashlib
        import json

        def compute_hash(log: AuditLog) -> str:
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

        broken_chain = []
        previous_hash = None

        for i, log in enumerate(logs):
            computed_hash = compute_hash(log)

            if log.previous_hash != previous_hash:
                broken_chain.append({
                    "index": i,
                    "log_id": str(log.id),
                    "issue": "previous_hash_mismatch",
                    "expected": previous_hash,
                    "actual": log.previous_hash,
                })

            if log.current_hash != computed_hash:
                broken_chain.append({
                    "index": i,
                    "log_id": str(log.id),
                    "issue": "current_hash_mismatch",
                    "expected": computed_hash,
                    "actual": log.current_hash,
                })

            previous_hash = log.current_hash

        return {
            "total_logs": len(logs),
            "verified": len(broken_chain) == 0,
            "issues": broken_chain,
        }

    async def export_logs(
        self,
        actor: Employee,
        company_id: UUID,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[AuditLog]:
        """Export audit logs for compliance."""
        if not actor.is_admin_or_above():
            raise ValueError("Insufficient permissions")

        if actor.role == EmployeeRole.ADMIN and actor.company_id != company_id:
            raise ValueError("Insufficient permissions")

        stmt = select(AuditLog).where(AuditLog.company_id == company_id)

        if start_date:
            stmt = stmt.where(AuditLog.created_at >= start_date)

        if end_date:
            stmt = stmt.where(AuditLog.created_at <= end_date)

        stmt = stmt.order_by(AuditLog.created_at)

        result = await self.db.execute(stmt)
        return list(result.scalars().all())


async def get_audit_service(db: Annotated[AsyncSession, Depends(get_db)]) -> AuditService:
    """Get audit service instance."""
    return AuditService(db)
