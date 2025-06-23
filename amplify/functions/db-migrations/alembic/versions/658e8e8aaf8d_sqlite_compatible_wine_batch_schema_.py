"""SQLite compatible wine batch schema update

Revision ID: 658e8e8aaf8d
Revises: a370e09fe716
Create Date: 2025-06-24 00:15:15.652968

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import Text, String, Integer, DECIMAL, Boolean, Date, DateTime
from sqlalchemy.dialects import postgresql
import sys
from pathlib import Path

# Add models path for imports
sys.path.append(str(Path(__file__).parent.parent.parent / "models"))
from base import GUID

# revision identifiers, used by Alembic.
revision = '658e8e8aaf8d'
down_revision = 'a370e09fe716'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    SQLite-compatible version of the wine batch schema update.
    Instead of using ALTER COLUMN (not supported in SQLite), 
    we'll handle the schema changes in a compatible way.
    """
    
    # Get the database dialect
    bind = op.get_bind()
    is_sqlite = bind.dialect.name == 'sqlite'
    
    if is_sqlite:
        # For SQLite, we need to handle the status column change differently
        # Since ALTER COLUMN is not supported, we'll work with the existing structure
        
        # The problematic migration tried to change status from NOT NULL to nullable
        # In SQLite, we can update existing records to handle this gracefully
        
        # Update any NULL status values to a default
        op.execute("UPDATE wine_batches SET status = 'AVAILABLE' WHERE status IS NULL")
        
        # Add new columns that were supposed to be added
        try:
            op.add_column('wine_batches', sa.Column('import_date', Date(), nullable=True, comment='Date of import'))
        except Exception:
            pass  # Column might already exist
            
        try:
            op.add_column('wine_batches', sa.Column('supplier_id', String(length=36), nullable=True, comment='Reference to supplier'))
        except Exception:
            pass
            
        try:
            op.add_column('wine_batches', sa.Column('eur_exchange_rate', DECIMAL(precision=10, scale=6), nullable=True, comment='EUR to NOK exchange rate at import'))
        except Exception:
            pass
            
        try:
            op.add_column('wine_batches', sa.Column('wine_cost_eur_cents', Integer(), nullable=True, comment='Wine cost in EUR cents'))
        except Exception:
            pass
            
        try:
            op.add_column('wine_batches', sa.Column('transport_cost_ore', Integer(), nullable=True, comment='Transport cost in NOK øre'))
        except Exception:
            pass
            
        try:
            op.add_column('wine_batches', sa.Column('customs_fee_ore', Integer(), nullable=True, comment='Customs fee in NOK øre'))
        except Exception:
            pass
            
        try:
            op.add_column('wine_batches', sa.Column('freight_forwarding_ore', Integer(), nullable=True, comment='Freight forwarding cost in NOK øre'))
        except Exception:
            pass
            
        try:
            op.add_column('wine_batches', sa.Column('fiken_sync_status', String(length=20), nullable=True, comment='Fiken synchronization status'))
        except Exception:
            pass
            
        try:
            op.add_column('wine_batches', sa.Column('active', Boolean(), nullable=True, comment='Soft delete flag'))
        except Exception:
            pass
        
        # Set default values for new columns
        op.execute("UPDATE wine_batches SET active = 1 WHERE active IS NULL")
        op.execute("UPDATE wine_batches SET import_date = date('now') WHERE import_date IS NULL")
        
        # Create the new tables that should have been created
        try:
            op.create_table('suppliers',
                sa.Column('name', String(length=255), nullable=False, comment='Supplier company name'),
                sa.Column('country', String(length=100), nullable=False, comment='Country of origin'),
                sa.Column('contact_person', String(length=255), nullable=True, comment='Primary contact person'),
                sa.Column('email', String(length=255), nullable=True, comment='Primary email address'),
                sa.Column('phone', String(length=50), nullable=True, comment='Primary phone number'),
                sa.Column('payment_terms', Integer(), nullable=True, comment='Payment terms in days'),
                sa.Column('currency', String(length=3), nullable=True, comment='Primary currency (EUR, NOK, USD)'),
                sa.Column('tax_id', String(length=50), nullable=True, comment='VAT number or tax identification'),
                sa.Column('id', GUID(), nullable=False, comment='Primary key using UUID'),
                sa.Column('created_at', DateTime(timezone=True), nullable=False, comment='Timestamp when record was created'),
                sa.Column('updated_at', DateTime(timezone=True), nullable=False, comment='Timestamp when record was last updated'),
                sa.Column('active', Boolean(), nullable=False, comment='Soft delete flag'),
                sa.PrimaryKeyConstraint('id')
            )
        except Exception:
            pass  # Table might already exist
        
        try:
            op.create_table('wines',
                sa.Column('name', String(length=255), nullable=False, comment='Wine name'),
                sa.Column('producer', String(length=255), nullable=False, comment='Wine producer/winery'),
                sa.Column('region', String(length=255), nullable=True, comment='Wine region'),
                sa.Column('country', String(length=100), nullable=False, comment='Country of origin'),
                sa.Column('vintage', Integer(), nullable=True, comment='Wine vintage year'),
                sa.Column('grape_varieties', Text(), nullable=True, comment='JSON string of grape varieties'),
                sa.Column('alcohol_content', DECIMAL(precision=4, scale=2), nullable=True, comment='Alcohol percentage (e.g., 13.5)'),
                sa.Column('bottle_size_ml', Integer(), nullable=True, comment='Bottle size in milliliters'),
                sa.Column('product_category', String(length=50), nullable=True, comment='Wine category (red, white, rosé, sparkling, dessert)'),
                sa.Column('tasting_notes', Text(), nullable=True, comment='Tasting notes and description'),
                sa.Column('serving_temperature', String(length=50), nullable=True, comment='Recommended serving temperature'),
                sa.Column('food_pairing', Text(), nullable=True, comment='Food pairing suggestions'),
                sa.Column('organic', Boolean(), nullable=True, comment='Organic certification'),
                sa.Column('biodynamic', Boolean(), nullable=True, comment='Biodynamic certification'),
                sa.Column('fiken_product_id', Integer(), nullable=True, comment='Fiken product ID for sync'),
                sa.Column('id', GUID(), nullable=False, comment='Primary key using UUID'),
                sa.Column('created_at', DateTime(timezone=True), nullable=False, comment='Timestamp when record was created'),
                sa.Column('updated_at', DateTime(timezone=True), nullable=False, comment='Timestamp when record was last updated'),
                sa.Column('active', Boolean(), nullable=False, comment='Soft delete flag'),
                sa.PrimaryKeyConstraint('id')
            )
        except Exception:
            pass
            
    else:
        # For PostgreSQL, run the original migration operations
        # (This maintains compatibility with production PostgreSQL)
        
        # Create the new tables
        op.create_table('suppliers',
            sa.Column('name', String(length=255), nullable=False, comment='Supplier company name'),
            sa.Column('country', String(length=100), nullable=False, comment='Country of origin'),
            sa.Column('contact_person', String(length=255), nullable=True, comment='Primary contact person'),
            sa.Column('email', String(length=255), nullable=True, comment='Primary email address'),
            sa.Column('phone', String(length=50), nullable=True, comment='Primary phone number'),
            sa.Column('payment_terms', Integer(), nullable=True, comment='Payment terms in days'),
            sa.Column('currency', String(length=3), nullable=True, comment='Primary currency (EUR, NOK, USD)'),
            sa.Column('tax_id', String(length=50), nullable=True, comment='VAT number or tax identification'),
            sa.Column('id', GUID(), nullable=False, comment='Primary key using UUID'),
            sa.Column('created_at', DateTime(timezone=True), nullable=False, comment='Timestamp when record was created'),
            sa.Column('updated_at', DateTime(timezone=True), nullable=False, comment='Timestamp when record was last updated'),
            sa.Column('active', Boolean(), nullable=False, comment='Soft delete flag'),
            sa.PrimaryKeyConstraint('id')
        )
        
        op.create_table('wines',
            sa.Column('name', String(length=255), nullable=False, comment='Wine name'),
            sa.Column('producer', String(length=255), nullable=False, comment='Wine producer/winery'),
            sa.Column('region', String(length=255), nullable=True, comment='Wine region'),
            sa.Column('country', String(length=100), nullable=False, comment='Country of origin'),
            sa.Column('vintage', Integer(), nullable=True, comment='Wine vintage year'),
            sa.Column('grape_varieties', Text(), nullable=True, comment='JSON string of grape varieties'),
            sa.Column('alcohol_content', DECIMAL(precision=4, scale=2), nullable=True, comment='Alcohol percentage (e.g., 13.5)'),
            sa.Column('bottle_size_ml', Integer(), nullable=True, comment='Bottle size in milliliters'),
            sa.Column('product_category', String(length=50), nullable=True, comment='Wine category (red, white, rosé, sparkling, dessert)'),
            sa.Column('tasting_notes', Text(), nullable=True, comment='Tasting notes and description'),
            sa.Column('serving_temperature', String(length=50), nullable=True, comment='Recommended serving temperature'),
            sa.Column('food_pairing', Text(), nullable=True, comment='Food pairing suggestions'),
            sa.Column('organic', Boolean(), nullable=True, comment='Organic certification'),
            sa.Column('biodynamic', Boolean(), nullable=True, comment='Biodynamic certification'),
            sa.Column('fiken_product_id', Integer(), nullable=True, comment='Fiken product ID for sync'),
            sa.Column('id', GUID(), nullable=False, comment='Primary key using UUID'),
            sa.Column('created_at', DateTime(timezone=True), nullable=False, comment='Timestamp when record was created'),
            sa.Column('updated_at', DateTime(timezone=True), nullable=False, comment='Timestamp when record was last updated'),
            sa.Column('active', Boolean(), nullable=False, comment='Soft delete flag'),
            sa.PrimaryKeyConstraint('id')
        )
        
        # Add new columns to wine_batches
        op.add_column('wine_batches', sa.Column('import_date', Date(), nullable=False, comment='Date of import'))
        op.add_column('wine_batches', sa.Column('supplier_id', GUID(), nullable=True, comment='Reference to supplier'))
        op.add_column('wine_batches', sa.Column('eur_exchange_rate', DECIMAL(precision=10, scale=6), nullable=False, comment='EUR to NOK exchange rate at import'))
        op.add_column('wine_batches', sa.Column('wine_cost_eur_cents', Integer(), nullable=False, comment='Wine cost in EUR cents'))
        op.add_column('wine_batches', sa.Column('transport_cost_ore', Integer(), nullable=True, comment='Transport cost in NOK øre'))
        op.add_column('wine_batches', sa.Column('customs_fee_ore', Integer(), nullable=True, comment='Customs fee in NOK øre'))
        op.add_column('wine_batches', sa.Column('freight_forwarding_ore', Integer(), nullable=True, comment='Freight forwarding cost in NOK øre'))
        op.add_column('wine_batches', sa.Column('fiken_sync_status', String(length=20), nullable=True, comment='Fiken synchronization status'))
        op.add_column('wine_batches', sa.Column('active', Boolean(), nullable=False, comment='Soft delete flag'))
        
        # Use PostgreSQL-specific ENUM for status column
        op.alter_column('wine_batches', 'status',
                       existing_type=sa.VARCHAR(length=9),
                       type_=sa.Enum('ORDERED', 'IN_TRANSIT', 'CUSTOMS', 'AVAILABLE', 'SOLD_OUT', name='winebatchstatus'),
                       nullable=True)
        
        # Create foreign key constraint
        op.create_foreign_key(None, 'wine_batches', 'suppliers', ['supplier_id'], ['id'])


def downgrade() -> None:
    """
    Downgrade the migration.
    Note: This is a simplified downgrade that may not restore exact original state.
    """
    
    bind = op.get_bind()
    is_sqlite = bind.dialect.name == 'sqlite'
    
    if is_sqlite:
        # For SQLite, remove the columns we added
        try:
            op.drop_column('wine_batches', 'active')
        except Exception:
            pass
        try:
            op.drop_column('wine_batches', 'fiken_sync_status')
        except Exception:
            pass
        try:
            op.drop_column('wine_batches', 'freight_forwarding_ore')
        except Exception:
            pass
        try:
            op.drop_column('wine_batches', 'customs_fee_ore')
        except Exception:
            pass
        try:
            op.drop_column('wine_batches', 'transport_cost_ore')
        except Exception:
            pass
        try:
            op.drop_column('wine_batches', 'wine_cost_eur_cents')
        except Exception:
            pass
        try:
            op.drop_column('wine_batches', 'eur_exchange_rate')
        except Exception:
            pass
        try:
            op.drop_column('wine_batches', 'supplier_id')
        except Exception:
            pass
        try:
            op.drop_column('wine_batches', 'import_date')
        except Exception:
            pass
            
        # Drop tables if they exist
        try:
            op.drop_table('wines')
        except Exception:
            pass
        try:
            op.drop_table('suppliers')
        except Exception:
            pass
    else:
        # For PostgreSQL, reverse the operations
        op.drop_constraint(None, 'wine_batches', type_='foreignkey')
        op.alter_column('wine_batches', 'status',
                       existing_type=sa.Enum('ORDERED', 'IN_TRANSIT', 'CUSTOMS', 'AVAILABLE', 'SOLD_OUT', name='winebatchstatus'),
                       type_=sa.VARCHAR(length=9),
                       nullable=False)
        op.drop_column('wine_batches', 'active')
        op.drop_column('wine_batches', 'fiken_sync_status')
        op.drop_column('wine_batches', 'freight_forwarding_ore')
        op.drop_column('wine_batches', 'customs_fee_ore')
        op.drop_column('wine_batches', 'transport_cost_ore')
        op.drop_column('wine_batches', 'wine_cost_eur_cents')
        op.drop_column('wine_batches', 'eur_exchange_rate')
        op.drop_column('wine_batches', 'supplier_id')
        op.drop_column('wine_batches', 'import_date')
        op.drop_table('wines')
        op.drop_table('suppliers') 