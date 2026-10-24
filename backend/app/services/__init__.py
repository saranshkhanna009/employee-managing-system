"""Services package.

Service modules are intentionally imported explicitly by callers. Eagerly
importing every service here creates a circular dependency while SQLAlchemy
models are being imported for Alembic migrations.
"""
