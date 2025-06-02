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

# Database globals
engine = None
SessionLocal = None

def get_environment():
    """Determine environment"""
    amplify_env = os.environ.get('AMPLIFY_ENV', '')
    aws_branch = os.environ.get('AWS_BRANCH', '')
    function_name = os.environ.get('AWS_LAMBDA_FUNCTION_NAME', '')
    
    if ('sandbox' in amplify_env.lower() or 
        aws_branch in ['dev', 'test', 'sandbox'] or 
        'sandbox' in function_name.lower() or 
        'test' in function_name.lower()):
        return 'test'
    return 'prod'

def get_ssm_parameter(parameter_name):
    """Get SSM parameter"""
    env = get_environment()
    
    try:
        env_param = f"/arctan-wines/{env}/{parameter_name}"
        response = ssm_client.get_parameter(Name=env_param, WithDecryption=True)
        return response['Parameter']['Value']
    except:
        try:
            generic_param = f"/arctan-wines/{parameter_name}"
            response = ssm_client.get_parameter(Name=generic_param, WithDecryption=True)
            return response['Parameter']['Value']
        except:
            env_var = parameter_name.upper().replace('-', '_')
            return os.environ.get(env_var)

def init_database():
    """Initialize database"""
    global engine, SessionLocal
    
    if engine is None:
        db_host = get_ssm_parameter("database/host")
        db_port = get_ssm_parameter("database/port") or "5432"
        db_name = get_ssm_parameter("database/name")
        db_user = get_ssm_parameter("database/user")
        db_password = get_ssm_parameter("database/password")
        
        if not all([db_host, db_name, db_user, db_password]):
            raise Exception("Missing database configuration")
        
        database_url = f"postgresql+pg8000://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
        engine = create_engine(database_url, echo=False)
        SessionLocal = sessionmaker(bind=engine)

@app.get("/health")
def health_check():
    return {
        "status": "healthy", 
        "service": "arctan-wines-api",
        "environment": get_environment()
    }

@app.get("/db-test")
def db_test():
    try:
        init_database()
        db = SessionLocal()
        result = db.execute(text("SELECT 1")).scalar()
        db.close()
        return {
            "status": "database connected", 
            "result": result,
            "environment": get_environment()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@app.get("/api/v1/test")
def test_endpoint():
    return {
        "message": "API test successful",
        "environment": get_environment(),
        "lambda_function": os.environ.get('AWS_LAMBDA_FUNCTION_NAME')
    }

# AWS Lambda handler
handler = Mangum(app) 