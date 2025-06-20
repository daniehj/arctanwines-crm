#!/usr/bin/env python3
"""
Create initial Alembic migration for Arctan Wines CRM
Generates migration for WineBatch and Customer models
"""
import subprocess
import sys
import os
from pathlib import Path

# Change to the function directory
function_dir = Path(__file__).parent
os.chdir(function_dir)

def run_alembic_command(args):
    """Run an Alembic command"""
    try:
        result = subprocess.run(['alembic'] + args, capture_output=True, text=True)
        print(f"Command: alembic {' '.join(args)}")
        print(f"Return code: {result.returncode}")
        if result.stdout:
            print(f"STDOUT:\n{result.stdout}")
        if result.stderr:
            print(f"STDERR:\n{result.stderr}")
        return result.returncode == 0
    except Exception as e:
        print(f"Error running alembic command: {e}")
        return False

def main():
    print("🚀 Creating small initial migration for Arctan Wines CRM")
    print("=" * 60)
    
    # Create initial migration
    print("📝 Creating migration: Simple wine batch model")
    success = run_alembic_command([
        'revision', 
        '--autogenerate', 
        '-m', 
        'Add simple wine batch model'
    ])
    
    if success:
        print("✅ Migration created successfully!")
        print("\n📋 Next steps:")
        print("1. Review the generated migration file in alembic/versions/")
        print("2. Test the migration with: python test_migration.py")
        print("3. Deploy the migration via the Lambda API")
    else:
        print("❌ Failed to create migration")
        sys.exit(1)

if __name__ == "__main__":
    main() 