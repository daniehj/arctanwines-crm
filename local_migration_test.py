#!/usr/bin/env python3
"""
Local Migration Testing Script for Arctan Wines CRM
Uses the existing db-migrations Alembic setup for local testing before production deployment

Usage:
    python local_migration_test.py test      # Test migrations locally
    python local_migration_test.py current   # Check current revision
    python local_migration_test.py history   # View migration history
    python local_migration_test.py create "migration name"  # Create new migration
"""
import os
import subprocess
import sys
from pathlib import Path

def run_command(cmd, cwd=None):
    """Run a command and return the result"""
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            shell=True if sys.platform == "win32" else False
        )
        return {
            "success": result.returncode == 0,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode
        }
    except Exception as e:
        return {
            "success": False,
            "stdout": "",
            "stderr": str(e),
            "returncode": -1
        }

def test_migrations_locally():
    """Test migrations on local SQLite database"""
    print("🧪 TESTING MIGRATIONS LOCALLY")
    print("=" * 50)
    
    # Set up local environment
    db_migrations_dir = Path("amplify/functions/db-migrations")
    if not db_migrations_dir.exists():
        print("❌ db-migrations directory not found!")
        return False
    
    # Set environment variable for local testing
    env = os.environ.copy()
    env['DATABASE_URL'] = 'sqlite:///./test_arctanwines.db'
    
    print("1. Setting up local SQLite database...")
    print(f"   Database: {db_migrations_dir}/test_arctanwines.db")
    
    # Change to db-migrations directory and run Alembic commands
    print("\n2. Checking current revision...")
    current_cmd = ["python", "-m", "alembic", "current"]
    result = subprocess.run(current_cmd, cwd=db_migrations_dir, env=env, capture_output=True, text=True)
    
    if result.returncode == 0:
        print(f"✅ Current revision: {result.stdout.strip() or 'None (fresh database)'}")
    else:
        print(f"⚠️  Warning: {result.stderr}")
    
    print("\n3. Running migrations...")
    upgrade_cmd = ["python", "-m", "alembic", "upgrade", "head"]
    result = subprocess.run(upgrade_cmd, cwd=db_migrations_dir, env=env, capture_output=True, text=True)
    
    if result.returncode == 0:
        print("✅ Local migration test PASSED!")
        print("📋 Migration output:")
        print(result.stdout)
        
        # Show final revision
        final_cmd = ["python", "-m", "alembic", "current"]
        final_result = subprocess.run(final_cmd, cwd=db_migrations_dir, env=env, capture_output=True, text=True)
        if final_result.returncode == 0:
            print(f"📍 Final revision: {final_result.stdout.strip()}")
        
        return True
    else:
        print("❌ Local migration test FAILED!")
        print("Error output:")
        print(result.stderr)
        return False

def check_current_revision():
    """Check current migration revision"""
    print("📋 CHECKING CURRENT REVISION")
    print("=" * 30)
    
    db_migrations_dir = Path("amplify/functions/db-migrations")
    
    # Check local revision
    print("Local database:")
    env = os.environ.copy()
    env['DATABASE_URL'] = 'sqlite:///./test_arctanwines.db'
    
    cmd = ["python", "-m", "alembic", "current"]
    result = subprocess.run(cmd, cwd=db_migrations_dir, env=env, capture_output=True, text=True)
    
    if result.returncode == 0:
        print(f"  Local: {result.stdout.strip() or 'None'}")
    else:
        print(f"  Local: Error - {result.stderr}")
    
    # Check production revision (this would use SSM parameters)
    print("\nProduction database:")
    cmd = ["python", "-m", "alembic", "current"]
    result = subprocess.run(cmd, cwd=db_migrations_dir, capture_output=True, text=True)
    
    if result.returncode == 0:
        print(f"  Production: {result.stdout.strip() or 'None'}")
    else:
        print(f"  Production: Error - {result.stderr}")

def show_migration_history():
    """Show migration history"""
    print("📚 MIGRATION HISTORY")
    print("=" * 20)
    
    db_migrations_dir = Path("amplify/functions/db-migrations")
    cmd = ["python", "-m", "alembic", "history", "--verbose"]
    result = subprocess.run(cmd, cwd=db_migrations_dir, capture_output=True, text=True)
    
    if result.returncode == 0:
        print(result.stdout)
    else:
        print(f"Error: {result.stderr}")

def create_migration(message):
    """Create a new migration"""
    print(f"🔧 CREATING NEW MIGRATION: {message}")
    print("=" * 40)
    
    db_migrations_dir = Path("amplify/functions/db-migrations")
    cmd = ["python", "-m", "alembic", "revision", "--autogenerate", "-m", message]
    result = subprocess.run(cmd, cwd=db_migrations_dir, capture_output=True, text=True)
    
    if result.returncode == 0:
        print("✅ Migration created successfully!")
        print(result.stdout)
    else:
        print("❌ Migration creation failed!")
        print(result.stderr)

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    
    command = sys.argv[1].lower()
    
    if command == "test":
        success = test_migrations_locally()
        print("\n" + "=" * 50)
        if success:
            print("🎉 LOCAL TEST PASSED - Safe to deploy!")
        else:
            print("💥 LOCAL TEST FAILED - Do NOT deploy!")
        sys.exit(0 if success else 1)
        
    elif command == "current":
        check_current_revision()
        
    elif command == "history":
        show_migration_history()
        
    elif command == "create":
        if len(sys.argv) < 3:
            print("Usage: python local_migration_test.py create \"migration message\"")
            sys.exit(1)
        create_migration(sys.argv[2])
        
    else:
        print(f"Unknown command: {command}")
        print(__doc__)
        sys.exit(1)

if __name__ == "__main__":
    main() 