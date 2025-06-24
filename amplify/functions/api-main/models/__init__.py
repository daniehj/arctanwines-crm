"""
SQLAlchemy models for Arctan Wines CRM
"""
from .base import Base, BaseModel
from .supplier import Supplier
from .wine import Wine, WineInventory
from .batch import WineBatch, WineBatchCost, WineBatchStatus
from .customer import Customer
from .order import Order, OrderItem, OrderStatus, PaymentStatus
from .tasting import (
    WineTasting, TastingAttendee, TastingWine, TastingCost, TastingOutcome,
    VenueType, EventType, EventStatus, RSVPStatus, AttendeeType, WineSource, OutcomeType
)

# Export all models for Alembic to discover
__all__ = [
    'Base',
    'BaseModel', 
    'Supplier',
    'Wine',
    'WineInventory',
    'WineBatch',
    'WineBatchCost',
    'WineBatchStatus',
    'Customer',
    'Order',
    'OrderItem',
    'OrderStatus',
    'PaymentStatus',
    'WineTasting',
    'TastingAttendee',
    'TastingWine',
    'TastingCost',
    'TastingOutcome',
    'VenueType',
    'EventType',
    'EventStatus',
    'RSVPStatus',
    'AttendeeType',
    'WineSource',
    'OutcomeType'
] 