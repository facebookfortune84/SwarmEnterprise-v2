"""Phase 2 schema additions — notifications, messages, tickets, workflows.

Revision ID: 0002
Revises: 0001
Create Date: 2024-06-01 00:00:00.000000

Adds Phase 2 tables:
  - notifications
  - message_threads
  - messages
  - ticket_history
  - ticket_comments
  - workflows
  - workflow_steps

Also adds Phase 2 columns to the existing tickets table:
  priority, assignee_id, reporter_id, due_date, resolved_at, sla_hours,
  tags, parent_ticket_id, estimated_hours, actual_hours
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# ---------------------------------------------------------------------------
# Revision identifiers
# ---------------------------------------------------------------------------
revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── notifications ────────────────────────────────────────────────────────
    op.create_table(
        "notifications",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("type", sa.String(), nullable=True),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("is_read", sa.Boolean(), nullable=True),
        sa.Column("metadata_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_notifications_user_id", "notifications", ["user_id"], unique=False)

    # ── message_threads ──────────────────────────────────────────────────────
    op.create_table(
        "message_threads",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("subject", sa.String(), nullable=False),
        sa.Column("participants_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    # ── messages ─────────────────────────────────────────────────────────────
    op.create_table(
        "messages",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("thread_id", sa.String(), nullable=False),
        sa.Column("sender_id", sa.String(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("is_read", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["thread_id"], ["message_threads.id"]),
        sa.ForeignKeyConstraint(["sender_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_messages_thread_id", "messages", ["thread_id"], unique=False)

    # ── ticket_history ────────────────────────────────────────────────────────
    op.create_table(
        "ticket_history",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("ticket_id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=True),
        sa.Column("action", sa.String(), nullable=False),
        sa.Column("old_value", sa.Text(), nullable=True),
        sa.Column("new_value", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["ticket_id"], ["tickets.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ticket_history_ticket_id", "ticket_history", ["ticket_id"], unique=False)

    # ── ticket_comments ───────────────────────────────────────────────────────
    op.create_table(
        "ticket_comments",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("ticket_id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["ticket_id"], ["tickets.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ticket_comments_ticket_id", "ticket_comments", ["ticket_id"], unique=False)

    # ── workflows ─────────────────────────────────────────────────────────────
    op.create_table(
        "workflows",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("company_id", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=True),
        sa.Column("current_step", sa.Integer(), nullable=True),
        sa.Column("steps_json", sa.Text(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["company_id"], ["company_tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    # ── workflow_steps ────────────────────────────────────────────────────────
    op.create_table(
        "workflow_steps",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("workflow_id", sa.String(), nullable=False),
        sa.Column("step_name", sa.String(), nullable=False),
        sa.Column("step_type", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=True),
        sa.Column("input_json", sa.Text(), nullable=True),
        sa.Column("output_json", sa.Text(), nullable=True),
        sa.Column("retry_count", sa.Integer(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["workflow_id"], ["workflows.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_workflow_steps_workflow_id", "workflow_steps", ["workflow_id"], unique=False
    )

    # ── tickets — Phase 2 columns (use batch mode for SQLite compatibility) ───
    with op.batch_alter_table("tickets") as batch_op:
        batch_op.add_column(sa.Column("priority", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("assignee_id", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("reporter_id", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("due_date", sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column("resolved_at", sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column("sla_hours", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("tags", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("parent_ticket_id", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("estimated_hours", sa.Float(), nullable=True))
        batch_op.add_column(sa.Column("actual_hours", sa.Float(), nullable=True))


def downgrade() -> None:
    # Remove Phase 2 columns from tickets
    with op.batch_alter_table("tickets") as batch_op:
        for col in [
            "actual_hours",
            "estimated_hours",
            "parent_ticket_id",
            "tags",
            "sla_hours",
            "resolved_at",
            "due_date",
            "reporter_id",
            "assignee_id",
            "priority",
        ]:
            batch_op.drop_column(col)

    op.drop_index("ix_workflow_steps_workflow_id", table_name="workflow_steps")
    op.drop_table("workflow_steps")
    op.drop_table("workflows")

    op.drop_index("ix_ticket_comments_ticket_id", table_name="ticket_comments")
    op.drop_table("ticket_comments")

    op.drop_index("ix_ticket_history_ticket_id", table_name="ticket_history")
    op.drop_table("ticket_history")

    op.drop_index("ix_messages_thread_id", table_name="messages")
    op.drop_table("messages")

    op.drop_table("message_threads")

    op.drop_index("ix_notifications_user_id", table_name="notifications")
    op.drop_table("notifications")
