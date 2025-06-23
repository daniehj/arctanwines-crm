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
ssm_client = boto3.client('ssm')
secrets_client = boto3.client('secretsmanager')

# Database globals
engine = None
SessionLocal = None

def get_environment():
    """Determine environment"""
    amplify_env = os.environ.get('AMPLIFY_ENV', '')
    aws_branch = os.environ.get('AWS_BRANCH', '')
    function_name = os.environ.get('AWS_LAMBDA_FUNCTION_NAME', '')
    
    # Debug info
    env_info = {
        'amplify_env': amplify_env,
        'aws_branch': aws_branch,
        'function_name': function_name
    }
    
    if ('sandbox' in amplify_env.lower() or 
        aws_branch in ['dev', 'test', 'sandbox'] or 
        'sandbox' in function_name.lower() or 
        'test' in function_name.lower()):
        return 'test', env_info
    return 'prod', env_info

def get_ssm_parameter(parameter_name):
    """Get SSM parameter with fallback logic"""
    env, env_info = get_environment()
    
    # First try environment variables
    env_var_map = {
        "database/host": "DATABASE_HOST",
        "database/port": "DATABASE_PORT", 
        "database/name": "DATABASE_NAME",
        "database/username": "DATABASE_USERNAME",
        "database/password": "DATABASE_PASSWORD"
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
            f"/amplify/{parameter_name}"
        ]
        
        for path in paths_to_try:
            try:
                response = ssm_client.get_parameter(Name=path, WithDecryption=True)
                return response['Parameter']['Value']
            except:
                continue
        
        raise Exception(f"Parameter {parameter_name} not found in any SSM path")
        
    except Exception as e:
        # Final fallback to environment variable
        env_var = parameter_name.upper().replace('-', '_').replace('/', '_')
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
                missing = [k for k, v in {
                    "host": db_host, "name": db_name, 
                    "username": db_user, "password": db_password
                }.items() if not v]
                raise Exception(f"Missing database config: {', '.join(missing)}")
            
            print(f"[{time.time()}] Connecting to: {db_host}:{db_port}/{db_name}")
            
            database_url = f"postgresql+pg8000://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
            
            engine = create_engine(
                database_url, 
                echo=False,
                pool_timeout=10,
                pool_recycle=300,
                pool_pre_ping=True,
                connect_args={"timeout": 10}
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

@app.get("/")
def root():
    """Root endpoint"""
    return {"message": "Arctan Wines CRM API", "status": "online", "timestamp": time.time()}

@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "environment": get_environment(),
        "version": "1.0.0"
    }

@app.get("/config-debug")
def config_debug():
    """Debug configuration and environment"""
    env, env_info = get_environment()
    
    return {
        "environment": env,
        "env_info": env_info,
        "aws_region": os.environ.get('AWS_REGION', 'not-set'),
        "function_name": os.environ.get('AWS_LAMBDA_FUNCTION_NAME', 'not-set'),
        "timestamp": time.time()
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
            req = urllib.request.Request('http://169.254.169.254/latest/meta-data/instance-id')
            req.add_header('User-Agent', 'lambda-vpc-info')
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
                "VPC_ID": os.environ.get('VPC_ID', 'not-set'),
                "SUBNET_IDS": os.environ.get('SUBNET_IDS', 'not-set'),
                "SECURITY_GROUP_IDS": os.environ.get('SECURITY_GROUP_IDS', 'not-set'),
                "AWS_LAMBDA_FUNCTION_NAME": os.environ.get('AWS_LAMBDA_FUNCTION_NAME', 'not-set'),
                "AWS_REGION": os.environ.get('AWS_REGION', 'not-set')
            },
            "timestamp": time.time()
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "timestamp": time.time()
        }

@app.get("/dns-test")
def dns_test():
    """Test DNS resolution capabilities"""
    import socket
    
    test_hosts = [
        "google.com",
        "amazonaws.com", 
        "rds.amazonaws.com",
        "secretsmanager.eu-west-1.amazonaws.com",
        "ssm.eu-west-1.amazonaws.com"
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
                "duration_ms": round(duration * 1000, 2)
            }
        except Exception as e:
            results[host] = {
                "status": "error", 
                "error": str(e)
            }
    
    return {
        "status": "success",
        "dns_tests": results,
        "timestamp": time.time()
    }

@app.get("/network-test")
def network_test():
    """Test network connectivity to AWS services (avoiding external timeouts)"""
    import socket
    
    # Test AWS services only (these should be reachable via VPC endpoints)
    test_hosts = [
        ("ssm.eu-west-1.amazonaws.com", 443),
        ("secretsmanager.eu-west-1.amazonaws.com", 443),
        ("lambda.eu-west-1.amazonaws.com", 443),
        ("dynamodb.eu-west-1.amazonaws.com", 443)
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
                "duration_ms": round(duration * 1000, 2)
            }
        except Exception as e:
            results[f"{host}:{port}"] = {
                "status": "error", 
                "error": str(e)
            }
    
    return {
        "status": "success",
        "network_tests": results,
        "note": "Testing AWS service connectivity only (external URLs skipped to avoid VPC timeouts)",
        "timestamp": time.time()
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
            result = sock.connect_ex(('ssm.eu-west-1.amazonaws.com', 443))
            duration = time.time() - start_time
            sock.close()
            
            aws_tests['ssm'] = {
                "status": "success" if result == 0 else "failed",
                "result_code": result,
                "duration_ms": round(duration * 1000, 2)
            }
        except Exception as e:
            aws_tests['ssm'] = {"status": "error", "error": str(e)}
        
        # Test Secrets Manager endpoint  
        try:
            start_time = time.time()
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            result = sock.connect_ex(('secretsmanager.eu-west-1.amazonaws.com', 443))
            duration = time.time() - start_time
            sock.close()
            
            aws_tests['secrets_manager'] = {
                "status": "success" if result == 0 else "failed",
                "result_code": result,
                "duration_ms": round(duration * 1000, 2)
            }
        except Exception as e:
            aws_tests['secrets_manager'] = {"status": "error", "error": str(e)}
        
        # Test basic HTTP connectivity
        try:
            start_time = time.time()
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            result = sock.connect_ex(('google.com', 80))
            duration = time.time() - start_time
            sock.close()
            
            aws_tests['internet'] = {
                "status": "success" if result == 0 else "failed",
                "result_code": result,
                "duration_ms": round(duration * 1000, 2)
            }
        except Exception as e:
            aws_tests['internet'] = {"status": "error", "error": str(e)}
        
        return {
            "status": "success",
            "simple_network_tests": aws_tests,
            "timestamp": time.time()
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "timestamp": time.time()
        }

@app.get("/api/v1/test")
def test_endpoint():
    """Test endpoint for API functionality"""
    return {
        "message": "API is working correctly",
        "timestamp": time.time(),
        "version": "1.0.0"
    }

@app.get("/env-debug")
def env_debug():
    """Debug environment variables (filtered for security)"""
    env_vars = {}
    
    # Safe environment variables to display
    safe_vars = [
        'AWS_REGION', 'AWS_LAMBDA_FUNCTION_NAME', 'AWS_LAMBDA_FUNCTION_VERSION',
        'AWS_LAMBDA_LOG_GROUP_NAME', 'AWS_LAMBDA_LOG_STREAM_NAME',
        'AWS_EXECUTION_ENV', 'AWS_LAMBDA_RUNTIME_API', 'AWS_LAMBDA_INITIALIZATION_TYPE',
        'AMPLIFY_ENV', 'AWS_BRANCH', 'LAMBDA_TASK_ROOT', 'LAMBDA_RUNTIME_DIR',
        'PATH', 'PWD', 'LANG', 'TZ'
    ]
    
    for var in safe_vars:
        env_vars[var] = os.environ.get(var, 'not-set')
    
    # Count total environment variables
    total_env_vars = len(os.environ)
    
    return {
        "status": "success",
        "safe_environment_variables": env_vars,
        "total_env_var_count": total_env_vars,
        "timestamp": time.time()
    }

@app.get("/status")
def status():
    """Simple status endpoint with no external dependencies"""
    return {
        "status": "online",
        "service": "arctanwines-crm-api",
        "timestamp": time.time(),
        "environment": get_environment(),
        "lambda_function": os.environ.get('AWS_LAMBDA_FUNCTION_NAME', 'unknown'),
        "aws_region": os.environ.get('AWS_REGION', 'unknown')
    }

@app.get("/db/test")
def test_database():
    """Test database connection"""
    try:
        db = get_db_session()
        result = db.execute(text("SELECT 1 as test")).scalar()
        db.close()
        
        return {
            "status": "success",
            "database_test": result,
            "timestamp": time.time()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database test failed: {str(e)}")

@app.get("/db/wine-batches")
def list_wine_batches():
    """List all wine batches"""
    try:
        db = get_db_session()
        
        # Simple raw SQL query to avoid complex ORM setup
        result = db.execute(text("""
            SELECT id, batch_number, wine_name, producer, total_bottles, 
                   status, total_cost_nok_ore, target_price_nok_ore, 
                   created_at, updated_at
            FROM wine_batches 
            ORDER BY created_at DESC
        """))
        
        batches = []
        for row in result:
            batches.append({
                "id": str(row.id),
                "batch_number": row.batch_number,
                "wine_name": row.wine_name,
                "producer": row.producer,
                "total_bottles": row.total_bottles,
                "status": row.status,
                "total_cost_nok_ore": row.total_cost_nok_ore,
                "target_price_nok_ore": row.target_price_nok_ore,
                "created_at": row.created_at.isoformat() if row.created_at else None,
                "updated_at": row.updated_at.isoformat() if row.updated_at else None
            })
        
        db.close()
        
        return {
            "status": "success",
            "count": len(batches),
            "batches": batches
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch wine batches: {str(e)}")

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
                raise HTTPException(status_code=400, detail=f"Missing required field: {field}")
        
        db = get_db_session()
        
        # Check if batch number already exists
        existing = db.execute(text(
            "SELECT id FROM wine_batches WHERE batch_number = :batch_number"
        ), {"batch_number": body["batch_number"]}).fetchone()
        
        if existing:
            db.close()
            raise HTTPException(status_code=400, detail=f"Batch number {body['batch_number']} already exists")
        
        # Insert new batch using raw SQL
        batch_id = str(uuid.uuid4())
        
        db.execute(text("""
            INSERT INTO wine_batches 
            (id, batch_number, wine_name, producer, total_bottles, status, 
             total_cost_nok_ore, target_price_nok_ore, created_at, updated_at)
            VALUES (:id, :batch_number, :wine_name, :producer, :total_bottles, :status,
                    :total_cost_nok_ore, :target_price_nok_ore, NOW(), NOW())
        """), {
            "id": batch_id,
            "batch_number": body["batch_number"],
            "wine_name": body["wine_name"],
            "producer": body["producer"],
            "total_bottles": int(body["total_bottles"]),
            "status": "ORDERED",
            "total_cost_nok_ore": int(body.get("total_cost_nok_ore", 0)),
            "target_price_nok_ore": int(body.get("target_price_nok_ore", 0))
        })
        
        db.commit()
        
        # Fetch the created batch
        created = db.execute(text("""
            SELECT id, batch_number, wine_name, producer, total_bottles, 
                   status, total_cost_nok_ore, target_price_nok_ore, created_at
            FROM wine_batches WHERE id = :id
        """), {"id": batch_id}).fetchone()
        
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
                "created_at": created.created_at.isoformat() if created.created_at else None
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create wine batch: {str(e)}")

@app.post("/db/migrate")
def run_migrations():
    """Run database migrations"""
    try:
        # Try to create the wine_batches table manually as a fallback
        db = get_db_session()
        
        # Check if table exists
        table_exists = db.execute(text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'wine_batches'
            );
        """)).scalar()
        
        if not table_exists:
            print("Creating wine_batches table...")
            
            # Create the table manually (based on our migration)
            db.execute(text("""
                CREATE TABLE wine_batches (
                    id VARCHAR(36) PRIMARY KEY,
                    batch_number VARCHAR(50) NOT NULL UNIQUE,
                    wine_name VARCHAR(200) NOT NULL,
                    producer VARCHAR(200) NOT NULL,
                    total_bottles INTEGER NOT NULL,
                    status VARCHAR(20) NOT NULL DEFAULT 'ORDERED',
                    total_cost_nok_ore INTEGER NOT NULL DEFAULT 0,
                    target_price_nok_ore INTEGER,
                    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
                );
            """))
            
            # Create indexes
            db.execute(text("""
                CREATE INDEX idx_wine_batch_status ON wine_batches(status);
                CREATE UNIQUE INDEX ix_wine_batches_batch_number ON wine_batches(batch_number);
                CREATE INDEX ix_wine_batches_wine_name ON wine_batches(wine_name);
            """))
            
            db.commit()
            print("wine_batches table created successfully")
            
            db.close()
            
            return {
                "status": "success",
                "message": "Database migrations completed - wine_batches table created",
                "table_created": True
            }
        else:
            db.close()
            return {
                "status": "success", 
                "message": "Database is up to date - wine_batches table already exists",
                "table_created": False
            }
            
    except Exception as e:
        print(f"Migration failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Migration failed: {str(e)}")

# AWS Lambda handler
handler = Mangum(app) 