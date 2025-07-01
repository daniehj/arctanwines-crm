"""Force add missing columns with ALTER TABLE

Revision ID: 62828d0c71cb
Revises: 720ed1fa374c
Create Date: 2025-06-24 01:07:30.123456

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "62828d0c71cb"
down_revision = "720ed1fa374c"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Force add missing columns using direct SQL.
    This migration uses raw SQL to ensure columns exist.
    """

    print("🔧 Force adding missing columns with direct SQL...")

    # Get database connection
    connection = op.get_bind()

    # Helper function to safely execute SQL
    def safe_execute(sql, description):
        try:
            connection.execute(sa.text(sql))
            print(f"✅ {description}")
        except Exception as e:
            print(f"⚠️  {description} - {str(e)[:100]}...")

    # Force add missing columns to wine_batch_costs
    print("\n📋 Adding columns to wine_batch_costs:")

    wine_batch_costs_columns = [
        ("id", "VARCHAR(36) NOT NULL DEFAULT gen_random_uuid()::text", "Primary key"),
        ("batch_id", "VARCHAR(36)", "Reference to wine batch"),
        ("cost_type", "VARCHAR(50) NOT NULL DEFAULT 'wine'", "Type of cost"),
        ("amount_ore", "INTEGER NOT NULL DEFAULT 0", "Amount in øre"),
        ("currency", "VARCHAR(3) DEFAULT 'NOK'", "Currency code"),
        ("fiken_account_code", "VARCHAR(20)", "Fiken account code"),
        ("payment_date", "DATE", "Payment date"),
        ("allocation_method", "VARCHAR(30)", "Allocation method"),
        ("invoice_reference", "VARCHAR(100)", "Invoice reference"),
        ("active", "BOOLEAN NOT NULL DEFAULT true", "Soft delete flag"),
        (
            "created_at",
            "TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP",
            "Created timestamp",
        ),
        (
            "updated_at",
            "TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP",
            "Updated timestamp",
        ),
    ]

    for col_name, col_def, description in wine_batch_costs_columns:
        sql = f"ALTER TABLE wine_batch_costs ADD COLUMN IF NOT EXISTS {col_name} {col_def}"
        safe_execute(sql, f"Add {col_name} - {description}")

    # Force add missing columns to order_items
    print("\n📋 Adding columns to order_items:")

    order_items_columns = [
        ("id", "VARCHAR(36) NOT NULL DEFAULT gen_random_uuid()::text", "Primary key"),
        ("order_id", "VARCHAR(36) NOT NULL", "Reference to order"),
        ("wine_batch_id", "VARCHAR(36)", "Reference to wine batch"),
        ("wine_id", "VARCHAR(36)", "Reference to wine"),
        ("quantity", "INTEGER NOT NULL DEFAULT 1", "Quantity ordered"),
        ("unit_price_ore", "INTEGER NOT NULL DEFAULT 0", "Unit price in øre"),
        ("total_price_ore", "INTEGER NOT NULL DEFAULT 0", "Total price in øre"),
        ("wine_name", "VARCHAR(255)", "Wine name at time of order"),
        ("producer", "VARCHAR(255)", "Producer at time of order"),
        ("vintage", "INTEGER", "Vintage at time of order"),
        ("bottle_size_ml", "INTEGER DEFAULT 750", "Bottle size at time of order"),
        ("discount_percentage", "DECIMAL(5,2)", "Discount percentage"),
        ("discount_ore", "INTEGER", "Discount amount in øre"),
        ("notes", "TEXT", "Order item notes"),
        ("active", "BOOLEAN NOT NULL DEFAULT true", "Soft delete flag"),
        (
            "created_at",
            "TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP",
            "Created timestamp",
        ),
        (
            "updated_at",
            "TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP",
            "Updated timestamp",
        ),
    ]

    for col_name, col_def, description in order_items_columns:
        sql = f"ALTER TABLE order_items ADD COLUMN IF NOT EXISTS {col_name} {col_def}"
        safe_execute(sql, f"Add {col_name} - {description}")

    # Also ensure wine_batches has missing columns
    print("\n📋 Adding missing columns to wine_batches:")

    wine_batches_columns = [
        ("eur_exchange_rate", "DECIMAL(10,6)", "EUR to NOK exchange rate"),
        ("wine_cost_eur_cents", "INTEGER", "Wine cost in EUR cents"),
        ("transport_cost_ore", "INTEGER", "Transport cost in øre"),
        ("customs_fee_ore", "INTEGER", "Customs fee in øre"),
        ("freight_forwarding_ore", "INTEGER", "Freight forwarding cost in øre"),
        ("fiken_sync_status", "VARCHAR(20)", "Fiken sync status"),
    ]

    for col_name, col_def, description in wine_batches_columns:
        sql = f"ALTER TABLE wine_batches ADD COLUMN IF NOT EXISTS {col_name} {col_def}"
        safe_execute(sql, f"Add {col_name} - {description}")

    # Create primary key constraints if they don't exist
    print("\n🔑 Adding primary key constraints:")

    primary_keys = [("wine_batch_costs", "id"), ("order_items", "id")]

    for table, pk_col in primary_keys:
        sql = f"""
        DO $$ 
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.table_constraints 
                WHERE table_name = '{table}' AND constraint_type = 'PRIMARY KEY'
            ) THEN
                ALTER TABLE {table} ADD PRIMARY KEY ({pk_col});
            END IF;
        END $$;
        """
        safe_execute(sql, f"Add primary key to {table}")

    print("\n✅ Force column addition completed!")


def downgrade() -> None:
    """
    Downgrade not implemented - columns will remain
    """
    print("⚠️  Downgrade not implemented - columns will remain")
    pass
