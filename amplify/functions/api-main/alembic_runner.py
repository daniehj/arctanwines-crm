"""
Alembic Migration Runner for Arctan Wines CRM
Provides local testing and production migration capabilities
"""
import os
import subprocess
import sys
from pathlib import Path
from typing import Dict, Any

def run_alembic_command(command_args: list, local_db: bool = False) -> Dict[str, Any]:
    """
    Run an Alembic command with environment-aware configuration
    
    Args:
        command_args: Alembic command arguments (e.g., ['upgrade', 'head'])
        local_db: If True, uses local SQLite for testing
    
    Returns:
        Dict with command result
    """
    try:
        # Set up environment for local testing
        if local_db:
            os.environ['DATABASE_URL'] = 'sqlite:///./test_arctanwines.db'
            print("🧪 Using LOCAL SQLite database for testing")
        
        # Change to the function directory where alembic.ini is located
        current_dir = Path(__file__).parent
        original_cwd = os.getcwd()
        os.chdir(current_dir)
        
        try:
            # Run the Alembic command
            result = subprocess.run(
                ['python', '-m', 'alembic'] + command_args,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            return {
                "success": result.returncode == 0,
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "command": " ".join(['alembic'] + command_args),
                "local_testing": local_db
            }
        finally:
            # Restore original working directory
            os.chdir(original_cwd)
            
            # Clean up environment variable
            if local_db and 'DATABASE_URL' in os.environ:
                del os.environ['DATABASE_URL']
                
    except Exception as e:
        return {
            "success": False,
            "returncode": -1,
            "stdout": "",
            "stderr": str(e),
            "command": " ".join(['alembic'] + command_args),
            "local_testing": local_db
        }

def test_migration_locally() -> Dict[str, Any]:
    """
    Test migrations on a local SQLite database before applying to production
    
    Returns:
        Dict with test results
    """
    print("🧪 TESTING MIGRATIONS LOCALLY")
    print("=" * 50)
    
    # Step 1: Check current revision in local DB
    print("1. Checking current local revision...")
    current_result = run_alembic_command(['current'], local_db=True)
    
    if not current_result['success']:
        print(f"❌ Failed to check current revision: {current_result['stderr']}")
        return current_result
    
    print(f"✅ Current local revision: {current_result['stdout'].strip()}")
    
    # Step 2: Check available migrations
    print("\n2. Checking available migrations...")
    history_result = run_alembic_command(['heads'], local_db=True)
    
    if not history_result['success']:
        print(f"❌ Failed to check migration heads: {history_result['stderr']}")
        return history_result
    
    print(f"✅ Available heads: {history_result['stdout'].strip()}")
    
    # Step 3: Run migrations
    print("\n3. Running migrations on local database...")
    upgrade_result = run_alembic_command(['upgrade', 'head'], local_db=True)
    
    if not upgrade_result['success']:
        print(f"❌ Migration failed: {upgrade_result['stderr']}")
        return upgrade_result
    
    print("✅ Local migration successful!")
    print(upgrade_result['stdout'])
    
    return {
        "success": True,
        "local_test_passed": True,
        "message": "Local migration testing completed successfully",
        "details": {
            "current": current_result,
            "heads": history_result,
            "upgrade": upgrade_result
        }
    }

def run_production_migration() -> Dict[str, Any]:
    """
    Run migrations on production database (only after local testing)
    
    Returns:
        Dict with migration results
    """
    print("🚀 RUNNING PRODUCTION MIGRATIONS")
    print("=" * 50)
    
    # Run migrations on production
    result = run_alembic_command(['upgrade', 'head'], local_db=False)
    
    if result['success']:
        print("✅ Production migration successful!")
        print(result['stdout'])
    else:
        print(f"❌ Production migration failed: {result['stderr']}")
    
    return result

if __name__ == "__main__":
    """
    Command-line interface for testing migrations locally
    
    Usage:
        python alembic_runner.py test    # Test migrations locally
        python alembic_runner.py prod    # Run production migrations
        python alembic_runner.py current # Check current revision
    """
    if len(sys.argv) < 2:
        print("Usage: python alembic_runner.py [test|prod|current]")
        sys.exit(1)
    
    command = sys.argv[1].lower()
    
    if command == "test":
        result = test_migration_locally()
        sys.exit(0 if result['success'] else 1)
    elif command == "prod":
        result = run_production_migration()
        sys.exit(0 if result['success'] else 1)
    elif command == "current":
        result = run_alembic_command(['current'], local_db=False)
        print(result['stdout'])
        sys.exit(0 if result['success'] else 1)
    else:
        print("Unknown command. Use: test, prod, or current")
        sys.exit(1) 