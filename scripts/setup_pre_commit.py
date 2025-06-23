#!/usr/bin/env python3
"""
Setup Pre-commit Hooks for Migration Testing
Installs and configures pre-commit hooks for the project
"""

import subprocess
import sys
import os
from pathlib import Path

def check_pre_commit_installed():
    """Check if pre-commit is installed"""
    try:
        result = subprocess.run(
            [sys.executable, "-c", "import pre_commit"],
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='ignore'
        )
        return result.returncode == 0
    except Exception:
        return False

def install_pre_commit():
    """Install pre-commit if not already installed"""
    print("📦 Installing pre-commit...")
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "pre-commit"],
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='ignore'
        )
        
        if result.returncode == 0:
            print("✅ pre-commit installed successfully")
            return True
        else:
            print(f"❌ Failed to install pre-commit: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ Error installing pre-commit: {e}")
        return False

def install_hooks():
    """Install the pre-commit hooks"""
    print("🔗 Installing pre-commit hooks...")
    try:
        result = subprocess.run(
            ["pre-commit", "install"],
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='ignore'
        )
        
        if result.returncode == 0:
            print("✅ Pre-commit hooks installed successfully")
            return True
        else:
            print(f"❌ Failed to install hooks: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ Error installing hooks: {e}")
        return False

def test_hooks():
    """Test the pre-commit hooks on all files"""
    print("🧪 Testing pre-commit hooks...")
    try:
        result = subprocess.run(
            ["pre-commit", "run", "--all-files"],
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='ignore'
        )
        
        print("📋 Pre-commit test output:")
        print(result.stdout)
        if result.stderr:
            print("⚠️  Warnings/Errors:")
            print(result.stderr)
        
        if result.returncode == 0:
            print("✅ All hooks passed!")
        else:
            print("⚠️  Some hooks failed or made changes")
            print("💡 This is normal on first run - files may have been reformatted")
        
        return True
    except Exception as e:
        print(f"❌ Error testing hooks: {e}")
        return False

def verify_migration_requirements():
    """Verify migration testing requirements are met"""
    print("🔍 Verifying migration test requirements...")
    
    req_script = Path("scripts/check_migration_requirements.py")
    if not req_script.exists():
        print("❌ Missing migration requirements check script")
        return False
    
    try:
        result = subprocess.run(
            [sys.executable, str(req_script)],
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='ignore'
        )
        
        print(result.stdout)
        if result.stderr:
            print(result.stderr)
        
        return result.returncode == 0
    except Exception as e:
        print(f"❌ Error checking migration requirements: {e}")
        return False

def main():
    print("🚀 Setting up Pre-commit Hooks for Migration Testing")
    print("=" * 60)
    
    # Check if we're in the right directory
    if not Path(".pre-commit-config.yaml").exists():
        print("❌ No .pre-commit-config.yaml found in current directory")
        print("💡 Please run this script from the project root")
        sys.exit(1)
    
    # Step 1: Install pre-commit if needed
    if not check_pre_commit_installed():
        if not install_pre_commit():
            sys.exit(1)
    else:
        print("✅ pre-commit is already installed")
    
    # Step 2: Verify migration requirements
    if not verify_migration_requirements():
        print("❌ Migration requirements check failed")
        print("💡 Please ensure all required packages are installed")
        sys.exit(1)
    
    # Step 3: Install hooks
    if not install_hooks():
        sys.exit(1)
    
    # Step 4: Test hooks
    test_hooks()
    
    print("\n🎉 Pre-commit hook setup complete!")
    print("\n📋 What happens now:")
    print("• Every commit will automatically check model/migration changes")
    print("• Local migration tests will run before commits are allowed")
    print("• Code formatting (black, flake8) will be enforced")
    print("• Failed migration tests will block commits")
    
    print("\n💡 Useful commands:")
    print("• Run hooks manually: pre-commit run --all-files")
    print("• Skip hooks for urgent commits: git commit --no-verify")
    print("• Update hooks: pre-commit autoupdate")
    print("• Test migration manually: python scripts/test_migrations_hook.py <file>")

if __name__ == "__main__":
    main() 