# Arctan Wines CRM - Implementation Plan

## 🎯 **Project Overview**

A comprehensive CRM system for Norwegian wine import business with complex margin tracking, Fiken accounting integration, and wine tasting event management.

### **Key Business Requirements:**
- **Multi-layer cost tracking** (EUR wine cost + NOK transport/customs/taxes)
- **Fiken integration** as source of truth for financial data
- **Wine tasting event management** with ROI tracking
- **Norwegian tax compliance** (særavgift system)
- **B2B focus** with organization number tracking

### **Critical Design Decision: Fiken-Native Monetary Format**
- **All monetary values stored as integers** (øre for NOK, cents for EUR)
- **No conversion layer** - direct compatibility with Fiken API
- **Display formatting only** at frontend presentation layer
- **Example**: 336000 = 3,360.00 NOK, 84000 = 840.00 NOK

---

## 🏗️ **Technical Architecture**

### **Tech Stack**
- **Frontend**: Next.js 14 + Tailwind CSS + React Query
- **Backend**: FastAPI (Python) on AWS Lambda
- **Database**: PostgreSQL on AWS RDS
- **Migrations**: Alembic with environment-aware configuration
- **Infrastructure**: AWS Amplify Gen2
- **Authentication**: AWS Cognito
- **Integration**: Fiken API for accounting sync

### **AWS Services**
- **Amplify Gen2**: Full-stack hosting with SSR
- **RDS PostgreSQL**: Primary database with VPC setup
- **Lambda Functions**: FastAPI + migration functions
- **Cognito**: Authentication with custom attributes
- **S3**: Document and wine image storage
- **SSM Parameter Store**: Configuration management
- **Secrets Manager**: Database credentials

---

## 📊 **Database Schema Design**

### **Core Principles**
1. **Fiken-Native Format**: All monetary values as integers (øre/cents)
2. **UUID Primary Keys**: For better distributed system support
3. **Audit Trails**: created_at/updated_at on all tables
4. **Soft Deletes**: active/inactive flags instead of hard deletes
5. **JSONB Fields**: For flexible data like wine preferences

### **1. Wine Batch Management (Central Cost Tracking)**
```sql
wine_batches (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  import_date DATE NOT NULL,
  supplier_id UUID REFERENCES suppliers(id),
  total_bottles INTEGER NOT NULL,
  eur_exchange_rate DECIMAL(10,6) NOT NULL,
  wine_cost_eur_cents INTEGER NOT NULL,      -- EUR stored as cents
  transport_cost_ore INTEGER DEFAULT 0,      -- NOK stored as øre
  customs_fee_ore INTEGER DEFAULT 0,
  freight_forwarding_ore INTEGER DEFAULT 0,
  landed_cost_per_bottle_ore INTEGER,        -- Calculated field
  fiken_sync_status VARCHAR(20) DEFAULT 'pending',
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

wine_batch_costs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  batch_id UUID REFERENCES wine_batches(id) ON DELETE CASCADE,
  cost_type VARCHAR(50) NOT NULL, -- 'transport', 'customs', 'freight', 'wine_purchase'
  amount_ore INTEGER NOT NULL,    -- Always in øre (or cents for EUR)
  currency VARCHAR(3) NOT NULL,   -- 'NOK', 'EUR'
  fiken_account_code VARCHAR(20),
  payment_date DATE,
  allocation_method VARCHAR(30) DEFAULT 'per_bottle', -- 'per_bottle', 'by_value', 'percentage'
  invoice_reference VARCHAR(100),
  created_at TIMESTAMP DEFAULT NOW()
);
```

### **2. Suppliers**
```sql
suppliers (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name VARCHAR(255) NOT NULL,
  country VARCHAR(100) NOT NULL,
  contact_person VARCHAR(255),
  email VARCHAR(255),
  phone VARCHAR(50),
  payment_terms INTEGER DEFAULT 30, -- days
  currency VARCHAR(3) DEFAULT 'EUR',
  tax_id VARCHAR(50), -- VAT number or equivalent
  active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);
```

### **3. Customer Management**
```sql
customers (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  customer_type VARCHAR(20) NOT NULL, -- 'individual', 'business', 'restaurant'
  name VARCHAR(255) NOT NULL,
  organization_number VARCHAR(20), -- Norwegian org numbers (9 digits)
  email VARCHAR(255),
  phone VARCHAR(50),
  preferred_contact_method VARCHAR(20) DEFAULT 'email',
  customer_segment VARCHAR(50),
  wine_preferences JSONB, -- {"red": true, "organic": true, "price_range": "300-500"}
  payment_terms INTEGER DEFAULT 30, -- days
  credit_limit_ore INTEGER DEFAULT 0, -- Credit limit in øre
  fiken_customer_id INTEGER, -- Sync with Fiken contacts
  active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

customer_addresses (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  customer_id UUID REFERENCES customers(id) ON DELETE CASCADE,
  address_type VARCHAR(20) NOT NULL, -- 'billing', 'shipping', 'primary'
  street_address VARCHAR(255) NOT NULL,
  city VARCHAR(100) NOT NULL,
  postal_code VARCHAR(10) NOT NULL,
  country VARCHAR(50) DEFAULT 'Norway',
  is_default BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMP DEFAULT NOW()
);

customer_interactions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  customer_id UUID REFERENCES customers(id) ON DELETE CASCADE,
  interaction_type VARCHAR(50) NOT NULL, -- 'email', 'phone', 'meeting', 'tasting', 'complaint'
  subject VARCHAR(255),
  notes TEXT,
  interaction_date TIMESTAMP DEFAULT NOW(),
  follow_up_date DATE,
  user_id UUID, -- Reference to Cognito user
  completed BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMP DEFAULT NOW()
);
```

### **4. Wine Product Catalog**
```sql
wines (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name VARCHAR(255) NOT NULL,
  producer VARCHAR(255) NOT NULL,
  region VARCHAR(255),
  country VARCHAR(100) NOT NULL,
  vintage INTEGER,
  grape_varieties JSONB, -- ["Cabernet Sauvignon", "Merlot"]
  alcohol_content DECIMAL(4,2), -- 13.5%
  bottle_size_ml INTEGER DEFAULT 750,
  product_category VARCHAR(50), -- 'red', 'white', 'rosé', 'sparkling', 'dessert'
  tasting_notes TEXT,
  serving_temperature VARCHAR(50),
  food_pairing TEXT,
  organic BOOLEAN DEFAULT FALSE,
  biodynamic BOOLEAN DEFAULT FALSE,
  active BOOLEAN DEFAULT TRUE,
  fiken_product_id INTEGER, -- Sync with Fiken products
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

wine_inventory (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  wine_id UUID REFERENCES wines(id) ON DELETE CASCADE,
  batch_id UUID REFERENCES wine_batches(id),
  quantity_available INTEGER NOT NULL DEFAULT 0,
  cost_per_bottle_ore INTEGER NOT NULL, -- Cost in øre
  selling_price_ore INTEGER NOT NULL,   -- Selling price in øre
  margin_ore INTEGER GENERATED ALWAYS AS (selling_price_ore - cost_per_bottle_ore) STORED,
  margin_percentage DECIMAL(5,2) GENERATED ALWAYS AS (
    CASE WHEN cost_per_bottle_ore > 0 
    THEN ((selling_price_ore - cost_per_bottle_ore)::DECIMAL / cost_per_bottle_ore * 100)
    ELSE 0 END
  ) STORED,
  minimum_stock_level INTEGER DEFAULT 0,
  location VARCHAR(100),
  best_before_date DATE,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);
```

### **5. Sales & Order Management**
```sql
orders (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  order_number VARCHAR(50) UNIQUE NOT NULL,
  customer_id UUID REFERENCES customers(id) NOT NULL,
  order_date DATE NOT NULL DEFAULT CURRENT_DATE,
  delivery_date DATE,
  order_status VARCHAR(30) DEFAULT 'draft', -- 'draft', 'confirmed', 'shipped', 'delivered', 'cancelled'
  payment_status VARCHAR(30) DEFAULT 'pending', -- 'pending', 'paid', 'overdue', 'cancelled'
  subtotal_ore INTEGER NOT NULL DEFAULT 0,
  vat_amount_ore INTEGER NOT NULL DEFAULT 0,
  total_amount_ore INTEGER GENERATED ALWAYS AS (subtotal_ore + vat_amount_ore) STORED,
  shipping_cost_ore INTEGER DEFAULT 0,
  order_type VARCHAR(30) DEFAULT 'retail', -- 'retail', 'wholesale', 'corporate', 'gift'
  special_instructions TEXT,
  fiken_invoice_id INTEGER, -- Sync with Fiken invoices
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

order_items (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  order_id UUID REFERENCES orders(id) ON DELETE CASCADE,
  wine_id UUID REFERENCES wines(id) NOT NULL,
  batch_id UUID REFERENCES wine_batches(id),
  quantity INTEGER NOT NULL CHECK (quantity > 0),
  unit_price_ore INTEGER NOT NULL,
  total_price_ore INTEGER GENERATED ALWAYS AS (quantity * unit_price_ore) STORED,
  cost_per_unit_ore INTEGER NOT NULL,
  margin_per_unit_ore INTEGER GENERATED ALWAYS AS (unit_price_ore - cost_per_unit_ore) STORED,
  created_at TIMESTAMP DEFAULT NOW()
);
```

### **6. Wine Tasting Event Management**
```sql
wine_tastings (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  event_name VARCHAR(255) NOT NULL,
  event_date DATE NOT NULL,
  event_time TIME,
  venue_type VARCHAR(50) NOT NULL, -- 'rented_venue', 'customer_location', 'own_premises'
  venue_name VARCHAR(255),
  venue_address TEXT,
  venue_cost_ore INTEGER DEFAULT 0,
  max_attendees INTEGER,
  actual_attendees INTEGER DEFAULT 0,
  event_type VARCHAR(50) NOT NULL, -- 'promotional', 'corporate', 'private', 'trade'
  event_status VARCHAR(30) DEFAULT 'planned', -- 'planned', 'confirmed', 'completed', 'cancelled'
  target_customer_segment VARCHAR(100),
  marketing_objective TEXT,
  total_event_cost_ore INTEGER DEFAULT 0,
  estimated_revenue_impact_ore INTEGER DEFAULT 0,
  actual_revenue_impact_ore INTEGER DEFAULT 0,
  notes TEXT,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

tasting_attendees (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tasting_id UUID REFERENCES wine_tastings(id) ON DELETE CASCADE,
  customer_id UUID REFERENCES customers(id), -- NULL for walk-ins
  attendee_name VARCHAR(255) NOT NULL,
  attendee_email VARCHAR(255),
  attendee_phone VARCHAR(50),
  attendee_type VARCHAR(30) NOT NULL, -- 'existing_customer', 'prospect', 'industry', 'press'
  rsvp_status VARCHAR(20) DEFAULT 'invited', -- 'invited', 'confirmed', 'attended', 'no_show'
  follow_up_required BOOLEAN DEFAULT FALSE,
  post_event_interest_level INTEGER CHECK (post_event_interest_level BETWEEN 1 AND 5),
  potential_order_value_ore INTEGER DEFAULT 0,
  created_at TIMESTAMP DEFAULT NOW()
);

tasting_wines (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tasting_id UUID REFERENCES wine_tastings(id) ON DELETE CASCADE,
  wine_id UUID REFERENCES wines(id), -- NULL for non-stock wines
  wine_name VARCHAR(255), -- For non-stock wines
  wine_producer VARCHAR(255),
  wine_vintage INTEGER,
  bottles_used INTEGER NOT NULL DEFAULT 1,
  wine_source VARCHAR(30) NOT NULL, -- 'imported_stock', 'brought_external', 'purchased_for_event'
  cost_per_bottle_ore INTEGER NOT NULL,
  total_wine_cost_ore INTEGER GENERATED ALWAYS AS (bottles_used * cost_per_bottle_ore) STORED,
  tasting_order INTEGER, -- Order of presentation
  tasting_notes TEXT,
  customer_feedback JSONB, -- {"average_rating": 4.2, "comments": ["Excellent", "Too dry"]}
  popularity_score DECIMAL(3,2), -- Based on attendee preferences (0.00-5.00)
  follow_up_orders INTEGER DEFAULT 0,
  created_at TIMESTAMP DEFAULT NOW()
);

tasting_costs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tasting_id UUID REFERENCES wine_tastings(id) ON DELETE CASCADE,
  cost_category VARCHAR(50) NOT NULL, -- 'venue', 'catering', 'staff', 'materials', 'transportation', 'marketing'
  cost_description VARCHAR(255) NOT NULL,
  supplier_name VARCHAR(255),
  amount_ore INTEGER NOT NULL,
  cost_date DATE NOT NULL DEFAULT CURRENT_DATE,
  invoice_reference VARCHAR(100),
  fiken_transaction_id INTEGER,
  cost_type VARCHAR(20) DEFAULT 'fixed', -- 'fixed', 'variable_per_person'
  created_at TIMESTAMP DEFAULT NOW()
);

tasting_outcomes (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tasting_id UUID REFERENCES wine_tastings(id) ON DELETE CASCADE,
  outcome_type VARCHAR(50) NOT NULL, -- 'immediate_order', 'follow_up_meeting', 'newsletter_signup', 'referral'
  customer_id UUID REFERENCES customers(id),
  outcome_value_ore INTEGER DEFAULT 0, -- Order value or estimated value
  outcome_date DATE NOT NULL DEFAULT CURRENT_DATE,
  notes TEXT,
  created_at TIMESTAMP DEFAULT NOW()
);
```

### **7. Financial Integration & Margin Tracking**
```sql
fiken_sync_log (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  sync_type VARCHAR(50) NOT NULL, -- 'customer', 'product', 'invoice', 'transaction'
  entity_id UUID NOT NULL,
  fiken_id INTEGER,
  sync_status VARCHAR(20) DEFAULT 'pending', -- 'pending', 'success', 'failed', 'retry'
  sync_timestamp TIMESTAMP DEFAULT NOW(),
  error_message TEXT,
  retry_count INTEGER DEFAULT 0,
  created_at TIMESTAMP DEFAULT NOW()
);

margin_analysis (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  order_id UUID REFERENCES orders(id) ON DELETE CASCADE,
  wine_id UUID REFERENCES wines(id) NOT NULL,
  batch_id UUID REFERENCES wine_batches(id),
  wine_cost_eur_cents INTEGER NOT NULL,
  exchange_rate DECIMAL(10,6) NOT NULL,
  wine_cost_ore INTEGER NOT NULL, -- Converted to NOK
  transport_cost_allocated_ore INTEGER DEFAULT 0,
  customs_cost_allocated_ore INTEGER DEFAULT 0,
  total_landed_cost_ore INTEGER NOT NULL,
  selling_price_ore INTEGER NOT NULL,
  gross_margin_ore INTEGER GENERATED ALWAYS AS (selling_price_ore - total_landed_cost_ore) STORED,
  margin_percentage DECIMAL(5,2) GENERATED ALWAYS AS (
    CASE WHEN total_landed_cost_ore > 0 
    THEN ((selling_price_ore - total_landed_cost_ore)::DECIMAL / total_landed_cost_ore * 100)
    ELSE 0 END
  ) STORED,
  import_tax_ore INTEGER DEFAULT 0, -- Norwegian særavgift
  vat_ore INTEGER DEFAULT 0,
  net_margin_ore INTEGER GENERATED ALWAYS AS (gross_margin_ore - import_tax_ore - vat_ore) STORED,
  created_at TIMESTAMP DEFAULT NOW()
);
```

---

## 🔧 **Alembic Migration Setup**

### **Directory Structure**
```
amplify/functions/db-migrations/
├── handler.py              # Lambda migration handler
├── alembic/
│   ├── env.py              # Environment-aware configuration
│   ├── script.py.mako      # Migration template
│   └── versions/           # Migration files
├── models/
│   ├── __init__.py
│   ├── base.py             # SQLAlchemy base
│   ├── customer.py         # Customer models
│   ├── wine.py             # Wine models
│   ├── order.py            # Order models
│   ├── batch.py            # Batch models
│   └── tasting.py          # Tasting models
├── requirements.txt
├── resource.ts             # Lambda configuration
└── alembic.ini
```

### **Environment-Aware Configuration**
```python
# alembic/env.py
import os
import boto3
from sqlalchemy import engine_from_config, pool
from alembic import context
from models.base import Base

def get_database_url():
    """Get database URL from SSM parameters based on environment"""
    ssm_client = boto3.client('ssm')
    
    # Determine environment
    amplify_env = os.environ.get('AMPLIFY_ENV', '')
    aws_branch = os.environ.get('AWS_BRANCH', '')
    function_name = os.environ.get('AWS_LAMBDA_FUNCTION_NAME', '')
    
    if ('sandbox' in amplify_env.lower() or 
        aws_branch in ['dev', 'test', 'sandbox'] or 
        'sandbox' in function_name.lower() or 
        'test' in function_name.lower()):
        env = 'test'
    else:
        env = 'prod'
    
    # Get parameters from SSM (using your existing parameter structure)
    try:
        db_host = ssm_client.get_parameter(Name=f"/amplify/arctanwines/database/host", WithDecryption=True)['Parameter']['Value']
        db_port = ssm_client.get_parameter(Name=f"/amplify/arctanwines/database/port", WithDecryption=True)['Parameter']['Value']
        db_name = ssm_client.get_parameter(Name=f"/amplify/arctanwines/database/name", WithDecryption=True)['Parameter']['Value']
        db_user = ssm_client.get_parameter(Name=f"/amplify/arctanwines/database/username", WithDecryption=True)['Parameter']['Value']
        db_password = ssm_client.get_parameter(Name=f"/amplify/arctanwines/database/password", WithDecryption=True)['Parameter']['Value']
        
        return f"postgresql+psycopg2://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    except Exception as e:
        raise Exception(f"Could not get database configuration: {str(e)}")

def run_migrations_online():
    """Run migrations in 'online' mode."""
    configuration = context.config.get_section(context.config.config_ini_section)
    configuration['sqlalchemy.url'] = get_database_url()
    
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, 
            target_metadata=Base.metadata,
            compare_type=True,
            compare_server_default=True
        )

        with context.begin_transaction():
            context.run_migrations()

run_migrations_online()
```

### **Migration Lambda Handler**
```python
# handler.py
import json
import subprocess
import os
from mangum import Mangum
from fastapi import FastAPI, HTTPException

app = FastAPI(title="Database Migrations")

@app.post("/migrate/upgrade")
async def upgrade_database():
    """Run all pending migrations"""
    try:
        result = subprocess.run([
            'alembic', 'upgrade', 'head'
        ], capture_output=True, text=True, cwd='/opt')
        
        if result.returncode == 0:
            return {
                "status": "success", 
                "message": "Database upgraded successfully",
                "output": result.stdout
            }
        else:
            raise HTTPException(
                status_code=500, 
                detail=f"Migration failed: {result.stderr}"
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/migrate/current")
async def current_revision():
    """Get current database revision"""
    try:
        result = subprocess.run([
            'alembic', 'current'
        ], capture_output=True, text=True, cwd='/opt')
        
        return {
            "current_revision": result.stdout.strip(),
            "status": "success"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/migrate/history")
async def migration_history():
    """Get migration history"""
    try:
        result = subprocess.run([
            'alembic', 'history', '--verbose'
        ], capture_output=True, text=True, cwd='/opt')
        
        return {
            "history": result.stdout,
            "status": "success"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

handler = Mangum(app)
```

---

## 💰 **Monetary Value Handling**

### **Storage Format (Fiken-Native)**
- **All monetary values as integers** (øre for NOK, cents for EUR)
- **No decimal fields** for money in database
- **Direct API compatibility** with Fiken

### **Utility Functions**
```python
# utils/currency.py
from decimal import Decimal

def format_nok(ore_amount: int) -> str:
    """Format øre as NOK for display"""
    return f"{ore_amount / 100:.2f} NOK"

def format_eur(cent_amount: int) -> str:
    """Format cents as EUR for display"""
    return f"€{cent_amount / 100:.2f}"

def parse_nok_input(nok_string: str) -> int:
    """Parse user input NOK to øre for storage"""
    return int(float(nok_string) * 100)

def parse_eur_input(eur_string: str) -> int:
    """Parse user input EUR to cents for storage"""
    return int(float(eur_string) * 100)

def convert_eur_to_nok_ore(eur_cents: int, exchange_rate: Decimal) -> int:
    """Convert EUR cents to NOK øre using exchange rate"""
    eur_amount = Decimal(eur_cents) / 100
    nok_amount = eur_amount * exchange_rate
    return int(nok_amount * 100)
```

### **Frontend TypeScript Utilities**
```typescript
// lib/currency.ts
export const formatNOK = (ore: number): string => {
  return `${(ore / 100).toFixed(2)} NOK`;
};

export const formatEUR = (cents: number): string => {
  return `€${(cents / 100).toFixed(2)}`;
};

export const parseNOKInput = (nokString: string): number => {
  return Math.round(parseFloat(nokString) * 100);
};

export const parseEURInput = (eurString: string): number => {
  return Math.round(parseFloat(eurString) * 100);
};
```

---

## 🚀 **Implementation Phases**

### **Phase 1: Foundation & Alembic Setup (Week 1)**
- [ ] Set up Alembic migration system
- [ ] Create migration Lambda function
- [ ] Implement base SQLAlchemy models
- [ ] Create initial database schema migration
- [ ] Set up currency utility functions
- [ ] Test migration system in sandbox environment

### **Phase 2: Core Data Models (Week 2)**
- [ ] Implement customer management models
- [ ] Create wine catalog models
- [ ] Set up supplier models
- [ ] Create wine batch tracking models
- [ ] Implement basic CRUD operations
- [ ] Add data validation and constraints

### **Phase 3: Order Management (Week 3)**
- [ ] Implement order and order items models
- [ ] Create inventory tracking system
- [ ] Set up margin calculation logic
- [ ] Implement order status workflow
- [ ] Add order number generation
- [ ] Create basic order API endpoints

### **Phase 4: Tasting Event System (Week 4)**
- [ ] Implement tasting event models
- [ ] Create attendee management system
- [ ] Set up tasting cost tracking
- [ ] Implement outcome tracking
- [ ] Add ROI calculation logic
- [ ] Create tasting event API endpoints

### **Phase 5: Fiken Integration (Week 5)**
- [ ] Implement Fiken API client
- [ ] Create customer sync functionality
- [ ] Set up product sync with Fiken
- [ ] Implement invoice generation
- [ ] Add transaction data import
- [ ] Create sync status tracking

### **Phase 6: Advanced Features (Week 6)**
- [ ] Implement margin analysis system
- [ ] Create financial reporting endpoints
- [ ] Add Norwegian tax calculations
- [ ] Implement automated cost allocation
- [ ] Create analytics dashboard data
- [ ] Add audit logging

### **Phase 7: Frontend Integration (Week 7)**
- [ ] Create Next.js pages for all entities
- [ ] Implement currency display components
- [ ] Add form validation with proper currency parsing
- [ ] Create dashboard with key metrics
- [ ] Implement search and filtering
- [ ] Add responsive design

### **Phase 8: Testing & Optimization (Week 8)**
- [ ] Comprehensive testing of all features
- [ ] Performance optimization
- [ ] Security audit
- [ ] Documentation completion
- [ ] Deployment to production
- [ ] User training and handover

---

## 🔍 **Key Decision Points**

### **Monetary Format Decision: ✅ Fiken-Native Integers**
- **Rationale**: Fiken is source of truth, eliminate conversion errors
- **Implementation**: All backend storage as integers, display formatting only
- **Impact**: Direct API compatibility, no rounding issues

### **Database Design Decisions**
- **UUIDs**: Better for distributed systems and external integrations
- **Generated Columns**: Automatic calculation of totals and margins
- **JSONB Fields**: Flexible storage for wine preferences and feedback
- **Soft Deletes**: Preserve data integrity with active/inactive flags

### **Migration Strategy Decision**
- **Separate Migration Lambda**: Dedicated function for schema changes
- **Environment-Aware**: Automatic environment detection
- **SSM Integration**: Reuse existing parameter structure

### **Integration Approach**
- **Fiken as Source**: Pull financial data, push CRM data
- **Bidirectional Sync**: Customers and products sync both ways
- **Conflict Resolution**: Fiken wins for financial data, CRM wins for relationship data

---

## 📋 **Development Checklist**

### **Before Starting**
- [ ] Confirm AWS infrastructure is ready
- [ ] Verify SSM parameters are configured
- [ ] Test database connectivity
- [ ] Set up development environment

### **During Development**
- [ ] Create migration for each major schema change
- [ ] Test all monetary calculations with real data
- [ ] Validate Fiken API integration with test data
- [ ] Ensure proper error handling and logging
- [ ] Document all business logic decisions

### **Before Production**
- [ ] Full data migration test
- [ ] Performance testing with realistic data volumes
- [ ] Security audit of all endpoints
- [ ] Backup and recovery procedures tested
- [ ] User acceptance testing completed

---

*This plan serves as the definitive guide for implementing the Arctan Wines CRM system with proper Alembic migrations and Fiken-native monetary handling.* 