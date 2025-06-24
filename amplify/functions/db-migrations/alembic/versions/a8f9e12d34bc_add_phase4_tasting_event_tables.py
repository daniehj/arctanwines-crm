"""add_phase4_tasting_event_tables

Revision ID: a8f9e12d34bc
Revises: 62828d0c71cb
Create Date: 2024-12-19 16:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import String, Integer, Date, Time, Text, Boolean, DECIMAL
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision = "a8f9e12d34bc"
down_revision = "62828d0c71cb"
branch_labels = None
depends_on = None


def get_dialect_name():
    """Get the current database dialect name"""
    try:
        bind = op.get_bind()
        return bind.dialect.name
    except Exception:
        return "sqlite"  # Default to SQLite for safety


def upgrade() -> None:
    """Create Phase 4 tasting event tables"""

    dialect_name = get_dialect_name()
    print(f"Creating Phase 4 tasting tables for dialect: {dialect_name}")

    # Use TEXT for JSONB in SQLite, JSONB for PostgreSQL
    json_type = JSONB() if dialect_name == "postgresql" else Text()

    # Create wine_tastings table
    try:
        op.create_table(
            "wine_tastings",
            sa.Column(
                "id",
                String(length=36),
                nullable=False,
                comment="Primary key using UUID",
            ),
            sa.Column(
                "event_name",
                String(length=255),
                nullable=False,
                comment="Name of the tasting event",
            ),
            sa.Column(
                "event_date", Date(), nullable=False, comment="Date of the event"
            ),
            sa.Column(
                "event_time", Time(), nullable=True, comment="Start time of the event"
            ),
            sa.Column(
                "venue_type", String(length=50), nullable=False, comment="Type of venue"
            ),
            sa.Column(
                "venue_name",
                String(length=255),
                nullable=True,
                comment="Name of the venue",
            ),
            sa.Column(
                "venue_address", Text(), nullable=True, comment="Full venue address"
            ),
            sa.Column(
                "venue_cost_ore",
                Integer(),
                nullable=True,
                comment="Venue rental cost in NOK øre",
            ),
            sa.Column(
                "max_attendees",
                Integer(),
                nullable=True,
                comment="Maximum number of attendees",
            ),
            sa.Column(
                "actual_attendees",
                Integer(),
                nullable=True,
                comment="Actual number of attendees",
            ),
            sa.Column(
                "event_type", String(length=50), nullable=False, comment="Type of event"
            ),
            sa.Column(
                "event_status",
                String(length=50),
                nullable=True,
                comment="Current status",
            ),
            sa.Column(
                "target_customer_segment",
                String(length=100),
                nullable=True,
                comment="Target customer segment",
            ),
            sa.Column(
                "marketing_objective",
                Text(),
                nullable=True,
                comment="Marketing objective for the event",
            ),
            sa.Column(
                "total_event_cost_ore",
                Integer(),
                nullable=True,
                comment="Total cost of event in NOK øre",
            ),
            sa.Column(
                "estimated_revenue_impact_ore",
                Integer(),
                nullable=True,
                comment="Estimated revenue impact in NOK øre",
            ),
            sa.Column(
                "actual_revenue_impact_ore",
                Integer(),
                nullable=True,
                comment="Actual revenue impact in NOK øre",
            ),
            sa.Column(
                "notes", Text(), nullable=True, comment="General notes about the event"
            ),
            sa.Column("active", Boolean(), nullable=False, comment="Soft delete flag"),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                comment="Timestamp when record was created",
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                nullable=False,
                comment="Timestamp when record was last updated",
            ),
            sa.PrimaryKeyConstraint("id"),
        )
        print("✅ Created wine_tastings table")
    except Exception as e:
        print(f"⚠️  Error creating wine_tastings table: {e}")

    # Create tasting_attendees table
    try:
        op.create_table(
            "tasting_attendees",
            sa.Column(
                "id",
                String(length=36),
                nullable=False,
                comment="Primary key using UUID",
            ),
            sa.Column(
                "tasting_id",
                String(length=36),
                nullable=False,
                comment="Reference to tasting event",
            ),
            sa.Column(
                "customer_id",
                String(length=36),
                nullable=True,
                comment="Reference to existing customer",
            ),
            sa.Column(
                "attendee_name",
                String(length=255),
                nullable=False,
                comment="Name of attendee",
            ),
            sa.Column(
                "attendee_email",
                String(length=255),
                nullable=True,
                comment="Email address",
            ),
            sa.Column(
                "attendee_phone",
                String(length=50),
                nullable=True,
                comment="Phone number",
            ),
            sa.Column(
                "attendee_type",
                String(length=50),
                nullable=False,
                comment="Type of attendee",
            ),
            sa.Column(
                "rsvp_status", String(length=50), nullable=True, comment="RSVP status"
            ),
            sa.Column(
                "follow_up_required",
                Boolean(),
                nullable=True,
                comment="Requires follow-up",
            ),
            sa.Column(
                "post_event_interest_level",
                Integer(),
                nullable=True,
                comment="Interest level 1-5 after event",
            ),
            sa.Column(
                "potential_order_value_ore",
                Integer(),
                nullable=True,
                comment="Estimated potential order value in NOK øre",
            ),
            sa.Column("active", Boolean(), nullable=False, comment="Soft delete flag"),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                comment="Timestamp when record was created",
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                nullable=False,
                comment="Timestamp when record was last updated",
            ),
            sa.PrimaryKeyConstraint("id"),
        )

        # Add foreign key constraints
        if dialect_name == "postgresql":
            op.create_foreign_key(
                "fk_tasting_attendees_tasting",
                "tasting_attendees",
                "wine_tastings",
                ["tasting_id"],
                ["id"],
            )
            op.create_foreign_key(
                "fk_tasting_attendees_customer",
                "tasting_attendees",
                "customers",
                ["customer_id"],
                ["id"],
            )

        print("✅ Created tasting_attendees table")
    except Exception as e:
        print(f"⚠️  Error creating tasting_attendees table: {e}")

    # Create tasting_wines table
    try:
        op.create_table(
            "tasting_wines",
            sa.Column(
                "id",
                String(length=36),
                nullable=False,
                comment="Primary key using UUID",
            ),
            sa.Column(
                "tasting_id",
                String(length=36),
                nullable=False,
                comment="Reference to tasting event",
            ),
            sa.Column(
                "wine_id",
                String(length=36),
                nullable=True,
                comment="Reference to wine in catalog",
            ),
            sa.Column(
                "wine_name",
                String(length=255),
                nullable=True,
                comment="Wine name if not in catalog",
            ),
            sa.Column(
                "wine_producer",
                String(length=255),
                nullable=True,
                comment="Producer name",
            ),
            sa.Column("wine_vintage", Integer(), nullable=True, comment="Wine vintage"),
            sa.Column(
                "bottles_used",
                Integer(),
                nullable=False,
                comment="Number of bottles used",
            ),
            sa.Column(
                "wine_source",
                String(length=50),
                nullable=False,
                comment="Source of the wine",
            ),
            sa.Column(
                "cost_per_bottle_ore",
                Integer(),
                nullable=False,
                comment="Cost per bottle in NOK øre",
            ),
            sa.Column(
                "tasting_order",
                Integer(),
                nullable=True,
                comment="Order of presentation in tasting",
            ),
            sa.Column(
                "tasting_notes",
                Text(),
                nullable=True,
                comment="Tasting notes from event",
            ),
            sa.Column(
                "customer_feedback",
                json_type,
                nullable=True,
                comment="Customer feedback and ratings",
            ),
            sa.Column(
                "popularity_score",
                DECIMAL(precision=3, scale=2),
                nullable=True,
                comment="Popularity score 0.00-5.00",
            ),
            sa.Column(
                "follow_up_orders",
                Integer(),
                nullable=True,
                comment="Number of follow-up orders generated",
            ),
            sa.Column("active", Boolean(), nullable=False, comment="Soft delete flag"),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                comment="Timestamp when record was created",
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                nullable=False,
                comment="Timestamp when record was last updated",
            ),
            sa.PrimaryKeyConstraint("id"),
        )

        # Add foreign key constraints
        if dialect_name == "postgresql":
            op.create_foreign_key(
                "fk_tasting_wines_tasting",
                "tasting_wines",
                "wine_tastings",
                ["tasting_id"],
                ["id"],
            )
            op.create_foreign_key(
                "fk_tasting_wines_wine", "tasting_wines", "wines", ["wine_id"], ["id"]
            )

        print("✅ Created tasting_wines table")
    except Exception as e:
        print(f"⚠️  Error creating tasting_wines table: {e}")

    # Create tasting_costs table
    try:
        op.create_table(
            "tasting_costs",
            sa.Column(
                "id",
                String(length=36),
                nullable=False,
                comment="Primary key using UUID",
            ),
            sa.Column(
                "tasting_id",
                String(length=36),
                nullable=False,
                comment="Reference to tasting event",
            ),
            sa.Column(
                "cost_category",
                String(length=50),
                nullable=False,
                comment="Category: venue, catering, staff, materials, "
                "transportation, marketing",
            ),
            sa.Column(
                "cost_description",
                String(length=255),
                nullable=False,
                comment="Description of the cost",
            ),
            sa.Column(
                "supplier_name",
                String(length=255),
                nullable=True,
                comment="Name of supplier/vendor",
            ),
            sa.Column(
                "amount_ore",
                Integer(),
                nullable=False,
                comment="Cost amount in NOK øre",
            ),
            sa.Column(
                "cost_date",
                Date(),
                nullable=False,
                comment="Date when cost was incurred",
            ),
            sa.Column(
                "invoice_reference",
                String(length=100),
                nullable=True,
                comment="Invoice or reference number",
            ),
            sa.Column(
                "fiken_transaction_id",
                Integer(),
                nullable=True,
                comment="Fiken transaction ID for sync",
            ),
            sa.Column(
                "cost_type",
                String(length=20),
                nullable=True,
                comment="fixed or variable_per_person",
            ),
            sa.Column("active", Boolean(), nullable=False, comment="Soft delete flag"),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                comment="Timestamp when record was created",
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                nullable=False,
                comment="Timestamp when record was last updated",
            ),
            sa.PrimaryKeyConstraint("id"),
        )

        # Add foreign key constraints
        if dialect_name == "postgresql":
            op.create_foreign_key(
                "fk_tasting_costs_tasting",
                "tasting_costs",
                "wine_tastings",
                ["tasting_id"],
                ["id"],
            )

        print("✅ Created tasting_costs table")
    except Exception as e:
        print(f"⚠️  Error creating tasting_costs table: {e}")

    # Create tasting_outcomes table
    try:
        op.create_table(
            "tasting_outcomes",
            sa.Column(
                "id",
                String(length=36),
                nullable=False,
                comment="Primary key using UUID",
            ),
            sa.Column(
                "tasting_id",
                String(length=36),
                nullable=False,
                comment="Reference to tasting event",
            ),
            sa.Column(
                "customer_id",
                String(length=36),
                nullable=True,
                comment="Reference to customer",
            ),
            sa.Column(
                "outcome_type",
                String(length=50),
                nullable=False,
                comment="Type of outcome",
            ),
            sa.Column(
                "outcome_value_ore",
                Integer(),
                nullable=True,
                comment="Order value or estimated value in NOK øre",
            ),
            sa.Column(
                "outcome_date",
                Date(),
                nullable=False,
                comment="Date when outcome occurred",
            ),
            sa.Column(
                "notes", Text(), nullable=True, comment="Notes about the outcome"
            ),
            sa.Column("active", Boolean(), nullable=False, comment="Soft delete flag"),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                comment="Timestamp when record was created",
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                nullable=False,
                comment="Timestamp when record was last updated",
            ),
            sa.PrimaryKeyConstraint("id"),
        )

        # Add foreign key constraints
        if dialect_name == "postgresql":
            op.create_foreign_key(
                "fk_tasting_outcomes_tasting",
                "tasting_outcomes",
                "wine_tastings",
                ["tasting_id"],
                ["id"],
            )
            op.create_foreign_key(
                "fk_tasting_outcomes_customer",
                "tasting_outcomes",
                "customers",
                ["customer_id"],
                ["id"],
            )

        print("✅ Created tasting_outcomes table")
    except Exception as e:
        print(f"⚠️  Error creating tasting_outcomes table: {e}")

    print("🎉 Phase 4 tasting event tables created successfully!")


def downgrade() -> None:
    """Drop Phase 4 tasting event tables"""

    # Drop tables in reverse order to handle foreign key constraints
    tables_to_drop = [
        "tasting_outcomes",
        "tasting_costs",
        "tasting_wines",
        "tasting_attendees",
        "wine_tastings",
    ]

    for table_name in tables_to_drop:
        try:
            op.drop_table(table_name)
            print(f"✅ Dropped {table_name} table")
        except Exception as e:
            print(f"⚠️  Error dropping {table_name} table: {e}")

    print("🗑️  Phase 4 tasting event tables dropped successfully!")
