from sqlalchemy import Column, String, Integer, DateTime, Text, Boolean, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from .base import BaseModel, GUID
import enum

class OrderStatus(enum.Enum):
    DRAFT = "draft"
    CONFIRMED = "confirmed"
    PROCESSING = "processing"
    READY_FOR_DELIVERY = "ready_for_delivery"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
    RETURNED = "returned"

class PaymentStatus(enum.Enum):
    PENDING = "pending"
    PAID = "paid"
    PARTIAL = "partial"
    OVERDUE = "overdue"
    REFUNDED = "refunded"

class Order(BaseModel):
    __tablename__ = 'orders'
    
    # Order identification
    order_number = Column(String(50), unique=True, nullable=False)
    
    # Customer relationship
    customer_id = Column(GUID, ForeignKey('customers.id'), nullable=False)
    customer = relationship("Customer", back_populates="orders")
    
    # Order status and workflow
    status = Column(SQLEnum(OrderStatus), default=OrderStatus.DRAFT, nullable=False)
    payment_status = Column(SQLEnum(PaymentStatus), default=PaymentStatus.PENDING, nullable=False)
    
    # Order dates
    order_date = Column(DateTime, nullable=False)
    requested_delivery_date = Column(DateTime)
    confirmed_delivery_date = Column(DateTime)
    delivered_date = Column(DateTime)
    
    # Delivery information
    delivery_method = Column(String(50), nullable=False)  # 'pickup', 'delivery', 'shipping'
    delivery_address_line1 = Column(String(255))
    delivery_address_line2 = Column(String(255))
    delivery_postal_code = Column(String(20))
    delivery_city = Column(String(100))
    delivery_country = Column(String(100))
    delivery_notes = Column(Text)
    
    # Financial information (all in NOK øre)
    subtotal_ore = Column(Integer, default=0, nullable=False)  # Sum of line items
    delivery_fee_ore = Column(Integer, default=0, nullable=False)
    discount_ore = Column(Integer, default=0, nullable=False)
    vat_ore = Column(Integer, default=0, nullable=False)  # Calculated VAT
    total_ore = Column(Integer, default=0, nullable=False)  # Final total
    
    # Payment information
    payment_terms = Column(Integer, default=0)  # Days
    payment_due_date = Column(DateTime)
    
    # Order notes and communication
    customer_notes = Column(Text)  # Notes from customer
    internal_notes = Column(Text)  # Internal staff notes
    
    # Fiken integration
    fiken_order_id = Column(String(100))  # Reference to Fiken order/invoice
    fiken_invoice_number = Column(String(50))
    
    # Relationships
    order_items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Order(id='{self.id}', number='{self.order_number}', status='{self.status}')>"

class OrderItem(BaseModel):
    __tablename__ = 'order_items'
    
    # Order relationship
    order_id = Column(GUID, ForeignKey('orders.id'), nullable=False)
    order = relationship("Order", back_populates="order_items")
    
    # Product relationship - can be wine batch or individual wine
    wine_batch_id = Column(GUID, ForeignKey('wine_batches.id'))
    wine_batch = relationship("WineBatch")
    
    wine_id = Column(GUID, ForeignKey('wines.id'))
    wine = relationship("Wine")
    
    # Order item details
    quantity = Column(Integer, nullable=False)
    unit_price_ore = Column(Integer, nullable=False)  # Price per bottle in øre
    total_price_ore = Column(Integer, nullable=False)  # quantity * unit_price_ore
    
    # Product information snapshot (for historical accuracy)
    wine_name = Column(String(255), nullable=False)
    producer = Column(String(255))
    vintage = Column(Integer)
    bottle_size_ml = Column(Integer, default=750)
    
    # Discount and adjustments
    discount_percentage = Column(Integer, default=0)  # Percentage discount
    discount_ore = Column(Integer, default=0)  # Fixed discount in øre
    
    # Item notes
    notes = Column(Text)
    
    def __repr__(self):
        return f"<OrderItem(id='{self.id}', wine='{self.wine_name}', qty={self.quantity})>" 