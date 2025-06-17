"""
Base SQLAlchemy model for Arctan Wines CRM
Includes UUID support and common audit fields
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, DateTime, String, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()

class BaseModel(Base):
    """
    Abstract base model with common fields for all tables
    """
    __abstract__ = True
    
    id = Column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
        comment="Primary key using UUID"
    )
    
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        server_default=func.now(),
        comment="Timestamp when record was created"
    )
    
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        server_default=func.now(),
        comment="Timestamp when record was last updated"
    )
    
    def __repr__(self):
        return f"<{self.__class__.__name__}(id={self.id})>" 