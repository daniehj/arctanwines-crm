import json
import os
import time
import socket
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum
import boto3
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import uuid
import subprocess
from pathlib import Path
import pg8000
from datetime import datetime, date
from decimal import Decimal

# Initialize FastAPI app
app = FastAPI(title="Arctan Wines CRM API")

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# AWS clients
ssm_client = boto3.client("ssm")
secrets_client = boto3.client("secretsmanager")

# Database globals
engine = None
SessionLocal = None


def get_environment():
    """Determine environment"""
    amplify_env = os.environ.get("AMPLIFY_ENV", "")
    aws_branch = os.environ.get("AWS_BRANCH", "")
    function_name = os.environ.get("AWS_LAMBDA_FUNCTION_NAME", "")

    # Debug info
    env_info = {
        "amplify_env": amplify_env,
        "aws_branch": aws_branch,
        "function_name": function_name,
    }

    if (
        "sandbox" in amplify_env.lower()
        or aws_branch in ["dev", "test", "sandbox"]
        or "sandbox" in function_name.lower()
        or "test" in function_name.lower()
    ):
        return "test", env_info
    return "prod", env_info


def get_ssm_parameter(parameter_name):
    """Get SSM parameter with fallback logic"""
    env, env_info = get_environment()

    # First try environment variables
    env_var_map = {
        "database/host": "DATABASE_HOST",
        "database/port": "DATABASE_PORT",
        "database/name": "DATABASE_NAME",
        "database/username": "DATABASE_USERNAME",
        "database/password": "DATABASE_PASSWORD",
    }

    if parameter_name in env_var_map:
        env_value = os.environ.get(env_var_map[parameter_name])
        if env_value:
            return env_value

    # Try SSM with multiple path variations
    try:
        paths_to_try = [
            f"/amplify/arctanwines/{env}/{parameter_name}",
            f"/amplify/arctanwines/{parameter_name}",
            f"/amplify/arctan-wines/{env}/{parameter_name}",
            f"/amplify/arctan-wines/{parameter_name}",
            f"/amplify/{env}/{parameter_name}",
            f"/amplify/{parameter_name}",
        ]

        for path in paths_to_try:
            try:
                response = ssm_client.get_parameter(Name=path, WithDecryption=True)
                return response["Parameter"]["Value"]
            except:
                continue

        raise Exception(f"Parameter {parameter_name} not found in any SSM path")

    except Exception as e:
        # Final fallback to environment variable
        env_var = parameter_name.upper().replace("-", "_").replace("/", "_")
        env_value = os.environ.get(env_var)
        if env_value:
            return env_value

        raise Exception(f"Could not get parameter {parameter_name}: {str(e)}")


def init_database():
    """Initialize database connection"""
    global engine, SessionLocal

    if engine is None:
        try:
            print(f"[{time.time()}] Initializing database...")

            # Get database configuration
            db_host = get_ssm_parameter("database/host")
            db_port = get_ssm_parameter("database/port") or "5432"
            db_name = get_ssm_parameter("database/name")
            db_user = get_ssm_parameter("database/username")
            db_password = get_ssm_parameter("database/password")

            if not all([db_host, db_name, db_user, db_password]):
                missing = [
                    k
                    for k, v in {
                        "host": db_host,
                        "name": db_name,
                        "username": db_user,
                        "password": db_password,
                    }.items()
                    if not v
                ]
                raise Exception(f"Missing database config: {', '.join(missing)}")

            print(f"[{time.time()}] Connecting to: {db_host}:{db_port}/{db_name}")

            database_url = f"postgresql+pg8000://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"

            engine = create_engine(
                database_url,
                echo=False,
                pool_timeout=10,
                pool_recycle=300,
                pool_pre_ping=True,
                connect_args={"timeout": 10},
            )

            SessionLocal = sessionmaker(bind=engine)
            print(f"[{time.time()}] Database initialization completed")

        except Exception as e:
            print(f"[{time.time()}] Database init failed: {str(e)}")
            raise Exception(f"Database initialization failed: {str(e)}")


def get_db_session():
    """Get database session"""
    if SessionLocal is None:
        init_database()
    return SessionLocal()


def get_database_config():
    """Get database configuration for raw connections"""
    return {
        "host": get_ssm_parameter("database/host"),
        "port": get_ssm_parameter("database/port") or "5432",
        "name": get_ssm_parameter("database/name"),
        "username": get_ssm_parameter("database/username"),
        "password": get_ssm_parameter("database/password"),
    }


@app.get("/")
def root():
    """Root endpoint"""
    return {
        "message": "Arctan Wines CRM API",
        "status": "online",
        "timestamp": time.time(),
    }


@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "environment": get_environment(),
        "version": "1.0.0",
    }


@app.get("/config-debug")
def config_debug():
    """Debug configuration and environment"""
    env, env_info = get_environment()

    return {
        "environment": env,
        "env_info": env_info,
        "aws_region": os.environ.get("AWS_REGION", "not-set"),
        "function_name": os.environ.get("AWS_LAMBDA_FUNCTION_NAME", "not-set"),
        "timestamp": time.time(),
    }


@app.get("/vpc-info")
def vpc_info():
    """Get VPC and network information"""
    try:
        # Try to get metadata about the Lambda environment
        import urllib.request
        import urllib.error

        # This will work if Lambda has internet access
        try:
            # Get AWS metadata
            req = urllib.request.Request(
                "http://169.254.169.254/latest/meta-data/instance-id"
            )
            req.add_header("User-Agent", "lambda-vpc-info")
            with urllib.request.urlopen(req, timeout=5) as response:
                instance_id = response.read().decode()
        except:
            instance_id = "not-available-in-lambda"

        # Get network interface info if available
        try:
            import netifaces

            interfaces = netifaces.interfaces()
            interface_info = {}
            for iface in interfaces:
                addrs = netifaces.ifaddresses(iface)
                interface_info[iface] = addrs
        except ImportError:
            interface_info = "netifaces-not-available"
        except Exception as e:
            interface_info = f"error: {str(e)}"

        return {
            "status": "success",
            "instance_id": instance_id,
            "interfaces": interface_info,
            "environment_vars": {
                "VPC_ID": os.environ.get("VPC_ID", "not-set"),
                "SUBNET_IDS": os.environ.get("SUBNET_IDS", "not-set"),
                "SECURITY_GROUP_IDS": os.environ.get("SECURITY_GROUP_IDS", "not-set"),
                "AWS_LAMBDA_FUNCTION_NAME": os.environ.get(
                    "AWS_LAMBDA_FUNCTION_NAME", "not-set"
                ),
                "AWS_REGION": os.environ.get("AWS_REGION", "not-set"),
            },
            "timestamp": time.time(),
        }
    except Exception as e:
        return {"status": "error", "error": str(e), "timestamp": time.time()}


@app.get("/dns-test")
def dns_test():
    """Test DNS resolution capabilities"""
    import socket

    test_hosts = [
        "google.com",
        "amazonaws.com",
        "rds.amazonaws.com",
        "secretsmanager.eu-west-1.amazonaws.com",
        "ssm.eu-west-1.amazonaws.com",
    ]

    results = {}

    for host in test_hosts:
        try:
            start_time = time.time()
            ip = socket.gethostbyname(host)
            duration = time.time() - start_time
            results[host] = {
                "status": "success",
                "ip": ip,
                "duration_ms": round(duration * 1000, 2),
            }
        except Exception as e:
            results[host] = {"status": "error", "error": str(e)}

    return {"status": "success", "dns_tests": results, "timestamp": time.time()}


@app.get("/network-test")
def network_test():
    """Test network connectivity to AWS services (avoiding external timeouts)"""
    import socket

    # Test AWS services only (these should be reachable via VPC endpoints)
    test_hosts = [
        ("ssm.eu-west-1.amazonaws.com", 443),
        ("secretsmanager.eu-west-1.amazonaws.com", 443),
        ("lambda.eu-west-1.amazonaws.com", 443),
        ("dynamodb.eu-west-1.amazonaws.com", 443),
    ]

    results = {}

    for host, port in test_hosts:
        try:
            start_time = time.time()
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)  # Short timeout to avoid API Gateway timeout
            result = sock.connect_ex((host, port))
            duration = time.time() - start_time
            sock.close()

            results[f"{host}:{port}"] = {
                "status": "success" if result == 0 else "failed",
                "result_code": result,
                "duration_ms": round(duration * 1000, 2),
            }
        except Exception as e:
            results[f"{host}:{port}"] = {"status": "error", "error": str(e)}

    return {
        "status": "success",
        "network_tests": results,
        "note": "Testing AWS service connectivity only (external URLs skipped to avoid VPC timeouts)",
        "timestamp": time.time(),
    }


@app.get("/network-simple-test")
def network_simple_test():
    """Simple network connectivity test"""
    try:
        # Test basic socket connectivity
        import socket

        # Test AWS services
        aws_tests = {}

        # Test SSM endpoint
        try:
            start_time = time.time()
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            result = sock.connect_ex(("ssm.eu-west-1.amazonaws.com", 443))
            duration = time.time() - start_time
            sock.close()

            aws_tests["ssm"] = {
                "status": "success" if result == 0 else "failed",
                "result_code": result,
                "duration_ms": round(duration * 1000, 2),
            }
        except Exception as e:
            aws_tests["ssm"] = {"status": "error", "error": str(e)}

        # Test Secrets Manager endpoint
        try:
            start_time = time.time()
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            result = sock.connect_ex(("secretsmanager.eu-west-1.amazonaws.com", 443))
            duration = time.time() - start_time
            sock.close()

            aws_tests["secrets_manager"] = {
                "status": "success" if result == 0 else "failed",
                "result_code": result,
                "duration_ms": round(duration * 1000, 2),
            }
        except Exception as e:
            aws_tests["secrets_manager"] = {"status": "error", "error": str(e)}

        # Test basic HTTP connectivity
        try:
            start_time = time.time()
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            result = sock.connect_ex(("google.com", 80))
            duration = time.time() - start_time
            sock.close()

            aws_tests["internet"] = {
                "status": "success" if result == 0 else "failed",
                "result_code": result,
                "duration_ms": round(duration * 1000, 2),
            }
        except Exception as e:
            aws_tests["internet"] = {"status": "error", "error": str(e)}

        return {
            "status": "success",
            "simple_network_tests": aws_tests,
            "timestamp": time.time(),
        }

    except Exception as e:
        return {"status": "error", "error": str(e), "timestamp": time.time()}


@app.get("/api/v1/test")
def test_endpoint():
    """Test endpoint for API functionality"""
    return {
        "message": "API is working correctly",
        "timestamp": time.time(),
        "version": "1.0.0",
    }


@app.get("/env-debug")
def env_debug():
    """Debug environment variables (filtered for security)"""
    env_vars = {}

    # Safe environment variables to display
    safe_vars = [
        "AWS_REGION",
        "AWS_LAMBDA_FUNCTION_NAME",
        "AWS_LAMBDA_FUNCTION_VERSION",
        "AWS_LAMBDA_LOG_GROUP_NAME",
        "AWS_LAMBDA_LOG_STREAM_NAME",
        "AWS_EXECUTION_ENV",
        "AWS_LAMBDA_RUNTIME_API",
        "AWS_LAMBDA_INITIALIZATION_TYPE",
        "AMPLIFY_ENV",
        "AWS_BRANCH",
        "LAMBDA_TASK_ROOT",
        "LAMBDA_RUNTIME_DIR",
        "PATH",
        "PWD",
        "LANG",
        "TZ",
    ]

    for var in safe_vars:
        env_vars[var] = os.environ.get(var, "not-set")

    # Count total environment variables
    total_env_vars = len(os.environ)

    return {
        "status": "success",
        "safe_environment_variables": env_vars,
        "total_env_var_count": total_env_vars,
        "timestamp": time.time(),
    }


@app.get("/status")
def status():
    """Simple status endpoint with no external dependencies"""
    return {
        "status": "online",
        "service": "arctanwines-crm-api",
        "timestamp": time.time(),
        "environment": get_environment(),
        "lambda_function": os.environ.get("AWS_LAMBDA_FUNCTION_NAME", "unknown"),
        "aws_region": os.environ.get("AWS_REGION", "unknown"),
    }


@app.get("/db/test")
def test_database():
    """Test database connection"""
    try:
        db = get_db_session()
        result = db.execute(text("SELECT 1 as test")).scalar()
        db.close()

        return {"status": "success", "database_test": result, "timestamp": time.time()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database test failed: {str(e)}")


@app.get("/db/wine-batches")
async def list_wine_batches():
    """List all wine batches"""
    try:
        # Use same connection logic as before
        db_config = get_database_config()

        conn_params = {
            "host": db_config["host"],
            "port": int(db_config["port"]),
            "database": db_config["name"],
            "user": db_config["username"],
            "password": db_config["password"],
        }

        conn = pg8000.connect(**conn_params)
        cursor = conn.cursor()

        # Query with enhanced fields
        cursor.execute(
            """
            SELECT id, batch_number, status, wine_name, producer, total_bottles, 
                   import_date, eur_exchange_rate, wine_cost_eur_cents,
                   transport_cost_ore, customs_fee_ore, freight_forwarding_ore,
                   supplier_id, fiken_sync_status, created_at, updated_at
            FROM wine_batches 
            ORDER BY created_at DESC
        """
        )

        columns = [
            "id",
            "batch_number",
            "status",
            "wine_name",
            "producer",
            "total_bottles",
            "import_date",
            "eur_exchange_rate",
            "wine_cost_eur_cents",
            "transport_cost_ore",
            "customs_fee_ore",
            "freight_forwarding_ore",
            "supplier_id",
            "fiken_sync_status",
            "created_at",
            "updated_at",
        ]

        batches = []
        for row in cursor.fetchall():
            batch = {}
            for i, col in enumerate(columns):
                value = row[i]
                if isinstance(value, date):
                    batch[col] = value.isoformat()
                elif isinstance(value, datetime):
                    batch[col] = value.isoformat()
                elif isinstance(value, Decimal):
                    batch[col] = float(value)
                else:
                    batch[col] = value
            batches.append(batch)

        cursor.close()
        conn.close()

        return {"wine_batches": batches}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@app.post("/db/wine-batches")
async def create_wine_batch(request: Request):
    """Create a new wine batch using JSON body"""
    try:
        # Parse JSON body manually instead of using Pydantic
        body = await request.json()

        # Validate required fields
        required_fields = ["batch_number", "wine_name", "producer", "total_bottles"]
        for field in required_fields:
            if field not in body or not body[field]:
                raise HTTPException(
                    status_code=400, detail=f"Missing required field: {field}"
                )

        db = get_db_session()

        # Check if batch number already exists
        existing = db.execute(
            text("SELECT id FROM wine_batches WHERE batch_number = :batch_number"),
            {"batch_number": body["batch_number"]},
        ).fetchone()

        if existing:
            db.close()
            raise HTTPException(
                status_code=400,
                detail=f"Batch number {body['batch_number']} already exists",
            )

        # Insert new batch using raw SQL
        batch_id = str(uuid.uuid4())

        db.execute(
            text(
                """
            INSERT INTO wine_batches 
            (id, batch_number, wine_name, producer, total_bottles, status, 
             total_cost_nok_ore, target_price_nok_ore, created_at, updated_at)
            VALUES (:id, :batch_number, :wine_name, :producer, :total_bottles, :status,
                    :total_cost_nok_ore, :target_price_nok_ore, NOW(), NOW())
        """
            ),
            {
                "id": batch_id,
                "batch_number": body["batch_number"],
                "wine_name": body["wine_name"],
                "producer": body["producer"],
                "total_bottles": int(body["total_bottles"]),
                "status": "ORDERED",
                "total_cost_nok_ore": int(body.get("total_cost_nok_ore", 0)),
                "target_price_nok_ore": int(body.get("target_price_nok_ore", 0)),
            },
        )

        db.commit()

        # Fetch the created batch
        created = db.execute(
            text(
                """
            SELECT id, batch_number, wine_name, producer, total_bottles, 
                   status, total_cost_nok_ore, target_price_nok_ore, created_at
            FROM wine_batches WHERE id = :id
        """
            ),
            {"id": batch_id},
        ).fetchone()

        db.close()

        return {
            "status": "success",
            "message": "Wine batch created successfully",
            "batch": {
                "id": str(created.id),
                "batch_number": created.batch_number,
                "wine_name": created.wine_name,
                "producer": created.producer,
                "total_bottles": created.total_bottles,
                "status": created.status,
                "total_cost_nok_ore": created.total_cost_nok_ore,
                "target_price_nok_ore": created.target_price_nok_ore,
                "created_at": created.created_at.isoformat()
                if created.created_at
                else None,
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to create wine batch: {str(e)}"
        )


@app.post("/db/migrate")
def run_migrations():
    """Run database migrations"""
    try:
        db = get_db_session()

        tables_created = []

        suppliers_exists = db.execute(
            text(
                """
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'suppliers'
            );
        """
            )
        ).scalar()

        if not suppliers_exists:
            print("Creating suppliers table...")

            db.execute(
                text(
                    """
                CREATE TABLE suppliers (
                    id VARCHAR(36) PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    country VARCHAR(100) NOT NULL,
                    contact_person VARCHAR(255),
                    email VARCHAR(255),
                    phone VARCHAR(50),
                    payment_terms INTEGER DEFAULT 30,
                    currency VARCHAR(3) DEFAULT 'EUR',
                    tax_id VARCHAR(50),
                    active BOOLEAN NOT NULL DEFAULT true,
                    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
                );
            """
                )
            )

            tables_created.append("suppliers")
            print("suppliers table created successfully")

        # Check and create wines table
        wines_exists = db.execute(
            text(
                """
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'wines'
            );
        """
            )
        ).scalar()

        if not wines_exists:
            print("Creating wines table...")

            db.execute(
                text(
                    """
                CREATE TABLE wines (
                    id VARCHAR(36) PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    producer VARCHAR(255) NOT NULL,
                    region VARCHAR(255),
                    country VARCHAR(100) NOT NULL,
                    vintage INTEGER,
                    alcohol_content DECIMAL(4,2),
                    bottle_size_ml INTEGER DEFAULT 750,
                    product_category VARCHAR(50),
                    tasting_notes TEXT,
                    serving_temperature VARCHAR(50),
                    food_pairing TEXT,
                    organic BOOLEAN DEFAULT false,
                    biodynamic BOOLEAN DEFAULT false,
                    fiken_product_id INTEGER,
                    active BOOLEAN NOT NULL DEFAULT true,
                    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
                );
            """
                )
            )

            tables_created.append("wines")
            print("wines table created successfully")

        # Check and create wine_inventory table
        wine_inventory_exists = db.execute(
            text(
                """
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'wine_inventory'
            );
        """
            )
        ).scalar()

        if not wine_inventory_exists:
            print("Creating wine_inventory table with Phase 3 columns...")

            db.execute(
                text(
                    """
                CREATE TABLE wine_inventory (
                    id VARCHAR(36) PRIMARY KEY,
                    wine_id VARCHAR(36) REFERENCES wines(id),
                    batch_id VARCHAR(36) REFERENCES wine_batches(id),
                    quantity_available INTEGER NOT NULL DEFAULT 0,
                    quantity_reserved INTEGER DEFAULT 0,
                    quantity_sold INTEGER DEFAULT 0,
                    cost_per_bottle_ore INTEGER NOT NULL,
                    selling_price_ore INTEGER NOT NULL,
                    markup_percentage INTEGER DEFAULT 0,
                    margin_per_bottle_ore INTEGER DEFAULT 0,
                    minimum_stock_level INTEGER DEFAULT 0,
                    location VARCHAR(100),
                    best_before_date TIMESTAMP WITH TIME ZONE,
                    low_stock_alert BOOLEAN DEFAULT false,
                    active BOOLEAN NOT NULL DEFAULT true,
                    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
                );
            """
                )
            )

            tables_created.append("wine_inventory")
            print("wine_inventory table created successfully")

        # Check and create wine_batch_costs table
        wine_batch_costs_exists = db.execute(
            text(
                """
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'wine_batch_costs'
            );
        """
            )
        ).scalar()

        if not wine_batch_costs_exists:
            print("Creating wine_batch_costs table...")

            db.execute(
                text(
                    """
                CREATE TABLE wine_batch_costs (
                    id VARCHAR(36) PRIMARY KEY,
                    batch_id VARCHAR(36) REFERENCES wine_batches(id),
                    cost_type VARCHAR(50) NOT NULL,
                    amount_ore INTEGER NOT NULL,
                    currency VARCHAR(3) NOT NULL,
                    fiken_account_code VARCHAR(20),
                    payment_date DATE,
                    allocation_method VARCHAR(30) DEFAULT 'per_bottle',
                    invoice_reference VARCHAR(100),
                    active BOOLEAN NOT NULL DEFAULT true,
                    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
                );
            """
                )
            )

            tables_created.append("wine_batch_costs")
            print("wine_batch_costs table created successfully")

        # Check and update wine_batches table (add missing columns if table exists)
        wine_batches_exists = db.execute(
            text(
                """
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'wine_batches'
            );
        """
            )
        ).scalar()

        if not wine_batches_exists:
            print("Creating wine_batches table...")

            # Create the table manually (based on our migration)
            db.execute(
                text(
                    """
                CREATE TABLE wine_batches (
                    id VARCHAR(36) PRIMARY KEY,
                    batch_number VARCHAR(50) NOT NULL UNIQUE,
                    wine_name VARCHAR(200) NOT NULL,
                    producer VARCHAR(200) NOT NULL,
                    import_date DATE,
                    supplier_id VARCHAR(36) REFERENCES suppliers(id),
                    total_bottles INTEGER NOT NULL,
                    eur_exchange_rate DECIMAL(10,6),
                    wine_cost_eur_cents INTEGER,
                    transport_cost_ore INTEGER DEFAULT 0,
                    customs_fee_ore INTEGER DEFAULT 0,
                    freight_forwarding_ore INTEGER DEFAULT 0,
                    status VARCHAR(20) NOT NULL DEFAULT 'ORDERED',
                    fiken_sync_status VARCHAR(20) DEFAULT 'pending',
                    total_cost_nok_ore INTEGER NOT NULL DEFAULT 0,
                    target_price_nok_ore INTEGER,
                    active BOOLEAN NOT NULL DEFAULT true,
                    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
                );
            """
                )
            )

            # Create indexes
            db.execute(
                text(
                    """
                CREATE INDEX idx_wine_batch_status ON wine_batches(status);
                CREATE UNIQUE INDEX ix_wine_batches_batch_number ON wine_batches(batch_number);
                CREATE INDEX ix_wine_batches_wine_name ON wine_batches(wine_name);
            """
                )
            )

            tables_created.append("wine_batches")
            print("wine_batches table created successfully")
        else:
            print("wine_batches table exists, checking for missing columns...")

            # Check and add missing columns one by one
            missing_columns = []

            # Helper function to check if column exists
            def column_exists(table_name, column_name):
                return db.execute(
                    text(
                        f"""
                    SELECT EXISTS (
                        SELECT FROM information_schema.columns 
                        WHERE table_schema = 'public' 
                        AND table_name = '{table_name}' 
                        AND column_name = '{column_name}'
                    );
                """
                    )
                ).scalar()

            # List of columns that should exist
            expected_columns = [
                ("import_date", "DATE"),
                ("supplier_id", "VARCHAR(36)"),
                ("eur_exchange_rate", "DECIMAL(10,6)"),
                ("wine_cost_eur_cents", "INTEGER"),
                ("transport_cost_ore", "INTEGER DEFAULT 0"),
                ("customs_fee_ore", "INTEGER DEFAULT 0"),
                ("freight_forwarding_ore", "INTEGER DEFAULT 0"),
                ("fiken_sync_status", "VARCHAR(20) DEFAULT 'pending'"),
                ("active", "BOOLEAN NOT NULL DEFAULT true"),
            ]

            for column_name, column_type in expected_columns:
                if not column_exists("wine_batches", column_name):
                    print(f"Adding missing column: {column_name}")
                    db.execute(
                        text(
                            f"""
                        ALTER TABLE wine_batches 
                        ADD COLUMN {column_name} {column_type};
                    """
                        )
                    )
                    missing_columns.append(column_name)

            if missing_columns:
                print(
                    f"Added missing columns to wine_batches: {', '.join(missing_columns)}"
                )
                tables_created.append(
                    f"wine_batches (added columns: {', '.join(missing_columns)})"
                )
            else:
                print("wine_batches table is up to date")

            # Add foreign key constraint for supplier_id if it doesn't exist
            try:
                if "supplier_id" in missing_columns:
                    db.execute(
                        text(
                            """
                        ALTER TABLE wine_batches 
                        ADD CONSTRAINT fk_wine_batches_supplier 
                        FOREIGN KEY (supplier_id) REFERENCES suppliers(id);
                    """
                        )
                    )
                    print("Added foreign key constraint for supplier_id")
            except Exception as e:
                print(
                    f"Foreign key constraint may already exist or suppliers table not ready: {e}"
                )

        # Update wine_inventory table with Phase 3 columns
        wine_inventory_table_exists = db.execute(
            text(
                """
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'wine_inventory'
            );
        """
            )
        ).scalar()

        if wine_inventory_table_exists:
            print("Updating wine_inventory table with Phase 3 columns...")

            # Add Phase 3 columns to wine_inventory
            phase3_inventory_columns = {
                "quantity_reserved": "INTEGER DEFAULT 0",
                "quantity_sold": "INTEGER DEFAULT 0",
                "markup_percentage": "INTEGER DEFAULT 0",
                "margin_per_bottle_ore": "INTEGER DEFAULT 0",
                "low_stock_alert": "BOOLEAN DEFAULT false",
            }

            inventory_missing_columns = []
            for col, col_def in phase3_inventory_columns.items():
                if not db.execute(
                    text(
                        f"""
                    SELECT EXISTS (
                        SELECT FROM information_schema.columns 
                        WHERE table_name = 'wine_inventory' 
                        AND column_name = '{col}'
                    );
                """
                    )
                ).scalar():
                    print(f"Adding column {col} to wine_inventory...")
                    db.execute(
                        text(f"ALTER TABLE wine_inventory ADD COLUMN {col} {col_def};")
                    )
                    inventory_missing_columns.append(col)

            if inventory_missing_columns:
                tables_created.append(
                    f"wine_inventory (added Phase 3 columns: {', '.join(inventory_missing_columns)})"
                )

        # Create customers table
        customers_exists = db.execute(
            text(
                """
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'customers'
            );
        """
            )
        ).scalar()

        if not customers_exists:
            print("Creating customers table...")

            db.execute(
                text(
                    """
                CREATE TABLE customers (
                    id VARCHAR(36) PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    customer_type VARCHAR(50) NOT NULL,
                    email VARCHAR(255),
                    phone VARCHAR(50),
                    address_line1 VARCHAR(255),
                    address_line2 VARCHAR(255),
                    postal_code VARCHAR(20),
                    city VARCHAR(100),
                    country VARCHAR(100) DEFAULT 'Norway',
                    organization_number VARCHAR(50),
                    vat_number VARCHAR(50),
                    preferred_delivery_method VARCHAR(50),
                    payment_terms INTEGER DEFAULT 0,
                    credit_limit_nok_ore INTEGER DEFAULT 0,
                    marketing_consent BOOLEAN DEFAULT false,
                    newsletter_subscription BOOLEAN DEFAULT false,
                    preferred_language VARCHAR(10) DEFAULT 'no',
                    notes TEXT,
                    fiken_customer_id VARCHAR(100),
                    active BOOLEAN NOT NULL DEFAULT true,
                    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
                );
            """
                )
            )

            tables_created.append("customers")
            print("customers table created successfully")

        # Create orders table
        orders_exists = db.execute(
            text(
                """
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'orders'
            );
        """
            )
        ).scalar()

        if not orders_exists:
            print("Creating orders table...")

            db.execute(
                text(
                    """
                CREATE TABLE orders (
                    id VARCHAR(36) PRIMARY KEY,
                    order_number VARCHAR(50) UNIQUE NOT NULL,
                    customer_id VARCHAR(36) REFERENCES customers(id) NOT NULL,
                    status VARCHAR(30) DEFAULT 'draft',
                    payment_status VARCHAR(30) DEFAULT 'pending',
                    order_date TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                    requested_delivery_date TIMESTAMP WITH TIME ZONE,
                    confirmed_delivery_date TIMESTAMP WITH TIME ZONE,
                    delivered_date TIMESTAMP WITH TIME ZONE,
                    delivery_method VARCHAR(50) NOT NULL,
                    delivery_address_line1 VARCHAR(255),
                    delivery_address_line2 VARCHAR(255),
                    delivery_postal_code VARCHAR(20),
                    delivery_city VARCHAR(100),
                    delivery_country VARCHAR(100),
                    delivery_notes TEXT,
                    subtotal_ore INTEGER DEFAULT 0 NOT NULL,
                    delivery_fee_ore INTEGER DEFAULT 0 NOT NULL,
                    discount_ore INTEGER DEFAULT 0 NOT NULL,
                    vat_ore INTEGER DEFAULT 0 NOT NULL,
                    total_ore INTEGER DEFAULT 0 NOT NULL,
                    payment_terms INTEGER DEFAULT 0,
                    payment_due_date TIMESTAMP WITH TIME ZONE,
                    customer_notes TEXT,
                    internal_notes TEXT,
                    fiken_order_id VARCHAR(100),
                    fiken_invoice_number VARCHAR(50),
                    active BOOLEAN NOT NULL DEFAULT true,
                    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
                );
            """
                )
            )

            tables_created.append("orders")
            print("orders table created successfully")

        # Create order_items table
        order_items_exists = db.execute(
            text(
                """
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'order_items'
            );
        """
            )
        ).scalar()

        if not order_items_exists:
            print("Creating order_items table...")

            db.execute(
                text(
                    """
                CREATE TABLE order_items (
                    id VARCHAR(36) PRIMARY KEY,
                    order_id VARCHAR(36) REFERENCES orders(id) NOT NULL,
                    wine_batch_id VARCHAR(36) REFERENCES wine_batches(id),
                    wine_id VARCHAR(36) REFERENCES wines(id),
                    quantity INTEGER NOT NULL,
                    unit_price_ore INTEGER NOT NULL,
                    total_price_ore INTEGER NOT NULL,
                    wine_name VARCHAR(255) NOT NULL,
                    producer VARCHAR(255),
                    vintage INTEGER,
                    bottle_size_ml INTEGER DEFAULT 750,
                    discount_percentage INTEGER DEFAULT 0,
                    discount_ore INTEGER DEFAULT 0,
                    notes TEXT,
                    active BOOLEAN NOT NULL DEFAULT true,
                    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
                );
            """
                )
            )

            tables_created.append("order_items")
            print("order_items table created successfully")

        # Create tasting_outcomes table
        tasting_outcomes_exists = db.execute(
            text(
                """
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'tasting_outcomes'
            );
        """
            )
        ).scalar()

        if not tasting_outcomes_exists:
            print("Creating tasting_outcomes table...")

            db.execute(
                text(
                    """
                CREATE TABLE tasting_outcomes (
                    id VARCHAR(36) PRIMARY KEY,
                    tasting_id VARCHAR(36) REFERENCES wine_tastings(id),
                    customer_id VARCHAR(36) REFERENCES customers(id),
                    outcome_type VARCHAR(50) NOT NULL,
                    outcome_value_ore INTEGER DEFAULT 0,
                    outcome_date DATE NOT NULL,
                    notes TEXT,
                    active BOOLEAN NOT NULL DEFAULT true,
                    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
                );
            """
                )
            )

            tables_created.append("tasting_outcomes")
            print("tasting_outcomes table created successfully")

        # Create wine_tastings table
        wine_tastings_exists = db.execute(
            text(
                """
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'wine_tastings'
            );
        """
            )
        ).scalar()

        if not wine_tastings_exists:
            print("Creating wine_tastings table...")

            db.execute(
                text(
                    """
                CREATE TABLE wine_tastings (
                    id VARCHAR(36) PRIMARY KEY,
                    event_name VARCHAR(255) NOT NULL,
                    event_date DATE NOT NULL,
                    event_time TIME,
                    venue_type VARCHAR(50) NOT NULL,
                    venue_name VARCHAR(255),
                    venue_address TEXT,
                    venue_cost_ore INTEGER DEFAULT 0,
                    max_attendees INTEGER,
                    actual_attendees INTEGER DEFAULT 0,
                    event_type VARCHAR(50) NOT NULL,
                    event_status VARCHAR(50) DEFAULT 'planned',
                    target_customer_segment VARCHAR(100),
                    marketing_objective TEXT,
                    total_event_cost_ore INTEGER DEFAULT 0,
                    estimated_revenue_impact_ore INTEGER DEFAULT 0,
                    actual_revenue_impact_ore INTEGER DEFAULT 0,
                    notes TEXT,
                    active BOOLEAN NOT NULL DEFAULT true,
                    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
                );
            """
                )
            )

            tables_created.append("wine_tastings")
            print("wine_tastings table created successfully")

        # Create tasting_attendees table
        tasting_attendees_exists = db.execute(
            text(
                """
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'tasting_attendees'
            );
        """
            )
        ).scalar()

        if not tasting_attendees_exists:
            print("Creating tasting_attendees table...")

            db.execute(
                text(
                    """
                CREATE TABLE tasting_attendees (
                    id VARCHAR(36) PRIMARY KEY,
                    tasting_id VARCHAR(36) NOT NULL REFERENCES wine_tastings(id),
                    customer_id VARCHAR(36) REFERENCES customers(id),
                    attendee_name VARCHAR(255) NOT NULL,
                    attendee_email VARCHAR(255),
                    attendee_phone VARCHAR(50),
                    attendee_type VARCHAR(50) NOT NULL,
                    rsvp_status VARCHAR(50) DEFAULT 'invited',
                    follow_up_required BOOLEAN DEFAULT false,
                    post_event_interest_level INTEGER,
                    potential_order_value_ore INTEGER DEFAULT 0,
                    active BOOLEAN NOT NULL DEFAULT true,
                    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
                );
            """
                )
            )

            tables_created.append("tasting_attendees")
            print("tasting_attendees table created successfully")

        # Create tasting_wines table
        tasting_wines_exists = db.execute(
            text(
                """
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'tasting_wines'
            );
        """
            )
        ).scalar()

        if not tasting_wines_exists:
            print("Creating tasting_wines table...")

            db.execute(
                text(
                    """
                CREATE TABLE tasting_wines (
                    id VARCHAR(36) PRIMARY KEY,
                    tasting_id VARCHAR(36) NOT NULL REFERENCES wine_tastings(id),
                    wine_id VARCHAR(36) REFERENCES wines(id),
                    wine_name VARCHAR(255),
                    wine_producer VARCHAR(255),
                    wine_vintage INTEGER,
                    bottles_used INTEGER NOT NULL DEFAULT 1,
                    wine_source VARCHAR(50) NOT NULL,
                    cost_per_bottle_ore INTEGER NOT NULL,
                    tasting_order INTEGER,
                    tasting_notes TEXT,
                    customer_feedback JSONB,
                    popularity_score DECIMAL(3,2),
                    follow_up_orders INTEGER DEFAULT 0,
                    active BOOLEAN NOT NULL DEFAULT true,
                    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
                );
            """
                )
            )

            tables_created.append("tasting_wines")
            print("tasting_wines table created successfully")
        else:
            print("tasting_wines table exists, checking for missing columns...")

            # Check and add missing columns for tasting_wines
            tasting_wines_missing_columns = []

            # List of columns that should exist in tasting_wines
            expected_tasting_wines_columns = [
                ("wine_id", "VARCHAR(36)"),
                ("wine_name", "VARCHAR(255)"),
                ("wine_producer", "VARCHAR(255)"),
                ("wine_vintage", "INTEGER"),
                ("bottles_used", "INTEGER NOT NULL DEFAULT 1"),
                ("wine_source", "VARCHAR(50) NOT NULL DEFAULT 'inventory'"),
                ("cost_per_bottle_ore", "INTEGER NOT NULL DEFAULT 0"),
                ("tasting_order", "INTEGER"),
                ("tasting_notes", "TEXT"),
                ("customer_feedback", "JSONB"),
                ("popularity_score", "DECIMAL(3,2)"),
                ("follow_up_orders", "INTEGER DEFAULT 0"),
                ("active", "BOOLEAN NOT NULL DEFAULT true"),
                ("created_at", "TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()"),
                ("updated_at", "TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()"),
            ]

            for column_name, column_type in expected_tasting_wines_columns:
                if not column_exists("tasting_wines", column_name):
                    print(f"Adding missing column: {column_name} to tasting_wines")
                    db.execute(
                        text(
                            f"""
                        ALTER TABLE tasting_wines 
                        ADD COLUMN {column_name} {column_type};
                    """
                        )
                    )
                    tasting_wines_missing_columns.append(column_name)

            if tasting_wines_missing_columns:
                tables_created.append(
                    f"tasting_wines (added missing columns: {', '.join(tasting_wines_missing_columns)})"
                )

        # Create tasting_costs table
        tasting_costs_exists = db.execute(
            text(
                """
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'tasting_costs'
            );
        """
            )
        ).scalar()

        if not tasting_costs_exists:
            print("Creating tasting_costs table...")

            db.execute(
                text(
                    """
                CREATE TABLE tasting_costs (
                    id VARCHAR(36) PRIMARY KEY,
                    tasting_id VARCHAR(36) NOT NULL REFERENCES wine_tastings(id),
                    cost_category VARCHAR(50) NOT NULL,
                    cost_description VARCHAR(255) NOT NULL,
                    supplier_name VARCHAR(255),
                    amount_ore INTEGER NOT NULL,
                    cost_date DATE NOT NULL,
                    invoice_reference VARCHAR(100),
                    fiken_transaction_id INTEGER,
                    cost_type VARCHAR(20) DEFAULT 'fixed',
                    active BOOLEAN NOT NULL DEFAULT true,
                    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
                );
            """
                )
            )

            tables_created.append("tasting_costs")
            print("tasting_costs table created successfully")
        else:
            print("tasting_costs table exists, checking for missing columns...")

            # Check and add missing columns for tasting_costs
            tasting_costs_missing_columns = []

            # List of columns that should exist in tasting_costs
            expected_tasting_costs_columns = [
                ("cost_category", "VARCHAR(50) NOT NULL DEFAULT 'venue'"),
                ("cost_description", "VARCHAR(255) NOT NULL DEFAULT 'Event cost'"),
                ("supplier_name", "VARCHAR(255)"),
                ("amount_ore", "INTEGER NOT NULL DEFAULT 0"),
                ("cost_date", "DATE NOT NULL DEFAULT CURRENT_DATE"),
                ("invoice_reference", "VARCHAR(100)"),
                ("fiken_transaction_id", "INTEGER"),
                ("cost_type", "VARCHAR(20) DEFAULT 'fixed'"),
                ("active", "BOOLEAN NOT NULL DEFAULT true"),
                ("created_at", "TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()"),
                ("updated_at", "TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()"),
            ]

            for column_name, column_type in expected_tasting_costs_columns:
                if not column_exists("tasting_costs", column_name):
                    print(f"Adding missing column: {column_name} to tasting_costs")
                    db.execute(
                        text(
                            f"""
                        ALTER TABLE tasting_costs 
                        ADD COLUMN {column_name} {column_type};
                    """
                        )
                    )
                    tasting_costs_missing_columns.append(column_name)

            if tasting_costs_missing_columns:
                tables_created.append(
                    f"tasting_costs (added missing columns: {', '.join(tasting_costs_missing_columns)})"
                )

        db.commit()
        db.close()

        if tables_created:
            return {
                "status": "success",
                "message": f"Database migrations completed - created tables: {', '.join(tables_created)}",
                "tables_created": tables_created,
            }
        else:
            return {
                "status": "success",
                "message": "Database is up to date - all tables already exist",
                "tables_created": [],
            }

    except Exception as e:
        print(f"Migration failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Migration failed: {str(e)}")


# Suppliers endpoints
@app.get("/db/suppliers")
async def list_suppliers():
    """List all suppliers"""
    try:
        db_config = get_database_config()

        conn_params = {
            "host": db_config["host"],
            "port": int(db_config["port"]),
            "database": db_config["name"],
            "user": db_config["username"],
            "password": db_config["password"],
        }

        conn = pg8000.connect(**conn_params)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT id, name, country, contact_person, email, phone, 
                   payment_terms, currency, tax_id, active, created_at, updated_at
            FROM suppliers 
            WHERE active = true
            ORDER BY name
        """
        )

        columns = [
            "id",
            "name",
            "country",
            "contact_person",
            "email",
            "phone",
            "payment_terms",
            "currency",
            "tax_id",
            "active",
            "created_at",
            "updated_at",
        ]

        suppliers = []
        for row in cursor.fetchall():
            supplier = {}
            for i, col in enumerate(columns):
                value = row[i]
                if isinstance(value, datetime):
                    supplier[col] = value.isoformat()
                else:
                    supplier[col] = value
            suppliers.append(supplier)

        cursor.close()
        conn.close()

        return {"suppliers": suppliers}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@app.post("/db/suppliers")
async def create_supplier(request: Request):
    """Create a new supplier"""
    try:
        data = await request.json()

        # Validate required fields
        required_fields = ["name", "country"]
        for field in required_fields:
            if field not in data:
                raise HTTPException(
                    status_code=400, detail=f"Missing required field: {field}"
                )

        db_config = get_database_config()

        conn_params = {
            "host": db_config["host"],
            "port": int(db_config["port"]),
            "database": db_config["name"],
            "user": db_config["username"],
            "password": db_config["password"],
        }

        conn = pg8000.connect(**conn_params)
        cursor = conn.cursor()

        # Generate UUID for supplier
        supplier_id = str(uuid.uuid4())

        cursor.execute(
            """
            INSERT INTO suppliers (
                id, name, country, contact_person, email, phone,
                payment_terms, currency, tax_id, active, created_at, updated_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
            (
                supplier_id,
                data["name"],
                data["country"],
                data.get("contact_person"),
                data.get("email"),
                data.get("phone"),
                data.get("payment_terms", 30),
                data.get("currency", "EUR"),
                data.get("tax_id"),
                True,
                datetime.now(),
                datetime.now(),
            ),
        )

        conn.commit()
        cursor.close()
        conn.close()

        return {"message": "Supplier created successfully", "supplier_id": supplier_id}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


# Wines endpoints
@app.get("/db/wines")
async def list_wines():
    """List all wines"""
    try:
        db_config = get_database_config()

        conn_params = {
            "host": db_config["host"],
            "port": int(db_config["port"]),
            "database": db_config["name"],
            "user": db_config["username"],
            "password": db_config["password"],
        }

        conn = pg8000.connect(**conn_params)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT id, name, producer, region, country, vintage, 
                   alcohol_content, bottle_size_ml, product_category,
                   tasting_notes, organic, biodynamic, active, created_at, updated_at
            FROM wines 
            WHERE active = true
            ORDER BY name, vintage DESC
        """
        )

        columns = [
            "id",
            "name",
            "producer",
            "region",
            "country",
            "vintage",
            "alcohol_content",
            "bottle_size_ml",
            "product_category",
            "tasting_notes",
            "organic",
            "biodynamic",
            "active",
            "created_at",
            "updated_at",
        ]

        wines = []
        for row in cursor.fetchall():
            wine = {}
            for i, col in enumerate(columns):
                value = row[i]
                if isinstance(value, datetime):
                    wine[col] = value.isoformat()
                elif isinstance(value, Decimal):
                    wine[col] = float(value)
                else:
                    wine[col] = value
            wines.append(wine)

        cursor.close()
        conn.close()

        return {"wines": wines}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@app.post("/db/wines")
async def create_wine(request: Request):
    """Create a new wine"""
    try:
        data = await request.json()

        # Validate required fields
        required_fields = ["name", "producer", "country"]
        for field in required_fields:
            if field not in data:
                raise HTTPException(
                    status_code=400, detail=f"Missing required field: {field}"
                )

        db_config = get_database_config()

        conn_params = {
            "host": db_config["host"],
            "port": int(db_config["port"]),
            "database": db_config["name"],
            "user": db_config["username"],
            "password": db_config["password"],
        }

        conn = pg8000.connect(**conn_params)
        cursor = conn.cursor()

        # Generate UUID for wine
        wine_id = str(uuid.uuid4())

        cursor.execute(
            """
            INSERT INTO wines (
                id, name, producer, region, country, vintage, 
                alcohol_content, bottle_size_ml, product_category,
                tasting_notes, organic, biodynamic, active, created_at, updated_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
            (
                wine_id,
                data["name"],
                data["producer"],
                data.get("region"),
                data["country"],
                data.get("vintage"),
                data.get("alcohol_content"),
                data.get("bottle_size_ml", 750),
                data.get("product_category"),
                data.get("tasting_notes"),
                data.get("organic", False),
                data.get("biodynamic", False),
                True,
                datetime.now(),
                datetime.now(),
            ),
        )

        conn.commit()
        cursor.close()
        conn.close()

        return {"message": "Wine created successfully", "wine_id": wine_id}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


# Phase 3: Customer Management endpoints
@app.get("/db/customers")
async def list_customers():
    """List all customers"""
    try:
        db_config = get_database_config()

        conn_params = {
            "host": db_config["host"],
            "port": int(db_config["port"]),
            "database": db_config["name"],
            "user": db_config["username"],
            "password": db_config["password"],
        }

        conn = pg8000.connect(**conn_params)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT id, name, customer_type, email, phone, address_line1, 
                   city, country, organization_number, vat_number,
                   preferred_delivery_method, payment_terms, credit_limit_nok_ore,
                   marketing_consent, newsletter_subscription, preferred_language,
                   active, created_at, updated_at
            FROM customers 
            WHERE active = true
            ORDER BY name
        """
        )

        columns = [
            "id",
            "name",
            "customer_type",
            "email",
            "phone",
            "address_line1",
            "city",
            "country",
            "organization_number",
            "vat_number",
            "preferred_delivery_method",
            "payment_terms",
            "credit_limit_nok_ore",
            "marketing_consent",
            "newsletter_subscription",
            "preferred_language",
            "active",
            "created_at",
            "updated_at",
        ]

        customers = []
        for row in cursor.fetchall():
            customer = {}
            for i, col in enumerate(columns):
                value = row[i]
                if isinstance(value, datetime):
                    customer[col] = value.isoformat()
                else:
                    customer[col] = value
            customers.append(customer)

        cursor.close()
        conn.close()

        return {"customers": customers}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@app.post("/db/customers")
async def create_customer(request: Request):
    """Create a new customer"""
    try:
        data = await request.json()

        # Validate required fields
        required_fields = ["name", "customer_type"]
        for field in required_fields:
            if field not in data:
                raise HTTPException(
                    status_code=400, detail=f"Missing required field: {field}"
                )

        # Validate customer type
        valid_types = ["individual", "restaurant", "retailer", "distributor"]
        if data["customer_type"] not in valid_types:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid customer_type. Must be one of: {', '.join(valid_types)}",
            )

        db_config = get_database_config()

        conn_params = {
            "host": db_config["host"],
            "port": int(db_config["port"]),
            "database": db_config["name"],
            "user": db_config["username"],
            "password": db_config["password"],
        }

        conn = pg8000.connect(**conn_params)
        cursor = conn.cursor()

        # Generate UUID for customer
        customer_id = str(uuid.uuid4())

        cursor.execute(
            """
            INSERT INTO customers (
                id, name, customer_type, email, phone, address_line1, address_line2,
                postal_code, city, country, organization_number, vat_number,
                preferred_delivery_method, payment_terms, credit_limit_nok_ore,
                marketing_consent, newsletter_subscription, preferred_language,
                notes, active, created_at, updated_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
            (
                customer_id,
                data["name"],
                data["customer_type"],
                data.get("email"),
                data.get("phone"),
                data.get("address_line1"),
                data.get("address_line2"),
                data.get("postal_code"),
                data.get("city"),
                data.get("country", "Norway"),
                data.get("organization_number"),
                data.get("vat_number"),
                data.get("preferred_delivery_method"),
                data.get("payment_terms", 0),
                data.get("credit_limit_nok_ore", 0),
                data.get("marketing_consent", False),
                data.get("newsletter_subscription", False),
                data.get("preferred_language", "no"),
                data.get("notes"),
                True,
                datetime.now(),
                datetime.now(),
            ),
        )

        conn.commit()
        cursor.close()
        conn.close()

        return {"message": "Customer created successfully", "customer_id": customer_id}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


# Phase 3: Order Management endpoints
@app.get("/db/orders")
async def list_orders():
    """List all orders with customer information"""
    try:
        db_config = get_database_config()

        conn_params = {
            "host": db_config["host"],
            "port": int(db_config["port"]),
            "database": db_config["name"],
            "user": db_config["username"],
            "password": db_config["password"],
        }

        conn = pg8000.connect(**conn_params)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT o.id, o.order_number, o.customer_id, c.name as customer_name,
                   o.status, o.payment_status, o.order_date, o.requested_delivery_date,
                   o.delivery_method, o.delivery_city, o.subtotal_ore, o.delivery_fee_ore,
                   o.discount_ore, o.vat_ore, o.total_ore, o.payment_terms,
                   o.customer_notes, o.internal_notes, o.active, o.created_at, o.updated_at
            FROM orders o
            LEFT JOIN customers c ON o.customer_id = c.id
            WHERE o.active = true
            ORDER BY o.order_date DESC, o.order_number
        """
        )

        columns = [
            "id",
            "order_number",
            "customer_id",
            "customer_name",
            "status",
            "payment_status",
            "order_date",
            "requested_delivery_date",
            "delivery_method",
            "delivery_city",
            "subtotal_ore",
            "delivery_fee_ore",
            "discount_ore",
            "vat_ore",
            "total_ore",
            "payment_terms",
            "customer_notes",
            "internal_notes",
            "active",
            "created_at",
            "updated_at",
        ]

        orders = []
        for row in cursor.fetchall():
            order = {}
            for i, col in enumerate(columns):
                value = row[i]
                if isinstance(value, datetime):
                    order[col] = value.isoformat()
                elif isinstance(value, date):
                    order[col] = value.isoformat()
                else:
                    order[col] = value
            orders.append(order)

        cursor.close()
        conn.close()

        return {"orders": orders}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@app.get("/db/orders/{order_id}")
async def get_order_details(order_id: str):
    """Get detailed order information including items"""
    try:
        db_config = get_database_config()

        conn_params = {
            "host": db_config["host"],
            "port": int(db_config["port"]),
            "database": db_config["name"],
            "user": db_config["username"],
            "password": db_config["password"],
        }

        conn = pg8000.connect(**conn_params)
        cursor = conn.cursor()

        # Get order details
        cursor.execute(
            """
            SELECT o.id, o.order_number, o.customer_id, c.name as customer_name, c.email as customer_email,
                   o.status, o.payment_status, o.order_date, o.requested_delivery_date,
                   o.confirmed_delivery_date, o.delivered_date, o.delivery_method,
                   o.delivery_address_line1, o.delivery_address_line2, o.delivery_postal_code,
                   o.delivery_city, o.delivery_country, o.delivery_notes,
                   o.subtotal_ore, o.delivery_fee_ore, o.discount_ore, o.vat_ore, o.total_ore,
                   o.payment_terms, o.payment_due_date, o.customer_notes, o.internal_notes,
                   o.fiken_order_id, o.fiken_invoice_number, o.active, o.created_at, o.updated_at
            FROM orders o
            LEFT JOIN customers c ON o.customer_id = c.id
            WHERE o.id = %s AND o.active = true
        """,
            (order_id,),
        )

        order_row = cursor.fetchone()
        if not order_row:
            raise HTTPException(status_code=404, detail="Order not found")

        order_columns = [
            "id",
            "order_number",
            "customer_id",
            "customer_name",
            "customer_email",
            "status",
            "payment_status",
            "order_date",
            "requested_delivery_date",
            "confirmed_delivery_date",
            "delivered_date",
            "delivery_method",
            "delivery_address_line1",
            "delivery_address_line2",
            "delivery_postal_code",
            "delivery_city",
            "delivery_country",
            "delivery_notes",
            "subtotal_ore",
            "delivery_fee_ore",
            "discount_ore",
            "vat_ore",
            "total_ore",
            "payment_terms",
            "payment_due_date",
            "customer_notes",
            "internal_notes",
            "fiken_order_id",
            "fiken_invoice_number",
            "active",
            "created_at",
            "updated_at",
        ]

        order = {}
        for i, col in enumerate(order_columns):
            value = order_row[i]
            if isinstance(value, (datetime, date)):
                order[col] = value.isoformat()
            else:
                order[col] = value

        # Get order items
        cursor.execute(
            """
            SELECT oi.id, oi.wine_batch_id, oi.wine_id, oi.quantity, oi.unit_price_ore,
                   oi.total_price_ore, oi.wine_name, oi.producer, oi.vintage, oi.bottle_size_ml,
                   oi.discount_percentage, oi.discount_ore, oi.notes, oi.created_at
            FROM order_items oi
            WHERE oi.order_id = %s AND oi.active = true
            ORDER BY oi.created_at
        """,
            (order_id,),
        )

        item_columns = [
            "id",
            "wine_batch_id",
            "wine_id",
            "quantity",
            "unit_price_ore",
            "total_price_ore",
            "wine_name",
            "producer",
            "vintage",
            "bottle_size_ml",
            "discount_percentage",
            "discount_ore",
            "notes",
            "created_at",
        ]

        items = []
        for row in cursor.fetchall():
            item = {}
            for i, col in enumerate(item_columns):
                value = row[i]
                if isinstance(value, (datetime, date)):
                    item[col] = value.isoformat()
                else:
                    item[col] = value
            items.append(item)

        order["items"] = items

        cursor.close()
        conn.close()

        return {"order": order}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


# Phase 3: Inventory Management endpoints
@app.get("/db/inventory")
async def list_inventory():
    """List wine inventory with stock levels and margins"""
    try:
        db_config = get_database_config()

        conn_params = {
            "host": db_config["host"],
            "port": int(db_config["port"]),
            "database": db_config["name"],
            "user": db_config["username"],
            "password": db_config["password"],
        }

        conn = pg8000.connect(**conn_params)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT i.id, i.wine_id, w.name as wine_name, w.producer, w.vintage,
                   i.batch_id, b.batch_number, i.quantity_available, i.quantity_reserved,
                   i.quantity_sold, i.cost_per_bottle_ore, i.selling_price_ore,
                   i.markup_percentage, i.margin_per_bottle_ore, i.minimum_stock_level,
                   i.location, i.best_before_date, i.low_stock_alert,
                   (i.quantity_available - i.quantity_reserved) as available_stock,
                   i.active, i.created_at, i.updated_at
            FROM wine_inventory i
            LEFT JOIN wines w ON i.wine_id = w.id
            LEFT JOIN wine_batches b ON i.batch_id = b.id
            WHERE i.active = true
            ORDER BY w.name, w.vintage, b.batch_number
        """
        )

        columns = [
            "id",
            "wine_id",
            "wine_name",
            "producer",
            "vintage",
            "batch_id",
            "batch_number",
            "quantity_available",
            "quantity_reserved",
            "quantity_sold",
            "cost_per_bottle_ore",
            "selling_price_ore",
            "markup_percentage",
            "margin_per_bottle_ore",
            "minimum_stock_level",
            "location",
            "best_before_date",
            "low_stock_alert",
            "available_stock",
            "active",
            "created_at",
            "updated_at",
        ]

        inventory = []
        for row in cursor.fetchall():
            item = {}
            for i, col in enumerate(columns):
                value = row[i]
                if isinstance(value, (datetime, date)):
                    item[col] = value.isoformat()
                else:
                    item[col] = value
            inventory.append(item)

        cursor.close()
        conn.close()

        return {"inventory": inventory}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@app.get("/db/inventory/low-stock")
async def list_low_stock():
    """List inventory items with low stock alerts"""
    try:
        db_config = get_database_config()

        conn_params = {
            "host": db_config["host"],
            "port": int(db_config["port"]),
            "database": db_config["name"],
            "user": db_config["username"],
            "password": db_config["password"],
        }

        conn = pg8000.connect(**conn_params)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT i.id, i.wine_id, w.name as wine_name, w.producer, w.vintage,
                   i.batch_id, b.batch_number, i.quantity_available, i.quantity_reserved,
                   i.minimum_stock_level, (i.quantity_available - i.quantity_reserved) as available_stock,
                   i.location, i.created_at, i.updated_at
            FROM wine_inventory i
            LEFT JOIN wines w ON i.wine_id = w.id
            LEFT JOIN wine_batches b ON i.batch_id = b.id
            WHERE i.active = true 
            AND (i.quantity_available - i.quantity_reserved) <= i.minimum_stock_level
            ORDER BY (i.quantity_available - i.quantity_reserved) ASC, w.name
        """
        )

        columns = [
            "id",
            "wine_id",
            "wine_name",
            "producer",
            "vintage",
            "batch_id",
            "batch_number",
            "quantity_available",
            "quantity_reserved",
            "minimum_stock_level",
            "available_stock",
            "location",
            "created_at",
            "updated_at",
        ]

        low_stock = []
        for row in cursor.fetchall():
            item = {}
            for i, col in enumerate(columns):
                value = row[i]
                if isinstance(value, (datetime, date)):
                    item[col] = value.isoformat()
                else:
                    item[col] = value
            low_stock.append(item)

        cursor.close()
        conn.close()

        return {"low_stock_items": low_stock}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


# Wine Batch Costs endpoints
@app.get("/db/wine-batch-costs")
async def list_wine_batch_costs():
    """List all wine batch costs for accounting and cost tracking"""
    try:
        db_config = get_database_config()

        conn_params = {
            "host": db_config["host"],
            "port": int(db_config["port"]),
            "database": db_config["name"],
            "user": db_config["username"],
            "password": db_config["password"],
        }

        conn = pg8000.connect(**conn_params)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT wbc.id, wbc.batch_id, wb.batch_number, wb.wine_name,
                   wbc.cost_type, wbc.amount_ore, wbc.currency, 
                   wbc.fiken_account_code, wbc.payment_date, wbc.allocation_method,
                   wbc.invoice_reference, wbc.active, wbc.created_at, wbc.updated_at
            FROM wine_batch_costs wbc
            LEFT JOIN wine_batches wb ON wbc.batch_id = wb.id
            WHERE wbc.active = true
            ORDER BY wb.batch_number, wbc.cost_type, wbc.created_at
        """
        )

        columns = [
            "id",
            "batch_id",
            "batch_number",
            "wine_name",
            "cost_type",
            "amount_ore",
            "currency",
            "fiken_account_code",
            "payment_date",
            "allocation_method",
            "invoice_reference",
            "active",
            "created_at",
            "updated_at",
        ]

        costs = []
        for row in cursor.fetchall():
            cost = {}
            for i, col in enumerate(columns):
                value = row[i]
                if isinstance(value, (datetime, date)):
                    cost[col] = value.isoformat()
                else:
                    cost[col] = value
            costs.append(cost)

        cursor.close()
        conn.close()

        return {"wine_batch_costs": costs}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@app.get("/db/wine-batch-costs/{batch_id}")
async def get_batch_costs(batch_id: str):
    """Get all costs for a specific wine batch"""
    try:
        db_config = get_database_config()

        conn_params = {
            "host": db_config["host"],
            "port": int(db_config["port"]),
            "database": db_config["name"],
            "user": db_config["username"],
            "password": db_config["password"],
        }

        conn = pg8000.connect(**conn_params)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT wbc.id, wbc.batch_id, wb.batch_number, wb.wine_name,
                   wbc.cost_type, wbc.amount_ore, wbc.currency, 
                   wbc.fiken_account_code, wbc.payment_date, wbc.allocation_method,
                   wbc.invoice_reference, wbc.active, wbc.created_at, wbc.updated_at
            FROM wine_batch_costs wbc
            LEFT JOIN wine_batches wb ON wbc.batch_id = wb.id
            WHERE wbc.batch_id = %s AND wbc.active = true
            ORDER BY wbc.cost_type, wbc.created_at
        """,
            (batch_id,),
        )

        columns = [
            "id",
            "batch_id",
            "batch_number",
            "wine_name",
            "cost_type",
            "amount_ore",
            "currency",
            "fiken_account_code",
            "payment_date",
            "allocation_method",
            "invoice_reference",
            "active",
            "created_at",
            "updated_at",
        ]

        costs = []
        for row in cursor.fetchall():
            cost = {}
            for i, col in enumerate(columns):
                value = row[i]
                if isinstance(value, (datetime, date)):
                    cost[col] = value.isoformat()
                else:
                    cost[col] = value
            costs.append(cost)

        cursor.close()
        conn.close()

        return {"batch_costs": costs}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


# Order Items endpoints
@app.get("/db/order-items")
async def list_order_items():
    """List all order items across all orders"""
    try:
        db_config = get_database_config()

        conn_params = {
            "host": db_config["host"],
            "port": int(db_config["port"]),
            "database": db_config["name"],
            "user": db_config["username"],
            "password": db_config["password"],
        }

        conn = pg8000.connect(**conn_params)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT oi.id, oi.order_id, o.order_number, oi.wine_batch_id, oi.wine_id,
                   oi.quantity, oi.unit_price_ore, oi.total_price_ore, 
                   oi.wine_name, oi.producer, oi.vintage, oi.bottle_size_ml,
                   oi.discount_percentage, oi.discount_ore, oi.notes,
                   wb.batch_number, c.name as customer_name,
                   oi.active, oi.created_at, oi.updated_at
            FROM order_items oi
            LEFT JOIN orders o ON oi.order_id = o.id
            LEFT JOIN wine_batches wb ON oi.wine_batch_id = wb.id
            LEFT JOIN customers c ON o.customer_id = c.id
            WHERE oi.active = true
            ORDER BY o.order_number, oi.wine_name, oi.created_at
        """
        )

        columns = [
            "id",
            "order_id",
            "order_number",
            "wine_batch_id",
            "wine_id",
            "quantity",
            "unit_price_ore",
            "total_price_ore",
            "wine_name",
            "producer",
            "vintage",
            "bottle_size_ml",
            "discount_percentage",
            "discount_ore",
            "notes",
            "batch_number",
            "customer_name",
            "active",
            "created_at",
            "updated_at",
        ]

        items = []
        for row in cursor.fetchall():
            item = {}
            for i, col in enumerate(columns):
                value = row[i]
                if isinstance(value, (datetime, date)):
                    item[col] = value.isoformat()
                elif isinstance(value, Decimal):
                    item[col] = float(value)
                else:
                    item[col] = value
            items.append(item)

        cursor.close()
        conn.close()

        return {"order_items": items}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@app.get("/db/order-items/{order_id}")
async def get_order_items(order_id: str):
    """Get all items for a specific order"""
    try:
        db_config = get_database_config()

        conn_params = {
            "host": db_config["host"],
            "port": int(db_config["port"]),
            "database": db_config["name"],
            "user": db_config["username"],
            "password": db_config["password"],
        }

        conn = pg8000.connect(**conn_params)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT oi.id, oi.order_id, oi.wine_batch_id, oi.wine_id,
                   oi.quantity, oi.unit_price_ore, oi.total_price_ore, 
                   oi.wine_name, oi.producer, oi.vintage, oi.bottle_size_ml,
                   oi.discount_percentage, oi.discount_ore, oi.notes,
                   wb.batch_number, oi.active, oi.created_at, oi.updated_at
            FROM order_items oi
            LEFT JOIN wine_batches wb ON oi.wine_batch_id = wb.id
            WHERE oi.order_id = %s AND oi.active = true
            ORDER BY oi.wine_name, oi.created_at
        """,
            (order_id,),
        )

        columns = [
            "id",
            "order_id",
            "wine_batch_id",
            "wine_id",
            "quantity",
            "unit_price_ore",
            "total_price_ore",
            "wine_name",
            "producer",
            "vintage",
            "bottle_size_ml",
            "discount_percentage",
            "discount_ore",
            "notes",
            "batch_number",
            "active",
            "created_at",
            "updated_at",
        ]

        items = []
        for row in cursor.fetchall():
            item = {}
            for i, col in enumerate(columns):
                value = row[i]
                if isinstance(value, (datetime, date)):
                    item[col] = value.isoformat()
                elif isinstance(value, Decimal):
                    item[col] = float(value)
                else:
                    item[col] = value
            items.append(item)

        cursor.close()
        conn.close()

        return {"order_items": items}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


# Phase 4: Wine Tasting Event Management endpoints
@app.get("/db/wine-tastings")
async def list_wine_tastings():
    """List all wine tasting events"""
    try:
        db_config = get_database_config()

        conn_params = {
            "host": db_config["host"],
            "port": int(db_config["port"]),
            "database": db_config["name"],
            "user": db_config["username"],
            "password": db_config["password"],
        }

        conn = pg8000.connect(**conn_params)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT wt.id, wt.event_name, wt.event_date, wt.event_time, wt.venue_type,
                   wt.venue_name, wt.venue_address, wt.venue_cost_ore, wt.max_attendees,
                   wt.actual_attendees, wt.event_type, wt.event_status, wt.target_customer_segment,
                   wt.marketing_objective, wt.total_event_cost_ore, wt.estimated_revenue_impact_ore,
                   wt.actual_revenue_impact_ore, wt.notes, wt.active, wt.created_at, wt.updated_at,
                   COUNT(ta.id) as attendee_count,
                   COUNT(tw.id) as wine_count,
                   SUM(tc.amount_ore) as total_costs
            FROM wine_tastings wt
            LEFT JOIN tasting_attendees ta ON wt.id = ta.tasting_id AND ta.active = true
            LEFT JOIN tasting_wines tw ON wt.id = tw.tasting_id AND tw.active = true
            LEFT JOIN tasting_costs tc ON wt.id = tc.tasting_id AND tc.active = true
            WHERE wt.active = true
            GROUP BY wt.id, wt.event_name, wt.event_date, wt.event_time, wt.venue_type,
                     wt.venue_name, wt.venue_address, wt.venue_cost_ore, wt.max_attendees,
                     wt.actual_attendees, wt.event_type, wt.event_status, wt.target_customer_segment,
                     wt.marketing_objective, wt.total_event_cost_ore, wt.estimated_revenue_impact_ore,
                     wt.actual_revenue_impact_ore, wt.notes, wt.active, wt.created_at, wt.updated_at
            ORDER BY wt.event_date DESC, wt.event_name
        """
        )

        columns = [
            "id",
            "event_name",
            "event_date",
            "event_time",
            "venue_type",
            "venue_name",
            "venue_address",
            "venue_cost_ore",
            "max_attendees",
            "actual_attendees",
            "event_type",
            "event_status",
            "target_customer_segment",
            "marketing_objective",
            "total_event_cost_ore",
            "estimated_revenue_impact_ore",
            "actual_revenue_impact_ore",
            "notes",
            "active",
            "created_at",
            "updated_at",
            "attendee_count",
            "wine_count",
            "total_costs",
        ]

        tastings = []
        for row in cursor.fetchall():
            tasting = {}
            for i, col in enumerate(columns):
                value = row[i]
                if isinstance(value, (datetime, date)):
                    tasting[col] = value.isoformat()
                elif isinstance(value, time):
                    tasting[col] = str(value)
                else:
                    tasting[col] = value

            # Calculate ROI percentage
            if tasting["total_event_cost_ore"] and tasting["total_event_cost_ore"] > 0:
                revenue_impact = tasting["actual_revenue_impact_ore"] or 0
                roi = (
                    (revenue_impact - tasting["total_event_cost_ore"])
                    / tasting["total_event_cost_ore"]
                ) * 100
                tasting["roi_percentage"] = round(roi, 2)
            else:
                tasting["roi_percentage"] = 0

            tastings.append(tasting)

        cursor.close()
        conn.close()

        return {"wine_tastings": tastings}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@app.get("/db/wine-tastings/{tasting_id}")
async def get_wine_tasting_details(tasting_id: str):
    """Get detailed wine tasting information including attendees, wines, costs, and outcomes"""
    try:
        db_config = get_database_config()

        conn_params = {
            "host": db_config["host"],
            "port": int(db_config["port"]),
            "database": db_config["name"],
            "user": db_config["username"],
            "password": db_config["password"],
        }

        conn = pg8000.connect(**conn_params)
        cursor = conn.cursor()

        # Get tasting details
        cursor.execute(
            """
            SELECT id, event_name, event_date, event_time, venue_type, venue_name, venue_address,
                   venue_cost_ore, max_attendees, actual_attendees, event_type, event_status,
                   target_customer_segment, marketing_objective, total_event_cost_ore,
                   estimated_revenue_impact_ore, actual_revenue_impact_ore, notes,
                   active, created_at, updated_at
            FROM wine_tastings
            WHERE id = %s AND active = true
        """,
            (tasting_id,),
        )

        tasting_row = cursor.fetchone()
        if not tasting_row:
            raise HTTPException(status_code=404, detail="Wine tasting not found")

        tasting_columns = [
            "id",
            "event_name",
            "event_date",
            "event_time",
            "venue_type",
            "venue_name",
            "venue_address",
            "venue_cost_ore",
            "max_attendees",
            "actual_attendees",
            "event_type",
            "event_status",
            "target_customer_segment",
            "marketing_objective",
            "total_event_cost_ore",
            "estimated_revenue_impact_ore",
            "actual_revenue_impact_ore",
            "notes",
            "active",
            "created_at",
            "updated_at",
        ]

        tasting = {}
        for i, col in enumerate(tasting_columns):
            value = tasting_row[i]
            if isinstance(value, (datetime, date)):
                tasting[col] = value.isoformat()
            else:
                tasting[col] = value

        # Calculate ROI
        if tasting["total_event_cost_ore"] and tasting["total_event_cost_ore"] > 0:
            revenue_impact = tasting["actual_revenue_impact_ore"] or 0
            roi = (
                (revenue_impact - tasting["total_event_cost_ore"])
                / tasting["total_event_cost_ore"]
            ) * 100
            tasting["roi_percentage"] = round(roi, 2)
        else:
            tasting["roi_percentage"] = 0

        # Get attendees
        cursor.execute(
            """
            SELECT ta.id, ta.customer_id, c.name as customer_name, ta.attendee_name,
                   ta.attendee_email, ta.attendee_phone, ta.attendee_type, ta.rsvp_status,
                   ta.follow_up_required, ta.post_event_interest_level, ta.potential_order_value_ore,
                   ta.created_at, ta.updated_at
            FROM tasting_attendees ta
            LEFT JOIN customers c ON ta.customer_id = c.id
            WHERE ta.tasting_id = %s AND ta.active = true
            ORDER BY ta.attendee_name
        """,
            (tasting_id,),
        )

        attendee_columns = [
            "id",
            "customer_id",
            "customer_name",
            "attendee_name",
            "attendee_email",
            "attendee_phone",
            "attendee_type",
            "rsvp_status",
            "follow_up_required",
            "post_event_interest_level",
            "potential_order_value_ore",
            "created_at",
            "updated_at",
        ]

        attendees = []
        for row in cursor.fetchall():
            attendee = {}
            for i, col in enumerate(attendee_columns):
                value = row[i]
                if isinstance(value, (datetime, date)):
                    attendee[col] = value.isoformat()
                else:
                    attendee[col] = value
            attendees.append(attendee)

        # Get wines
        cursor.execute(
            """
            SELECT tw.id, tw.wine_id, w.name as wine_name, w.producer as wine_producer,
                   tw.wine_name as custom_wine_name, tw.wine_producer as custom_producer,
                   tw.wine_vintage, tw.bottles_used, tw.wine_source, tw.cost_per_bottle_ore,
                   tw.tasting_order, tw.tasting_notes, tw.customer_feedback, tw.popularity_score,
                   tw.follow_up_orders, tw.created_at, tw.updated_at
            FROM tasting_wines tw
            LEFT JOIN wines w ON tw.wine_id = w.id
            WHERE tw.tasting_id = %s AND tw.active = true
            ORDER BY tw.tasting_order, tw.wine_name, tw.custom_wine_name
        """,
            (tasting_id,),
        )

        wine_columns = [
            "id",
            "wine_id",
            "wine_name",
            "wine_producer",
            "custom_wine_name",
            "custom_producer",
            "wine_vintage",
            "bottles_used",
            "wine_source",
            "cost_per_bottle_ore",
            "tasting_order",
            "tasting_notes",
            "customer_feedback",
            "popularity_score",
            "follow_up_orders",
            "created_at",
            "updated_at",
        ]

        wines = []
        for row in cursor.fetchall():
            wine = {}
            for i, col in enumerate(wine_columns):
                value = row[i]
                if isinstance(value, (datetime, date)):
                    wine[col] = value.isoformat()
                elif col == "customer_feedback" and value:
                    try:
                        import json

                        wine[col] = (
                            json.loads(value) if isinstance(value, str) else value
                        )
                    except:
                        wine[col] = value
                else:
                    wine[col] = value

            # Calculate total wine cost
            wine["total_wine_cost_ore"] = (
                wine["bottles_used"] * wine["cost_per_bottle_ore"]
            )

            # Use catalog wine name if custom name not provided
            wine["display_name"] = wine["custom_wine_name"] or wine["wine_name"]
            wine["display_producer"] = wine["custom_producer"] or wine["wine_producer"]

            wines.append(wine)

        # Get costs
        cursor.execute(
            """
            SELECT id, cost_category, cost_description, supplier_name, amount_ore,
                   cost_date, invoice_reference, fiken_transaction_id, cost_type,
                   created_at, updated_at
            FROM tasting_costs
            WHERE tasting_id = %s AND active = true
            ORDER BY cost_date, cost_category
        """,
            (tasting_id,),
        )

        cost_columns = [
            "id",
            "cost_category",
            "cost_description",
            "supplier_name",
            "amount_ore",
            "cost_date",
            "invoice_reference",
            "fiken_transaction_id",
            "cost_type",
            "created_at",
            "updated_at",
        ]

        costs = []
        for row in cursor.fetchall():
            cost = {}
            for i, col in enumerate(cost_columns):
                value = row[i]
                if isinstance(value, (datetime, date)):
                    cost[col] = value.isoformat()
                else:
                    cost[col] = value
            costs.append(cost)

        # Get outcomes
        cursor.execute(
            """
            SELECT to_.id, to_.customer_id, c.name as customer_name, to_.outcome_type,
                   to_.outcome_value_ore, to_.outcome_date, to_.notes,
                   to_.created_at, to_.updated_at
            FROM tasting_outcomes to_
            LEFT JOIN customers c ON to_.customer_id = c.id
            WHERE to_.tasting_id = %s AND to_.active = true
            ORDER BY to_.outcome_date DESC
        """,
            (tasting_id,),
        )

        outcome_columns = [
            "id",
            "customer_id",
            "customer_name",
            "outcome_type",
            "outcome_value_ore",
            "outcome_date",
            "notes",
            "created_at",
            "updated_at",
        ]

        outcomes = []
        for row in cursor.fetchall():
            outcome = {}
            for i, col in enumerate(outcome_columns):
                value = row[i]
                if isinstance(value, (datetime, date)):
                    outcome[col] = value.isoformat()
                else:
                    outcome[col] = value
            outcomes.append(outcome)

        cursor.close()
        conn.close()

        # Add related data to tasting
        tasting["attendees"] = attendees
        tasting["wines"] = wines
        tasting["costs"] = costs
        tasting["outcomes"] = outcomes

        # Add summary statistics
        tasting["summary"] = {
            "total_attendees": len(attendees),
            "total_wines": len(wines),
            "total_costs": sum(cost["amount_ore"] for cost in costs),
            "total_wine_cost": sum(wine["total_wine_cost_ore"] for wine in wines),
            "total_outcomes_value": sum(
                outcome["outcome_value_ore"] or 0 for outcome in outcomes
            ),
            "confirmed_attendees": len(
                [a for a in attendees if a["rsvp_status"] in ["confirmed", "attended"]]
            ),
            "follow_up_required": len(
                [a for a in attendees if a["follow_up_required"]]
            ),
        }

        return tasting

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@app.get("/db/tasting-attendees")
async def list_tasting_attendees():
    """List all tasting attendees across all events"""
    try:
        db_config = get_database_config()

        conn_params = {
            "host": db_config["host"],
            "port": int(db_config["port"]),
            "database": db_config["name"],
            "user": db_config["username"],
            "password": db_config["password"],
        }

        conn = pg8000.connect(**conn_params)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT ta.id, ta.tasting_id, wt.event_name, ta.customer_id, c.name as customer_name,
                   ta.attendee_name, ta.attendee_email, ta.attendee_phone, ta.attendee_type,
                   ta.rsvp_status, ta.follow_up_required, ta.post_event_interest_level,
                   ta.potential_order_value_ore, ta.active, ta.created_at, ta.updated_at
            FROM tasting_attendees ta
            LEFT JOIN wine_tastings wt ON ta.tasting_id = wt.id
            LEFT JOIN customers c ON ta.customer_id = c.id
            WHERE ta.active = true
            ORDER BY wt.event_date DESC, ta.attendee_name
        """
        )

        columns = [
            "id",
            "tasting_id",
            "event_name",
            "customer_id",
            "customer_name",
            "attendee_name",
            "attendee_email",
            "attendee_phone",
            "attendee_type",
            "rsvp_status",
            "follow_up_required",
            "post_event_interest_level",
            "potential_order_value_ore",
            "active",
            "created_at",
            "updated_at",
        ]

        attendees = []
        for row in cursor.fetchall():
            attendee = {}
            for i, col in enumerate(columns):
                value = row[i]
                if isinstance(value, (datetime, date)):
                    attendee[col] = value.isoformat()
                else:
                    attendee[col] = value
            attendees.append(attendee)

        cursor.close()
        conn.close()

        return {"tasting_attendees": attendees}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@app.get("/db/tasting-outcomes")
async def list_tasting_outcomes():
    """List all tasting outcomes with ROI analysis"""
    try:
        db_config = get_database_config()

        conn_params = {
            "host": db_config["host"],
            "port": int(db_config["port"]),
            "database": db_config["name"],
            "user": db_config["username"],
            "password": db_config["password"],
        }

        conn = pg8000.connect(**conn_params)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT to_.id, to_.tasting_id, wt.event_name, to_.customer_id, c.name as customer_name,
                   to_.outcome_type, to_.outcome_value_ore, to_.outcome_date, to_.notes,
                   wt.total_event_cost_ore, wt.event_date,
                   to_.active, to_.created_at, to_.updated_at
            FROM tasting_outcomes to_
            LEFT JOIN wine_tastings wt ON to_.tasting_id = wt.id
            LEFT JOIN customers c ON to_.customer_id = c.id
            WHERE to_.active = true
            ORDER BY to_.outcome_date DESC, to_.outcome_value_ore DESC
        """
        )

        columns = [
            "id",
            "tasting_id",
            "event_name",
            "customer_id",
            "customer_name",
            "outcome_type",
            "outcome_value_ore",
            "outcome_date",
            "notes",
            "total_event_cost_ore",
            "event_date",
            "active",
            "created_at",
            "updated_at",
        ]

        outcomes = []
        for row in cursor.fetchall():
            outcome = {}
            for i, col in enumerate(columns):
                value = row[i]
                if isinstance(value, (datetime, date)):
                    outcome[col] = value.isoformat()
                else:
                    outcome[col] = value
            outcomes.append(outcome)

        cursor.close()
        conn.close()

        return {"tasting_outcomes": outcomes}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


# AWS Lambda handler
handler = Mangum(app)
