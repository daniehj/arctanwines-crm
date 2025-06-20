"""
Customer Model for Arctan Wines CRM
Norwegian B2B customers with organization numbers and Fiken integration
"""
from sqlalchemy import Column, String, Integer, Text, Boolean, DateTime, Index
from sqlalchemy.dialects.postgresql import UUID
from .base import BaseModel

class Customer(BaseModel):
    """
    Norwegian B2B customers
    Designed for integration with Fiken accounting system
    """
    __tablename__ = "customers"
    
    # Basic Information
    company_name = Column(String(200), nullable=False, index=True,
                         comment="Company name (e.g., Kaotisk AS)")
    
    organization_number = Column(String(9), unique=True, nullable=False, index=True,
                                comment="Norwegian organization number (9 digits)")
    
    # Contact Information
    contact_person = Column(String(200), nullable=True,
                           comment="Primary contact person name")
    
    email = Column(String(320), nullable=True, index=True,
                  comment="Primary email address")
    
    phone = Column(String(20), nullable=True,
                  comment="Primary phone number")
    
    mobile = Column(String(20), nullable=True,
                   comment="Mobile phone number")
    
    # Address Information
    address_line1 = Column(String(200), nullable=True,
                          comment="Street address line 1")
    
    address_line2 = Column(String(200), nullable=True,
                          comment="Street address line 2")
    
    postal_code = Column(String(10), nullable=True, index=True,
                        comment="Norwegian postal code")
    
    city = Column(String(100), nullable=True, index=True,
                 comment="City name")
    
    country = Column(String(100), nullable=False, default="Norway",
                    comment="Country (default: Norway)")
    
    # Business Information
    industry = Column(String(200), nullable=True,
                     comment="Industry/business type")
    
    website = Column(String(500), nullable=True,
                    comment="Company website URL")
    
    # Fiken Integration
    fiken_customer_id = Column(Integer, nullable=True, unique=True, index=True,
                              comment="Fiken customer ID for accounting integration")
    
    fiken_contact_id = Column(Integer, nullable=True,
                             comment="Fiken contact person ID")
    
    fiken_last_sync = Column(DateTime(timezone=True), nullable=True,
                            comment="Last successful sync with Fiken")
    
    # Business Relationship
    customer_since = Column(DateTime(timezone=True), nullable=True,
                           comment="Date when customer relationship started")
    
    credit_limit_nok_ore = Column(Integer, nullable=False, default=0,
                                 comment="Credit limit in NOK øre")
    
    payment_terms_days = Column(Integer, nullable=False, default=30,
                               comment="Payment terms in days (default: 30)")
    
    # Status and Preferences
    active = Column(Boolean, nullable=False, default=True, index=True,
                   comment="Is customer active")
    
    newsletter_subscription = Column(Boolean, nullable=False, default=False,
                                    comment="Subscribed to newsletter")
    
    marketing_consent = Column(Boolean, nullable=False, default=False,
                              comment="Consent for marketing communications")
    
    # Wine Preferences
    preferred_wine_types = Column(Text, nullable=True,
                                 comment="JSON array of preferred wine types")
    
    preferred_price_range_min_nok_ore = Column(Integer, nullable=True,
                                              comment="Minimum preferred price per bottle in NOK øre")
    
    preferred_price_range_max_nok_ore = Column(Integer, nullable=True,
                                              comment="Maximum preferred price per bottle in NOK øre")
    
    # Sales Information
    total_orders = Column(Integer, nullable=False, default=0,
                         comment="Total number of orders placed")
    
    total_revenue_nok_ore = Column(Integer, nullable=False, default=0,
                                  comment="Total revenue from customer in NOK øre")
    
    average_order_value_nok_ore = Column(Integer, nullable=False, default=0,
                                        comment="Average order value in NOK øre")
    
    last_order_date = Column(DateTime(timezone=True), nullable=True,
                            comment="Date of last order")
    
    # Notes and Internal Information
    internal_notes = Column(Text, nullable=True,
                           comment="Internal notes about the customer")
    
    sales_rep_notes = Column(Text, nullable=True,
                            comment="Sales representative notes")
    
    # Customer Service
    preferred_communication_method = Column(String(50), nullable=True,
                                           comment="Preferred communication method (email, phone, etc.)")
    
    special_requirements = Column(Text, nullable=True,
                                 comment="Special delivery or service requirements")
    
    # Compliance and Legal
    vat_registered = Column(Boolean, nullable=False, default=True,
                           comment="Is customer VAT registered")
    
    gdpr_consent_date = Column(DateTime(timezone=True), nullable=True,
                              comment="Date of GDPR consent")
    
    data_retention_consent = Column(Boolean, nullable=False, default=False,
                                   comment="Consent for data retention beyond legal requirements")
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_customer_org_active', 'organization_number', 'active'),
        Index('idx_customer_fiken', 'fiken_customer_id', 'fiken_last_sync'),
        Index('idx_customer_sales', 'total_revenue_nok_ore', 'last_order_date'),
        Index('idx_customer_location', 'postal_code', 'city'),
        {'comment': 'Norwegian B2B customers with Fiken integration'}
    )
    
    def __repr__(self):
        return f"<Customer(company_name='{self.company_name}', org_number='{self.organization_number}', active={self.active})>"
    
    @property
    def display_name(self) -> str:
        """Get display name for customer"""
        return f"{self.company_name} ({self.organization_number})"
    
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