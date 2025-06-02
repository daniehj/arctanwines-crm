import json
import os
from typing import Optional, Generator
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum
import jwt
import boto3
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session, declarative_base

# Initialize FastAPI app
app = FastAPI(
    title="Arctan Wines CRM API",
    description="Wine Import CRM API with Fiken integration",
    version="1.0.0"
)

# CORS configuration for Amplify frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://*.amplifyapp.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# JWT Bearer token authentication
security = HTTPBearer()

# AWS clients
ssm_client = boto3.client('ssm')

# Database setup
Base = declarative_base()
engine = None
SessionLocal = None

def get_environment() -> str:
    """
    Determine the current environment (sandbox/test vs production)
    """
    # Check for Amplify environment indicators
    amplify_env = os.environ.get('AMPLIFY_ENV')
    aws_branch = os.environ.get('AWS_BRANCH')
    stack_name = os.environ.get('AWS_LAMBDA_FUNCTION_NAME', '')
    
    # Sandbox/test environment detection
    if (amplify_env and 'sandbox' in amplify_env.lower()) or \
       (aws_branch and aws_branch in ['dev', 'test', 'sandbox']) or \
       ('sandbox' in stack_name.lower()) or \
       ('test' in stack_name.lower()):
        return 'test'
    
    # Default to production
    return 'prod'

def get_ssm_parameter(parameter_name: str) -> str:
    """Get parameter from AWS SSM Parameter Store with environment awareness"""
    env = get_environment()
    
    try:
        # Try environment-specific parameter first
        env_parameter_name = f"/arctan-wines/{env}/{parameter_name}"
        response = ssm_client.get_parameter(
            Name=env_parameter_name,
            WithDecryption=True
        )
        return response['Parameter']['Value']
    except ssm_client.exceptions.ParameterNotFound:
        try:
            # Fallback to generic parameter
            generic_parameter_name = f"/arctan-wines/{parameter_name}"
            response = ssm_client.get_parameter(
                Name=generic_parameter_name,
                WithDecryption=True
            )
            return response['Parameter']['Value']
        except Exception as e:
            # Final fallback to environment variables for local development
            env_var_name = f"{parameter_name.upper().replace('-', '_')}"
            return os.environ.get(env_var_name)
    except Exception as e:
        # Fallback to environment variables for local development
        env_var_name = f"{parameter_name.upper().replace('-', '_')}"
        return os.environ.get(env_var_name)

def init_database():
    """Initialize database connection"""
    global engine, SessionLocal
    
    if engine is None:
        # Get database configuration from SSM (environment-aware)
        db_host = get_ssm_parameter("database/host")
        db_port = get_ssm_parameter("database/port") or "5432"
        db_name = get_ssm_parameter("database/name")
        db_user = get_ssm_parameter("database/user")
        db_password = get_ssm_parameter("database/password")
        
        if not all([db_host, db_name, db_user, db_password]):
            raise Exception("Missing required database configuration parameters")
        
        # Create database URL using pg8000 (pure Python PostgreSQL driver)
        database_url = f"postgresql+pg8000://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
        
        engine = create_engine(database_url, echo=False)
        SessionLocal = sessionmaker(bind=engine)

def get_db() -> Generator[Session, None, None]:
    """Database dependency"""
    init_database()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_cognito_config():
    """Get Cognito configuration from SSM or environment"""
    user_pool_id = (
        get_ssm_parameter("cognito-user-pool-id") or 
        os.environ.get('AMPLIFY_AUTH_USERPOOL_ID')
    )
    app_client_id = (
        get_ssm_parameter("cognito-app-client-id") or 
        os.environ.get('AMPLIFY_AUTH_USERPOOL_WEB_CLIENT_ID')
    )
    return user_pool_id, app_client_id

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    Validate JWT token from Cognito and extract user information
    """
    token = credentials.credentials
    
    try:
        # In production, you'd want to verify the JWT signature
        # For now, we'll decode without verification (development only)
        payload = jwt.decode(token, options={"verify_signature": False})
        
        user_id = payload.get('sub')
        email = payload.get('email')
        custom_role = payload.get('custom:role')
        custom_company = payload.get('custom:company')
        
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
        
        return {
            'user_id': user_id,
            'email': email,
            'role': custom_role,
            'company': custom_company
        }
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )

# Health check endpoint
@app.get("/health")
def health_check():
    env = get_environment()
    return {
        "status": "healthy", 
        "service": "arctan-wines-api",
        "environment": env
    }

# Database test endpoint
@app.get("/db-test")
def db_test(db: Session = Depends(get_db)):
    try:
        # Test database connection
        result = db.execute(text("SELECT 1")).scalar()
        env = get_environment()
        return {
            "status": "database connected", 
            "result": result,
            "environment": env
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database connection failed: {str(e)}"
        )

# Test protected endpoint
@app.get("/me")
def get_me(current_user: dict = Depends(get_current_user)):
    """Get current user information"""
    return {
        "message": "Authentication successful",
        "user": current_user,
        "environment": get_environment()
    }

# Users endpoints (placeholder for testing)
@app.get("/api/v1/users")
def get_users(current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get list of users - placeholder endpoint"""
    return {
        "users": [],
        "message": "Users endpoint working",
        "environment": get_environment(),
        "authenticated_user": current_user['email']
    }

@app.get("/api/v1/users/{user_id}")
def get_user(user_id: str, current_user: dict = Depends(get_current_user)):
    """Get specific user - placeholder endpoint"""
    return {
        "user_id": user_id,
        "message": f"User {user_id} endpoint working",
        "environment": get_environment(),
        "authenticated_user": current_user['email']
    }

# Test endpoint (no auth required)
@app.get("/api/v1/test")
def test_endpoint():
    """Test endpoint without authentication"""
    return {
        "message": "Test endpoint working",
        "environment": get_environment(),
        "status": "success"
    }

# Configuration endpoint
@app.get("/api/v1/config")
def get_config(current_user: dict = Depends(get_current_user)):
    """Get API configuration"""
    return {
        "environment": get_environment(),
        "user": current_user,
        "message": "Configuration retrieved successfully"
    }

# Lambda handler
handler = Mangum(app) 