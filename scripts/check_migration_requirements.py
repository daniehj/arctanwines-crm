#!/usr/bin/env python3
"""
Check Migration Requirements
Ensures all required packages are installed for running migration tests locally
"""
import subprocess
import sys
from pathlib import Path

REQUIRED_PACKAGES = [
    "sqlalchemy",
    "alembic", 
    "psycopg2-binary",  # imports as psycopg2
    "pg8000",
]

# Mapping of package names to import names
PACKAGE_IMPORT_MAP = {
    "psycopg2-binary": "psycopg2",
    "pg8000": "pg8000",
    "sqlalchemy": "sqlalchemy",
    "alembic": "alembic"
}

def check_package_installed(package_name):
    """Check if a package is installed"""
    import_name = PACKAGE_IMPORT_MAP.get(package_name, package_name.replace('-', '_'))
    
    try:
        result = subprocess.run(
            [sys.executable, "-c", f"import {import_name}"],
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='ignore'
        )
        return result.returncode == 0
    except Exception:
        return False

def check_requirements_file():
    """Check if requirements file exists in db-migrations"""
    req_file = Path("amplify/functions/db-migrations/requirements.txt")
    return req_file.exists()

def install_requirements():
    """Install requirements from db-migrations requirements.txt"""
    req_file = Path("amplify/functions/db-migrations/requirements.txt")
    
    if not req_file.exists():
        print("❌ Missing requirements.txt in amplify/functions/db-migrations/")
        return False
    
    print("📦 Installing migration testing requirements...")
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", str(req_file)],
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='ignore'
        )
        
        if result.returncode == 0:
            print("✅ Requirements installed successfully")
            return True
        else:
            print(f"❌ Failed to install requirements: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ Error installing requirements: {e}")
        return False

def main():
    print("🔍 Checking migration test requirements...")
    
    missing_packages = []
    
    for package in REQUIRED_PACKAGES:
        if not check_package_installed(package):
            missing_packages.append(package)
    
    if missing_packages:
        print(f"⚠️  Missing packages: {', '.join(missing_packages)}")
        
        if check_requirements_file():
            print("🔧 Attempting to install missing packages...")
            if install_requirements():
                # Re-check packages
                still_missing = []
                for package in missing_packages:
                    if not check_package_installed(package):
                        still_missing.append(package)
                
                if still_missing:
                    print(f"❌ Still missing after install: {', '.join(still_missing)}")
                    print("💡 Try running: pip install -r amplify/functions/db-migrations/requirements.txt")
                    
                    # Try individual package installation
                    print("🔧 Attempting individual package installation...")
                    for package in still_missing:
                        try:
                            result = subprocess.run(
                                [sys.executable, "-m", "pip", "install", package],
                                capture_output=True,
                                text=True,
                                encoding='utf-8',
                                errors='ignore'
                            )
                            if result.returncode == 0:
                                print(f"✅ Successfully installed {package}")
                            else:
                                print(f"❌ Failed to install {package}")
                        except Exception as e:
                            print(f"❌ Error installing {package}: {e}")
                    
                    # Final check
                    final_missing = []
                    for package in still_missing:
                        if not check_package_installed(package):
                            final_missing.append(package)
                    
                    if final_missing:
                        print(f"❌ Final check - still missing: {', '.join(final_missing)}")
                        sys.exit(1)
                    else:
                        print("✅ All packages now installed!")
                else:
                    print("✅ All packages now installed!")
            else:
                sys.exit(1)
        else:
            print("❌ No requirements.txt found for automatic installation")
            print("💡 Please install manually:")
            for package in missing_packages:
                print(f"   pip install {package}")
            sys.exit(1)
    else:
        print("✅ All required packages are installed")
    
    print("🎉 Migration test environment is ready!")
    return True

if __name__ == "__main__":
    main() 