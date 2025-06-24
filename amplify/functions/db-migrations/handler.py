"""
Database Migration Lambda Handler for Arctan Wines CRM
Provides REST API endpoints for running Alembic migrations
"""
import json
import subprocess
import os
import sys
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum

# Add current directory to Python path for imports
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

app = FastAPI(
    title="Arctan Wines CRM - Database Migrations",
    description="REST API for managing database schema migrations",
    version="1.0.0",
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def run_alembic_command(command_args: list) -> dict:
    """Run an Alembic command and return the result"""
    try:
        # Change to the function directory where alembic.ini is located
        os.chdir(current_dir)

        # Run the Alembic command using python -m alembic
        result = subprocess.run(
            [sys.executable, "-m", "alembic"] + command_args,
            capture_output=True,
            text=True,
            timeout=300,  # 5 minute timeout
        )

        return {
            "success": result.returncode == 0,
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "command": " ".join([sys.executable, "-m", "alembic"] + command_args),
        }
    except Exception as e:
        return {
            "success": False,
            "returncode": -1,
            "stdout": "",
            "stderr": str(e),
            "command": " ".join([sys.executable, "-m", "alembic"] + command_args),
        }


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "service": "arctan-wines-db-migrations",
        "status": "healthy",
        "message": "Database Migration Service is running",
    }


@app.post("/migrate/upgrade")
async def upgrade_database():
    """Run all pending migrations (alembic upgrade head)"""
    result = run_alembic_command(["upgrade", "head"])

    if result["success"]:
        return {
            "status": "success",
            "message": "Database upgraded successfully",
            "output": result["stdout"],
            "command": result["command"],
        }
    else:
        raise HTTPException(
            status_code=500,
            detail={
                "message": "Migration failed",
                "error": result["stderr"],
                "output": result["stdout"],
                "command": result["command"],
            },
        )


@app.get("/migrate/current")
async def current_revision():
    """Get current database revision"""
    result = run_alembic_command(["current"])

    if result["success"]:
        return {
            "status": "success",
            "current_revision": result["stdout"].strip(),
            "output": result["stdout"],
        }
    else:
        raise HTTPException(
            status_code=500,
            detail={
                "message": "Failed to get current revision",
                "error": result["stderr"],
            },
        )


@app.get("/migrate/history")
async def migration_history():
    """Get migration history"""
    result = run_alembic_command(["history", "--verbose"])

    if result["success"]:
        return {
            "status": "success",
            "history": result["stdout"],
            "command": result["command"],
        }
    else:
        raise HTTPException(
            status_code=500,
            detail={
                "message": "Failed to get migration history",
                "error": result["stderr"],
            },
        )


# Create the Lambda handler
handler = Mangum(app)
