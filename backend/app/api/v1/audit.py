"""Audit log API routes."""

from typing import Annotated
from uuid import UUID
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.responses import StreamingResponse
import io

from app.api.deps import (
    DBSession,
    AuditSvc,
    get_current_employee,
    RequireAdmin,
)
from app.api.route import SnakeCaseAPIRoute
from app.schemas.audit import AuditLogResponse, AuditLogListResponse, AuditLogQuery
from app.models.employee import Employee, EmployeeRole


router = APIRouter(prefix="/audit", tags=["Audit Logs"], route_class=SnakeCaseAPIRoute)


@router.get("", response_model=AuditLogListResponse)
async def query_audit_logs(
    query: Annotated[AuditLogQuery, Depends()],
    audit_service: AuditSvc,
    admin: RequireAdmin,
) -> AuditLogListResponse:
    """Query audit logs with filters."""
    try:
        logs, total = await audit_service.query(admin, query)
        return AuditLogListResponse(
            items=[AuditLogResponse.model_validate(l, from_attributes=True) for l in logs],
            total=total,
            page=query.page,
            page_size=query.page_size,
            total_pages=(total + query.page_size - 1) // query.page_size,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.get("/actions", response_model=list[str])
async def get_audit_actions(
    audit_service: AuditSvc,
    admin: RequireAdmin,
) -> list[str]:
    """Get distinct audit actions for admin's company."""
    return await audit_service.get_actions(admin.company_id)


@router.get("/resource-types", response_model=list[str])
async def get_audit_resource_types(
    audit_service: AuditSvc,
    admin: RequireAdmin,
) -> list[str]:
    """Get distinct resource types for admin's company."""
    return await audit_service.get_resource_types(admin.company_id)


@router.get("/verify-integrity")
async def verify_audit_integrity(
    audit_service: AuditSvc,
    admin: RequireAdmin,
) -> dict:
    """Verify audit log hash chain integrity."""
    return await audit_service.verify_integrity(admin.company_id)


@router.get("/export")
async def export_audit_logs(
    audit_service: AuditSvc,
    admin: RequireAdmin,
    company_id: UUID | None = Query(None),
    start_date: datetime | None = Query(None),
    end_date: datetime | None = Query(None),
) -> StreamingResponse:
    """Export audit logs as JSON for compliance."""
    try:
        target_company_id = company_id or admin.company_id

        # Verify permissions
        if admin.role == EmployeeRole.ADMIN and admin.company_id != target_company_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")

        logs = await audit_service.export_logs(admin, target_company_id, start_date, end_date)

        import json
        data = [AuditLogResponse.model_validate(l, from_attributes=True).model_dump() for l in logs]
        json_data = json.dumps(data, indent=2, default=str)

        return StreamingResponse(
            io.BytesIO(json_data.encode()),
            media_type="application/json",
            headers={
                "Content-Disposition": f"attachment; filename=audit_logs_{target_company_id}_{datetime.now().strftime('%Y%m%d')}.json"
            },
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
