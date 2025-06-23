"""
Wine catalog and inventory models
"""
from sqlalchemy import Column, String, Integer, Boolean, Text, DECIMAL, ForeignKey
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

class WineInventory(BaseModel):
    """Wine inventory tracking with cost and pricing"""
    __tablename__ = 'wine_inventory'
    
    wine_id = Column(GUID(), ForeignKey('wines.id'), nullable=False, comment="Reference to wine")
    batch_id = Column(GUID(), ForeignKey('wine_batches.id'), comment="Reference to import batch")
    quantity_available = Column(Integer, nullable=False, default=0, comment="Current stock quantity")
    cost_per_bottle_ore = Column(Integer, nullable=False, comment="Cost per bottle in NOK øre")
    selling_price_ore = Column(Integer, nullable=False, comment="Selling price in NOK øre")
    minimum_stock_level = Column(Integer, default=0, comment="Minimum stock alert level")
    location = Column(String(100), comment="Storage location")
    best_before_date = Column(String(10), comment="Best before date (YYYY-MM-DD)")  # Using string for simplicity
    
    # Relationships
    wine = relationship("Wine", back_populates="inventory_items")
    
    def __repr__(self):
        return f"<WineInventory(wine_id={self.wine_id}, quantity={self.quantity_available})>" 