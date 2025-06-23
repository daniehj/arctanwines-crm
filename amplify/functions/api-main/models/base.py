"""
Base SQLAlchemy models for Arctan Wines CRM - API Main Function
"""
import uuid
from datetime import datetime, timezone
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, String, DateTime, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.types import TypeDecorator, String as SqlString

Base = declarative_base()

class GUID(TypeDecorator):
    """Platform-independent GUID type that uses PostgreSQL UUID or String for SQLite"""
    impl = SqlString
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(UUID(as_uuid=True))
        else:
            return dialect.type_descriptor(SqlString(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        elif dialect.name == 'postgresql':
            return value
        else:
            return str(value) if isinstance(value, uuid.UUID) else value

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        elif dialect.name == 'postgresql':
            return value
        else:
            return uuid.UUID(value) if isinstance(value, str) else value

class BaseModel(Base):
    """Base model with common fields for all tables"""
    __abstract__ = True
    
    id = Column(GUID(), primary_key=True, default=uuid.uuid4, comment="Primary key using UUID")
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), comment="Timestamp when record was created")
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), comment="Timestamp when record was last updated")
    active = Column(Boolean, nullable=False, default=True, comment="Soft delete flag")

    def __repr__(self):
        return f"<{self.__class__.__name__}(id={self.id})>" 