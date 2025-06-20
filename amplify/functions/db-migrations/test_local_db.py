#!/usr/bin/env python3
"""
Test local database setup for Arctan Wines CRM
"""
import os
import sys
from pathlib import Path

# Add current directory to Python path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

from models.base import Base
from models.wine_batch import WineBatch, WineBatchStatus
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

def test_local_database():
    """Test database connection and model creation"""
    print("🧪 Testing local database setup...")
    
    # Use local SQLite database
    database_url = "sqlite:///./test_arctanwines.db"
    print(f"Database URL: {database_url}")
    
    # Create engine and session
    engine = create_engine(database_url, echo=True)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    # Create tables
    print("Creating tables...")
    Base.metadata.create_all(bind=engine)
    
    # Test session
    db = SessionLocal()
    
    try:
        # Create a test wine batch
        print("Creating test wine batch...")
        test_batch = WineBatch(
            batch_number="TEST-2024-001",
            wine_name="Test Monastrell",
            producer="Test Bodega",
            total_bottles=144,
            total_cost_nok_ore=84000,  # 840.00 NOK
            target_price_nok_ore=18000,  # 180.00 NOK per bottle
            status=WineBatchStatus.ORDERED
        )
        
        db.add(test_batch)
        db.commit()
        db.refresh(test_batch)
        
        print(f"✅ Created batch: {test_batch}")
        print(f"   ID: {test_batch.id}")
        print(f"   Batch Number: {test_batch.batch_number}")
        print(f"   Wine Name: {test_batch.wine_name}")
        print(f"   Status: {test_batch.status.value}")
        print(f"   Created At: {test_batch.created_at}")
        
        # Query all batches
        print("\nQuerying all batches...")
        batches = db.query(WineBatch).all()
        print(f"Found {len(batches)} batch(es)")
        
        for batch in batches:
            print(f"  - {batch.batch_number}: {batch.wine_name} ({batch.status.value})")
        
        print("\n✅ Local database test completed successfully!")
        
    except Exception as e:
        print(f"❌ Database test failed: {str(e)}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    test_local_database() 