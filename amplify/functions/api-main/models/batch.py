"""
Wine batch and cost tracking models for Phase 3
"""
from sqlalchemy import Column, String, Integer, DECIMAL, ForeignKey, Date, Enum as SQLEnum
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
    """Wine import batches with enhanced cost tracking"""
    __tablename__ = 'wine_batches'
    
    # Basic batch information
    batch_number = Column(String(50), nullable=False, unique=True, comment="Unique batch identifier")
    wine_name = Column(String(255), nullable=False, comment="Wine name")
    producer = Column(String(255), nullable=False, comment="Producer name")
    
    # Import details
    import_date = Column(Date, nullable=False, comment="Date of import")
    supplier_id = Column(GUID, ForeignKey('suppliers.id'), comment="Reference to supplier")
    total_bottles = Column(Integer, nullable=False, comment="Total bottles in batch")
    
    # Cost information
    eur_exchange_rate = Column(DECIMAL(10,6), comment="EUR to NOK exchange rate at import")
    wine_cost_eur_cents = Column(Integer, comment="Wine cost in EUR cents")
    transport_cost_ore = Column(Integer, default=0, comment="Transport cost in NOK øre")
    customs_fee_ore = Column(Integer, default=0, comment="Customs fee in NOK øre")
    freight_forwarding_ore = Column(Integer, default=0, comment="Freight forwarding cost in NOK øre")
    total_cost_nok_ore = Column(Integer, default=0, comment="Total cost in NOK øre")
    target_price_nok_ore = Column(Integer, default=0, comment="Target selling price per bottle in NOK øre")
    
    # Status tracking
    status = Column(SQLEnum(WineBatchStatus), default=WineBatchStatus.ORDERED, comment="Current batch status")
    fiken_sync_status = Column(String(20), default='pending', comment="Fiken synchronization status")
    
    # Relationships
    supplier = relationship("Supplier")
    cost_breakdowns = relationship("WineBatchCost", back_populates="batch", cascade="all, delete-orphan")
    inventory_items = relationship("WineInventory")
    
    def __repr__(self):
        return f"<WineBatch(batch_number='{self.batch_number}', status='{self.status.value if self.status else None}')>"
    
    def calculate_total_cost(self):
        """Calculate total cost including all fees"""
        wine_cost_nok = 0
        if self.wine_cost_eur_cents and self.eur_exchange_rate:
            # Convert EUR cents to NOK øre
            wine_cost_nok = int(self.wine_cost_eur_cents * float(self.eur_exchange_rate))
        
        self.total_cost_nok_ore = (
            wine_cost_nok + 
            self.transport_cost_ore + 
            self.customs_fee_ore + 
            self.freight_forwarding_ore
        )
    
    def get_cost_per_bottle_ore(self):
        """Get cost per bottle in NOK øre"""
        if self.total_bottles > 0:
            return self.total_cost_nok_ore // self.total_bottles
        return 0
    
    def to_dict(self):
        return {
            'id': str(self.id),
            'batch_number': self.batch_number,
            'wine_name': self.wine_name,
            'producer': self.producer,
            'import_date': self.import_date.isoformat() if self.import_date else None,
            'supplier_id': str(self.supplier_id) if self.supplier_id else None,
            'total_bottles': self.total_bottles,
            'eur_exchange_rate': float(self.eur_exchange_rate) if self.eur_exchange_rate else None,
            'wine_cost_eur_cents': self.wine_cost_eur_cents,
            'transport_cost_ore': self.transport_cost_ore,
            'customs_fee_ore': self.customs_fee_ore,
            'freight_forwarding_ore': self.freight_forwarding_ore,
            'total_cost_nok_ore': self.total_cost_nok_ore,
            'target_price_nok_ore': self.target_price_nok_ore,
            'cost_per_bottle_ore': self.get_cost_per_bottle_ore(),
            'status': self.status.value if self.status else None,
            'fiken_sync_status': self.fiken_sync_status,
            'active': self.active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class WineBatchCost(BaseModel):
    """Detailed cost breakdown for wine batches"""
    __tablename__ = 'wine_batch_costs'
    
    batch_id = Column(GUID, ForeignKey('wine_batches.id'), nullable=False, comment="Reference to wine batch")
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
    
    def to_dict(self):
        return {
            'id': str(self.id),
            'batch_id': str(self.batch_id),
            'cost_type': self.cost_type,
            'amount_ore': self.amount_ore,
            'currency': self.currency,
            'fiken_account_code': self.fiken_account_code,
            'payment_date': self.payment_date.isoformat() if self.payment_date else None,
            'allocation_method': self.allocation_method,
            'invoice_reference': self.invoice_reference,
            'active': self.active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        } 