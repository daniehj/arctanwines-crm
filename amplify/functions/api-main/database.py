"""
Database service for Arctan Wines CRM API
Shared database models and connection handling
"""
import os
import uuid
from datetime import datetime
from sqlalchemy import Column, DateTime, String, Integer, Enum as SQLEnum, create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from enum import Enum
import boto3

Base = declarative_base()

# === Database Models ===

class BaseModel(Base):
    """Abstract base model with common fields for all tables"""
    __abstract__ = True
    
    id = Column(
        String(36), 
        primary_key=True, 
        default=lambda: str(uuid.uuid4()),
        comment="Primary key using UUID as string"
    )
    
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        comment="Timestamp when record was created"
    )
    
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        comment="Timestamp when record was last updated"
    )
    
    def __repr__(self):
        return f"<{self.__class__.__name__}(id={self.id})>"

class WineBatchStatus(Enum):
    """Basic status of wine batch"""
    ORDERED = "ordered"
    AVAILABLE = "available"
    SOLD_OUT = "sold_out"

class WineBatch(BaseModel):
    """Simplified wine batch for initial implementation"""
    __tablename__ = "wine_batches"
    
    # Essential Information
    batch_number = Column(String(50), unique=True, nullable=False, index=True,
                         comment="Unique batch identifier (e.g., ACEDIANO-2024-001)")
    
    wine_name = Column(String(200), nullable=False, index=True,
                      comment="Wine name (e.g., ACEDIANO Monastrell)")
    
    producer = Column(String(200), nullable=False,
                     comment="Wine producer/winery name")
    
    # Basic Details
    total_bottles = Column(Integer, nullable=False,
                          comment="Total number of bottles in batch")
    
    status = Column(SQLEnum(WineBatchStatus), nullable=False, default=WineBatchStatus.ORDERED,
                   comment="Current status of the batch")
    
    # Simple Cost (NOK øre only for now)
    total_cost_nok_ore = Column(Integer, nullable=False, default=0,
                               comment="Total cost in NOK øre (84000 = 840.00 NOK)")
    
    target_price_nok_ore = Column(Integer, nullable=True,
                                 comment="Target selling price per bottle in NOK øre")
    
    def __repr__(self):
        return f"<WineBatch(batch_number='{self.batch_number}', wine_name='{self.wine_name}')>"

# === Database Configuration ===

def get_environment():
    """Determine environment based on AWS Lambda context"""
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
    """Get SSM parameter with detailed error handling"""
    ssm_client = boto3.client('ssm')
    env = get_environment()
    
    # Try environment-specific parameter first
    try:
        env_param = f"/amplify/arctanwines/{env}/{parameter_name}"
        response = ssm_client.get_parameter(Name=env_param, WithDecryption=True)
        return response['Parameter']['Value']
    except Exception as e1:
        # Try generic parameter
        try:
            generic_param = f"/amplify/arctanwines/{parameter_name}"
            response = ssm_client.get_parameter(Name=generic_param, WithDecryption=True)
            return response['Parameter']['Value']
        except Exception as e2:
            # Final fallback to environment variable
            env_var = parameter_name.upper().replace('-', '_').replace('/', '_')
            env_value = os.environ.get(env_var)
            if env_value:
                return env_value
            
            raise Exception(f"Parameter {parameter_name} not found. Tried: {env_param} ({str(e1)}), {generic_param} ({str(e2)}), env var {env_var} (not set)")

def get_database_url():
    """Get database URL from SSM parameters or environment variables"""
    # For local development - check for LOCAL_DB environment variable
    if os.environ.get('LOCAL_DB') == 'true':
        print("Using local SQLite database for testing")
        return 'sqlite:///./arctanwines_local.db'
    
    # For local development with custom DATABASE_URL
    local_db_url = os.environ.get('DATABASE_URL')
    if local_db_url:
        print(f"Using custom DATABASE_URL: {local_db_url}")
        return local_db_url
    
    try:
        print("Attempting to get database configuration from SSM...")
        db_host = get_ssm_parameter("database/host")
        db_port = get_ssm_parameter("database/port") or "5432"
        db_name = get_ssm_parameter("database/name")
        db_user = get_ssm_parameter("database/username")
        db_password = get_ssm_parameter("database/password")
        
        db_url = f"postgresql+psycopg2://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
        print(f"Using PostgreSQL database: {db_host}:{db_port}/{db_name}")
        return db_url
    except Exception as e:
        print(f"Error getting database configuration from SSM: {str(e)}")
        print("Falling back to local SQLite database")
        # Fallback for development
        return 'sqlite:///./arctanwines_local.db'

# === Database Session Management ===

class DatabaseService:
    """Database service with connection management"""
    
    def __init__(self):
        self.engine = None
        self.SessionLocal = None
    
    def init_database(self):
        """Initialize database connection"""
        if self.engine is None:
            database_url = get_database_url()
            print(f"Connecting to database: {database_url.split('@')[0]}@***")
            
            self.engine = create_engine(
                database_url,
                pool_pre_ping=True,
                pool_recycle=300,
                echo=False  # Set to True for SQL debugging
            )
            
            self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
    
    def get_session(self):
        """Get database session"""
        if self.SessionLocal is None:
            self.init_database()
        return self.SessionLocal()
    
    def test_connection(self):
        """Test database connection"""
        try:
            if self.engine is None:
                self.init_database()
            
            with self.engine.connect() as connection:
                result = connection.execute(text("SELECT 1"))
                return {"status": "connected", "result": result.scalar()}
        except Exception as e:
            return {"status": "error", "error": str(e)}

# Global database service instance
db_service = DatabaseService() 