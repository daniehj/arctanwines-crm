#!/usr/bin/env python3
"""
Manual Migration Testing
Test database migrations manually with fixtures
"""

import os
import sys
import argparse
import subprocess
import sqlite3
import tempfile
import shutil
from pathlib import Path
from datetime import datetime

def create_test_database_with_fixtures():
    """Create test database and populate with fixtures"""
    print("🏗️  Creating test database with fixtures...")
    
    # Create temporary database
    temp_dir = tempfile.mkdtemp(prefix="manual_migration_test_")
    db_path = Path(temp_dir) / "test_migration.db"
    
    print(f"📁 Test database: {db_path}")
    
    # Set environment for migration
    env = os.environ.copy()
    env['DATABASE_URL'] = f'sqlite:///{db_path}'
    env['PYTHONPATH'] = str(Path.cwd() / 'amplify/functions/db-migrations')
    
    migration_dir = Path('amplify/functions/db-migrations')
    
    if not migration_dir.exists():
        print("❌ Migration directory not found")
        return None, None
    
    try:
        # Change to migration directory
        original_cwd = os.getcwd()
        os.chdir(migration_dir)
        
        # Run Alembic upgrade
        print("🔄 Running Alembic migrations...")
        result = subprocess.run(
            [sys.executable, '-m', 'alembic', 'upgrade', 'head'],
            env=env,
            capture_output=True,
            text=True
        )
        
        os.chdir(original_cwd)
        
        if result.returncode != 0:
            print(f"❌ Migration failed:")
            print(f"STDOUT: {result.stdout}")
            print(f"STDERR: {result.stderr}")
            return None, None
        
        print("✅ Migrations completed successfully")
        
        # Populate with fixtures
        try:
            # Make sure we can import from the project root
            project_root = Path(original_cwd)
            if str(project_root) not in sys.path:
                sys.path.insert(0, str(project_root))
            
            from scripts.fixtures.test_data import (
                generate_wine_batch_fixtures,
                generate_customer_fixtures
            )
            
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Load wine fixtures
            wine_fixtures = generate_wine_batch_fixtures()
            for wine in wine_fixtures:
                try:
                    cursor.execute("""
                        INSERT INTO wine_batches (
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
                except Exception as e:
                    print(f"⚠️  Error inserting wine: {e}")
            
            # Check for customers table
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='customers'")
            if cursor.fetchone():
                customer_fixtures = generate_customer_fixtures()
                for customer in customer_fixtures:
                    try:
                        cursor.execute("""
                            INSERT INTO customers (
                                id, organization_number, name, customer_type, contact_person,
                                email, phone, address_line1, postal_code, city, country, vat_number,
                                payment_terms, credit_limit_nok_ore, marketing_consent,
                                newsletter_subscription, preferred_language, notes, fiken_customer_id,
                                active, created_at, updated_at
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            customer['id'], customer['organization_number'], customer['name'],
                            customer['customer_type'], customer['contact_person'], customer['email'],
                            customer['phone'], customer['address_line1'], customer['postal_code'],
                            customer['city'], customer['country'], customer['vat_number'],
                            customer['payment_terms'], customer['credit_limit_nok_ore'],
                            customer['marketing_consent'], customer['newsletter_subscription'],
                            customer['preferred_language'], customer['notes'], customer['fiken_customer_id'],
                            customer['active'], customer['created_at'], customer['updated_at']
                        ))
                    except Exception as e:
                        print(f"⚠️  Error inserting customer: {e}")
            
            conn.commit()
            conn.close()
            print("🧪 Test fixtures loaded successfully")
            
        except ImportError:
            print("⚠️  Could not load fixtures - using empty database")
        except Exception as e:
            print(f"⚠️  Error loading fixtures: {e}")
        
        return str(db_path), temp_dir
        
    except Exception as e:
        os.chdir(original_cwd)
        print(f"❌ Error creating test database: {e}")
        return None, None

def inspect_database(db_path):
    """Inspect the database schema and data"""
    print("\n🔍 Database Inspection")
    print("=" * 50)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # List all tables
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name NOT LIKE 'sqlite_%'
            ORDER BY name
        """)
        tables = [row[0] for row in cursor.fetchall()]
        print(f"📊 Tables ({len(tables)}): {', '.join(tables)}")
        
        # Show alembic version
        if 'alembic_version' in tables:
            cursor.execute("SELECT version_num FROM alembic_version")
            version = cursor.fetchone()
            if version:
                print(f"📋 Migration version: {version[0]}")
        
        # Show row counts for each table
        print("\n📈 Row counts:")
        for table in tables:
            if table != 'alembic_version':
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                print(f"  {table}: {count} rows")
        
        # Show sample data from wine_batches
        if 'wine_batches' in tables:
            print("\n🍷 Sample wine batches:")
            cursor.execute("SELECT wine_name, producer, status, total_bottles FROM wine_batches LIMIT 5")
            for row in cursor.fetchall():
                print(f"  • {row[0]} by {row[1]} ({row[2]}, {row[3]} bottles)")
        
        # Show sample customers if available
        if 'customers' in tables:
            print("\n👥 Sample customers:")
            cursor.execute("SELECT name, customer_type FROM customers LIMIT 3")
            for row in cursor.fetchall():
                print(f"  • {row[0]} ({row[1]})")
                
    except Exception as e:
        print(f"❌ Error inspecting database: {e}")
    finally:
        conn.close()

def main():
    parser = argparse.ArgumentParser(description="Manual Migration Testing Tool")
    parser.add_argument("--inspect", action="store_true", 
                       help="Inspect database after migration")
    parser.add_argument("--keep-db", action="store_true",
                       help="Keep test database after completion")
    
    args = parser.parse_args()
    
    print("🧪 Manual Migration Testing Tool")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # Create test database
    db_path, temp_dir = create_test_database_with_fixtures()
    
    if not db_path:
        print("❌ Failed to create test database")
        sys.exit(1)
    
    try:
        print(f"\n✅ Test database ready: {db_path}")
        
        if args.inspect:
            inspect_database(db_path)
        else:
            # Default behavior - show basic info
            inspect_database(db_path)
            
        print("\n💡 Usage:")
        print(f"• Database path: {db_path}")
        print(f"• Re-run with --inspect for detailed analysis")
        print(f"• Use --keep-db to preserve database after exit")
    
    finally:
        if not args.keep_db:
            try:
                shutil.rmtree(temp_dir)
                print(f"\n🧹 Cleaned up test database")
            except Exception as e:
                print(f"\n⚠️  Warning: Could not clean up {temp_dir}: {e}")
        else:
            print(f"\n💾 Test database preserved at: {db_path}")

if __name__ == "__main__":
    main() 