import json
import os
from typing import Optional, AsyncGenerator
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum
import jwt
import boto3
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
import asyncio

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

async def get_ssm_parameter(parameter_name: str) -> str:
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

async def init_database():
    """Initialize database connection"""
    global engine, SessionLocal
    
    if engine is None:
        # Get database configuration from SSM (environment-aware)
        db_host = await get_ssm_parameter("db-host")
        db_port = await get_ssm_parameter("db-port") or "5432"
        db_name = await get_ssm_parameter("db-name")
        db_user = await get_ssm_parameter("db-user")
        db_password = await get_ssm_parameter("db-password")
        
        if not all([db_host, db_name, db_user, db_password]):
            raise Exception("Missing required database configuration parameters")
        
        # Create async database URL
        database_url = f"postgresql+asyncpg://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
        
        engine = create_async_engine(database_url, echo=False)
        SessionLocal = async_sessionmaker(
            bind=engine,
            class_=AsyncSession,
            expire_on_commit=False
        )

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Database dependency"""
    await init_database()
    async with SessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

async def get_cognito_config():
    """Get Cognito configuration from SSM or environment"""
    user_pool_id = (
        await get_ssm_parameter("cognito-user-pool-id") or 
        os.environ.get('AMPLIFY_AUTH_USERPOOL_ID')
    )
    app_client_id = (
        await get_ssm_parameter("cognito-app-client-id") or 
        os.environ.get('AMPLIFY_AUTH_USERPOOL_WEB_CLIENT_ID')
    )
    return user_pool_id, app_client_id

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
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
async def health_check():
    env = get_environment()
    return {
        "status": "healthy", 
        "service": "arctan-wines-api",
        "environment": env
    }

# Database test endpoint
@app.get("/db-test")
async def db_test(db: AsyncSession = Depends(get_db)):
    try:
        # Test database connection
        result = await db.execute("SELECT 1")
        env = get_environment()
        return {
            "status": "database connected", 
            "result": result.scalar(),
            "environment": env
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database connection failed: {str(e)}"
        )

# Test protected endpoint
@app.get("/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    return {
        "user": current_user,
        "message": "Authentication successful",
        "environment": get_environment()
    }

# API v1 routes will be added here
@app.get("/api/v1/test")
async def test_endpoint(current_user: dict = Depends(get_current_user)):
    return {
        "message": "API v1 is working",
        "user": current_user['email'],
        "role": current_user.get('role'),
        "environment": get_environment()
    }

# Configuration endpoint
@app.get("/api/v1/config")
async def get_config(current_user: dict = Depends(get_current_user)):
    """Get configuration information for debugging"""
    user_pool_id, app_client_id = await get_cognito_config()
    env = get_environment()
    return {
        "environment": env,
        "cognito_user_pool_id": user_pool_id,
        "cognito_app_client_id": app_client_id,
        "aws_region": os.environ.get('AWS_REGION'),
        "amplify_env": os.environ.get('AMPLIFY_ENV'),
        "aws_branch": os.environ.get('AWS_BRANCH'),
        "function_name": os.environ.get('AWS_LAMBDA_FUNCTION_NAME'),
        "user": current_user
    }

# Lambda handler
handler = Mangum(app) 