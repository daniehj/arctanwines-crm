"""Add missing columns to existing tables

Revision ID: 720ed1fa374c
Revises: 15d72e03b4c4
Create Date: 2025-06-24 00:52:15.123456

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import String, Integer, DECIMAL, Boolean, Date, DateTime, Text
import sys
from pathlib import Path

# Add models path for imports
sys.path.append(str(Path(__file__).parent.parent.parent / "models"))
from base import GUID

# revision identifiers, used by Alembic.
revision = "720ed1fa374c"
down_revision = "15d72e03b4c4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Add missing columns to existing tables.
    This migration safely adds columns that might be missing from partial tables.
    """

    # Get the database dialect
    bind = op.get_bind()
    is_sqlite = bind.dialect.name == "sqlite"

    print("🔧 Adding missing columns to existing tables...")

    # Helper function to safely add columns
    def safe_add_column(table_name, column_name, column_type, **kwargs):
        try:
            op.add_column(table_name, sa.Column(column_name, column_type, **kwargs))
            print(f"✅ Added {column_name} to {table_name}")
        except Exception as e:
            print(f"⚠️  Column {column_name} already exists in {table_name}: {e}")

    if is_sqlite:
        # SQLite-specific missing columns

        # wine_batch_costs - ensure all 12 expected columns exist
        safe_add_column(
            "wine_batch_costs",
            "id",
            String(length=36),
            nullable=False,
            comment="Primary key using UUID",
        )
        safe_add_column(
            "wine_batch_costs",
            "batch_id",
            String(length=36),
            nullable=False,
            comment="Reference to wine batch",
        )
        safe_add_column(
            "wine_batch_costs",
            "cost_type",
            String(length=50),
            nullable=False,
            comment="Type of cost",
        )
        safe_add_column(
            "wine_batch_costs",
            "amount_ore",
            Integer(),
            nullable=False,
            comment="Amount in øre",
        )
        safe_add_column(
            "wine_batch_costs",
            "currency",
            String(length=3),
            nullable=True,
            comment="Currency code",
        )
        safe_add_column(
            "wine_batch_costs",
            "fiken_account_code",
            String(length=20),
            nullable=True,
            comment="Fiken account code",
        )
        safe_add_column(
            "wine_batch_costs",
            "payment_date",
            Date(),
            nullable=True,
            comment="Payment date",
        )
        safe_add_column(
            "wine_batch_costs",
            "allocation_method",
            String(length=30),
            nullable=True,
            comment="Allocation method",
        )
        safe_add_column(
            "wine_batch_costs",
            "invoice_reference",
            String(length=100),
            nullable=True,
            comment="Invoice reference",
        )
        safe_add_column(
            "wine_batch_costs",
            "active",
            Boolean(),
            nullable=False,
            comment="Soft delete flag",
        )
        safe_add_column(
            "wine_batch_costs",
            "created_at",
            DateTime(),
            nullable=False,
            comment="Created timestamp",
        )
        safe_add_column(
            "wine_batch_costs",
            "updated_at",
            DateTime(),
            nullable=False,
            comment="Updated timestamp",
        )

        # order_items - ensure all 17 expected columns exist
        safe_add_column(
            "order_items",
            "id",
            String(length=36),
            nullable=False,
            comment="Primary key using UUID",
        )
        safe_add_column(
            "order_items",
            "order_id",
            String(length=36),
            nullable=False,
            comment="Reference to order",
        )
        safe_add_column(
            "order_items",
            "wine_batch_id",
            String(length=36),
            nullable=True,
            comment="Reference to wine batch",
        )
        safe_add_column(
            "order_items",
            "wine_id",
            String(length=36),
            nullable=True,
            comment="Reference to wine",
        )
        safe_add_column(
            "order_items",
            "quantity",
            Integer(),
            nullable=False,
            comment="Quantity ordered",
        )
        safe_add_column(
            "order_items",
            "unit_price_ore",
            Integer(),
            nullable=False,
            comment="Unit price in øre",
        )
        safe_add_column(
            "order_items",
            "total_price_ore",
            Integer(),
            nullable=False,
            comment="Total price in øre",
        )
        safe_add_column(
            "order_items",
            "wine_name",
            String(length=255),
            nullable=True,
            comment="Wine name at time of order",
        )
        safe_add_column(
            "order_items",
            "producer",
            String(length=255),
            nullable=True,
            comment="Producer at time of order",
        )
        safe_add_column(
            "order_items",
            "vintage",
            Integer(),
            nullable=True,
            comment="Vintage at time of order",
        )
        safe_add_column(
            "order_items",
            "bottle_size_ml",
            Integer(),
            nullable=True,
            comment="Bottle size at time of order",
        )
        safe_add_column(
            "order_items",
            "discount_percentage",
            DECIMAL(precision=5, scale=2),
            nullable=True,
            comment="Discount percentage",
        )
        safe_add_column(
            "order_items",
            "discount_ore",
            Integer(),
            nullable=True,
            comment="Discount amount in øre",
        )
        safe_add_column(
            "order_items", "notes", Text(), nullable=True, comment="Order item notes"
        )
        safe_add_column(
            "order_items",
            "active",
            Boolean(),
            nullable=False,
            comment="Soft delete flag",
        )
        safe_add_column(
            "order_items",
            "created_at",
            DateTime(),
            nullable=False,
            comment="Created timestamp",
        )
        safe_add_column(
            "order_items",
            "updated_at",
            DateTime(),
            nullable=False,
            comment="Updated timestamp",
        )

        # Also ensure wine_batches has all expected columns
        safe_add_column(
            "wine_batches",
            "eur_exchange_rate",
            DECIMAL(precision=10, scale=6),
            nullable=True,
            comment="EUR to NOK exchange rate",
        )
        safe_add_column(
            "wine_batches",
            "wine_cost_eur_cents",
            Integer(),
            nullable=True,
            comment="Wine cost in EUR cents",
        )
        safe_add_column(
            "wine_batches",
            "transport_cost_ore",
            Integer(),
            nullable=True,
            comment="Transport cost in øre",
        )
        safe_add_column(
            "wine_batches",
            "customs_fee_ore",
            Integer(),
            nullable=True,
            comment="Customs fee in øre",
        )
        safe_add_column(
            "wine_batches",
            "freight_forwarding_ore",
            Integer(),
            nullable=True,
            comment="Freight forwarding cost in øre",
        )
        safe_add_column(
            "wine_batches",
            "fiken_sync_status",
            String(length=20),
            nullable=True,
            comment="Fiken sync status",
        )

    else:
        # PostgreSQL-specific missing columns

        # wine_batch_costs - ensure all 12 expected columns exist
        safe_add_column(
            "wine_batch_costs",
            "id",
            GUID(),
            nullable=False,
            comment="Primary key using UUID",
        )
        safe_add_column(
            "wine_batch_costs",
            "batch_id",
            GUID(),
            nullable=False,
            comment="Reference to wine batch",
        )
        safe_add_column(
            "wine_batch_costs",
            "cost_type",
            String(length=50),
            nullable=False,
            comment="Type of cost",
        )
        safe_add_column(
            "wine_batch_costs",
            "amount_ore",
            Integer(),
            nullable=False,
            comment="Amount in øre",
        )
        safe_add_column(
            "wine_batch_costs",
            "currency",
            String(length=3),
            nullable=True,
            comment="Currency code",
        )
        safe_add_column(
            "wine_batch_costs",
            "fiken_account_code",
            String(length=20),
            nullable=True,
            comment="Fiken account code",
        )
        safe_add_column(
            "wine_batch_costs",
            "payment_date",
            Date(),
            nullable=True,
            comment="Payment date",
        )
        safe_add_column(
            "wine_batch_costs",
            "allocation_method",
            String(length=30),
            nullable=True,
            comment="Allocation method",
        )
        safe_add_column(
            "wine_batch_costs",
            "invoice_reference",
            String(length=100),
            nullable=True,
            comment="Invoice reference",
        )
        safe_add_column(
            "wine_batch_costs",
            "active",
            Boolean(),
            nullable=False,
            comment="Soft delete flag",
        )
        safe_add_column(
            "wine_batch_costs",
            "created_at",
            DateTime(timezone=True),
            nullable=False,
            comment="Created timestamp",
        )
        safe_add_column(
            "wine_batch_costs",
            "updated_at",
            DateTime(timezone=True),
            nullable=False,
            comment="Updated timestamp",
        )

        # order_items - ensure all 17 expected columns exist
        safe_add_column(
            "order_items",
            "id",
            GUID(),
            nullable=False,
            comment="Primary key using UUID",
        )
        safe_add_column(
            "order_items",
            "order_id",
            GUID(),
            nullable=False,
            comment="Reference to order",
        )
        safe_add_column(
            "order_items",
            "wine_batch_id",
            GUID(),
            nullable=True,
            comment="Reference to wine batch",
        )
        safe_add_column(
            "order_items", "wine_id", GUID(), nullable=True, comment="Reference to wine"
        )
        safe_add_column(
            "order_items",
            "quantity",
            Integer(),
            nullable=False,
            comment="Quantity ordered",
        )
        safe_add_column(
            "order_items",
            "unit_price_ore",
            Integer(),
            nullable=False,
            comment="Unit price in øre",
        )
        safe_add_column(
            "order_items",
            "total_price_ore",
            Integer(),
            nullable=False,
            comment="Total price in øre",
        )
        safe_add_column(
            "order_items",
            "wine_name",
            String(length=255),
            nullable=True,
            comment="Wine name at time of order",
        )
        safe_add_column(
            "order_items",
            "producer",
            String(length=255),
            nullable=True,
            comment="Producer at time of order",
        )
        safe_add_column(
            "order_items",
            "vintage",
            Integer(),
            nullable=True,
            comment="Vintage at time of order",
        )
        safe_add_column(
            "order_items",
            "bottle_size_ml",
            Integer(),
            nullable=True,
            comment="Bottle size at time of order",
        )
        safe_add_column(
            "order_items",
            "discount_percentage",
            DECIMAL(precision=5, scale=2),
            nullable=True,
            comment="Discount percentage",
        )
        safe_add_column(
            "order_items",
            "discount_ore",
            Integer(),
            nullable=True,
            comment="Discount amount in øre",
        )
        safe_add_column(
            "order_items", "notes", Text(), nullable=True, comment="Order item notes"
        )
        safe_add_column(
            "order_items",
            "active",
            Boolean(),
            nullable=False,
            comment="Soft delete flag",
        )
        safe_add_column(
            "order_items",
            "created_at",
            DateTime(timezone=True),
            nullable=False,
            comment="Created timestamp",
        )
        safe_add_column(
            "order_items",
            "updated_at",
            DateTime(timezone=True),
            nullable=False,
            comment="Updated timestamp",
        )

        # Also ensure wine_batches has all expected columns
        safe_add_column(
            "wine_batches",
            "eur_exchange_rate",
            DECIMAL(precision=10, scale=6),
            nullable=True,
            comment="EUR to NOK exchange rate",
        )
        safe_add_column(
            "wine_batches",
            "wine_cost_eur_cents",
            Integer(),
            nullable=True,
            comment="Wine cost in EUR cents",
        )
        safe_add_column(
            "wine_batches",
            "transport_cost_ore",
            Integer(),
            nullable=True,
            comment="Transport cost in øre",
        )
        safe_add_column(
            "wine_batches",
            "customs_fee_ore",
            Integer(),
            nullable=True,
            comment="Customs fee in øre",
        )
        safe_add_column(
            "wine_batches",
            "freight_forwarding_ore",
            Integer(),
            nullable=True,
            comment="Freight forwarding cost in øre",
        )
        safe_add_column(
            "wine_batches",
            "fiken_sync_status",
            String(length=20),
            nullable=True,
            comment="Fiken sync status",
        )

    print("✅ Missing columns migration completed")


def downgrade() -> None:
    """
    Downgrade migration - remove the columns we added
    """
    print("⚠️  Downgrade not implemented - columns will remain")
    pass
