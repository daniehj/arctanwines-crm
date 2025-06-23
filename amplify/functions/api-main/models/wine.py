"""
Wine catalog and inventory models with enhanced tracking for Phase 3
"""
from sqlalchemy import Column, String, Integer, Boolean, Text, DECIMAL, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from .base import BaseModel, GUID

class Wine(BaseModel):
    """Wine product catalog"""
    __tablename__ = 'wines'
    
    name = Column(String(255), nullable=False, comment="Wine name")
    producer = Column(String(255), nullable=False, comment="Wine producer/winery")
    region = Column(String(255), comment="Wine region")
    country = Column(String(100), nullable=False, comment="Country of origin")
    vintage = Column(Integer, comment="Wine vintage year")
    grape_varieties = Column(JSONB, comment="Array of grape varieties")
    alcohol_content = Column(DECIMAL(4,2), comment="Alcohol percentage (e.g., 13.5)")
    bottle_size_ml = Column(Integer, default=750, comment="Bottle size in milliliters")
    product_category = Column(String(50), comment="Wine category (red, white, rosé, sparkling, dessert)")
    tasting_notes = Column(Text, comment="Tasting notes and description")
    serving_temperature = Column(String(50), comment="Recommended serving temperature")
    food_pairing = Column(Text, comment="Food pairing suggestions")
    organic = Column(Boolean, default=False, comment="Organic certification")
    biodynamic = Column(Boolean, default=False, comment="Biodynamic certification")
    fiken_product_id = Column(Integer, comment="Fiken product ID for sync")
    
    # Relationships
    inventory_items = relationship("WineInventory", back_populates="wine")
    
    def __repr__(self):
        return f"<Wine(name='{self.name}', producer='{self.producer}', vintage={self.vintage})>"
    
    def to_dict(self):
        return {
            'id': str(self.id),
            'name': self.name,
            'producer': self.producer,
            'region': self.region,
            'country': self.country,
            'vintage': self.vintage,
            'grape_varieties': self.grape_varieties,
            'alcohol_content': float(self.alcohol_content) if self.alcohol_content else None,
            'bottle_size_ml': self.bottle_size_ml,
            'product_category': self.product_category,
            'tasting_notes': self.tasting_notes,
            'serving_temperature': self.serving_temperature,
            'food_pairing': self.food_pairing,
            'organic': self.organic,
            'biodynamic': self.biodynamic,
            'fiken_product_id': self.fiken_product_id,
            'active': self.active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class WineInventory(BaseModel):
    """Wine inventory tracking with enhanced cost and pricing management"""
    __tablename__ = 'wine_inventory'
    
    # Product relationships
    wine_id = Column(GUID, ForeignKey('wines.id'), nullable=False, comment="Reference to wine")
    batch_id = Column(GUID, ForeignKey('wine_batches.id'), comment="Reference to import batch")
    
    # Enhanced inventory tracking
    quantity_available = Column(Integer, default=0, nullable=False, comment="Current stock quantity")
    quantity_reserved = Column(Integer, default=0, nullable=False, comment="Reserved for orders")
    quantity_sold = Column(Integer, default=0, nullable=False, comment="Total sold from this inventory")
    
    # Pricing (all in NOK øre for Fiken compatibility)
    cost_per_bottle_ore = Column(Integer, nullable=False, comment="Cost per bottle in NOK øre")
    selling_price_ore = Column(Integer, nullable=False, comment="Selling price in NOK øre")
    
    # Margin calculations
    markup_percentage = Column(Integer, default=0, comment="Markup percentage applied")
    margin_per_bottle_ore = Column(Integer, default=0, comment="Calculated margin per bottle in øre")
    
    # Inventory management
    minimum_stock_level = Column(Integer, default=0, comment="Minimum stock alert level")
    location = Column(String(100), comment="Storage location")
    best_before_date = Column(DateTime, comment="Best before date for quality tracking")
    
    # Inventory alerts
    low_stock_alert = Column(Boolean, default=False, comment="Low stock alert flag")
    
    # Relationships
    wine = relationship("Wine", back_populates="inventory_items")
    batch = relationship("WineBatch")
    
    def __repr__(self):
        return f"<WineInventory(wine_id={self.wine_id}, quantity={self.quantity_available})>"
    
    def calculate_margin(self):
        """Calculate margin per bottle and markup percentage"""
        self.margin_per_bottle_ore = self.selling_price_ore - self.cost_per_bottle_ore
        
        # Calculate markup percentage
        if self.cost_per_bottle_ore > 0:
            self.markup_percentage = int((self.margin_per_bottle_ore / self.cost_per_bottle_ore) * 100)
    
    def check_stock_alert(self):
        """Check if stock is below minimum level"""
        available_unreserved = self.quantity_available - self.quantity_reserved
        self.low_stock_alert = available_unreserved <= self.minimum_stock_level
    
    def reserve_stock(self, quantity):
        """Reserve stock for an order"""
        available = self.quantity_available - self.quantity_reserved
        if available >= quantity:
            self.quantity_reserved += quantity
            return True
        return False
    
    def release_reservation(self, quantity):
        """Release reserved stock (e.g., when order is cancelled)"""
        self.quantity_reserved = max(0, self.quantity_reserved - quantity)
    
    def sell_stock(self, quantity):
        """Process a sale - remove from available and reserved, add to sold"""
        if self.quantity_reserved >= quantity:
            self.quantity_reserved -= quantity
            self.quantity_available -= quantity
            self.quantity_sold += quantity
            self.check_stock_alert()  # Update alert status
            return True
        return False
    
    def get_available_stock(self):
        """Get available stock (not reserved)"""
        return self.quantity_available - self.quantity_reserved
    
    def to_dict(self):
        return {
            'id': str(self.id),
            'wine_id': str(self.wine_id),
            'batch_id': str(self.batch_id) if self.batch_id else None,
            'quantity_available': self.quantity_available,
            'quantity_reserved': self.quantity_reserved,
            'quantity_sold': self.quantity_sold,
            'cost_per_bottle_ore': self.cost_per_bottle_ore,
            'selling_price_ore': self.selling_price_ore,
            'markup_percentage': self.markup_percentage,
            'margin_per_bottle_ore': self.margin_per_bottle_ore,
            'minimum_stock_level': self.minimum_stock_level,
            'location': self.location,
            'best_before_date': self.best_before_date.isoformat() if self.best_before_date else None,
            'low_stock_alert': self.low_stock_alert,
            'available_stock': self.get_available_stock(),
            'active': self.active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        } 