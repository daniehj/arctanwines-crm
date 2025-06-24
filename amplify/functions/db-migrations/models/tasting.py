"""
Wine tasting event management models for Phase 4
Tracks marketing events, attendees, costs, and ROI
"""
from sqlalchemy import Column, String, Integer, Date, Time, Text, Boolean, ForeignKey, DECIMAL, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from .base import BaseModel, GUID
import enum

class VenueType(enum.Enum):
    """Type of venue for tasting event"""
    RENTED_VENUE = "rented_venue"
    CUSTOMER_LOCATION = "customer_location"
    OWN_PREMISES = "own_premises"

class EventType(enum.Enum):
    """Type of tasting event"""
    PROMOTIONAL = "promotional"
    CORPORATE = "corporate"
    PRIVATE = "private"
    TRADE = "trade"

class EventStatus(enum.Enum):
    """Status of tasting event"""
    PLANNED = "planned"
    CONFIRMED = "confirmed"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class RSVPStatus(enum.Enum):
    """RSVP status for attendees"""
    INVITED = "invited"
    CONFIRMED = "confirmed"
    ATTENDED = "attended"
    NO_SHOW = "no_show"

class AttendeeType(enum.Enum):
    """Type of attendee"""
    EXISTING_CUSTOMER = "existing_customer"
    PROSPECT = "prospect"
    INDUSTRY = "industry"
    PRESS = "press"

class WineSource(enum.Enum):
    """Source of wine for tasting"""
    IMPORTED_STOCK = "imported_stock"
    BROUGHT_EXTERNAL = "brought_external"
    PURCHASED_FOR_EVENT = "purchased_for_event"

class OutcomeType(enum.Enum):
    """Type of tasting outcome"""
    IMMEDIATE_ORDER = "immediate_order"
    FOLLOW_UP_MEETING = "follow_up_meeting"
    NEWSLETTER_SIGNUP = "newsletter_signup"
    REFERRAL = "referral"

class WineTasting(BaseModel):
    """Wine tasting events for marketing and customer development"""
    __tablename__ = 'wine_tastings'
    
    # Event identification
    event_name = Column(String(255), nullable=False, comment="Name of the tasting event")
    event_date = Column(Date, nullable=False, comment="Date of the event")
    event_time = Column(Time, comment="Start time of the event")
    
    # Venue information
    venue_type = Column(SQLEnum(VenueType), nullable=False, comment="Type of venue")
    venue_name = Column(String(255), comment="Name of the venue")
    venue_address = Column(Text, comment="Full venue address")
    venue_cost_ore = Column(Integer, default=0, comment="Venue rental cost in NOK øre")
    
    # Event capacity and attendance
    max_attendees = Column(Integer, comment="Maximum number of attendees")
    actual_attendees = Column(Integer, default=0, comment="Actual number of attendees")
    
    # Event classification
    event_type = Column(SQLEnum(EventType), nullable=False, comment="Type of event")
    event_status = Column(SQLEnum(EventStatus), default=EventStatus.PLANNED, comment="Current status")
    target_customer_segment = Column(String(100), comment="Target customer segment")
    
    # Marketing and objectives
    marketing_objective = Column(Text, comment="Marketing objective for the event")
    
    # Cost and ROI tracking
    total_event_cost_ore = Column(Integer, default=0, comment="Total cost of event in NOK øre")
    estimated_revenue_impact_ore = Column(Integer, default=0, comment="Estimated revenue impact in NOK øre")
    actual_revenue_impact_ore = Column(Integer, default=0, comment="Actual revenue impact in NOK øre")
    
    # Event notes
    notes = Column(Text, comment="General notes about the event")
    
    # Relationships
    attendees = relationship("TastingAttendee", back_populates="tasting", cascade="all, delete-orphan")
    wines = relationship("TastingWine", back_populates="tasting", cascade="all, delete-orphan")
    costs = relationship("TastingCost", back_populates="tasting", cascade="all, delete-orphan")
    outcomes = relationship("TastingOutcome", back_populates="tasting", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<WineTasting(name='{self.event_name}', date='{self.event_date}')>"
    
    def calculate_roi_percentage(self):
        """Calculate ROI percentage"""
        if self.total_event_cost_ore > 0:
            return ((self.actual_revenue_impact_ore - self.total_event_cost_ore) / self.total_event_cost_ore) * 100
        return 0
    
    def to_dict(self):
        return {
            'id': str(self.id),
            'event_name': self.event_name,
            'event_date': self.event_date.isoformat() if self.event_date else None,
            'event_time': str(self.event_time) if self.event_time else None,
            'venue_type': self.venue_type.value if self.venue_type else None,
            'venue_name': self.venue_name,
            'venue_address': self.venue_address,
            'venue_cost_ore': self.venue_cost_ore,
            'max_attendees': self.max_attendees,
            'actual_attendees': self.actual_attendees,
            'event_type': self.event_type.value if self.event_type else None,
            'event_status': self.event_status.value if self.event_status else None,
            'target_customer_segment': self.target_customer_segment,
            'marketing_objective': self.marketing_objective,
            'total_event_cost_ore': self.total_event_cost_ore,
            'estimated_revenue_impact_ore': self.estimated_revenue_impact_ore,
            'actual_revenue_impact_ore': self.actual_revenue_impact_ore,
            'roi_percentage': self.calculate_roi_percentage(),
            'notes': self.notes,
            'active': self.active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class TastingAttendee(BaseModel):
    """Attendees at wine tasting events"""
    __tablename__ = 'tasting_attendees'
    
    # Event relationship
    tasting_id = Column(GUID, ForeignKey('wine_tastings.id'), nullable=False, comment="Reference to tasting event")
    tasting = relationship("WineTasting", back_populates="attendees")
    
    # Customer relationship (optional for walk-ins)
    customer_id = Column(GUID, ForeignKey('customers.id'), comment="Reference to existing customer")
    customer = relationship("Customer")
    
    # Attendee information
    attendee_name = Column(String(255), nullable=False, comment="Name of attendee")
    attendee_email = Column(String(255), comment="Email address")
    attendee_phone = Column(String(50), comment="Phone number")
    attendee_type = Column(SQLEnum(AttendeeType), nullable=False, comment="Type of attendee")
    
    # RSVP and attendance tracking
    rsvp_status = Column(SQLEnum(RSVPStatus), default=RSVPStatus.INVITED, comment="RSVP status")
    
    # Follow-up and interest tracking
    follow_up_required = Column(Boolean, default=False, comment="Requires follow-up")
    post_event_interest_level = Column(Integer, comment="Interest level 1-5 after event")
    potential_order_value_ore = Column(Integer, default=0, comment="Estimated potential order value in NOK øre")
    
    def __repr__(self):
        return f"<TastingAttendee(name='{self.attendee_name}', type='{self.attendee_type}')>"
    
    def to_dict(self):
        return {
            'id': str(self.id),
            'tasting_id': str(self.tasting_id),
            'customer_id': str(self.customer_id) if self.customer_id else None,
            'attendee_name': self.attendee_name,
            'attendee_email': self.attendee_email,
            'attendee_phone': self.attendee_phone,
            'attendee_type': self.attendee_type.value if self.attendee_type else None,
            'rsvp_status': self.rsvp_status.value if self.rsvp_status else None,
            'follow_up_required': self.follow_up_required,
            'post_event_interest_level': self.post_event_interest_level,
            'potential_order_value_ore': self.potential_order_value_ore,
            'active': self.active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class TastingWine(BaseModel):
    """Wines presented at tasting events"""
    __tablename__ = 'tasting_wines'
    
    # Event relationship
    tasting_id = Column(GUID, ForeignKey('wine_tastings.id'), nullable=False, comment="Reference to tasting event")
    tasting = relationship("WineTasting", back_populates="wines")
    
    # Wine relationship (optional for non-stock wines)
    wine_id = Column(GUID, ForeignKey('wines.id'), comment="Reference to wine in catalog")
    wine = relationship("Wine")
    
    # Wine information (for non-stock wines or overrides)
    wine_name = Column(String(255), comment="Wine name if not in catalog")
    wine_producer = Column(String(255), comment="Producer name")
    wine_vintage = Column(Integer, comment="Wine vintage")
    
    # Cost tracking
    bottles_used = Column(Integer, nullable=False, default=1, comment="Number of bottles used")
    wine_source = Column(SQLEnum(WineSource), nullable=False, comment="Source of the wine")
    cost_per_bottle_ore = Column(Integer, nullable=False, comment="Cost per bottle in NOK øre")
    
    # Tasting details
    tasting_order = Column(Integer, comment="Order of presentation in tasting")
    tasting_notes = Column(Text, comment="Tasting notes from event")
    
    # Customer feedback
    customer_feedback = Column(JSONB, comment="Customer feedback and ratings")
    popularity_score = Column(DECIMAL(3,2), comment="Popularity score 0.00-5.00")
    follow_up_orders = Column(Integer, default=0, comment="Number of follow-up orders generated")
    
    def __repr__(self):
        return f"<TastingWine(wine='{self.wine_name or 'from catalog'}', bottles={self.bottles_used})>"
    
    def calculate_total_wine_cost(self):
        """Calculate total cost for wine used"""
        return self.bottles_used * self.cost_per_bottle_ore
    
    def to_dict(self):
        return {
            'id': str(self.id),
            'tasting_id': str(self.tasting_id),
            'wine_id': str(self.wine_id) if self.wine_id else None,
            'wine_name': self.wine_name,
            'wine_producer': self.wine_producer,
            'wine_vintage': self.wine_vintage,
            'bottles_used': self.bottles_used,
            'wine_source': self.wine_source.value if self.wine_source else None,
            'cost_per_bottle_ore': self.cost_per_bottle_ore,
            'total_wine_cost_ore': self.calculate_total_wine_cost(),
            'tasting_order': self.tasting_order,
            'tasting_notes': self.tasting_notes,
            'customer_feedback': self.customer_feedback,
            'popularity_score': float(self.popularity_score) if self.popularity_score else None,
            'follow_up_orders': self.follow_up_orders,
            'active': self.active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class TastingCost(BaseModel):
    """Cost breakdown for tasting events"""
    __tablename__ = 'tasting_costs'
    
    # Event relationship
    tasting_id = Column(GUID, ForeignKey('wine_tastings.id'), nullable=False, comment="Reference to tasting event")
    tasting = relationship("WineTasting", back_populates="costs")
    
    # Cost details
    cost_category = Column(String(50), nullable=False, comment="Category: venue, catering, staff, materials, transportation, marketing")
    cost_description = Column(String(255), nullable=False, comment="Description of the cost")
    supplier_name = Column(String(255), comment="Name of supplier/vendor")
    amount_ore = Column(Integer, nullable=False, comment="Cost amount in NOK øre")
    
    # Payment and accounting
    cost_date = Column(Date, nullable=False, comment="Date when cost was incurred")
    invoice_reference = Column(String(100), comment="Invoice or reference number")
    fiken_transaction_id = Column(Integer, comment="Fiken transaction ID for sync")
    
    # Cost allocation
    cost_type = Column(String(20), default='fixed', comment="fixed or variable_per_person")
    
    def __repr__(self):
        return f"<TastingCost(category='{self.cost_category}', amount={self.amount_ore} øre)>"
    
    def to_dict(self):
        return {
            'id': str(self.id),
            'tasting_id': str(self.tasting_id),
            'cost_category': self.cost_category,
            'cost_description': self.cost_description,
            'supplier_name': self.supplier_name,
            'amount_ore': self.amount_ore,
            'cost_date': self.cost_date.isoformat() if self.cost_date else None,
            'invoice_reference': self.invoice_reference,
            'fiken_transaction_id': self.fiken_transaction_id,
            'cost_type': self.cost_type,
            'active': self.active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class TastingOutcome(BaseModel):
    """Outcomes and results from tasting events"""
    __tablename__ = 'tasting_outcomes'
    
    # Event relationship
    tasting_id = Column(GUID, ForeignKey('wine_tastings.id'), nullable=False, comment="Reference to tasting event")
    tasting = relationship("WineTasting", back_populates="outcomes")
    
    # Customer relationship
    customer_id = Column(GUID, ForeignKey('customers.id'), comment="Reference to customer")
    customer = relationship("Customer")
    
    # Outcome details
    outcome_type = Column(SQLEnum(OutcomeType), nullable=False, comment="Type of outcome")
    outcome_value_ore = Column(Integer, default=0, comment="Order value or estimated value in NOK øre")
    outcome_date = Column(Date, nullable=False, comment="Date when outcome occurred")
    notes = Column(Text, comment="Notes about the outcome")
    
    def __repr__(self):
        return f"<TastingOutcome(type='{self.outcome_type}', value={self.outcome_value_ore} øre)>"
    
    def to_dict(self):
        return {
            'id': str(self.id),
            'tasting_id': str(self.tasting_id),
            'customer_id': str(self.customer_id) if self.customer_id else None,
            'outcome_type': self.outcome_type.value if self.outcome_type else None,
            'outcome_value_ore': self.outcome_value_ore,
            'outcome_date': self.outcome_date.isoformat() if self.outcome_date else None,
            'notes': self.notes,
            'active': self.active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        } 