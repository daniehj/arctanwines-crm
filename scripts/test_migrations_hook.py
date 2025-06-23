#!/usr/bin/env python3
"""
Enhanced Migration Testing Hook
- Detects model changes and provides guidance
- Tests migrations locally when models or migration files change
- Validates Lambda runtime compatibility
"""
import os
import sys
import subprocess
import sqlite3
import tempfile
import shutil
import re
from pathlib import Path
from datetime import datetime

# Lambda-incompatible packages (binary/compiled extensions)
LAMBDA_INCOMPATIBLE_PACKAGES = {
    'pydantic-core': 'Use pydantic v1.x instead of v2.x (pydantic-core is a compiled extension)',
    'psycopg2': 'Use psycopg2-binary instead (psycopg2 requires compilation)',
    'lxml': 'Contains C extensions, use xml.etree.ElementTree or pure Python alternatives',
    'pillow': 'Contains C extensions, consider using PIL alternatives or AWS Lambda layers',
    'numpy': 'Large binary package, consider using AWS Lambda layers',
    'pandas': 'Large binary package with C extensions, consider using AWS Lambda layers',
    'scipy': 'Large binary package with C extensions, consider using AWS Lambda layers',
    'matplotlib': 'Large binary package with C extensions, consider using AWS Lambda layers',
    'opencv-python': 'Large binary package, use opencv-python-headless or Lambda layers',
    'cryptography': 'Contains C extensions, may need specific versions for Lambda',
    'pyodbc': 'Contains C extensions, use pure Python database drivers',
    'mysqlclient': 'Contains C extensions, use PyMySQL instead',
    'cx-Oracle': 'Contains C extensions, not compatible with Lambda',
    'psycopg2-binary': '✅ OK - This is the Lambda-compatible version',
    'pg8000': '✅ OK - Pure Python PostgreSQL driver',
    'PyMySQL': '✅ OK - Pure Python MySQL driver',
    'boto3': '✅ OK - AWS SDK for Python',
    'requests': '✅ OK - Pure Python HTTP library',
    'sqlalchemy': '✅ OK - Pure Python ORM (with compatible drivers)',
    'alembic': '✅ OK - Pure Python migration tool',
    'pydantic': '✅ OK - Pure Python data validation (v1.x)',
}

def detect_changes(changed_files):
    """Detect what type of changes occurred"""
    changes = {
        'models': [],
        'migrations': [],
        'requirements': [],
        'has_model_changes': False,
        'has_migration_changes': False,
        'has_requirements_changes': False
    }
    
    for file_path in changed_files:
        if 'models/' in file_path and file_path.endswith('.py'):
            changes['models'].append(file_path)
            changes['has_model_changes'] = True
        elif 'alembic/versions/' in file_path and file_path.endswith('.py'):
            changes['migrations'].append(file_path)
            changes['has_migration_changes'] = True
        elif file_path.endswith('requirements.txt') or file_path.endswith('pyproject.toml'):
            changes['requirements'].append(file_path)
            changes['has_requirements_changes'] = True
    
    return changes

def check_lambda_compatibility():
    """Check for Lambda-incompatible packages in requirements"""
    print("\n🔍 Checking Lambda Runtime Compatibility...")
    
    issues = []
    warnings = []
    
    # Check requirements.txt files
    requirements_files = [
        'requirements.txt',
        'amplify/functions/api-main/requirements.txt',
        'amplify/functions/db-migrations/requirements.txt'
    ]
    
    for req_file in requirements_files:
        if not Path(req_file).exists():
            continue
            
        print(f"📄 Checking {req_file}...")
        
        try:
            with open(req_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            for line_num, line in enumerate(lines, 1):
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                
                # Extract package name (handle version specifiers)
                package_name = re.split(r'[>=<!=~]', line)[0].strip()
                
                if package_name in LAMBDA_INCOMPATIBLE_PACKAGES:
                    message = LAMBDA_INCOMPATIBLE_PACKAGES[package_name]
                    
                    if message.startswith('✅ OK'):
                        print(f"  ✅ {package_name}: {message}")
                    elif 'consider using' in message.lower() or 'may need' in message.lower():
                        warnings.append(f"{req_file}:{line_num} - {package_name}: {message}")
                        print(f"  ⚠️  {package_name}: {message}")
                    else:
                        issues.append(f"{req_file}:{line_num} - {package_name}: {message}")
                        print(f"  ❌ {package_name}: {message}")
                
        except Exception as e:
            print(f"⚠️  Error reading {req_file}: {e}")
    
    # Report results
    if issues:
        print(f"\n❌ Found {len(issues)} Lambda compatibility issues:")
        for issue in issues:
            print(f"   • {issue}")
        print("\n💡 These packages will likely cause Lambda deployment failures.")
        return False
    
    if warnings:
        print(f"\n⚠️  Found {len(warnings)} potential Lambda compatibility concerns:")
        for warning in warnings:
            print(f"   • {warning}")
        print("\n💡 These packages may work but could cause size or performance issues.")
    
    if not issues and not warnings:
        print("✅ No obvious Lambda compatibility issues found")
    
    return True

def analyze_model_changes(model_files):
    """Analyze what changed in model files"""
    print(f"\n🔍 Analyzing {len(model_files)} model file(s)...")
    
    changes_detected = []
    
    for model_file in model_files:
        print(f"📄 {model_file}")
        
        # Try to detect what changed using git diff
        try:
            result = subprocess.run([
                'git', 'diff', '--cached', model_file
            ], capture_output=True, text=True, encoding='utf-8', errors='ignore')
            
            if result.returncode == 0:
                diff_content = result.stdout
                
                # Look for common model changes
                if 'class ' in diff_content and '+' in diff_content:
                    changes_detected.append(f"New model class in {model_file}")
                if 'Column(' in diff_content and '+' in diff_content:
                    changes_detected.append(f"New column(s) in {model_file}")
                if 'relationship(' in diff_content and '+' in diff_content:
                    changes_detected.append(f"New relationship(s) in {model_file}")
                if '__tablename__' in diff_content and '+' in diff_content:
                    changes_detected.append(f"New table in {model_file}")
                
        except Exception as e:
            print(f"   ⚠️  Could not analyze changes: {e}")
    
    return changes_detected

def check_migration_status():
    """Check if migrations exist for model changes"""
    print("\n🔍 Checking migration status...")
    
    try:
        # Check if there are any migration files
        migration_dir = Path("amplify/functions/db-migrations/alembic/versions")
        if not migration_dir.exists():
            print("❌ Migration directory not found")
            return False
        
        migrations = list(migration_dir.glob("*.py"))
        migrations = [m for m in migrations if not m.name.startswith("__")]
        
        print(f"📊 Found {len(migrations)} existing migrations")
        
        # Check if there are uncommitted migrations
        try:
            result = subprocess.run([
                'git', 'diff', '--cached', '--name-only'
            ], capture_output=True, text=True, encoding='utf-8', errors='ignore')
            
            if result.returncode == 0:
                staged_files = result.stdout.strip().split('\n')
                staged_migrations = [f for f in staged_files if 'alembic/versions/' in f and f.endswith('.py')]
                
                if staged_migrations:
                    print(f"✅ Found {len(staged_migrations)} new migration(s) staged for commit:")
                    for migration in staged_migrations:
                        print(f"   📄 {migration}")
                    return True
                else:
                    print("⚠️  No new migrations found in staged files")
                    return False
        
        except Exception as e:
            print(f"⚠️  Could not check staged migrations: {e}")
            return False
    
    except Exception as e:
        print(f"❌ Error checking migration status: {e}")
        return False

def provide_migration_guidance(has_model_changes, has_migration_changes, model_changes):
    """Provide guidance based on detected changes"""
    print("\n" + "="*60)
    print("🎯 MIGRATION WORKFLOW GUIDANCE")
    print("="*60)
    
    if has_model_changes and not has_migration_changes:
        print("📋 MODEL CHANGES DETECTED - MIGRATION REQUIRED")
        print()
        print("🔍 Detected changes:")
        for change in model_changes:
            print(f"   • {change}")
        print()
        print("🚨 NEXT STEPS REQUIRED:")
        print("   1. Generate migration for your model changes:")
        print("      cd amplify/functions/db-migrations")
        print("      python -m alembic revision --autogenerate -m \"Your migration description\"")
        print()
        print("   2. Review the generated migration file:")
        print("      - Check that it captures your intended changes")
        print("      - Verify column types and constraints")
        print("      - Add any custom logic if needed")
        print()
        print("   3. Test the migration locally:")
        print("      python ../../../scripts/manual_migration_test.py")
        print()
        print("   4. Add the migration file to git:")
        print("      git add alembic/versions/[new_migration_file].py")
        print()
        print("   5. Commit both model and migration changes:")
        print("      git commit -m \"Add [description] with migration\"")
        print()
        print("❌ COMMIT BLOCKED: Please generate migration first!")
        return False
    
    elif has_model_changes and has_migration_changes:
        print("✅ MODEL + MIGRATION CHANGES DETECTED")
        print()
        print("🔍 Detected changes:")
        for change in model_changes:
            print(f"   • {change}")
        print()
        print("🧪 Testing migration compatibility...")
        return True  # Proceed with testing
    
    elif not has_model_changes and has_migration_changes:
        print("🔄 MIGRATION-ONLY CHANGES DETECTED")
        print()
        print("🧪 Testing migration...")
        return True  # Proceed with testing
    
    else:
        print("ℹ️  No model or migration changes detected")
        print("✅ Proceeding with other checks...")
        return True

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
    """Main hook function"""
    print("🔧 Enhanced Migration Testing Hook")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    
    # Get changed files from git
    try:
        result = subprocess.run([
            'git', 'diff', '--cached', '--name-only'
        ], capture_output=True, text=True, encoding='utf-8', errors='ignore')
        
        if result.returncode != 0:
            print("❌ Could not get changed files from git")
            return 1
        
        changed_files = result.stdout.strip().split('\n')
        changed_files = [f for f in changed_files if f]  # Remove empty strings
        
    except Exception as e:
        print(f"❌ Error getting changed files: {e}")
        return 1
    
    if not changed_files:
        print("ℹ️  No files changed, skipping migration checks")
        return 0
    
    print(f"📁 Checking {len(changed_files)} changed file(s)...")
    
    # Detect what types of changes occurred
    changes = detect_changes(changed_files)
    
    # Check Lambda compatibility for requirements changes
    if changes['has_requirements_changes']:
        if not check_lambda_compatibility():
            print("\n❌ Lambda compatibility issues found!")
            print("💡 Fix the package issues before committing")
            return 1
    
    # Handle model and migration changes
    if changes['has_model_changes'] or changes['has_migration_changes']:
        
        # Analyze model changes
        model_changes = []
        if changes['has_model_changes']:
            model_changes = analyze_model_changes(changes['models'])
        
        # Provide guidance and check if we should proceed
        should_proceed = provide_migration_guidance(
            changes['has_model_changes'], 
            changes['has_migration_changes'],
            model_changes
        )
        
        if not should_proceed:
            return 1
        
        # If we have migrations to test, run the tests
        if changes['has_migration_changes']:
            print("\n🧪 TESTING MIGRATIONS...")
            
            # Create test database
            db_path, temp_dir = create_test_database()
            
            try:
                # Run migrations
                if not run_migration_test(db_path):
                    print("\n❌ Migration test failed!")
                    return 1
                
                # Populate test data
                populate_test_fixtures(db_path)
                
                # Validate schema
                if not validate_database_schema(db_path):
                    print("\n❌ Schema validation failed!")
                    return 1
                
                print("\n✅ All migration tests passed!")
                
            finally:
                cleanup_test_environment(temp_dir)
    
    # Final Lambda compatibility check
    if not check_lambda_compatibility():
        print("\n⚠️  Lambda compatibility warnings detected")
        print("💡 Review the warnings above before deploying")
        # Don't fail on warnings, just inform
    
    print("\n" + "="*60)
    print("✅ PRE-COMMIT CHECKS COMPLETED SUCCESSFULLY")
    print("="*60)
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 