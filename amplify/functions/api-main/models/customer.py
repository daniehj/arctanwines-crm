from sqlalchemy import Column, String, Boolean, DateTime, Text, Integer
from sqlalchemy.orm import relationship
from .base import BaseModel

class Customer(BaseModel):
    __tablename__ = 'customers'
    
    # Basic customer information
    name = Column(String(255), nullable=False)
    customer_type = Column(String(50), nullable=False)  # 'individual', 'restaurant', 'retailer', 'distributor'
    
    # Contact information
    email = Column(String(255))
    phone = Column(String(50))
    
    # Address information
    address_line1 = Column(String(255))
    address_line2 = Column(String(255))
    postal_code = Column(String(20))
    city = Column(String(100))
    country = Column(String(100), default='Norway')
    
    # Business information (for business customers)
    organization_number = Column(String(50))  # Norwegian org number
    vat_number = Column(String(50))
    
    # Customer preferences and settings
    preferred_delivery_method = Column(String(50))  # 'pickup', 'delivery', 'shipping'
    payment_terms = Column(Integer, default=0)  # Days, 0 = immediate payment
    credit_limit_nok_ore = Column(Integer, default=0)  # Credit limit in øre
    
    # Marketing and communication
    marketing_consent = Column(Boolean, default=False)
    newsletter_subscription = Column(Boolean, default=False)
    preferred_language = Column(String(10), default='no')  # 'no', 'en'
    
    # Customer notes and history
    notes = Column(Text)
    
    # Fiken integration
    fiken_customer_id = Column(String(100))  # Reference to Fiken customer
    
    # Relationships
    orders = relationship("Order", back_populates="customer", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Customer(id='{self.id}', name='{self.name}', type='{self.customer_type}')>"
    
    def to_dict(self):
        return {
            'id': str(self.id),
            'name': self.name,
            'customer_type': self.customer_type,
            'email': self.email,
            'phone': self.phone,
            'address_line1': self.address_line1,
            'address_line2': self.address_line2,
            'postal_code': self.postal_code,
            'city': self.city,
            'country': self.country,
            'organization_number': self.organization_number,
            'vat_number': self.vat_number,
            'preferred_delivery_method': self.preferred_delivery_method,
            'payment_terms': self.payment_terms,
            'credit_limit_nok_ore': self.credit_limit_nok_ore,
            'marketing_consent': self.marketing_consent,
            'newsletter_subscription': self.newsletter_subscription,
            'preferred_language': self.preferred_language,
            'notes': self.notes,
            'fiken_customer_id': self.fiken_customer_id,
            'active': self.active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        } 