"""Company service."""

from typing import Annotated, Optional, List
from uuid import UUID

from fastapi import Depends
from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.company import Company
from app.models.audit import AuditLog, AuditAction
from app.schemas.company import CompanyCreate, CompanyUpdate
from app.services.auth import AuthService
from app.database import get_db


class CompanyService:
    """Company management service."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, data: CompanyCreate, actor_id: UUID) -> Company:
        """Create a new company (super admin only)."""
        # Check slug uniqueness
        existing = await self.db.execute(select(Company).where(Company.slug == data.slug))
        if existing.scalar_one_or_none():
            raise ValueError("Company slug already exists")

        company = Company(
            name=data.name,
            slug=data.slug,
            email=data.email,
            phone=data.phone,
            address=data.address,
        )
        self.db.add(company)
        await self.db.flush()

        await self._log_audit(
            company_id=company.id,
            employee_id=actor_id,
            action=AuditAction.COMPANY_CREATED,
            resource_type="company",
            resource_id=company.id,
            metadata={"slug": company.slug, "name": company.name},
        )

        await self.db.commit()
        await self.db.refresh(company)
        return company

    async def get_by_id(self, company_id: UUID) -> Optional[Company]:
        """Get company by ID."""
        stmt = select(Company).where(Company.id == company_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_slug(self, slug: str) -> Optional[Company]:
        """Get company by slug."""
        stmt = select(Company).where(Company.slug == slug)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_for_employee(self, employee_id: UUID) -> Optional[Company]:
        """Get company for an employee."""
        from app.models.employee import Employee
        stmt = (
            select(Company)
            .join(Employee, Employee.company_id == Company.id)
            .where(Employee.id == employee_id)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def update(self, company: Company, data: CompanyUpdate, actor_id: UUID) -> Company:
        """Update company."""
        update_data = data.model_dump(exclude_unset=True)
        old_data = {k: getattr(company, k) for k in update_data.keys()}

        for key, value in update_data.items():
            setattr(company, key, value)

        await self._log_audit(
            company_id=company.id,
            employee_id=actor_id,
            action=AuditAction.COMPANY_UPDATED,
            resource_type="company",
            resource_id=company.id,
            metadata={"old": old_data, "new": update_data},
        )

        await self.db.commit()
        await self.db.refresh(company)
        return company

    async def delete(self, company: Company, actor_id: UUID) -> None:
        """Delete company (GDPR - hard delete with audit trail)."""
        await self._log_audit(
            company_id=company.id,
            employee_id=actor_id,
            action=AuditAction.COMPANY_DELETED,
            resource_type="company",
            resource_id=company.id,
            metadata={"slug": company.slug, "name": company.name},
        )

        await self.db.delete(company)
        await self.db.commit()

    async def list_companies(
        self,
        page: int = 1,
        page_size: int = 20,
        search: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> tuple[List[Company], int]:
        """List companies with pagination."""
        stmt = select(Company)

        if search:
            stmt = stmt.where(Company.name.ilike(f"%{search}%"))
        if is_active is not None:
            stmt = stmt.where(Company.is_active == is_active)

        # Count total
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = await self.db.scalar(count_stmt) or 0

        # Paginate
        stmt = stmt.order_by(Company.created_at.desc())
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)

        result = await self.db.execute(stmt)
        companies = result.scalars().all()

        return list(companies), total

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


async def get_company_service(db: Annotated[AsyncSession, Depends(get_db)]) -> CompanyService:
    """Get company service instance."""
    return CompanyService(db)
