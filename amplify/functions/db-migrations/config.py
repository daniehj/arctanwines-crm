"""
Database configuration for Arctan Wines CRM
Uses SSM Parameter Store for environment-aware configuration
"""
import os
import boto3
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from typing import Tuple, Dict, Any

def get_environment() -> Tuple[str, Dict[str, Any]]:
    """Determine environment based on AWS Lambda context"""
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

def get_ssm_parameter(parameter_name: str) -> str:
    """Get SSM parameter with detailed error handling"""
    ssm_client = boto3.client('ssm')
    env, env_info = get_environment()
    
    # Try environment-specific parameter first with correct Amplify + project prefix
    try:
        env_param = f"/amplify/arctanwines/{env}/{parameter_name}"
        response = ssm_client.get_parameter(Name=env_param, WithDecryption=True)
        return response['Parameter']['Value']
    except Exception as e1:
        # Try generic parameter with Amplify + project prefix
        try:
            generic_param = f"/amplify/arctanwines/{parameter_name}"
            response = ssm_client.get_parameter(Name=generic_param, WithDecryption=True)
            return response['Parameter']['Value']
        except Exception as e2:
            # Try with hyphen fallback
            try:
                env_hyphen_param = f"/amplify/arctan-wines/{env}/{parameter_name}"
                response = ssm_client.get_parameter(Name=env_hyphen_param, WithDecryption=True)
                return response['Parameter']['Value']
            except Exception as e3:
                try:
                    generic_hyphen_param = f"/amplify/arctan-wines/{parameter_name}"
                    response = ssm_client.get_parameter(Name=generic_hyphen_param, WithDecryption=True)
                    return response['Parameter']['Value']
                except Exception as e4:
                    # Final fallback to environment variable
                    env_var = parameter_name.upper().replace('-', '_').replace('/', '_')
                    env_value = os.environ.get(env_var)
                    if env_value:
                        return env_value
                    
                    # Return detailed error
                    raise Exception(f"Parameter {parameter_name} not found. Tried: {env_param} ({str(e1)}), {generic_param} ({str(e2)}), {env_hyphen_param} ({str(e3)}), {generic_hyphen_param} ({str(e4)}), env var {env_var} (not set). Environment: {env}, Info: {env_info}")

def get_database_url() -> str:
    """Get database URL from SSM parameters"""
    try:
        db_host = get_ssm_parameter("database/host")
        db_port = get_ssm_parameter("database/port") or "5432"
        db_name = get_ssm_parameter("database/name")
        db_user = get_ssm_parameter("database/username")
        db_password = get_ssm_parameter("database/password")
        
        return f"postgresql+psycopg2://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    except Exception as e:
        print(f"Error getting database configuration: {str(e)}")
        # Fallback to environment variable for local development
        return os.environ.get('DATABASE_URL', 'postgresql+psycopg2://localhost/arctanwines_dev')

def create_database_engine():
    """Create SQLAlchemy engine with proper configuration"""
    database_url = get_database_url()
    
    engine = create_engine(
        database_url,
        pool_pre_ping=True,
        pool_recycle=300,
        echo=False  # Set to True for SQL debugging
    )
    
    return engine

def create_session_factory():
    """Create SQLAlchemy session factory"""
    engine = create_database_engine()
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal 