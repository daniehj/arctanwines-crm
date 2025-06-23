#!/usr/bin/env python3
"""
Migration Testing Hook
Tests migrations locally when models or migration files change
"""
import os
import sys
import subprocess
import sqlite3
import tempfile
import shutil
from pathlib import Path
from datetime import datetime

def detect_changes(changed_files):
    """Detect what type of changes occurred"""
    changes = {
        'models': [],
        'migrations': [],
        'has_model_changes': False,
        'has_migration_changes': False
    }
    
    for file_path in changed_files:
        if 'models/' in file_path and file_path.endswith('.py'):
            changes['models'].append(file_path)
            changes['has_model_changes'] = True
        elif 'alembic/versions/' in file_path and file_path.endswith('.py'):
            changes['migrations'].append(file_path)
            changes['has_migration_changes'] = True
    
    return changes

def create_test_database():
    """Create a temporary SQLite database for testing"""
    temp_dir = tempfile.mkdtemp(prefix="migration_test_")
    db_path = Path(temp_dir) / "test_migration.db"
    
    print(f"📁 Created test database: {db_path}")
    return str(db_path), temp_dir

def populate_test_fixtures(db_path):
    """Populate test database with fixtures"""
    print("🧪 Loading test fixtures...")
    
    # Import fixtures
    import sys
    from pathlib import Path
    
    # Add scripts directory to path
    scripts_dir = Path(__file__).parent
    sys.path.insert(0, str(scripts_dir))
    
    try:
        from fixtures.test_data import (
            generate_wine_batch_fixtures,
            generate_customer_fixtures,
            generate_order_fixtures,
            generate_order_item_fixtures
        )
    except ImportError as e:
        print(f"⚠️  Could not import fixtures: {e}")
        print("⚠️  Using basic fixtures instead")
        _populate_basic_fixtures(db_path)
        return
    
    # Connect to SQLite
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Load wine batch fixtures
        wine_fixtures = generate_wine_batch_fixtures()
        wine_ids = []
        
        for wine in wine_fixtures:
            try:
                cursor.execute("""
                    INSERT OR IGNORE INTO wine_batches (
                        id, batch_number, wine_name, producer, total_bottles,
                        status, total_cost_nok_ore, target_price_nok_ore, 
                        import_date, active, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    wine['id'], wine['batch_number'], wine['wine_name'], wine['producer'],
                    wine['total_bottles'], wine['status'], wine['total_cost_nok_ore'],
                    wine['target_price_nok_ore'], wine['import_date'], wine['active'],
                    wine['created_at'], wine['updated_at']
                ))
                wine_ids.append(wine['id'])
            except Exception as e:
                print(f"⚠️  Error inserting wine batch {wine.get('wine_name', 'unknown')}: {e}")
        
        print(f"✅ Loaded {len(wine_ids)} wine batch fixtures")
        
        # Check if customers table exists (Phase 3)
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='customers'
        """)
        
        customer_ids = []
        if cursor.fetchone():
            customer_fixtures = generate_customer_fixtures()
            
            for customer in customer_fixtures:
                try:
                    cursor.execute("""
                        INSERT OR IGNORE INTO customers (
                            id, organization_number, company_name, contact_person,
                            email, phone, address, postal_code, city, vat_number,
                            payment_terms_days, discount_percentage, customer_category,
                            notes, created_at, updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        customer['id'], customer['organization_number'], customer['company_name'],
                        customer['contact_person'], customer['email'], customer['phone'],
                        customer['address'], customer['postal_code'], customer['city'],
                        customer['vat_number'], customer['payment_terms_days'],
                        customer['discount_percentage'], customer['customer_category'],
                        customer['notes'], customer['created_at'], customer['updated_at']
                    ))
                    customer_ids.append(customer['id'])
                except Exception as e:
                    print(f"⚠️  Error inserting customer {customer.get('company_name', 'unknown')}: {e}")
            
            print(f"✅ Loaded {len(customer_ids)} customer fixtures")
            
            # Load orders and order items if we have customers and wines
            if customer_ids and wine_ids:
                _load_order_fixtures(cursor, customer_ids, wine_ids)
        
        conn.commit()
        print("✅ All test fixtures loaded successfully")
        
    except Exception as e:
        print(f"⚠️  Warning loading fixtures: {e}")
        # Fall back to basic fixtures
        _populate_basic_fixtures(db_path)
    finally:
        conn.close()

def _load_order_fixtures(cursor, customer_ids, wine_ids):
    """Load order and order item fixtures"""
    try:
        from fixtures.test_data import generate_order_fixtures, generate_order_item_fixtures
        
        # Check if orders table exists
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='orders'
        """)
        
        if not cursor.fetchone():
            return
        
        order_fixtures = generate_order_fixtures(customer_ids, wine_ids)
        order_ids = []
        
        for order in order_fixtures:
            try:
                cursor.execute("""
                    INSERT OR IGNORE INTO orders (
                        id, customer_id, order_number, order_date, expected_delivery_date,
                        status, total_amount_nok, vat_amount_nok, payment_status,
                        payment_terms_days, discount_percentage, notes, shipping_address,
                        created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    order['id'], order['customer_id'], order['order_number'],
                    order['order_date'], order['expected_delivery_date'], order['status'],
                    order['total_amount_nok'], order['vat_amount_nok'], order['payment_status'],
                    order['payment_terms_days'], order['discount_percentage'], order['notes'],
                    order['shipping_address'], order['created_at'], order['updated_at']
                ))
                order_ids.append(order['id'])
            except Exception as e:
                print(f"⚠️  Error inserting order {order.get('order_number', 'unknown')}: {e}")
        
        print(f"✅ Loaded {len(order_ids)} order fixtures")
        
        # Load order items
        if order_ids:
            item_fixtures = generate_order_item_fixtures(order_ids, wine_ids)
            item_count = 0
            
            for item in item_fixtures:
                try:
                    cursor.execute("""
                        INSERT OR IGNORE INTO order_items (
                            id, order_id, wine_batch_id, quantity, unit_price_nok,
                            total_price_nok, margin_percentage, notes
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        item['id'], item['order_id'], item['wine_batch_id'],
                        item['quantity'], item['unit_price_nok'], item['total_price_nok'],
                        item['margin_percentage'], item['notes']
                    ))
                    item_count += 1
                except Exception as e:
                    print(f"⚠️  Error inserting order item: {e}")
            
            print(f"✅ Loaded {item_count} order item fixtures")
    
    except Exception as e:
        print(f"⚠️  Error loading order fixtures: {e}")

def _populate_basic_fixtures(db_path):
    """Fallback basic fixtures if main fixtures fail"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Basic wine batch data
        cursor.execute("""
            INSERT OR IGNORE INTO wine_batches (
                id, wine_name, producer, region, vintage, grape_variety,
                alcohol_content, volume_ml, bottles_in_batch,
                cost_per_bottle_nok, status, created_at, updated_at
            ) VALUES (
                'test-batch-1', 'Test Barolo', 'Test Producer', 'Piedmont',
                2019, 'Nebbiolo', 14.5, 750, 12,
                450.0, 'available', datetime('now'), datetime('now')
            )
        """)
        
        conn.commit()
        print("✅ Basic test fixtures loaded")
        
    except Exception as e:
        print(f"⚠️  Error loading basic fixtures: {e}")
    finally:
        conn.close()

def run_migration_test(db_path):
    """Run Alembic migrations on test database"""
    print("🔄 Running migration test...")
    
    # Set environment variables for test
    env = os.environ.copy()
    env['DATABASE_URL'] = f'sqlite:///{db_path}'
    env['PYTHONPATH'] = str(Path.cwd() / 'amplify/functions/db-migrations')
    
    migration_dir = Path('amplify/functions/db-migrations')
    
    if not migration_dir.exists():
        print("❌ Migration directory not found")
        return False
    
    try:
        # Change to migration directory
        original_cwd = os.getcwd()
        os.chdir(migration_dir)
        
        # Run Alembic upgrade
        result = subprocess.run(
            [sys.executable, '-m', 'alembic', 'upgrade', 'head'],
            env=env,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='ignore'
        )
        
        os.chdir(original_cwd)
        
        if result.returncode == 0:
            print("✅ Migration test passed!")
            return True
        else:
            print(f"❌ Migration test failed:")
            print(f"STDOUT: {result.stdout}")
            print(f"STDERR: {result.stderr}")
            return False
            
    except Exception as e:
        os.chdir(original_cwd)
        print(f"❌ Error running migration test: {e}")
        return False

def validate_database_schema(db_path):
    """Validate the final database schema"""
    print("🔍 Validating database schema...")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check that core tables exist
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name NOT LIKE 'sqlite_%'
            ORDER BY name
        """)
        
        tables = [row[0] for row in cursor.fetchall()]
        print(f"📊 Found tables: {', '.join(tables)}")
        
        # Ensure wine_batches exists (core requirement)
        if 'wine_batches' not in tables:
            print("❌ Missing core table: wine_batches")
            return False
        
        # Check alembic_version table exists
        if 'alembic_version' not in tables:
            print("❌ Missing alembic_version table")
            return False
            
        # Get current migration version
        cursor.execute("SELECT version_num FROM alembic_version")
        version = cursor.fetchone()
        if version:
            print(f"📋 Current migration version: {version[0]}")
        else:
            print("⚠️  No migration version found")
        
        print("✅ Database schema validation passed")
        return True
        
    except Exception as e:
        print(f"❌ Schema validation error: {e}")
        return False
    finally:
        conn.close()

def cleanup_test_environment(temp_dir):
    """Clean up temporary test files"""
    try:
        shutil.rmtree(temp_dir)
        print("🧹 Cleaned up test environment")
    except Exception as e:
        print(f"⚠️  Warning: Could not clean up {temp_dir}: {e}")

def main():
    if len(sys.argv) < 2:
        print("❌ No files provided to check")
        sys.exit(1)
    
    changed_files = sys.argv[1:]
    changes = detect_changes(changed_files)
    
    print("🔍 Migration Test Hook")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📁 Changed files: {len(changed_files)}")
    
    if changes['has_model_changes']:
        print(f"🔧 Model changes detected: {changes['models']}")
    
    if changes['has_migration_changes']:
        print(f"📜 Migration changes detected: {changes['migrations']}")
    
    if not (changes['has_model_changes'] or changes['has_migration_changes']):
        print("ℹ️  No relevant changes detected, skipping migration test")
        return
    
    # Create test environment
    db_path, temp_dir = create_test_database()
    
    try:
        # Run the migration test
        if not run_migration_test(db_path):
            print("❌ Migration test failed - commit blocked")
            sys.exit(1)
        
        # Populate with test data
        populate_test_fixtures(db_path)
        
        # Validate schema
        if not validate_database_schema(db_path):
            print("❌ Schema validation failed - commit blocked")
            sys.exit(1)
        
        print("🎉 All migration tests passed!")
        
    finally:
        cleanup_test_environment(temp_dir)

if __name__ == "__main__":
    main() 