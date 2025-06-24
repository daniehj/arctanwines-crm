"""
Supplier models for wine import business
"""
from sqlalchemy import Column, String, Integer, Boolean
from .base import BaseModel

class Supplier(BaseModel):
    """Wine suppliers and importers"""
    __tablename__ = 'suppliers'
    
    name = Column(String(255), nullable=False, comment="Supplier company name")
    country = Column(String(100), nullable=False, comment="Country of origin")
    contact_person = Column(String(255), comment="Primary contact person")
    email = Column(String(255), comment="Primary email address")
    phone = Column(String(50), comment="Primary phone number")
    payment_terms = Column(Integer, default=30, comment="Payment terms in days")
    currency = Column(String(3), default='EUR', comment="Primary currency (EUR, NOK, USD)")
    tax_id = Column(String(50), comment="VAT number or tax identification")
    
    def __repr__(self):
        return f"<Supplier(name='{self.name}', country='{self.country}')>" 