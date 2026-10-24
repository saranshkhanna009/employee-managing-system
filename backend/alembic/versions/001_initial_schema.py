"""Initial schema

Revision ID: 001
Revises:
Create Date: 2026-10-10 00:00:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Enable UUID extension
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
    op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto"')

    # Companies table
    op.create_table(
        'companies',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('slug', sa.String(100), nullable=False),
        sa.Column('email_encrypted', postgresql.BYTEA(), nullable=False),
        sa.Column('phone_encrypted', postgresql.BYTEA(), nullable=True),
        sa.Column('address_encrypted', postgresql.BYTEA(), nullable=True),
        sa.Column('subscription_tier', sa.String(50), server_default='free', nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('slug'),
    )
    op.create_index('ix_companies_slug_active', 'companies', ['slug', 'is_active'])
    op.create_index('ix_companies_name_active', 'companies', ['name', 'is_active'])

    # Departments table
    op.create_table(
        'departments',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('company_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('parent_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('sort_order', sa.Integer(), server_default='0', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['parent_id'], ['departments.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_departments_company_parent', 'departments', ['company_id', 'parent_id'])
    op.create_index('ix_departments_company_sort', 'departments', ['company_id', 'sort_order'])

    # Employees table
    op.create_table(
        'employees',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('company_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('department_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('employee_id', sa.String(50), nullable=False),
        sa.Column('email_encrypted', postgresql.BYTEA(), nullable=False),
        sa.Column('password_hash', postgresql.BYTEA(), nullable=False),
        sa.Column('first_name_encrypted', postgresql.BYTEA(), nullable=False),
        sa.Column('last_name_encrypted', postgresql.BYTEA(), nullable=False),
        sa.Column('phone_encrypted', postgresql.BYTEA(), nullable=True),
        sa.Column('role', sa.String(50), server_default='employee', nullable=False),
        sa.Column('status', sa.String(50), server_default='active', nullable=False),
        sa.Column('last_login', sa.DateTime(timezone=True), nullable=True),
        sa.Column('failed_login_attempts', sa.Integer(), server_default='0', nullable=False),
        sa.Column('locked_until', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['department_id'], ['departments.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('employee_id'),
    )
    op.create_index('ix_employees_company_dept', 'employees', ['company_id', 'department_id'])
    op.create_index('ix_employees_company_role', 'employees', ['company_id', 'role'])
    op.create_index('ix_employees_status_active', 'employees', ['status'])

    # Tasks table
    op.create_table(
        'tasks',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('company_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('department_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('assigned_to_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_by_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('description_encrypted', postgresql.BYTEA(), nullable=True),
        sa.Column('status', sa.String(50), server_default='pending', nullable=False),
        sa.Column('priority', sa.String(20), server_default='medium', nullable=False),
        sa.Column('due_date', sa.Date(), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('estimated_hours', sa.Numeric(5, 2), nullable=True),
        sa.Column('actual_hours', sa.Numeric(5, 2), server_default='0', nullable=False),
        sa.Column('sort_order', sa.Integer(), server_default='0', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['department_id'], ['departments.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['assigned_to_id'], ['employees.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['created_by_id'], ['employees.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_tasks_company_dept_status', 'tasks', ['company_id', 'department_id', 'status'])
    op.create_index('ix_tasks_assignee_status', 'tasks', ['assigned_to_id', 'status'])
    op.create_index('ix_tasks_due_date_status', 'tasks', ['due_date', 'status'])
    op.create_index('ix_tasks_created_by', 'tasks', ['created_by_id'])

    # Daily logs table
    op.create_table(
        'daily_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('employee_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('task_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('log_date', sa.Date(), nullable=False),
        sa.Column('hours_spent', sa.Numeric(4, 2), nullable=True),
        sa.Column('progress_notes_encrypted', postgresql.BYTEA(), nullable=True),
        sa.Column('status', sa.String(50), server_default='in_progress', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['employee_id'], ['employees.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['task_id'], ['tasks.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_daily_logs_employee_date', 'daily_logs', ['employee_id', 'log_date'], unique=True)
    op.create_index('ix_daily_logs_task_date', 'daily_logs', ['task_id', 'log_date'])
    op.create_index('ix_daily_logs_date_status', 'daily_logs', ['log_date', 'status'])

    # Leave requests table
    op.create_table(
        'leave_requests',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('employee_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('leave_type', sa.String(50), nullable=False),
        sa.Column('start_date', sa.Date(), nullable=False),
        sa.Column('end_date', sa.Date(), nullable=False),
        sa.Column('reason_encrypted', postgresql.BYTEA(), nullable=True),
        sa.Column('status', sa.String(50), server_default='pending', nullable=False),
        sa.Column('reviewed_by_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('review_notes_encrypted', postgresql.BYTEA(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['employee_id'], ['employees.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['reviewed_by_id'], ['employees.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_leave_requests_employee_status', 'leave_requests', ['employee_id', 'status'])
    op.create_index('ix_leave_requests_dates', 'leave_requests', ['start_date', 'end_date'])

    # Sessions table
    op.create_table(
        'sessions',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('employee_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('session_token_hash', postgresql.BYTEA(), nullable=False),
        sa.Column('ip_address', postgresql.INET(), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('device_fingerprint', sa.String(64), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_activity', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['employee_id'], ['employees.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_sessions_employee_expires', 'sessions', ['employee_id', 'expires_at'])
    op.create_index('ix_sessions_device_active', 'sessions', ['device_fingerprint', 'revoked_at'])
    op.create_index('ix_sessions_cleanup', 'sessions', ['expires_at', 'revoked_at'])

    # Audit logs table
    op.create_table(
        'audit_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('company_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('employee_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('action', sa.String(100), nullable=False),
        sa.Column('resource_type', sa.String(50), nullable=True),
        sa.Column('resource_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('ip_address', postgresql.INET(), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('metadata', postgresql.JSONB(), server_default='{}', nullable=False),
        sa.Column('previous_hash', sa.String(64), nullable=True),
        sa.Column('current_hash', sa.String(64), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['employee_id'], ['employees.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_audit_logs_company_action', 'audit_logs', ['company_id', 'action'])
    op.create_index('ix_audit_logs_employee_action', 'audit_logs', ['employee_id', 'action'])
    op.create_index('ix_audit_logs_resource', 'audit_logs', ['resource_type', 'resource_id'])
    op.create_index('ix_audit_logs_created', 'audit_logs', ['created_at'])
    op.create_index('ix_audit_logs_hash_chain', 'audit_logs', ['current_hash'])

    # Enable Row Level Security
    op.execute('ALTER TABLE employees ENABLE ROW LEVEL SECURITY')
    op.execute('ALTER TABLE tasks ENABLE ROW LEVEL SECURITY')
    op.execute('ALTER TABLE daily_logs ENABLE ROW LEVEL SECURITY')
    op.execute('ALTER TABLE leave_requests ENABLE ROW LEVEL SECURITY')

    # RLS Policies for employees
    op.execute("""
        CREATE POLICY employee_company_isolation ON employees
        FOR ALL USING (
            company_id = current_setting('app.current_company_id', true)::uuid
        )
    """)

    # RLS Policies for tasks
    op.execute("""
        CREATE POLICY task_company_isolation ON tasks
        FOR ALL USING (
            company_id = current_setting('app.current_company_id', true)::uuid
        )
    """)

    # RLS Policies for daily_logs
    op.execute("""
        CREATE POLICY daily_log_company_isolation ON daily_logs
        FOR ALL USING (
            employee_id IN (
                SELECT id FROM employees WHERE company_id = current_setting('app.current_company_id', true)::uuid
            )
        )
    """)

    # RLS Policies for leave_requests
    op.execute("""
        CREATE POLICY leave_company_isolation ON leave_requests
        FOR ALL USING (
            employee_id IN (
                SELECT id FROM employees WHERE company_id = current_setting('app.current_company_id', true)::uuid
            )
        )
    """)


def downgrade() -> None:
    # Drop RLS policies
    op.execute('DROP POLICY IF EXISTS employee_company_isolation ON employees')
    op.execute('DROP POLICY IF EXISTS task_company_isolation ON tasks')
    op.execute('DROP POLICY IF EXISTS daily_log_company_isolation ON daily_logs')
    op.execute('DROP POLICY IF EXISTS leave_company_isolation ON leave_requests')

    # Drop tables in reverse order
    op.drop_table('audit_logs')
    op.drop_table('sessions')
    op.drop_table('leave_requests')
    op.drop_table('daily_logs')
    op.drop_table('tasks')
    op.drop_table('employees')
    op.drop_table('departments')
    op.drop_table('companies')

    # Drop extensions (optional, might be used by other schemas)
    # op.execute('DROP EXTENSION IF EXISTS "uuid-ossp"')
    # op.execute('DROP EXTENSION IF EXISTS "pgcrypto"')
