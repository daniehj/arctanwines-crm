#!/usr/bin/env python3
"""
Schema Diagnostic Tool
Helps identify what columns actually exist vs what's expected
"""

import os
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def diagnose_schema():
    """
    This script will help diagnose schema issues by showing:
    1. What columns your schema validation expects
    2. What we can determine from migration files
    3. Suggested fixes
    """
    
    print("🔍 Schema Diagnostic Tool")
    print("=" * 50)
    
    # Expected schema from your Data Management output
    expected_schema = {
        'wine_batch_costs': [
            'id', 'batch_id', 'cost_type', 'amount_ore', 'currency',
            'fiken_account_code', 'payment_date', 'allocation_method',
            'invoice_reference', 'active', 'created_at', 'updated_at'
        ],
        'order_items': [
            'id', 'order_id', 'wine_batch_id', 'wine_id', 'quantity',
            'unit_price_ore', 'total_price_ore', 'wine_name', 'producer',
            'vintage', 'bottle_size_ml', 'discount_percentage', 'discount_ore',
            'notes', 'active', 'created_at', 'updated_at'
        ]
    }
    
    print("📋 Expected Schema for Partial Tables:")
    print()
    
    for table_name, columns in expected_schema.items():
        print(f"🔸 {table_name} (expected {len(columns)} columns):")
        for i, col in enumerate(columns, 1):
            print(f"   {i:2d}. {col}")
        print()
    
    print("🔍 Possible Issues:")
    print()
    print("1. 📛 **Table doesn't exist**: Migration didn't create the table")
    print("2. 📛 **Missing columns**: Table exists but missing some columns") 
    print("3. 📛 **Wrong column names**: Columns exist but with different names")
    print("4. 📛 **Wrong data types**: Columns exist but wrong type")
    print("5. 📛 **Case sensitivity**: Column names have different case")
    print()
    
    print("💡 Diagnostic Steps:")
    print()
    print("**Step 1: Check if tables exist**")
    print("   - Look in your Data Management UI")
    print("   - Tables should be listed even if 'partial'")
    print()
    
    print("**Step 2: Check actual column names**")
    print("   - If you have database access, run:")
    print("   - `SELECT column_name FROM information_schema.columns WHERE table_name = 'wine_batch_costs';`")
    print("   - `SELECT column_name FROM information_schema.columns WHERE table_name = 'order_items';`")
    print()
    
    print("**Step 3: Check migration history**")
    print("   - Our migrations created these tables in migration 15d72e03b4c4")
    print("   - Added missing columns in migration 720ed1fa374c")
    print("   - Check if both migrations were applied")
    print()
    
    print("🛠️ Potential Solutions:")
    print()
    print("**Solution A: Force column creation**")
    print("   - Create a new migration that uses IF NOT EXISTS logic")
    print("   - Add columns with different approach")
    print()
    
    print("**Solution B: Check column name mapping**")
    print("   - Your schema validation might expect different column names")
    print("   - Check what your validation code is looking for")
    print()
    
    print("**Solution C: Manual SQL fix**")
    print("   - If you have database access, manually add missing columns")
    print("   - Then mark migration as applied")
    print()
    
    print("📊 Migration Analysis:")
    print()
    
    # Check migration files
    migration_dir = project_root / "amplify/functions/db-migrations/alembic/versions"
    
    if migration_dir.exists():
        migrations = list(migration_dir.glob("*.py"))
        migrations = [m for m in migrations if not m.name.startswith("__")]
        
        print(f"Found {len(migrations)} migration files:")
        for migration in sorted(migrations):
            print(f"   📄 {migration.name}")
        print()
        
        # Check the latest migration that should have created these tables
        latest_migration = migration_dir / "720ed1fa374c_add_missing_columns_to_existing_tables.py"
        if latest_migration.exists():
            print("✅ Latest migration file exists (720ed1fa374c)")
            print("   This migration should add missing columns to both tables")
        else:
            print("❌ Latest migration file missing")
    
    print()
    print("🎯 **Next Steps:**")
    print("1. Check if tables wine_batch_costs and order_items exist in your database")
    print("2. If they exist, check what columns they actually have")
    print("3. Compare actual columns with expected columns above")
    print("4. Let me know what you find - I can create a targeted fix")
    print()
    print("**To get actual column info from your database:**")
    print("- Look in your database management tool")
    print("- Or check if your Data Management UI shows column details")
    print("- Or run SQL queries if you have direct access")

if __name__ == "__main__":
    diagnose_schema() 