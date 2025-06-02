#!/usr/bin/env python3
"""
Fix Lambda dependencies by installing them with correct platform
Run this in the amplify/functions/api-main/ directory
"""

import subprocess
import sys
import os

def fix_dependencies():
    """Install dependencies with correct platform for Lambda"""
    
    # Change to the function directory
    function_dir = "amplify/functions/api-main"
    if os.path.exists(function_dir):
        os.chdir(function_dir)
    
    print("Installing dependencies for Lambda (Linux x86_64)...")
    
    # Remove existing dependencies
    subprocess.run([
        "rm", "-rf", 
        "pydantic*", "fastapi*", "starlette*", 
        "typing_extensions*", "annotated_types*"
    ], capture_output=True)
    
    # Install with correct platform
    cmd = [
        sys.executable, "-m", "pip", "install",
        "--platform", "linux_x86_64",
        "--target", ".",
        "--implementation", "cp", 
        "--python-version", "3.12",
        "--only-binary=:all:",
        "--upgrade",
        "--force-reinstall",
        "-r", "requirements.txt"
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode == 0:
        print("✅ Dependencies installed successfully!")
        print("Now deploy with: npx amplify deploy")
    else:
        print("❌ Error installing dependencies:")
        print(result.stderr)

if __name__ == "__main__":
    fix_dependencies() 