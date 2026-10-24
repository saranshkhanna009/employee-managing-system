"""Authentication service with session management."""

import secrets
import hashlib
import uuid
import json
from datetime import datetime, timezone, timedelta
from typing import Annotated, Optional, List, Tuple, Dict, Any

from fastapi import Depends
from sqlalchemy import select, delete, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.database import get_db
from app.models.employee import Employee, EmployeeRole, EmployeeStatus
from app.models.session import Session
from app.models.company import Company
from app.models.audit import AuditLog, AuditAction
from app.models.task import Task, TaskStatus
from app.models.daily_log import DailyLog
from app.models.leave import LeaveRequest, LeaveStatus
from app.models.department import Department
from app.utils.passwords import hash_password, verify_password, validate_password_strength
from app.services.encryption import get_encryption_service


class AuthError(Exception):
    """Authentication error."""
    pass


class AccountLockedError(AuthError):
    """Account temporarily locked."""
    pass


class InvalidCredentialsError(AuthError):
    """Invalid credentials."""
    pass


class AuthService:
    """Authentication and session management service."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.encryption = get_encryption_service()

    async def register_company(self, data: dict) -> Tuple[Company, Employee]:
        """
        Register a new company with super admin.

        Args:
            data: Registration data

        Returns:
            Tuple of (Company, Super Admin Employee)
        """
        # Check if slug exists
        existing = await self.db.execute(
            select(Company).where(Company.slug == data["company_slug"])
        )
        if existing.scalar_one_or_none():
            raise AuthError("Company slug already exists")

        # Check if email exists
        existing_email = await self.db.execute(
            select(Employee).where(Employee._email_encrypted == self.encryption.encrypt(data["admin_email"], "email"))
        )
        if existing_email.scalar_one_or_none():
            raise AuthError("Email already registered")

        # Validate password
        errors = validate_password_strength(data["admin_password"])
        if errors:
            raise AuthError(f"Password validation failed: {', '.join(errors)}")

        # Create company
        company = Company(
            name=data["company_name"],
            slug=data["company_slug"],
            email=data["admin_email"],
            phone=data.get("admin_phone"),
        )
        self.db.add(company)
        await self.db.flush()

        # Generate admin ID for super admin
        admin_id = f"{settings.ADMIN_ID_PREFIX}-{company.slug}-0001"

        # Create super admin employee
        super_admin = Employee(
            company_id=company.id,
            company=company,
            employee_id=admin_id,
            email=data["admin_email"],
            first_name=data["admin_first_name"],
            last_name=data["admin_last_name"],
            phone=data.get("admin_phone"),
            role=EmployeeRole.SUPER_ADMIN,
            status=EmployeeStatus.ACTIVE,
        )
        super_admin.set_password(data["admin_password"])
        self.db.add(super_admin)

        # Create default department
        from app.models.department import Department
        default_dept = Department(
            company_id=company.id,
            name="General",
            description="Default department",
            sort_order=0,
        )
        self.db.add(default_dept)
        await self.db.flush()

        # Assign super admin to default department
        super_admin.department_id = default_dept.id

        # Audit log
        await self._log_audit(
            company_id=company.id,
            employee_id=super_admin.id,
            action=AuditAction.COMPANY_CREATED,
            resource_type="company",
            resource_id=company.id,
            metadata={"slug": company.slug},
        )
        await self._log_audit(
            company_id=company.id,
            employee_id=super_admin.id,
            action=AuditAction.EMPLOYEE_CREATED,
            resource_type="employee",
            resource_id=super_admin.id,
            metadata={"role": "super_admin", "employee_id": admin_id},
        )

        await self.db.commit()
        return company, super_admin

    async def authenticate(
        self,
        employee_id: str,
        password: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        remember_me: bool = False,
    ) -> Tuple[Employee, Session, str]:
        """
        Authenticate employee and create session.

        Args:
            employee_id: Admin ID
            password: Password
            ip_address: Client IP
            user_agent: Client user agent
            remember_me: Extend session to 30 days

        Returns:
            Tuple of (Employee, Session, session_token)
        """
        # Find employee by employee_id
        stmt = select(Employee).where(Employee.employee_id == employee_id)
        result = await self.db.execute(stmt)
        employee = result.scalar_one_or_none()

        if not employee:
            await self._log_audit(
                action=AuditAction.LOGIN_FAILED,
                metadata={"employee_id": employee_id, "reason": "not_found"},
                ip_address=ip_address,
                user_agent=user_agent,
            )
            raise InvalidCredentialsError("Invalid credentials")

        # Check if account is locked
        if employee.locked_until and employee.locked_until > datetime.now(timezone.utc):
            await self._log_audit(
                company_id=employee.company_id,
                employee_id=employee.id,
                action=AuditAction.LOGIN_FAILED,
                metadata={"reason": "account_locked"},
                ip_address=ip_address,
                user_agent=user_agent,
            )
            raise AccountLockedError("Account temporarily locked. Try again later.")

        # Check status
        if employee.status != EmployeeStatus.ACTIVE:
            await self._log_audit(
                company_id=employee.company_id,
                employee_id=employee.id,
                action=AuditAction.LOGIN_FAILED,
                metadata={"reason": f"status_{employee.status.value}"},
                ip_address=ip_address,
                user_agent=user_agent,
            )
            raise InvalidCredentialsError("Account not active")

        # Verify password
        if not employee.check_password(password):
            # Increment failed attempts
            employee.failed_login_attempts += 1
            if employee.failed_login_attempts >= 5:
                employee.locked_until = datetime.now(timezone.utc) + timedelta(minutes=15)
                employee.status = EmployeeStatus.LOCKED

            await self.db.commit()

            await self._log_audit(
                company_id=employee.company_id,
                employee_id=employee.id,
                action=AuditAction.LOGIN_FAILED,
                metadata={"attempts": employee.failed_login_attempts},
                ip_address=ip_address,
                user_agent=user_agent,
            )
            raise InvalidCredentialsError("Invalid credentials")

        # Reset failed attempts on successful login
        employee.failed_login_attempts = 0
        employee.locked_until = None
        employee.status = EmployeeStatus.ACTIVE
        employee.last_login = datetime.now(timezone.utc)

        # Determine session TTL
        ttl = settings.SESSION_TTL_SECONDS * (30 * 24 * 60 * 60 // settings.SESSION_TTL_SECONDS) if remember_me else settings.SESSION_TTL_SECONDS

        # Check concurrent sessions
        await self._enforce_session_limit(employee.id)

        # Create session
        session = Session(
            employee_id=employee.id,
            ip_address=ip_address,
            user_agent=user_agent,
            device_fingerprint=self._generate_device_fingerprint(user_agent),
        )
        token = session.generate_token()
        session.expires_at = datetime.now(timezone.utc) + timedelta(seconds=ttl)
        self.db.add(session)

        # Audit log
        await self._log_audit(
            company_id=employee.company_id,
            employee_id=employee.id,
            action=AuditAction.LOGIN,
            ip_address=ip_address,
            user_agent=user_agent,
            metadata={"remember_me": remember_me, "session_id": str(session.id)},
        )

        await self.db.commit()
        return employee, session, token

    async def logout(self, session: Session, revoke_all: bool = False) -> None:
        """
        Logout and revoke session(s).

        Args:
            session: Current session
            revoke_all: Revoke all sessions for this employee
        """
        if revoke_all:
            stmt = select(Session).where(
                Session.employee_id == session.employee_id,
                Session.revoked_at.is_(None)
            )
            result = await self.db.execute(stmt)
            sessions = result.scalars().all()
            for s in sessions:
                s.revoke()
            await self._log_audit(
                company_id=session.employee.company_id,
                employee_id=session.employee_id,
                action=AuditAction.SESSION_REVOKED,
                metadata={"revoke_all": True, "count": len(sessions)},
                ip_address=session.ip_address,
                user_agent=session.user_agent,
            )
        else:
            session.revoke()
            await self._log_audit(
                company_id=session.employee.company_id,
                employee_id=session.employee_id,
                action=AuditAction.LOGOUT,
                metadata={"session_id": str(session.id)},
                ip_address=session.ip_address,
                user_agent=session.user_agent,
            )

        await self.db.commit()

    async def refresh_session(self, session: Session) -> Session:
        """
        Refresh session expiry.

        Args:
            session: Current session

        Returns:
            Updated session
        """
        if not session.is_valid():
            raise AuthError("Session expired or revoked")

        ttl = settings.SESSION_TTL_SECONDS
        session.extend(ttl)
        session.update_activity()

        await self.db.commit()
        return session

    async def validate_session(self, token: str) -> Optional[Session]:
        """
        Validate session token and return session with employee.

        Args:
            token: Session token

        Returns:
            Session with employee loaded, or None if invalid
        """
        token_hash = hashlib.sha256(token.encode()).digest()

        stmt = (
            select(Session)
            .options(selectinload(Session.employee).selectinload(Employee.company))
            .where(Session._session_token_hash == token_hash)
        )
        result = await self.db.execute(stmt)
        session = result.scalar_one_or_none()

        if not session or not session.is_valid():
            return None

        # Update last activity
        session.update_activity()
        await self.db.commit()

        return session

    async def change_password(
        self,
        employee: Employee,
        current_password: str,
        new_password: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> None:
        """
        Change password for authenticated employee.

        Args:
            employee: Employee instance
            current_password: Current password
            new_password: New password
        """
        errors = validate_password_strength(new_password)
        if errors:
            raise AuthError(f"Password validation failed: {', '.join(errors)}")

        if not employee.check_password(current_password):
            raise InvalidCredentialsError("Current password is incorrect")

        employee.set_password(new_password)

        # Revoke all other sessions for security
        stmt = select(Session).where(
            Session.employee_id == employee.id,
            Session.revoked_at.is_(None),
        )
        result = await self.db.execute(stmt)
        sessions = result.scalars().all()
        for s in sessions:
            s.revoke()

        await self._log_audit(
            company_id=employee.company_id,
            employee_id=employee.id,
            action=AuditAction.PASSWORD_CHANGED,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        await self.db.commit()

    async def admin_reset_password(
        self,
        admin: Employee,
        target_employee: Employee,
        new_password: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> None:
        """
        Admin reset password for another employee.

        Args:
            admin: Admin performing reset
            target_employee: Employee to reset
            new_password: New password
        """
        if not admin.can_manage(target_employee):
            raise AuthError("Insufficient permissions")

        errors = validate_password_strength(new_password)
        if errors:
            raise AuthError(f"Password validation failed: {', '.join(errors)}")

        target_employee.set_password(new_password)

        # Revoke all sessions for security
        stmt = select(Session).where(
            Session.employee_id == target_employee.id,
            Session.revoked_at.is_(None),
        )
        result = await self.db.execute(stmt)
        sessions = result.scalars().all()
        for s in sessions:
            s.revoke()

        await self._log_audit(
            company_id=admin.company_id,
            employee_id=admin.id,
            action=AuditAction.EMPLOYEE_PASSWORD_RESET,
            resource_type="employee",
            resource_id=target_employee.id,
            metadata={"target_employee_id": target_employee.employee_id},
            ip_address=ip_address,
            user_agent=user_agent,
        )

        await self.db.commit()

    async def get_active_sessions(self, employee_id: uuid.UUID) -> List[Session]:
        """Get all active sessions for an employee."""
        stmt = select(Session).where(
            Session.employee_id == employee_id,
            Session.revoked_at.is_(None),
            Session.expires_at > datetime.now(timezone.utc),
        ).order_by(Session.last_activity.desc())
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def _enforce_session_limit(self, employee_id: uuid.UUID) -> None:
        """Enforce maximum concurrent sessions per employee."""
        stmt = select(Session).where(
            Session.employee_id == employee_id,
            Session.revoked_at.is_(None),
            Session.expires_at > datetime.now(timezone.utc),
        ).order_by(Session.last_activity.asc())
        result = await self.db.execute(stmt)
        sessions = result.scalars().all()

        max_sessions = settings.SESSION_MAX_CONCURRENT
        if len(sessions) >= max_sessions:
            # Revoke oldest session
            oldest = sessions[0]
            oldest.revoke()

    def _generate_device_fingerprint(self, user_agent: Optional[str]) -> str:
        """Generate a simple device fingerprint from user agent."""
        if not user_agent:
            return secrets.token_hex(16)
        return hashlib.sha256(user_agent.encode()).hexdigest()[:32]

    async def _log_audit(
        self,
        action: str,
        company_id: Optional[uuid.UUID] = None,
        employee_id: Optional[uuid.UUID] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[uuid.UUID] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> None:
        """Create audit log entry."""
        audit = AuditLog(
            company_id=company_id,
            employee_id=employee_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            ip_address=ip_address,
            user_agent=user_agent,
            metadata=metadata or {},
        )
        self.db.add(audit)

    async def update_profile(
        self,
        employee: Employee,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        phone: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Employee:
        """Update employee profile."""
        old_data = {}
        if first_name is not None:
            old_data["first_name"] = employee.first_name
            employee.first_name = first_name
        if last_name is not None:
            old_data["last_name"] = employee.last_name
            employee.last_name = last_name
        if phone is not None:
            old_data["phone"] = employee.phone
            employee.phone = phone

        await self._log_audit(
            company_id=employee.company_id,
            employee_id=employee.id,
            action=AuditAction.PROFILE_UPDATED,
            ip_address=ip_address,
            user_agent=user_agent,
            metadata={"fields_updated": list(old_data.keys()), "old_values": {k: str(v) for k, v in old_data.items()}},
        )

        await self.db.commit()
        await self.db.refresh(employee)
        return employee

    async def delete_account(
        self,
        employee: Employee,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> None:
        """Delete employee account (GDPR right to erasure)."""
        company_id = employee.company_id
        employee_id = employee.id
        employee_name = employee.employee_id

        # Revoke all sessions
        stmt = select(Session).where(
            Session.employee_id == employee.id,
            Session.revoked_at.is_(None),
        )
        result = await self.db.execute(stmt)
        sessions = result.scalars().all()
        for s in sessions:
            s.revoke()

        # Delete employee (hard delete for GDPR)
        await self.db.delete(employee)

        await self._log_audit(
            company_id=company_id,
            employee_id=employee_id,
            action=AuditAction.EMPLOYEE_DELETED,
            resource_type="employee",
            resource_id=employee_id,
            ip_address=ip_address,
            user_agent=user_agent,
            metadata={"employee_id": employee_name},
        )

        await self.db.commit()

    async def export_employee_data(self, employee: Employee) -> Dict[str, Any]:
        """Export all data for an employee (GDPR right to data portability)."""
        # Get tasks
        tasks_result = await self.db.execute(
            select(Task).where(
                (Task.assigned_to_id == employee.id) | (Task.created_by_id == employee.id)
            )
        )
        tasks = tasks_result.scalars().all()

        # Get daily logs
        logs_result = await self.db.execute(
            select(DailyLog).where(DailyLog.employee_id == employee.id)
        )
        logs = logs_result.scalars().all()

        # Get leave requests
        leaves_result = await self.db.execute(
            select(LeaveRequest).where(LeaveRequest.employee_id == employee.id)
        )
        leaves = leaves_result.scalars().all()

        return {
            "employee": {
                "employee_id": employee.employee_id,
                "email": employee.email,
                "first_name": employee.first_name,
                "last_name": employee.last_name,
                "phone": employee.phone,
                "role": employee.role.value,
                "status": employee.status.value,
                "department": employee.department.name if employee.department else None,
                "created_at": employee.created_at.isoformat() if employee.created_at else None,
                "last_login": employee.last_login.isoformat() if employee.last_login else None,
            },
            "tasks": [
                {
                    "id": str(t.id),
                    "title": t.title,
                    "description": t.description,
                    "status": t.status.value,
                    "priority": t.priority.value,
                    "due_date": t.due_date.isoformat() if t.due_date else None,
                    "created_at": t.created_at.isoformat() if t.created_at else None,
                    "completed_at": t.completed_at.isoformat() if t.completed_at else None,
                }
                for t in tasks
            ],
            "daily_logs": [
                {
                    "id": str(l.id),
                    "task_id": str(l.task_id) if l.task_id else None,
                    "log_date": l.log_date.isoformat(),
                    "hours_spent": float(l.hours_spent) if l.hours_spent else None,
                    "progress_notes": l.progress_notes,
                    "status": l.status.value,
                    "created_at": l.created_at.isoformat() if l.created_at else None,
                }
                for l in logs
            ],
            "leave_requests": [
                {
                    "id": str(l.id),
                    "leave_type": l.leave_type.value,
                    "start_date": l.start_date.isoformat(),
                    "end_date": l.end_date.isoformat(),
                    "reason": l.reason,
                    "status": l.status.value,
                    "reviewed_at": l.reviewed_at.isoformat() if l.reviewed_at else None,
                    "created_at": l.created_at.isoformat() if l.created_at else None,
                }
                for l in leaves
            ],
        }

    async def revoke_session(
        self,
        employee: Employee,
        session_id: uuid.UUID,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> bool:
        """Revoke a specific session by ID."""
        stmt = select(Session).where(
            Session.id == session_id,
            Session.employee_id == employee.id,
        )
        result = await self.db.execute(stmt)
        session = result.scalar_one_or_none()

        if not session:
            return False

        if session.revoked_at:
            return True  # Already revoked

        session.revoke()
        await self._log_audit(
            company_id=employee.company_id,
            employee_id=employee.id,
            action=AuditAction.SESSION_REVOKED,
            resource_type="session",
            resource_id=session_id,
            ip_address=ip_address,
            user_agent=user_agent,
            metadata={"session_id": str(session_id)},
        )
        await self.db.commit()
        return True

    async def revoke_all_sessions(
        self,
        employee: Employee,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> int:
        """Revoke all sessions for an employee."""
        stmt = select(Session).where(
            Session.employee_id == employee.id,
            Session.revoked_at.is_(None),
        )
        result = await self.db.execute(stmt)
        sessions = result.scalars().all()

        count = 0
        for s in sessions:
            s.revoke()
            count += 1

        if count > 0:
            await self._log_audit(
                company_id=employee.company_id,
                employee_id=employee.id,
                action=AuditAction.SESSION_REVOKED,
                ip_address=ip_address,
                user_agent=user_agent,
                metadata={"revoke_all": True, "count": count},
            )
            await self.db.commit()

        return count


async def get_auth_service(db: Annotated[AsyncSession, Depends(get_db)]) -> AuthService:
    """Get auth service instance."""
    return AuthService(db)
