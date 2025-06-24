"""
Wine batch and cost tracking models
"""
from sqlalchemy import Column, String, Integer, DECIMAL, ForeignKey, Date, Enum
from sqlalchemy.orm import relationship
from .base import BaseModel, GUID
import enum

class WineBatchStatus(enum.Enum):
    """Status of wine batch"""
    ORDERED = "ORDERED"
    IN_TRANSIT = "IN_TRANSIT"
    CUSTOMS = "CUSTOMS"
    AVAILABLE = "AVAILABLE"
    SOLD_OUT = "SOLD_OUT"

class WineBatch(BaseModel):
    """Wine import batches with cost tracking"""
    __tablename__ = 'wine_batches'
    
    batch_number = Column(String(50), nullable=False, unique=True, comment="Unique batch identifier")
    import_date = Column(Date, nullable=False, comment="Date of import")
    supplier_id = Column(GUID(), ForeignKey('suppliers.id'), comment="Reference to supplier")
    total_bottles = Column(Integer, nullable=False, comment="Total bottles in batch")
    eur_exchange_rate = Column(DECIMAL(10,6), nullable=False, comment="EUR to NOK exchange rate at import")
    wine_cost_eur_cents = Column(Integer, nullable=False, comment="Wine cost in EUR cents")
    transport_cost_ore = Column(Integer, default=0, comment="Transport cost in NOK øre")
    customs_fee_ore = Column(Integer, default=0, comment="Customs fee in NOK øre")
    freight_forwarding_ore = Column(Integer, default=0, comment="Freight forwarding cost in NOK øre")
    status = Column(Enum(WineBatchStatus), default=WineBatchStatus.ORDERED, comment="Current batch status")
    fiken_sync_status = Column(String(20), default='pending', comment="Fiken synchronization status")
    
    # Relationships
    supplier = relationship("Supplier")
    cost_breakdowns = relationship("WineBatchCost", back_populates="batch")
    inventory_items = relationship("WineInventory")
    
    def __repr__(self):
        return f"<WineBatch(batch_number='{self.batch_number}', status='{self.status.value}')>"

class WineBatchCost(BaseModel):
    """Detailed cost breakdown for wine batches"""
    __tablename__ = 'wine_batch_costs'
    
    batch_id = Column(GUID(), ForeignKey('wine_batches.id'), nullable=False, comment="Reference to wine batch")
    cost_type = Column(String(50), nullable=False, comment="Type of cost (transport, customs, freight, wine_purchase)")
    amount_ore = Column(Integer, nullable=False, comment="Cost amount in øre (or cents for EUR)")
    currency = Column(String(3), nullable=False, comment="Currency (NOK, EUR)")
    fiken_account_code = Column(String(20), comment="Fiken account code for this cost")
    payment_date = Column(Date, comment="Date payment was made")
    allocation_method = Column(String(30), default='per_bottle', comment="How cost is allocated (per_bottle, by_value, percentage)")
    invoice_reference = Column(String(100), comment="Invoice or reference number")
    
    # Relationships
    batch = relationship("WineBatch", back_populates="cost_breakdowns")
    
    def __repr__(self):
        return f"<WineBatchCost(cost_type='{self.cost_type}', amount={self.amount_ore} {self.currency})>" 