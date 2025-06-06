import json
import os
import time
import socket
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum
import boto3
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

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
    """Get SSM parameter with detailed error handling and environment variable fallback"""
    env, env_info = get_environment()
    
    # First try environment variables (for VPC scenarios without internet access)
    env_var_map = {
        "database/host": "DATABASE_HOST",
        "database/port": "DATABASE_PORT", 
        "database/name": "DATABASE_NAME",
        "database/username": "DATABASE_USERNAME"
    }
    
    if parameter_name in env_var_map:
        env_value = os.environ.get(env_var_map[parameter_name])
        if env_value:
            print(f"Using environment variable {env_var_map[parameter_name]} for {parameter_name}")
            return env_value
    
    # If no environment variable, try SSM
    try:
        # Try environment-specific parameter first with correct Amplify + project prefix
        env_param = f"/amplify/arctanwines/{env}/{parameter_name}"
        try:
            response = ssm_client.get_parameter(Name=env_param, WithDecryption=True)
            return response['Parameter']['Value']
        except Exception as e1:
            # Try generic parameter with Amplify + project prefix
            generic_param = f"/amplify/arctanwines/{parameter_name}"
            try:
                response = ssm_client.get_parameter(Name=generic_param, WithDecryption=True)
                return response['Parameter']['Value']
            except Exception as e2:
                # Try with hyphen fallback
                env_hyphen_param = f"/amplify/arctan-wines/{env}/{parameter_name}"
                try:
                    response = ssm_client.get_parameter(Name=env_hyphen_param, WithDecryption=True)
                    return response['Parameter']['Value']
                except Exception as e3:
                    generic_hyphen_param = f"/amplify/arctan-wines/{parameter_name}"
                    try:
                        response = ssm_client.get_parameter(Name=generic_hyphen_param, WithDecryption=True)
                        return response['Parameter']['Value']
                    except Exception as e4:
                        # Try just Amplify prefix as fallback
                        amplify_env_param = f"/amplify/{env}/{parameter_name}"
                        try:
                            response = ssm_client.get_parameter(Name=amplify_env_param, WithDecryption=True)
                            return response['Parameter']['Value']
                        except Exception as e5:
                            amplify_generic_param = f"/amplify/{parameter_name}"
                            try:
                                response = ssm_client.get_parameter(Name=amplify_generic_param, WithDecryption=True)
                                return response['Parameter']['Value']
                            except Exception as e6:
                                # Try old arctan-wines paths as fallback
                                old_env_param = f"/arctan-wines/{env}/{parameter_name}"
                                try:
                                    response = ssm_client.get_parameter(Name=old_env_param, WithDecryption=True)
                                    return response['Parameter']['Value']
                                except Exception as e7:
                                    old_generic_param = f"/arctan-wines/{parameter_name}"
                                    try:
                                        response = ssm_client.get_parameter(Name=old_generic_param, WithDecryption=True)
                                        return response['Parameter']['Value']
                                    except Exception as e8:
                                        # Final fallback to environment variable (if not already checked)
                                        env_var = parameter_name.upper().replace('-', '_').replace('/', '_')
                                        env_value = os.environ.get(env_var)
                                        if env_value:
                                            return env_value
                                        
                                        # Return detailed error
                                        raise Exception(f"Parameter {parameter_name} not found. Tried: {env_param} ({str(e1)}), {generic_param} ({str(e2)}), {env_hyphen_param} ({str(e3)}), {generic_hyphen_param} ({str(e4)}), {amplify_env_param} ({str(e5)}), {amplify_generic_param} ({str(e6)}), {old_env_param} ({str(e7)}), {old_generic_param} ({str(e8)}), env var {env_var} (not set). Environment: {env}, Info: {env_info}")
    except Exception as outer_e:
        # If SSM client itself fails (e.g., no internet access in VPC), try environment variables
        env_var = parameter_name.upper().replace('-', '_').replace('/', '_')
        env_value = os.environ.get(env_var)
        if env_value:
            print(f"SSM failed ({str(outer_e)}), using environment variable {env_var} for {parameter_name}")
            return env_value
        
        raise Exception(f"Could not access SSM ({str(outer_e)}) and no environment variable {env_var} set for {parameter_name}")

def get_database_password():
    """Get database password and username from Secrets Manager with SSM parameter fallback"""
    
    # Try environment variable with Secrets Manager ARN first (for backwards compatibility)
    password_secret_arn = os.environ.get("DATABASE_PASSWORD_SECRET")
    if password_secret_arn:
        try:
            print(f"Using Secrets Manager ARN from environment variable: {password_secret_arn}")
            response = secrets_client.get_secret_value(SecretId=password_secret_arn)
            secret = json.loads(response['SecretString'])
            return secret.get('password'), secret.get('username')
        except Exception as e:
            print(f"Failed to get password from environment variable secret ARN: {str(e)}")
    
    # Try to get secret ARN from SSM parameter
    try:
        secret_arn = get_ssm_parameter("database/password_secret_arn")
        print(f"Using Secrets Manager ARN from SSM parameter: {secret_arn}")
        response = secrets_client.get_secret_value(SecretId=secret_arn)
        secret = json.loads(response['SecretString'])
        return secret.get('password'), secret.get('username')
    except Exception as e:
        print(f"Failed to get secret ARN from SSM parameter: {str(e)}")
    
    # Fallback to hardcoded secret ARN (for backwards compatibility)
    secret_arn = "arn:aws:secretsmanager:eu-west-1:390402552152:secret:rds!cluster-4c0ddb25-674d-4999-bf55-471ded9ed31a-5ehyNh"
    
    try:
        print(f"Using fallback hardcoded Secrets Manager ARN: {secret_arn}")
        response = secrets_client.get_secret_value(SecretId=secret_arn)
        secret = json.loads(response['SecretString'])
        return secret.get('password'), secret.get('username')
    except Exception as e:
        # Final fallback to SSM parameter for password directly
        try:
            print(f"Failed with secret ARN, trying direct password from SSM: {str(e)}")
            password = get_ssm_parameter("database/password")
            username = get_ssm_parameter("database/username")
            return password, username
        except Exception as e2:
            raise Exception(f"Could not get database password from Secrets Manager ({str(e)}) or SSM ({str(e2)})")

def init_database():
    """Initialize database using SSM Parameter Store (preferred) with Secrets Manager fallback"""
    global engine, SessionLocal
    
    if engine is None:
        try:
            print(f"[{time.time()}] Starting database initialization...")
            
            # Try pure SSM approach first (preferred)
            try:
                print(f"[{time.time()}] Attempting pure SSM Parameter Store approach...")
                
                db_host = get_ssm_parameter("database/host")
                db_port = get_ssm_parameter("database/port") or "5432"
                db_name = get_ssm_parameter("database/name")
                db_user = get_ssm_parameter("database/username")
                db_password = get_ssm_parameter("database/password")  # SecureString with WithDecryption=True
                
                print(f"[{time.time()}] All SSM parameters retrieved successfully")
                
                if all([db_host, db_name, db_user, db_password]):
                    print(f"[{time.time()}] Using pure SSM Parameter Store configuration")
                    print(f"[{time.time()}] Connecting to: {db_host}:{db_port}/{db_name} as user: {db_user}")
                    print(f"[{time.time()}] Password length: {len(db_password)} characters")
                    
                    database_url = f"postgresql+pg8000://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
                    
                    engine = create_engine(
                        database_url, 
                        echo=False,
                        pool_timeout=10,
                        pool_recycle=300,
                        pool_pre_ping=True,
                        connect_args={
                            "timeout": 10
                        }
                    )
                    
                    SessionLocal = sessionmaker(bind=engine)
                    print(f"[{time.time()}] Database initialization completed successfully using SSM Parameter Store")
                    return
                else:
                    missing = []
                    if not db_host: missing.append("host")
                    if not db_name: missing.append("name")
                    if not db_user: missing.append("username")
                    if not db_password: missing.append("password")
                    print(f"[{time.time()}] Missing SSM parameters: {', '.join(missing)}, falling back to Secrets Manager")
                    
            except Exception as e:
                print(f"[{time.time()}] Pure SSM approach failed: {str(e)}, falling back to Secrets Manager")
            
            # Fallback to mixed SSM + Secrets Manager approach (backwards compatibility)
            print(f"[{time.time()}] Using fallback: SSM parameters + Secrets Manager password...")
            
            print(f"[{time.time()}] Getting SSM parameters...")
            db_host = get_ssm_parameter("database/host")
            db_port = get_ssm_parameter("database/port") or "5432"
            db_name = get_ssm_parameter("database/name")
            print(f"[{time.time()}] SSM parameters retrieved successfully")
            
            print(f"[{time.time()}] Getting database credentials from Secrets Manager...")
            db_password, secret_username = get_database_password()
            
            # Use username from secret if available, otherwise fall back to SSM
            if secret_username:
                print(f"[{time.time()}] Using username from Secrets Manager: {secret_username}")
                db_user = secret_username
            else:
                print(f"[{time.time()}] No username in secret, using SSM parameter...")
                db_user = get_ssm_parameter("database/username")
            
            print(f"[{time.time()}] Database credentials retrieved successfully")
            
            if not all([db_host, db_name, db_user, db_password]):
                missing = []
                if not db_host: missing.append("host")
                if not db_name: missing.append("name")
                if not db_user: missing.append("username")
                if not db_password: missing.append("password")
                raise Exception(f"Missing database configuration: {', '.join(missing)}")
            
            # Log connection details for debugging (without password)
            print(f"[{time.time()}] Attempting database connection to: {db_host}:{db_port}/{db_name} as user: {db_user}")
            
            database_url = f"postgresql+pg8000://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
            
            print(f"[{time.time()}] Creating SQLAlchemy engine...")
            # Use much shorter timeouts to fail fast if there are network issues
            engine = create_engine(
                database_url, 
                echo=False,
                pool_timeout=10,  # Reduced from 30
                pool_recycle=300,
                pool_pre_ping=True,
                connect_args={
                    "timeout": 10  # Reduced from 30
                }
            )
            print(f"[{time.time()}] SQLAlchemy engine created successfully")
            
            SessionLocal = sessionmaker(bind=engine)
            print(f"[{time.time()}] Database initialization completed successfully using fallback method")
            
        except Exception as e:
            print(f"[{time.time()}] Database connection failed with error: {str(e)}")
            raise Exception(f"Database initialization failed: {str(e)}")

@app.get("/health")
def health_check():
    env, env_info = get_environment()
    return {
        "status": "healthy", 
        "service": "arctan-wines-api",
        "environment": env,
        "env_details": env_info
    }

@app.get("/config-debug")
def config_debug():
    """Debug endpoint to check what parameters are available"""
    env, env_info = get_environment()
    
    # Try to get each parameter individually
    params_status = {}
    test_params = ["database/host", "database/port", "database/name", "database/username"]
    
    for param in test_params:
        try:
            value = get_ssm_parameter(param)
            params_status[param] = "✅ Found" if value else "❌ Empty"
        except Exception as e:
            params_status[param] = f"❌ Error: {str(e)}"
    
    # Test Secrets Manager
    try:
        password = get_database_password()
        params_status["database/password"] = "✅ Found in Secrets Manager" if password else "❌ Empty in Secrets Manager"
    except Exception as e:
        params_status["database/password"] = f"❌ Secrets Manager Error: {str(e)}"
    
    return {
        "environment": env,
        "env_details": env_info,
        "parameters": params_status,
        "lambda_function": os.environ.get('AWS_LAMBDA_FUNCTION_NAME'),
        "aws_region": os.environ.get('AWS_REGION')
    }

@app.get("/vpc-info")
def vpc_info():
    """Get VPC and network information from Lambda environment"""
    try:
        print(f"[{time.time()}] Getting VPC information...")
        
        # Try to get metadata service information (works in VPC)
        import urllib.request
        import urllib.error
        
        vpc_info = {
            "timestamp": time.time(),
            "environment_variables": {
                key: value for key, value in os.environ.items() 
                if key.startswith(('AWS_', 'LAMBDA_'))
            }
        }
        
        # Try to get instance metadata (available in VPC-enabled Lambda)
        try:
            metadata_url = "http://169.254.169.254/latest/meta-data/local-ipv4"
            req = urllib.request.Request(metadata_url, headers={'User-Agent': 'lambda-vpc-check'})
            with urllib.request.urlopen(req, timeout=2) as response:
                vpc_info["local_ipv4"] = response.read().decode('utf-8')
        except Exception as e:
            vpc_info["local_ipv4_error"] = str(e)
        
        # Get network interface information if available
        try:
            import subprocess
            result = subprocess.run(['ip', 'addr', 'show'], capture_output=True, text=True, timeout=5)
            vpc_info["network_interfaces"] = result.stdout if result.returncode == 0 else result.stderr
        except Exception as e:
            vpc_info["network_interfaces_error"] = str(e)
        
        print(f"[{time.time()}] VPC information gathered successfully")
        return {
            "status": "vpc info retrieved",
            "info": vpc_info
        }
        
    except Exception as e:
        print(f"[{time.time()}] VPC info failed with error: {str(e)}")
        return {
            "status": "vpc info error",
            "error": str(e),
            "timestamp": time.time()
        }

@app.get("/dns-test")
def dns_test():
    """Test DNS resolution for database host"""
    try:
        print(f"[{time.time()}] Starting DNS resolution test...")
        
        # Get database host from SSM
        db_host = get_ssm_parameter("database/host")
        
        print(f"[{time.time()}] Testing DNS resolution for {db_host}")
        
        start_time = time.time()
        try:
            ip_addresses = socket.gethostbyname_ex(db_host)
            end_time = time.time()
            
            print(f"[{time.time()}] DNS resolution successful")
            return {
                "status": "dns resolved",
                "hostname": db_host,
                "ip_addresses": ip_addresses,
                "resolution_time_ms": round((end_time - start_time) * 1000, 2),
                "timestamp": time.time()
            }
        except socket.gaierror as e:
            end_time = time.time()
            print(f"[{time.time()}] DNS resolution failed: {str(e)}")
            return {
                "status": "dns resolution failed",
                "hostname": db_host,
                "error": str(e),
                "resolution_time_ms": round((end_time - start_time) * 1000, 2),
                "timestamp": time.time()
            }
            
    except Exception as e:
        print(f"[{time.time()}] DNS test failed with error: {str(e)}")
        return {
            "status": "dns test error",
            "error": str(e),
            "timestamp": time.time()
        }

@app.get("/network-test")
def network_test():
    """Test basic network connectivity to database host"""
    
    try:
        print(f"[{time.time()}] Starting network connectivity test...")
        
        # Get database host from SSM
        db_host = get_ssm_parameter("database/host")
        db_port = int(get_ssm_parameter("database/port") or "5432")
        
        print(f"[{time.time()}] Testing network connectivity to {db_host}:{db_port}")
        
        # Test basic socket connection with timeout
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)  # 10 second timeout
        
        start_time = time.time()
        result = sock.connect_ex((db_host, db_port))
        end_time = time.time()
        
        sock.close()
        
        if result == 0:
            print(f"[{time.time()}] Network connectivity test successful")
            return {
                "status": "network accessible",
                "host": db_host,
                "port": db_port,
                "connection_time_ms": round((end_time - start_time) * 1000, 2),
                "timestamp": time.time()
            }
        else:
            print(f"[{time.time()}] Network connectivity test failed with error code: {result}")
            return {
                "status": "network not accessible",
                "host": db_host,
                "port": db_port,
                "error_code": result,
                "connection_time_ms": round((end_time - start_time) * 1000, 2),
                "timestamp": time.time()
            }
            
    except Exception as e:
        print(f"[{time.time()}] Network test failed with error: {str(e)}")
        return {
            "status": "network test error",
            "error": str(e),
            "timestamp": time.time()
        }

@app.get("/network-simple-test")
def network_simple_test():
    """Test basic network connectivity to database host without authentication"""
    
    try:
        print(f"[{time.time()}] Starting simple network connectivity test...")
        
        # Get database host from environment variable (should work now)
        db_host = os.environ.get("DATABASE_HOST")
        db_port = int(os.environ.get("DATABASE_PORT", "5432"))
        
        if not db_host:
            return {
                "status": "configuration error",
                "error": "DATABASE_HOST environment variable not set",
                "timestamp": time.time()
            }
        
        print(f"[{time.time()}] Testing network connectivity to {db_host}:{db_port}")
        
        # Test basic socket connection with timeout
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)  # 10 second timeout
        
        start_time = time.time()
        result = sock.connect_ex((db_host, db_port))
        end_time = time.time()
        
        sock.close()
        
        if result == 0:
            print(f"[{time.time()}] Network connectivity test successful")
            return {
                "status": "network accessible",
                "host": db_host,
                "port": db_port,
                "connection_time_ms": round((end_time - start_time) * 1000, 2),
                "timestamp": time.time()
            }
        else:
            print(f"[{time.time()}] Network connectivity test failed with error code: {result}")
            return {
                "status": "network not accessible",
                "host": db_host,
                "port": db_port,
                "error_code": result,
                "connection_time_ms": round((end_time - start_time) * 1000, 2),
                "timestamp": time.time()
            }
            
    except Exception as e:
        print(f"[{time.time()}] Network simple test failed with error: {str(e)}")
        return {
            "status": "network test error",
            "error": str(e),
            "timestamp": time.time()
        }

@app.get("/db-test")
def db_test():
    try:
        print(f"[{time.time()}] Starting db-test endpoint")
        
        print(f"[{time.time()}] Initializing database...")
        init_database()
        
        print(f"[{time.time()}] Creating database session...")
        db = SessionLocal()
        
        print(f"[{time.time()}] Executing test query...")
        result = db.execute(text("SELECT 1")).scalar()
        
        print(f"[{time.time()}] Closing database session...")
        db.close()
        
        env, env_info = get_environment()
        print(f"[{time.time()}] db-test completed successfully")
        
        return {
            "status": "database connected", 
            "result": result,
            "environment": env,
            "timestamp": time.time()
        }
    except Exception as e:
        print(f"[{time.time()}] db-test failed with error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@app.get("/api/v1/test")
def test_endpoint():
    env, env_info = get_environment()
    return {
        "message": "API test successful",
        "environment": env,
        "env_details": env_info,
        "lambda_function": os.environ.get('AWS_LAMBDA_FUNCTION_NAME')
    }

@app.get("/env-debug")
def env_debug():
    """Debug environment variables and configuration"""
    try:
        env, env_info = get_environment()
        
        # Check database environment variables
        database_env_vars = {
            "DATABASE_HOST": os.environ.get("DATABASE_HOST"),
            "DATABASE_PORT": os.environ.get("DATABASE_PORT"),
            "DATABASE_NAME": os.environ.get("DATABASE_NAME"),
            "DATABASE_USERNAME": os.environ.get("DATABASE_USERNAME"),
            "DATABASE_PASSWORD_SECRET": os.environ.get("DATABASE_PASSWORD_SECRET")
        }
        
        # Check if any are missing or None
        missing_env_vars = [k for k, v in database_env_vars.items() if not v]
        
        return {
            "status": "success",
            "environment": env,
            "env_info": env_info,
            "database_env_vars": database_env_vars,
            "missing_env_vars": missing_env_vars,
            "timestamp": time.time()
        }
    except Exception as e:
        return {"status": "error", "error": str(e), "timestamp": time.time()}

@app.get("/secrets-debug")
def secrets_debug():
    """Debug Secrets Manager credentials to check authentication issue"""
    try:
        print(f"[{time.time()}] Starting secrets debug...")
        
        # Get the secret ARN from environment
        password_secret_arn = os.environ.get("DATABASE_PASSWORD_SECRET")
        if not password_secret_arn:
            return {"error": "DATABASE_PASSWORD_SECRET environment variable not set"}
        
        print(f"[{time.time()}] Using secret ARN: {password_secret_arn}")
        
        # Retrieve the secret
        response = secrets_client.get_secret_value(SecretId=password_secret_arn)
        secret_data = json.loads(response['SecretString'])
        
        # Return non-sensitive information about the secret
        return {
            "status": "success",
            "secret_arn": password_secret_arn,
            "secret_keys": list(secret_data.keys()),
            "username_from_secret": secret_data.get('username', 'NOT_FOUND'),
            "has_password": 'password' in secret_data,
            "password_length": len(secret_data.get('password', '')) if 'password' in secret_data else 0,
            "env_username": os.environ.get("DATABASE_USERNAME"),
            "username_match": secret_data.get('username') == os.environ.get("DATABASE_USERNAME"),
            "timestamp": time.time()
        }
    except Exception as e:
        return {"status": "error", "error": str(e), "timestamp": time.time()}

@app.get("/ssm-vs-secrets-debug")
def ssm_vs_secrets_debug():
    """Compare SSM parameters vs Secrets Manager values"""
    try:
        print(f"[{time.time()}] Starting SSM vs Secrets comparison...")
        
        # Get values from SSM
        ssm_values = {}
        ssm_params = ["database/host", "database/port", "database/name", "database/username", "database/password"]
        
        for param in ssm_params:
            try:
                value = get_ssm_parameter(param)
                ssm_values[param] = {
                    "found": True,
                    "value_length": len(value) if value else 0,
                    "value_preview": value[:20] + "..." if value and len(value) > 20 else value
                }
            except Exception as e:
                ssm_values[param] = {
                    "found": False,
                    "error": str(e)
                }
        
        # Get values from Secrets Manager
        secrets_values = {}
        try:
            password_secret_arn = os.environ.get("DATABASE_PASSWORD_SECRET")
            if password_secret_arn:
                response = secrets_client.get_secret_value(SecretId=password_secret_arn)
                secret_data = json.loads(response['SecretString'])
                
                secrets_values = {
                    "found": True,
                    "keys": list(secret_data.keys()),
                    "username": secret_data.get('username'),
                    "password_length": len(secret_data.get('password', '')) if 'password' in secret_data else 0
                }
            else:
                secrets_values = {"found": False, "error": "No DATABASE_PASSWORD_SECRET env var"}
        except Exception as e:
            secrets_values = {"found": False, "error": str(e)}
        
        return {
            "status": "success",
            "ssm_parameters": ssm_values,
            "secrets_manager": secrets_values,
            "recommendation": "Use SSM for all values if password is stored as SecureString",
            "timestamp": time.time()
        }
    except Exception as e:
        return {"status": "error", "error": str(e), "timestamp": time.time()}

def init_database_pure_ssm():
    """Initialize database using only SSM Parameter Store (including password)"""
    global engine, SessionLocal
    
    if engine is None:
        try:
            print(f"[{time.time()}] Starting pure SSM database initialization...")
            
            print(f"[{time.time()}] Getting all database config from SSM parameters...")
            db_host = get_ssm_parameter("database/host")
            db_port = get_ssm_parameter("database/port") or "5432"
            db_name = get_ssm_parameter("database/name")
            db_user = get_ssm_parameter("database/username")
            db_password = get_ssm_parameter("database/password")  # This should handle SecureString with WithDecryption=True
            print(f"[{time.time()}] All SSM parameters retrieved successfully")
            
            if not all([db_host, db_name, db_user, db_password]):
                missing = []
                if not db_host: missing.append("host")
                if not db_name: missing.append("name")
                if not db_user: missing.append("username")
                if not db_password: missing.append("password")
                raise Exception(f"Missing SSM database configuration: {', '.join(missing)}")
            
            # Log connection details for debugging (without password)
            print(f"[{time.time()}] Attempting database connection to: {db_host}:{db_port}/{db_name} as user: {db_user}")
            print(f"[{time.time()}] Password length: {len(db_password)} characters")
            
            database_url = f"postgresql+pg8000://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
            
            print(f"[{time.time()}] Creating SQLAlchemy engine...")
            # Use much shorter timeouts to fail fast if there are network issues
            engine = create_engine(
                database_url, 
                echo=False,
                pool_timeout=10,  # Reduced from 30
                pool_recycle=300,
                pool_pre_ping=True,
                connect_args={
                    "timeout": 10  # Reduced from 30
                }
            )
            print(f"[{time.time()}] SQLAlchemy engine created successfully")
            
            SessionLocal = sessionmaker(bind=engine)
            print(f"[{time.time()}] Pure SSM database initialization completed successfully")
            
        except Exception as e:
            print(f"[{time.time()}] Pure SSM database connection failed with error: {str(e)}")
            raise Exception(f"Pure SSM database initialization failed: {str(e)}")

@app.get("/db-test-pure-ssm")
def db_test_pure_ssm():
    """Test database connection using only SSM Parameter Store"""
    try:
        print(f"[{time.time()}] Starting db-test-pure-ssm endpoint")
        
        print(f"[{time.time()}] Initializing database with pure SSM...")
        init_database_pure_ssm()
        
        print(f"[{time.time()}] Creating database session...")
        db = SessionLocal()
        
        print(f"[{time.time()}] Executing test query...")
        result = db.execute(text("SELECT 1")).scalar()
        
        print(f"[{time.time()}] Closing database session...")
        db.close()
        
        env, env_info = get_environment()
        print(f"[{time.time()}] db-test-pure-ssm completed successfully")
        
        return {
            "status": "database connected via pure SSM", 
            "result": result,
            "environment": env,
            "method": "SSM Parameter Store only",
            "timestamp": time.time()
        }
    except Exception as e:
        print(f"[{time.time()}] db-test-pure-ssm failed with error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Pure SSM Database error: {str(e)}")

# AWS Lambda handler
handler = Mangum(app) 