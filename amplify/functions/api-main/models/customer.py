"""
Customer Model for Arctan Wines CRM
Norwegian B2B customers with organization numbers and Fiken integration
"""
from sqlalchemy import Column, String, Integer, Text, Boolean, DateTime, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from .base import BaseModel

class Customer(BaseModel):
    """
    Norwegian B2B customers
    Designed for integration with Fiken accounting system
    """
    __tablename__ = "customers"
    
    # Basic Information
    name = Column(String(255), nullable=False, index=True,
                 comment="Company name (e.g., Kaotisk AS)")
    
    customer_type = Column(String(50), nullable=False,
                          comment="Customer type (e.g., individual, restaurant, retailer, distributor)")
    
    organization_number = Column(String(50), unique=True, nullable=False, index=True,
                                comment="Norwegian organization number (9 digits)")
    
    vat_number = Column(String(50), comment="VAT number")
    
    # Contact Information
    email = Column(String(255), index=True,
                  comment="Primary email address")
    
    phone = Column(String(50), comment="Primary phone number")
    
    mobile = Column(String(20), comment="Mobile phone number")
    
    # Address Information
    address_line1 = Column(String(255), comment="Street address line 1")
    
    address_line2 = Column(String(255), comment="Street address line 2")
    
    postal_code = Column(String(20), index=True,
                        comment="Norwegian postal code")
    
    city = Column(String(100), index=True,
                 comment="City name")
    
    country = Column(String(100), default="Norway",
                    comment="Country (default: Norway)")
    
    # Business Information
    industry = Column(String(200), comment="Industry/business type")
    
    website = Column(String(500), comment="Company website URL")
    
    # Customer preferences and settings
    preferred_delivery_method = Column(String(50), comment="Preferred delivery method (pickup, delivery, shipping)")
    
    payment_terms = Column(Integer, default=0, comment="Payment terms in days (default: immediate payment)")
    
    credit_limit_nok_ore = Column(Integer, default=0, comment="Credit limit in NOK øre")
    
    # Marketing and communication
    marketing_consent = Column(Boolean, default=False, comment="Consent for marketing communications")
    
    newsletter_subscription = Column(Boolean, default=False, comment="Subscribed to newsletter")
    
    preferred_language = Column(String(10), default='no', comment="Preferred language (no, en)")
    
    # Customer notes and history
    notes = Column(Text, comment="Internal notes about the customer")
    
    # Fiken Integration
    fiken_customer_id = Column(String(100), comment="Fiken customer ID for accounting integration")
    
    fiken_contact_id = Column(Integer, comment="Fiken contact person ID")
    
    fiken_last_sync = Column(DateTime(timezone=True), comment="Last successful sync with Fiken")
    
    # Business Relationship
    customer_since = Column(DateTime(timezone=True), comment="Date when customer relationship started")
    
    # Sales Information
    total_orders = Column(Integer, comment="Total number of orders placed")
    
    total_revenue_nok_ore = Column(Integer, comment="Total revenue from customer in NOK øre")
    
    average_order_value_nok_ore = Column(Integer, comment="Average order value in NOK øre")
    
    last_order_date = Column(DateTime(timezone=True), comment="Date of last order")
    
    # Sales representative notes
    sales_rep_notes = Column(Text, comment="Sales representative notes")
    
    # Customer Service
    preferred_communication_method = Column(String(50), comment="Preferred communication method (email, phone, etc.)")
    
    special_requirements = Column(Text, comment="Special delivery or service requirements")
    
    # Compliance and Legal
    vat_registered = Column(Boolean, comment="Is customer VAT registered")
    
    gdpr_consent_date = Column(DateTime(timezone=True), comment="Date of GDPR consent")
    
    data_retention_consent = Column(Boolean, comment="Consent for data retention beyond legal requirements")
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_customer_org_active', 'organization_number', 'active'),
        Index('idx_customer_fiken', 'fiken_customer_id', 'fiken_last_sync'),
        Index('idx_customer_sales', 'total_revenue_nok_ore', 'last_order_date'),
        Index('idx_customer_location', 'postal_code', 'city'),
        {'comment': 'Norwegian B2B customers with Fiken integration'}
    )
    
    # Relationships
    orders = relationship("Order", back_populates="customer", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Customer(id='{self.id}', name='{self.name}', type='{self.customer_type}')>"
    
    @property
    def display_name(self) -> str:
        """Get display name for customer"""
        return f"{self.name} ({self.organization_number})"
    
    @property
    def full_address(self) -> str:
        """Get formatted full address"""
        address_parts = []
        if self.address_line1:
            address_parts.append(self.address_line1)
        if self.address_line2:
            address_parts.append(self.address_line2)
        if self.postal_code and self.city:
            address_parts.append(f"{self.postal_code} {self.city}")
        if self.country and self.country != "Norway":
            address_parts.append(self.country)
        return "\n".join(address_parts)
    
    @property
    def is_high_value_customer(self) -> bool:
        """Determine if customer is high-value (>100k NOK total revenue)"""
        return self.total_revenue_nok_ore >= 10000000  # 100,000 NOK in øre
    
    def update_sales_stats(self, order_value_nok_ore: int) -> None:
        """Update customer sales statistics after new order"""
        self.total_orders += 1
        self.total_revenue_nok_ore += order_value_nok_ore
        
        if self.total_orders > 0:
            self.average_order_value_nok_ore = self.total_revenue_nok_ore // self.total_orders 