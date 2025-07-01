"""Complete wine_batch_costs and order_items tables

Revision ID: 15d72e03b4c4
Revises: 658e8e8aaf8d
Create Date: 2025-06-24 00:30:02.652968

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
revision = "15d72e03b4c4"
down_revision = "658e8e8aaf8d"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Complete the missing tables and columns for wine_batch_costs and order_items
    """

    # Get the database dialect
    bind = op.get_bind()
    is_sqlite = bind.dialect.name == "sqlite"

    if is_sqlite:
        # SQLite-compatible implementation
        print("🔧 Creating SQLite-compatible tables...")

        # Create wine_batch_costs table
        try:
            op.create_table(
                "wine_batch_costs",
                sa.Column(
                    "id",
                    String(length=36),
                    nullable=False,
                    comment="Primary key using UUID",
                ),
                sa.Column(
                    "batch_id",
                    String(length=36),
                    nullable=False,
                    comment="Reference to wine batch",
                ),
                sa.Column(
                    "cost_type",
                    String(length=50),
                    nullable=False,
                    comment="Type of cost (wine, transport, customs, etc.)",
                ),
                sa.Column(
                    "amount_ore",
                    Integer(),
                    nullable=False,
                    comment="Cost amount in øre",
                ),
                sa.Column(
                    "currency",
                    String(length=3),
                    nullable=True,
                    comment="Currency code (NOK, EUR, USD)",
                ),
                sa.Column(
                    "fiken_account_code",
                    String(length=20),
                    nullable=True,
                    comment="Fiken accounting code",
                ),
                sa.Column(
                    "payment_date",
                    Date(),
                    nullable=True,
                    comment="Date payment was made",
                ),
                sa.Column(
                    "allocation_method",
                    String(length=30),
                    nullable=True,
                    comment="How cost is allocated",
                ),
                sa.Column(
                    "invoice_reference",
                    String(length=100),
                    nullable=True,
                    comment="Invoice or reference number",
                ),
                sa.Column(
                    "active", Boolean(), nullable=False, comment="Soft delete flag"
                ),
                sa.Column(
                    "created_at",
                    DateTime(),
                    nullable=False,
                    comment="Timestamp when record was created",
                ),
                sa.Column(
                    "updated_at",
                    DateTime(),
                    nullable=False,
                    comment="Timestamp when record was last updated",
                ),
                sa.PrimaryKeyConstraint("id"),
                comment="Wine batch cost breakdown for accounting",
            )
        except Exception as e:
            print(f"⚠️  wine_batch_costs table might already exist: {e}")

        # Create wine_inventory table
        try:
            op.create_table(
                "wine_inventory",
                sa.Column(
                    "id",
                    String(length=36),
                    nullable=False,
                    comment="Primary key using UUID",
                ),
                sa.Column(
                    "wine_id",
                    String(length=36),
                    nullable=True,
                    comment="Reference to wine",
                ),
                sa.Column(
                    "batch_id",
                    String(length=36),
                    nullable=True,
                    comment="Reference to wine batch",
                ),
                sa.Column(
                    "quantity_available",
                    Integer(),
                    nullable=False,
                    comment="Available quantity",
                ),
                sa.Column(
                    "quantity_reserved",
                    Integer(),
                    nullable=False,
                    comment="Reserved quantity",
                ),
                sa.Column(
                    "quantity_sold", Integer(), nullable=False, comment="Sold quantity"
                ),
                sa.Column(
                    "cost_per_bottle_ore",
                    Integer(),
                    nullable=False,
                    comment="Cost per bottle in øre",
                ),
                sa.Column(
                    "selling_price_ore",
                    Integer(),
                    nullable=False,
                    comment="Selling price per bottle in øre",
                ),
                sa.Column(
                    "markup_percentage",
                    DECIMAL(precision=5, scale=2),
                    nullable=True,
                    comment="Markup percentage",
                ),
                sa.Column(
                    "margin_per_bottle_ore",
                    Integer(),
                    nullable=True,
                    comment="Margin per bottle in øre",
                ),
                sa.Column(
                    "minimum_stock_level",
                    Integer(),
                    nullable=True,
                    comment="Minimum stock alert level",
                ),
                sa.Column(
                    "location",
                    String(length=100),
                    nullable=True,
                    comment="Storage location",
                ),
                sa.Column(
                    "best_before_date",
                    Date(),
                    nullable=True,
                    comment="Best before date",
                ),
                sa.Column(
                    "low_stock_alert",
                    Boolean(),
                    nullable=False,
                    comment="Low stock alert flag",
                ),
                sa.Column(
                    "active", Boolean(), nullable=False, comment="Soft delete flag"
                ),
                sa.Column(
                    "created_at",
                    DateTime(),
                    nullable=False,
                    comment="Timestamp when record was created",
                ),
                sa.Column(
                    "updated_at",
                    DateTime(),
                    nullable=False,
                    comment="Timestamp when record was last updated",
                ),
                sa.PrimaryKeyConstraint("id"),
                comment="Wine inventory tracking",
            )
        except Exception as e:
            print(f"⚠️  wine_inventory table might already exist: {e}")

        # Create customers table
        try:
            op.create_table(
                "customers",
                sa.Column(
                    "id",
                    String(length=36),
                    nullable=False,
                    comment="Primary key using UUID",
                ),
                sa.Column(
                    "name", String(length=255), nullable=False, comment="Customer name"
                ),
                sa.Column(
                    "customer_type",
                    String(length=50),
                    nullable=False,
                    comment="Customer type (restaurant, retail, etc.)",
                ),
                sa.Column(
                    "email",
                    String(length=255),
                    nullable=True,
                    comment="Primary email address",
                ),
                sa.Column(
                    "phone",
                    String(length=50),
                    nullable=True,
                    comment="Primary phone number",
                ),
                sa.Column(
                    "address_line1",
                    String(length=255),
                    nullable=True,
                    comment="Address line 1",
                ),
                sa.Column(
                    "address_line2",
                    String(length=255),
                    nullable=True,
                    comment="Address line 2",
                ),
                sa.Column(
                    "postal_code",
                    String(length=20),
                    nullable=True,
                    comment="Postal code",
                ),
                sa.Column("city", String(length=100), nullable=True, comment="City"),
                sa.Column(
                    "country", String(length=100), nullable=True, comment="Country"
                ),
                sa.Column(
                    "organization_number",
                    String(length=50),
                    nullable=True,
                    comment="Organization number",
                ),
                sa.Column(
                    "vat_number", String(length=50), nullable=True, comment="VAT number"
                ),
                sa.Column(
                    "preferred_delivery_method",
                    String(length=50),
                    nullable=True,
                    comment="Preferred delivery method",
                ),
                sa.Column(
                    "payment_terms",
                    Integer(),
                    nullable=True,
                    comment="Payment terms in days",
                ),
                sa.Column(
                    "credit_limit_nok_ore",
                    Integer(),
                    nullable=True,
                    comment="Credit limit in NOK øre",
                ),
                sa.Column(
                    "marketing_consent",
                    Boolean(),
                    nullable=False,
                    comment="Marketing consent flag",
                ),
                sa.Column(
                    "newsletter_subscription",
                    Boolean(),
                    nullable=False,
                    comment="Newsletter subscription flag",
                ),
                sa.Column(
                    "preferred_language",
                    String(length=10),
                    nullable=True,
                    comment="Preferred language code",
                ),
                sa.Column("notes", Text(), nullable=True, comment="Customer notes"),
                sa.Column(
                    "fiken_customer_id",
                    Integer(),
                    nullable=True,
                    comment="Fiken customer ID",
                ),
                sa.Column(
                    "active", Boolean(), nullable=False, comment="Soft delete flag"
                ),
                sa.Column(
                    "created_at",
                    DateTime(),
                    nullable=False,
                    comment="Timestamp when record was created",
                ),
                sa.Column(
                    "updated_at",
                    DateTime(),
                    nullable=False,
                    comment="Timestamp when record was last updated",
                ),
                sa.PrimaryKeyConstraint("id"),
                comment="Customer information",
            )
        except Exception as e:
            print(f"⚠️  customers table might already exist: {e}")

        # Create orders table
        try:
            op.create_table(
                "orders",
                sa.Column(
                    "id",
                    String(length=36),
                    nullable=False,
                    comment="Primary key using UUID",
                ),
                sa.Column(
                    "order_number",
                    String(length=50),
                    nullable=False,
                    comment="Order number",
                ),
                sa.Column(
                    "customer_id",
                    String(length=36),
                    nullable=False,
                    comment="Reference to customer",
                ),
                sa.Column(
                    "status", String(length=30), nullable=False, comment="Order status"
                ),
                sa.Column(
                    "payment_status",
                    String(length=30),
                    nullable=False,
                    comment="Payment status",
                ),
                sa.Column("order_date", Date(), nullable=False, comment="Order date"),
                sa.Column(
                    "requested_delivery_date",
                    Date(),
                    nullable=True,
                    comment="Requested delivery date",
                ),
                sa.Column(
                    "confirmed_delivery_date",
                    Date(),
                    nullable=True,
                    comment="Confirmed delivery date",
                ),
                sa.Column(
                    "delivered_date",
                    Date(),
                    nullable=True,
                    comment="Actual delivery date",
                ),
                sa.Column(
                    "delivery_method",
                    String(length=50),
                    nullable=True,
                    comment="Delivery method",
                ),
                sa.Column(
                    "delivery_address_line1",
                    String(length=255),
                    nullable=True,
                    comment="Delivery address line 1",
                ),
                sa.Column(
                    "delivery_address_line2",
                    String(length=255),
                    nullable=True,
                    comment="Delivery address line 2",
                ),
                sa.Column(
                    "delivery_postal_code",
                    String(length=20),
                    nullable=True,
                    comment="Delivery postal code",
                ),
                sa.Column(
                    "delivery_city",
                    String(length=100),
                    nullable=True,
                    comment="Delivery city",
                ),
                sa.Column(
                    "delivery_country",
                    String(length=100),
                    nullable=True,
                    comment="Delivery country",
                ),
                sa.Column(
                    "delivery_notes", Text(), nullable=True, comment="Delivery notes"
                ),
                sa.Column(
                    "subtotal_ore", Integer(), nullable=False, comment="Subtotal in øre"
                ),
                sa.Column(
                    "delivery_fee_ore",
                    Integer(),
                    nullable=True,
                    comment="Delivery fee in øre",
                ),
                sa.Column(
                    "discount_ore", Integer(), nullable=True, comment="Discount in øre"
                ),
                sa.Column(
                    "vat_ore", Integer(), nullable=False, comment="VAT amount in øre"
                ),
                sa.Column(
                    "total_ore",
                    Integer(),
                    nullable=False,
                    comment="Total amount in øre",
                ),
                sa.Column(
                    "payment_terms",
                    Integer(),
                    nullable=True,
                    comment="Payment terms in days",
                ),
                sa.Column(
                    "payment_due_date",
                    Date(),
                    nullable=True,
                    comment="Payment due date",
                ),
                sa.Column(
                    "customer_notes", Text(), nullable=True, comment="Customer notes"
                ),
                sa.Column(
                    "internal_notes", Text(), nullable=True, comment="Internal notes"
                ),
                sa.Column(
                    "fiken_order_id", Integer(), nullable=True, comment="Fiken order ID"
                ),
                sa.Column(
                    "fiken_invoice_number",
                    String(length=50),
                    nullable=True,
                    comment="Fiken invoice number",
                ),
                sa.Column(
                    "active", Boolean(), nullable=False, comment="Soft delete flag"
                ),
                sa.Column(
                    "created_at",
                    DateTime(),
                    nullable=False,
                    comment="Timestamp when record was created",
                ),
                sa.Column(
                    "updated_at",
                    DateTime(),
                    nullable=False,
                    comment="Timestamp when record was last updated",
                ),
                sa.PrimaryKeyConstraint("id"),
                comment="Customer orders",
            )
        except Exception as e:
            print(f"⚠️  orders table might already exist: {e}")

        # Create order_items table
        try:
            op.create_table(
                "order_items",
                sa.Column(
                    "id",
                    String(length=36),
                    nullable=False,
                    comment="Primary key using UUID",
                ),
                sa.Column(
                    "order_id",
                    String(length=36),
                    nullable=False,
                    comment="Reference to order",
                ),
                sa.Column(
                    "wine_batch_id",
                    String(length=36),
                    nullable=True,
                    comment="Reference to wine batch",
                ),
                sa.Column(
                    "wine_id",
                    String(length=36),
                    nullable=True,
                    comment="Reference to wine",
                ),
                sa.Column(
                    "quantity", Integer(), nullable=False, comment="Quantity ordered"
                ),
                sa.Column(
                    "unit_price_ore",
                    Integer(),
                    nullable=False,
                    comment="Unit price in øre",
                ),
                sa.Column(
                    "total_price_ore",
                    Integer(),
                    nullable=False,
                    comment="Total price in øre",
                ),
                sa.Column(
                    "wine_name",
                    String(length=255),
                    nullable=True,
                    comment="Wine name at time of order",
                ),
                sa.Column(
                    "producer",
                    String(length=255),
                    nullable=True,
                    comment="Producer at time of order",
                ),
                sa.Column(
                    "vintage",
                    Integer(),
                    nullable=True,
                    comment="Vintage at time of order",
                ),
                sa.Column(
                    "bottle_size_ml",
                    Integer(),
                    nullable=True,
                    comment="Bottle size at time of order",
                ),
                sa.Column(
                    "discount_percentage",
                    DECIMAL(precision=5, scale=2),
                    nullable=True,
                    comment="Discount percentage",
                ),
                sa.Column(
                    "discount_ore",
                    Integer(),
                    nullable=True,
                    comment="Discount amount in øre",
                ),
                sa.Column("notes", Text(), nullable=True, comment="Order item notes"),
                sa.Column(
                    "active", Boolean(), nullable=False, comment="Soft delete flag"
                ),
                sa.Column(
                    "created_at",
                    DateTime(),
                    nullable=False,
                    comment="Timestamp when record was created",
                ),
                sa.Column(
                    "updated_at",
                    DateTime(),
                    nullable=False,
                    comment="Timestamp when record was last updated",
                ),
                sa.PrimaryKeyConstraint("id"),
                comment="Order line items",
            )
        except Exception as e:
            print(f"⚠️  order_items table might already exist: {e}")

        print("✅ SQLite tables created successfully")

    else:
        # PostgreSQL implementation with full features
        print("🔧 Creating PostgreSQL tables...")

        # Create wine_batch_costs table
        op.create_table(
            "wine_batch_costs",
            sa.Column("id", GUID(), nullable=False, comment="Primary key using UUID"),
            sa.Column(
                "batch_id", GUID(), nullable=False, comment="Reference to wine batch"
            ),
            sa.Column(
                "cost_type",
                String(length=50),
                nullable=False,
                comment="Type of cost (wine, transport, customs, etc.)",
            ),
            sa.Column(
                "amount_ore", Integer(), nullable=False, comment="Cost amount in øre"
            ),
            sa.Column(
                "currency",
                String(length=3),
                nullable=True,
                comment="Currency code (NOK, EUR, USD)",
            ),
            sa.Column(
                "fiken_account_code",
                String(length=20),
                nullable=True,
                comment="Fiken accounting code",
            ),
            sa.Column(
                "payment_date", Date(), nullable=True, comment="Date payment was made"
            ),
            sa.Column(
                "allocation_method",
                String(length=30),
                nullable=True,
                comment="How cost is allocated",
            ),
            sa.Column(
                "invoice_reference",
                String(length=100),
                nullable=True,
                comment="Invoice or reference number",
            ),
            sa.Column("active", Boolean(), nullable=False, comment="Soft delete flag"),
            sa.Column(
                "created_at",
                DateTime(timezone=True),
                nullable=False,
                comment="Timestamp when record was created",
            ),
            sa.Column(
                "updated_at",
                DateTime(timezone=True),
                nullable=False,
                comment="Timestamp when record was last updated",
            ),
            sa.PrimaryKeyConstraint("id"),
            comment="Wine batch cost breakdown for accounting",
        )

        # Create wine_inventory table
        op.create_table(
            "wine_inventory",
            sa.Column("id", GUID(), nullable=False, comment="Primary key using UUID"),
            sa.Column("wine_id", GUID(), nullable=True, comment="Reference to wine"),
            sa.Column(
                "batch_id", GUID(), nullable=True, comment="Reference to wine batch"
            ),
            sa.Column(
                "quantity_available",
                Integer(),
                nullable=False,
                comment="Available quantity",
            ),
            sa.Column(
                "quantity_reserved",
                Integer(),
                nullable=False,
                comment="Reserved quantity",
            ),
            sa.Column(
                "quantity_sold", Integer(), nullable=False, comment="Sold quantity"
            ),
            sa.Column(
                "cost_per_bottle_ore",
                Integer(),
                nullable=False,
                comment="Cost per bottle in øre",
            ),
            sa.Column(
                "selling_price_ore",
                Integer(),
                nullable=False,
                comment="Selling price per bottle in øre",
            ),
            sa.Column(
                "markup_percentage",
                DECIMAL(precision=5, scale=2),
                nullable=True,
                comment="Markup percentage",
            ),
            sa.Column(
                "margin_per_bottle_ore",
                Integer(),
                nullable=True,
                comment="Margin per bottle in øre",
            ),
            sa.Column(
                "minimum_stock_level",
                Integer(),
                nullable=True,
                comment="Minimum stock alert level",
            ),
            sa.Column(
                "location",
                String(length=100),
                nullable=True,
                comment="Storage location",
            ),
            sa.Column(
                "best_before_date", Date(), nullable=True, comment="Best before date"
            ),
            sa.Column(
                "low_stock_alert",
                Boolean(),
                nullable=False,
                comment="Low stock alert flag",
            ),
            sa.Column("active", Boolean(), nullable=False, comment="Soft delete flag"),
            sa.Column(
                "created_at",
                DateTime(timezone=True),
                nullable=False,
                comment="Timestamp when record was created",
            ),
            sa.Column(
                "updated_at",
                DateTime(timezone=True),
                nullable=False,
                comment="Timestamp when record was last updated",
            ),
            sa.PrimaryKeyConstraint("id"),
            comment="Wine inventory tracking",
        )

        # Create customers table
        op.create_table(
            "customers",
            sa.Column("id", GUID(), nullable=False, comment="Primary key using UUID"),
            sa.Column(
                "name", String(length=255), nullable=False, comment="Customer name"
            ),
            sa.Column(
                "customer_type",
                String(length=50),
                nullable=False,
                comment="Customer type (restaurant, retail, etc.)",
            ),
            sa.Column(
                "email",
                String(length=255),
                nullable=True,
                comment="Primary email address",
            ),
            sa.Column(
                "phone",
                String(length=50),
                nullable=True,
                comment="Primary phone number",
            ),
            sa.Column(
                "address_line1",
                String(length=255),
                nullable=True,
                comment="Address line 1",
            ),
            sa.Column(
                "address_line2",
                String(length=255),
                nullable=True,
                comment="Address line 2",
            ),
            sa.Column(
                "postal_code", String(length=20), nullable=True, comment="Postal code"
            ),
            sa.Column("city", String(length=100), nullable=True, comment="City"),
            sa.Column("country", String(length=100), nullable=True, comment="Country"),
            sa.Column(
                "organization_number",
                String(length=50),
                nullable=True,
                comment="Organization number",
            ),
            sa.Column(
                "vat_number", String(length=50), nullable=True, comment="VAT number"
            ),
            sa.Column(
                "preferred_delivery_method",
                String(length=50),
                nullable=True,
                comment="Preferred delivery method",
            ),
            sa.Column(
                "payment_terms",
                Integer(),
                nullable=True,
                comment="Payment terms in days",
            ),
            sa.Column(
                "credit_limit_nok_ore",
                Integer(),
                nullable=True,
                comment="Credit limit in NOK øre",
            ),
            sa.Column(
                "marketing_consent",
                Boolean(),
                nullable=False,
                comment="Marketing consent flag",
            ),
            sa.Column(
                "newsletter_subscription",
                Boolean(),
                nullable=False,
                comment="Newsletter subscription flag",
            ),
            sa.Column(
                "preferred_language",
                String(length=10),
                nullable=True,
                comment="Preferred language code",
            ),
            sa.Column("notes", Text(), nullable=True, comment="Customer notes"),
            sa.Column(
                "fiken_customer_id",
                Integer(),
                nullable=True,
                comment="Fiken customer ID",
            ),
            sa.Column("active", Boolean(), nullable=False, comment="Soft delete flag"),
            sa.Column(
                "created_at",
                DateTime(timezone=True),
                nullable=False,
                comment="Timestamp when record was created",
            ),
            sa.Column(
                "updated_at",
                DateTime(timezone=True),
                nullable=False,
                comment="Timestamp when record was last updated",
            ),
            sa.PrimaryKeyConstraint("id"),
            comment="Customer information",
        )

        # Create orders table
        op.create_table(
            "orders",
            sa.Column("id", GUID(), nullable=False, comment="Primary key using UUID"),
            sa.Column(
                "order_number",
                String(length=50),
                nullable=False,
                comment="Order number",
            ),
            sa.Column(
                "customer_id", GUID(), nullable=False, comment="Reference to customer"
            ),
            sa.Column(
                "status", String(length=30), nullable=False, comment="Order status"
            ),
            sa.Column(
                "payment_status",
                String(length=30),
                nullable=False,
                comment="Payment status",
            ),
            sa.Column("order_date", Date(), nullable=False, comment="Order date"),
            sa.Column(
                "requested_delivery_date",
                Date(),
                nullable=True,
                comment="Requested delivery date",
            ),
            sa.Column(
                "confirmed_delivery_date",
                Date(),
                nullable=True,
                comment="Confirmed delivery date",
            ),
            sa.Column(
                "delivered_date", Date(), nullable=True, comment="Actual delivery date"
            ),
            sa.Column(
                "delivery_method",
                String(length=50),
                nullable=True,
                comment="Delivery method",
            ),
            sa.Column(
                "delivery_address_line1",
                String(length=255),
                nullable=True,
                comment="Delivery address line 1",
            ),
            sa.Column(
                "delivery_address_line2",
                String(length=255),
                nullable=True,
                comment="Delivery address line 2",
            ),
            sa.Column(
                "delivery_postal_code",
                String(length=20),
                nullable=True,
                comment="Delivery postal code",
            ),
            sa.Column(
                "delivery_city",
                String(length=100),
                nullable=True,
                comment="Delivery city",
            ),
            sa.Column(
                "delivery_country",
                String(length=100),
                nullable=True,
                comment="Delivery country",
            ),
            sa.Column(
                "delivery_notes", Text(), nullable=True, comment="Delivery notes"
            ),
            sa.Column(
                "subtotal_ore", Integer(), nullable=False, comment="Subtotal in øre"
            ),
            sa.Column(
                "delivery_fee_ore",
                Integer(),
                nullable=True,
                comment="Delivery fee in øre",
            ),
            sa.Column(
                "discount_ore", Integer(), nullable=True, comment="Discount in øre"
            ),
            sa.Column(
                "vat_ore", Integer(), nullable=False, comment="VAT amount in øre"
            ),
            sa.Column(
                "total_ore", Integer(), nullable=False, comment="Total amount in øre"
            ),
            sa.Column(
                "payment_terms",
                Integer(),
                nullable=True,
                comment="Payment terms in days",
            ),
            sa.Column(
                "payment_due_date", Date(), nullable=True, comment="Payment due date"
            ),
            sa.Column(
                "customer_notes", Text(), nullable=True, comment="Customer notes"
            ),
            sa.Column(
                "internal_notes", Text(), nullable=True, comment="Internal notes"
            ),
            sa.Column(
                "fiken_order_id", Integer(), nullable=True, comment="Fiken order ID"
            ),
            sa.Column(
                "fiken_invoice_number",
                String(length=50),
                nullable=True,
                comment="Fiken invoice number",
            ),
            sa.Column("active", Boolean(), nullable=False, comment="Soft delete flag"),
            sa.Column(
                "created_at",
                DateTime(timezone=True),
                nullable=False,
                comment="Timestamp when record was created",
            ),
            sa.Column(
                "updated_at",
                DateTime(timezone=True),
                nullable=False,
                comment="Timestamp when record was last updated",
            ),
            sa.PrimaryKeyConstraint("id"),
            comment="Customer orders",
        )

        # Create order_items table
        op.create_table(
            "order_items",
            sa.Column("id", GUID(), nullable=False, comment="Primary key using UUID"),
            sa.Column("order_id", GUID(), nullable=False, comment="Reference to order"),
            sa.Column(
                "wine_batch_id",
                GUID(),
                nullable=True,
                comment="Reference to wine batch",
            ),
            sa.Column("wine_id", GUID(), nullable=True, comment="Reference to wine"),
            sa.Column(
                "quantity", Integer(), nullable=False, comment="Quantity ordered"
            ),
            sa.Column(
                "unit_price_ore", Integer(), nullable=False, comment="Unit price in øre"
            ),
            sa.Column(
                "total_price_ore",
                Integer(),
                nullable=False,
                comment="Total price in øre",
            ),
            sa.Column(
                "wine_name",
                String(length=255),
                nullable=True,
                comment="Wine name at time of order",
            ),
            sa.Column(
                "producer",
                String(length=255),
                nullable=True,
                comment="Producer at time of order",
            ),
            sa.Column(
                "vintage", Integer(), nullable=True, comment="Vintage at time of order"
            ),
            sa.Column(
                "bottle_size_ml",
                Integer(),
                nullable=True,
                comment="Bottle size at time of order",
            ),
            sa.Column(
                "discount_percentage",
                DECIMAL(precision=5, scale=2),
                nullable=True,
                comment="Discount percentage",
            ),
            sa.Column(
                "discount_ore",
                Integer(),
                nullable=True,
                comment="Discount amount in øre",
            ),
            sa.Column("notes", Text(), nullable=True, comment="Order item notes"),
            sa.Column("active", Boolean(), nullable=False, comment="Soft delete flag"),
            sa.Column(
                "created_at",
                DateTime(timezone=True),
                nullable=False,
                comment="Timestamp when record was created",
            ),
            sa.Column(
                "updated_at",
                DateTime(timezone=True),
                nullable=False,
                comment="Timestamp when record was last updated",
            ),
            sa.PrimaryKeyConstraint("id"),
            comment="Order line items",
        )

        # Create foreign key constraints
        op.create_foreign_key(
            None, "wine_batch_costs", "wine_batches", ["batch_id"], ["id"]
        )
        op.create_foreign_key(None, "wine_inventory", "wines", ["wine_id"], ["id"])
        op.create_foreign_key(
            None, "wine_inventory", "wine_batches", ["batch_id"], ["id"]
        )
        op.create_foreign_key(None, "orders", "customers", ["customer_id"], ["id"])
        op.create_foreign_key(None, "order_items", "orders", ["order_id"], ["id"])
        op.create_foreign_key(
            None, "order_items", "wine_batches", ["wine_batch_id"], ["id"]
        )
        op.create_foreign_key(None, "order_items", "wines", ["wine_id"], ["id"])

        print("✅ PostgreSQL tables created successfully")


def downgrade() -> None:
    """
    Downgrade the migration.
    """

    bind = op.get_bind()
    is_sqlite = bind.dialect.name == "sqlite"

    if is_sqlite:
        # For SQLite, drop tables
        try:
            op.drop_table("order_items")
        except Exception:
            pass
        try:
            op.drop_table("orders")
        except Exception:
            pass
        try:
            op.drop_table("customers")
        except Exception:
            pass
        try:
            op.drop_table("wine_inventory")
        except Exception:
            pass
        try:
            op.drop_table("wine_batch_costs")
        except Exception:
            pass
    else:
        # For PostgreSQL, drop constraints then tables
        op.drop_constraint(None, "order_items", type_="foreignkey")
        op.drop_constraint(None, "order_items", type_="foreignkey")
        op.drop_constraint(None, "order_items", type_="foreignkey")
        op.drop_constraint(None, "orders", type_="foreignkey")
        op.drop_constraint(None, "wine_inventory", type_="foreignkey")
        op.drop_constraint(None, "wine_inventory", type_="foreignkey")
        op.drop_constraint(None, "wine_batch_costs", type_="foreignkey")

        op.drop_table("order_items")
        op.drop_table("orders")
        op.drop_table("customers")
        op.drop_table("wine_inventory")
        op.drop_table("wine_batch_costs")
