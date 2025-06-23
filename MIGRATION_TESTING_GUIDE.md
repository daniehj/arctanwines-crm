# Migration Testing System - Enhanced Guide

## 🎯 Overview

This enhanced migration testing system provides:
- **Automatic model change detection** with guided workflow
- **Migration compatibility testing** with SQLite/PostgreSQL support  
- **Lambda runtime compatibility checking** for dependencies
- **Norwegian wine import fixtures** for realistic testing
- **Pre-commit hook integration** for automated validation

## 🚀 Quick Start

### 1. Setup (One-time)
```bash
python scripts/setup_pre_commit.py
```

### 2. Development Workflow

#### When Modifying Models:
1. **Edit your model files** in `amplify/functions/db-migrations/models/`
2. **Commit your changes** - the hook will detect model changes and guide you:

```bash
git add amplify/functions/db-migrations/models/wine_batch.py
git commit -m "Add new wine batch fields"
```

**Expected Output:**
```
🎯 MIGRATION WORKFLOW GUIDANCE
============================================================
📋 MODEL CHANGES DETECTED - MIGRATION REQUIRED

🔍 Detected changes:
   • New column(s) in amplify/functions/db-migrations/models/wine_batch.py

🚨 NEXT STEPS REQUIRED:
   1. Generate migration for your model changes:
      cd amplify/functions/db-migrations
      python -m alembic revision --autogenerate -m "Add wine batch fields"

   2. Review the generated migration file...
   
❌ COMMIT BLOCKED: Please generate migration first!
```

3. **Follow the guidance** to generate and test your migration
4. **Commit both** model and migration changes together

#### When Migration Exists:
If you have both model and migration changes, the hook automatically:
- ✅ **Tests migrations** against SQLite database
- ✅ **Loads realistic fixtures** (Norwegian wine import data)
- ✅ **Validates schema** structure
- ✅ **Checks Lambda compatibility** of dependencies

## 🔍 Enhanced Features

### Model Change Detection

The system automatically detects:
- **New model classes** (`class WineBatch(Base):`)
- **New columns** (`Column(String(255))`)
- **New relationships** (`relationship("Customer")`)
- **New tables** (`__tablename__ = "wine_batches"`)

### Lambda Compatibility Checking

Automatically scans `requirements.txt` files for packages that won't work on AWS Lambda:

#### ❌ **Blocked Packages** (will fail deployment):
- `pydantic-core` → Use pydantic v1.x instead
- `psycopg2` → Use `psycopg2-binary` instead
- `lxml` → Use `xml.etree.ElementTree`
- `mysqlclient` → Use `PyMySQL` instead

#### ⚠️ **Warning Packages** (may cause issues):
- `numpy`, `pandas` → Consider AWS Lambda layers
- `pillow` → Consider Lambda layers or alternatives
- `cryptography` → May need specific versions

#### ✅ **Recommended Packages**:
- `psycopg2-binary` - Lambda-compatible PostgreSQL driver
- `pg8000` - Pure Python PostgreSQL driver  
- `boto3` - AWS SDK
- `sqlalchemy` - ORM with compatible drivers
- `alembic` - Migration tool

### Migration Testing Scenarios

The system handles different scenarios intelligently:

#### Scenario 1: Model Changes Only
```
📋 MODEL CHANGES DETECTED - MIGRATION REQUIRED
❌ COMMIT BLOCKED: Please generate migration first!
```

#### Scenario 2: Model + Migration Changes  
```
✅ MODEL + MIGRATION CHANGES DETECTED
🧪 Testing migration compatibility...
```

#### Scenario 3: Migration Only
```
🔄 MIGRATION-ONLY CHANGES DETECTED  
🧪 Testing migration...
```

## 🧪 Testing Tools

### Manual Testing
```bash
# Test current migrations
python scripts/manual_migration_test.py

# Test with detailed inspection
python scripts/manual_migration_test.py --inspect

# Keep database for manual inspection
python scripts/manual_migration_test.py --keep-db
```

### Lambda Compatibility Testing
```bash
# Test Lambda compatibility
python scripts/test_lambda_compatibility.py
```

## 📊 Norwegian Wine Import Fixtures

The system includes realistic test data:

### Wine Batches (4 fixtures)
- **Barolo DOCG** by Fontanafredda (Italian, 12 bottles, 89,500 NOK)
- **Chianti Classico DOCG** by Castello di Brolio (Italian, 24 bottles, 67,200 NOK)  
- **Chablis Premier Cru** by Domaine William Fèvre (French, 6 bottles, 45,000 NOK)
- **Ribera del Duero** by Vega Sicilia (Spanish, 18 bottles, 134,500 NOK)

### Norwegian Customers (3 fixtures)
- **Maaemo Restaurant AS** (Michelin starred, Oslo)
- **Theatercaféen AS** (Historic restaurant, Oslo)
- **Vinmonopolet** (State wine monopoly)

### Features
- **Norwegian compliance**: Organization numbers, 25% VAT
- **NOK øre pricing**: All amounts in øre (1 NOK = 100 øre)
- **Realistic margins**: 40-60% markup for restaurants
- **Fiken integration**: Account codes and sync status

## 🛠️ Configuration Files

### Pre-commit Configuration
```yaml
# .pre-commit-config.yaml
- id: test-migrations-on-model-changes
  name: Enhanced Migration Testing & Lambda Compatibility
  entry: python scripts/test_migrations_hook.py
  files: '^amplify/functions/db-migrations/models/.*\.py$|^amplify/functions/db-migrations/alembic/versions/.*\.py$|.*requirements\.txt$'
```

### Alembic Configuration
```ini
# amplify/functions/db-migrations/alembic.ini
sqlalchemy.url = sqlite:///test_migration.db  # For testing
# Production uses PostgreSQL via environment variables
```

## 🚨 Troubleshooting

### Common Issues

#### "Model changes detected but no migration"
**Solution:** Generate migration first:
```bash
cd amplify/functions/db-migrations
python -m alembic revision --autogenerate -m "Describe your changes"
```

#### "Lambda compatibility issues found"
**Solution:** Replace problematic packages:
```bash
# Replace psycopg2 with psycopg2-binary
pip uninstall psycopg2
pip install psycopg2-binary
```

#### "Migration test failed"
**Solution:** Check migration syntax:
```bash
# Test migration manually
python scripts/manual_migration_test.py --inspect
```

#### "Schema validation failed"
**Solution:** Check if all expected tables/columns exist:
```bash
# Inspect database schema
python scripts/manual_migration_test.py --inspect --keep-db
```

### Debug Mode

For detailed debugging:
```bash
# Enable verbose output
export MIGRATION_DEBUG=1
python scripts/test_migrations_hook.py
```

## 📈 Best Practices

### Development Workflow
1. **Make model changes** in small, focused commits
2. **Generate migrations immediately** after model changes
3. **Test locally** before committing
4. **Review migration files** for correctness
5. **Use descriptive commit messages**

### Migration Guidelines
- **One migration per logical change**
- **Test both upgrade and downgrade** (when applicable)
- **Include data migrations** when needed
- **Document complex migrations** with comments

### Lambda Compatibility
- **Prefer pure Python packages** over compiled extensions
- **Use Lambda layers** for large binary packages
- **Test package compatibility** before adding dependencies
- **Keep requirements.txt** up to date

## 🔧 Advanced Usage

### Custom Fixtures
Add your own test data in `scripts/fixtures/test_data.py`:

```python
def generate_custom_fixtures():
    return [
        {
            'id': str(uuid.uuid4()),
            'name': 'Custom Wine',
            # ... more fields
        }
    ]
```

### Migration Templates
Use Alembic templates for consistent migrations:

```bash
# Generate migration with custom template
python -m alembic revision --autogenerate -m "Add wine inventory" --template=custom
```

### Database Inspection
The system provides detailed schema inspection:

```python
# In manual_migration_test.py --inspect mode
📊 Tables (9): customers, orders, order_items, wine_batches, ...
📋 Migration version: 62828d0c71cb
📈 Row counts: wine_batches: 4 rows, customers: 3 rows
```

## 🎉 Success Indicators

When everything works correctly, you'll see:

```
✅ PRE-COMMIT CHECKS COMPLETED SUCCESSFULLY
============================================================
🧪 All migration tests passed!
🔍 No Lambda compatibility issues found
📊 Schema validation successful
🍷 Test fixtures loaded (4 wine batches, 3 customers)
```

This indicates your changes are ready for production deployment!
