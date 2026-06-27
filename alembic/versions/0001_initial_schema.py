"""Initial schema — all 9 application tables.

Revision ID: 0001
Revises: None
Create Date: 2024-01-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# ---------------------------------------------------------------------------
# Revision identifiers
# ---------------------------------------------------------------------------
revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# ---------------------------------------------------------------------------
# upgrade — create tables in FK dependency order
# ---------------------------------------------------------------------------
def upgrade() -> None:
    # 1. users (no FK dependencies)
    op.create_table(
        "users",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("password_hash", sa.String(), nullable=False),
        sa.Column("full_name", sa.String(), nullable=False),
        sa.Column("role", sa.String(), nullable=True),
        sa.Column("subscription_tier", sa.String(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)

    # 2. api_keys (FK → users)
    op.create_table(
        "api_keys",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("key", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("scope", sa.String(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=True),
        sa.Column("last_used_at", sa.DateTime(), nullable=True),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_api_keys_key"), "api_keys", ["key"], unique=True)
    op.create_index(op.f("ix_api_keys_user_id"), "api_keys", ["user_id"], unique=False)

    # 3. company_tenants (no FK dependencies)
    op.create_table(
        "company_tenants",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("slug", sa.String(), nullable=True),
        sa.Column("name", sa.String(), nullable=True),
        sa.Column("subdomain", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=True),
        sa.Column("vm_id", sa.String(), nullable=True),
        sa.Column("container_id", sa.String(), nullable=True),
        sa.Column("box_url", sa.String(), nullable=True),
        sa.Column("metadata_json", sa.Text(), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_company_tenants_slug"), "company_tenants", ["slug"], unique=True)
    op.create_index(
        op.f("ix_company_tenants_subdomain"),
        "company_tenants",
        ["subdomain"],
        unique=True,
    )

    # 4. deployments (FK → company_tenants)
    op.create_table(
        "deployments",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=True),
        sa.Column("strategy", sa.String(), nullable=True),
        sa.Column("version", sa.String(), nullable=True),
        sa.Column("metadata_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["company_tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_deployments_tenant_id"), "deployments", ["tenant_id"], unique=False)

    # 5. tickets (no FK dependencies)
    op.create_table(
        "tickets",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("project_id", sa.String(), nullable=True),
        sa.Column("department", sa.String(), nullable=True),
        sa.Column("title", sa.String(), nullable=True),
        sa.Column("instruction", sa.Text(), nullable=True),
        sa.Column("status", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_tickets_project_id"), "tickets", ["project_id"], unique=False)

    # 6. projects (no FK dependencies)
    op.create_table(
        "projects",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("stripe_session", sa.String(), nullable=True),
        sa.Column("customer_email", sa.String(), nullable=True),
        sa.Column("product_id", sa.String(), nullable=True),
        sa.Column("price_id", sa.String(), nullable=True),
        sa.Column("metadata_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    # 7. leads (no FK dependencies)
    op.create_table(
        "leads",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("email", sa.String(), nullable=True),
        sa.Column("name", sa.String(), nullable=True),
        sa.Column("company", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=True),
        sa.Column("metadata_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_leads_email"), "leads", ["email"], unique=False)

    # 8. usage_events (no FK dependencies)
    op.create_table(
        "usage_events",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("project_id", sa.String(), nullable=True),
        sa.Column("event_type", sa.String(), nullable=True),
        sa.Column("amount", sa.String(), nullable=True),
        sa.Column("metadata_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_usage_events_project_id"), "usage_events", ["project_id"], unique=False
    )

    # 9. processed_events (no FK dependencies)
    op.create_table(
        "processed_events",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("event_id", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_processed_events_event_id"),
        "processed_events",
        ["event_id"],
        unique=True,
    )


# ---------------------------------------------------------------------------
# downgrade — drop tables in exact reverse order
# ---------------------------------------------------------------------------
def downgrade() -> None:
    op.drop_index(op.f("ix_processed_events_event_id"), table_name="processed_events")
    op.drop_table("processed_events")

    op.drop_index(op.f("ix_usage_events_project_id"), table_name="usage_events")
    op.drop_table("usage_events")

    op.drop_index(op.f("ix_leads_email"), table_name="leads")
    op.drop_table("leads")

    op.drop_table("projects")

    op.drop_index(op.f("ix_tickets_project_id"), table_name="tickets")
    op.drop_table("tickets")

    op.drop_index(op.f("ix_deployments_tenant_id"), table_name="deployments")
    op.drop_table("deployments")

    op.drop_index(op.f("ix_company_tenants_subdomain"), table_name="company_tenants")
    op.drop_index(op.f("ix_company_tenants_slug"), table_name="company_tenants")
    op.drop_table("company_tenants")

    op.drop_index(op.f("ix_api_keys_user_id"), table_name="api_keys")
    op.drop_index(op.f("ix_api_keys_key"), table_name="api_keys")
    op.drop_table("api_keys")

    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")
