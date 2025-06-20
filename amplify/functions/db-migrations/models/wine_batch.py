"""
Wine Batch Model for Arctan Wines CRM - Starting Simple
Initial version with core fields only, will expand incrementally
All monetary values stored as integers (øre) for Fiken compatibility
"""
from sqlalchemy import Column, String, Integer, Date, Enum as SQLEnum, Index
from enum import Enum
from .base import BaseModel

class WineBatchStatus(Enum):
    """Basic status of wine batch"""
    ORDERED = "ordered"
    AVAILABLE = "available"
    SOLD_OUT = "sold_out"

class WineBatch(BaseModel):
    """
    Simplified wine batch for initial migration
    Contains only essential fields - we'll expand incrementally
    """
    __tablename__ = "wine_batches"
    
    # Essential Information
    batch_number = Column(String(50), unique=True, nullable=False, index=True,
                         comment="Unique batch identifier (e.g., ACEDIANO-2024-001)")
    
    wine_name = Column(String(200), nullable=False, index=True,
                      comment="Wine name (e.g., ACEDIANO Monastrell)")
    
    producer = Column(String(200), nullable=False,
                     comment="Wine producer/winery name")
    
    # Basic Details
    total_bottles = Column(Integer, nullable=False,
                          comment="Total number of bottles in batch")
    
    status = Column(SQLEnum(WineBatchStatus), nullable=False, default=WineBatchStatus.ORDERED,
                   comment="Current status of the batch")
    
    # Simple Cost (NOK øre only for now)
    total_cost_nok_ore = Column(Integer, nullable=False, default=0,
                               comment="Total cost in NOK øre (84000 = 840.00 NOK)")
    
    target_price_nok_ore = Column(Integer, nullable=True,
                                 comment="Target selling price per bottle in NOK øre")
    
    # Basic index
    __table_args__ = (
        Index('idx_wine_batch_status', 'status'),
        {'comment': 'Simplified wine batch for initial migration'}
    )
    
    def __repr__(self):
        return f"<WineBatch(batch_number='{self.batch_number}', wine_name='{self.wine_name}')>" 