"""
Alembic environment configuration for Arctan Wines CRM
Environment-aware database connection using SSM Parameter Store
"""
import os
import sys
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context
import boto3

# Add the current directory to the path so we can import models
sys.path.append(os.path.dirname(__file__))

# Import your models here - we'll create a models directory
try:
    from models.base import Base
    # Import all models
    from models.supplier import Supplier
    from models.wine import Wine, WineInventory
    from models.wine_batch import WineBatch, WineBatchCost, WineBatchStatus
    from models.customer import Customer
    from models.order import Order, OrderItem, OrderStatus, PaymentStatus
except ImportError:
    # Fallback for when models aren't available yet
    print("Warning: Could not import models. Creating empty metadata.")
    from sqlalchemy import MetaData
    Base = type('Base', (), {'metadata': MetaData()})

# This is the Alembic Config object
config = context.config

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Add your model's MetaData object here for 'autogenerate' support
target_metadata = Base.metadata

def get_environment():
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

def get_ssm_parameter(parameter_name):
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

def get_database_url():
    """Get database URL from SSM parameters"""
    # For local development, check environment variable first
    local_db_url = os.environ.get('DATABASE_URL')
    if local_db_url:
        print(f"Using local database URL: {local_db_url}")
        return local_db_url
    
    try:
        db_host = get_ssm_parameter("database/host")
        db_port = get_ssm_parameter("database/port") or "5432"
        db_name = get_ssm_parameter("database/name")
        db_user = get_ssm_parameter("database/username")
        db_password = get_ssm_parameter("database/password")
        
        return f"postgresql+psycopg2://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    except Exception as e:
        print(f"Error getting database configuration: {str(e)}")
        print("Falling back to local SQLite database")
        # Fallback to local SQLite for development
        return 'sqlite:///./arctanwines_local.db'

def run_migrations_offline():
    """Run migrations in 'offline' mode."""
    url = get_database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online():
    """Run migrations in 'online' mode."""
    configuration = config.get_section(config.config_ini_section)
    configuration['sqlalchemy.url'] = get_database_url()
    
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, 
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )

        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online() 