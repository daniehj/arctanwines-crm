import json
import os
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
    """Get SSM parameter with detailed error handling"""
    env, env_info = get_environment()
    
    # Try environment-specific parameter first
    env_param = f"/arctan-wines/{env}/{parameter_name}"
    try:
        response = ssm_client.get_parameter(Name=env_param, WithDecryption=True)
        return response['Parameter']['Value']
    except Exception as e1:
        # Try generic parameter
        generic_param = f"/arctan-wines/{parameter_name}"
        try:
            response = ssm_client.get_parameter(Name=generic_param, WithDecryption=True)
            return response['Parameter']['Value']
        except Exception as e2:
            # Try environment variable fallback
            env_var = parameter_name.upper().replace('-', '_').replace('/', '_')
            env_value = os.environ.get(env_var)
            if env_value:
                return env_value
            
            # Return detailed error
            raise Exception(f"Parameter {parameter_name} not found. Tried: {env_param} ({str(e1)}), {generic_param} ({str(e2)}), env var {env_var} (not set). Environment: {env}, Info: {env_info}")

def get_database_password():
    """Get database password from Secrets Manager"""
    # Known Secrets Manager ARN from the setup
    secret_arn = "arn:aws:secretsmanager:eu-west-1:390402552152:secret:rds!cluster-4c0ddb25-674d-4999-bf55-471ded9ed31a-5ehyNh"
    
    try:
        response = secrets_client.get_secret_value(SecretId=secret_arn)
        secret = json.loads(response['SecretString'])
        return secret.get('password')
    except Exception as e:
        # Fallback to SSM parameter
        try:
            return get_ssm_parameter("database/password")
        except Exception as e2:
            raise Exception(f"Could not get database password from Secrets Manager ({str(e)}) or SSM ({str(e2)})")

def init_database():
    """Initialize database with detailed error reporting"""
    global engine, SessionLocal
    
    if engine is None:
        try:
            db_host = get_ssm_parameter("database/host")
            db_port = get_ssm_parameter("database/port") or "5432"
            db_name = get_ssm_parameter("database/name")
            db_user = get_ssm_parameter("database/user")
            db_password = get_database_password()
            
            if not all([db_host, db_name, db_user, db_password]):
                missing = []
                if not db_host: missing.append("host")
                if not db_name: missing.append("name")
                if not db_user: missing.append("user")
                if not db_password: missing.append("password")
                raise Exception(f"Missing database configuration: {', '.join(missing)}")
            
            database_url = f"postgresql+pg8000://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
            engine = create_engine(database_url, echo=False)
            SessionLocal = sessionmaker(bind=engine)
            
        except Exception as e:
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
    test_params = ["database/host", "database/port", "database/name", "database/user"]
    
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

@app.get("/db-test")
def db_test():
    try:
        init_database()
        db = SessionLocal()
        result = db.execute(text("SELECT 1")).scalar()
        db.close()
        env, env_info = get_environment()
        return {
            "status": "database connected", 
            "result": result,
            "environment": env
        }
    except Exception as e:
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

# AWS Lambda handler
handler = Mangum(app) 