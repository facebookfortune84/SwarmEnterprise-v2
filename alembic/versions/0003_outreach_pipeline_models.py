"""Phase 3: Outreach pipeline models.

Revision ID: 0003
Revises: 0002
Create Date: 2024-07-01 00:00:00.000000

New tables:
  - sequences
  - sequence_enrollments
  - sequence_step_logs
  - outreach_daily_metrics
  - lead_timeline
  - processed_email_uids

New columns on leads:
  - website, linkedin_url, intent_score, needs_review, email_invalid
"""
from alembic import op
import sqlalchemy as sa

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── sequences ──────────────────────────────────────────────────────────
    op.create_table(
        "sequences",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("steps_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("status", sa.String(32), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )

    # ── sequence_enrollments ───────────────────────────────────────────────
    op.create_table(
        "sequence_enrollments",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("lead_id", sa.String(), sa.ForeignKey("leads.id"), nullable=False),
        sa.Column("sequence_id", sa.String(), sa.ForeignKey("sequences.id"), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="active"),
        sa.Column("current_step", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("enrolled_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("lead_id", "sequence_id", name="uq_enrollment_lead_sequence"),
    )
    op.create_index("ix_sequence_enrollments_lead_id", "sequence_enrollments", ["lead_id"])
    op.create_index(
        "ix_sequence_enrollments_sequence_id", "sequence_enrollments", ["sequence_id"]
    )

    # ── sequence_step_logs ─────────────────────────────────────────────────
    op.create_table(
        "sequence_step_logs",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column(
            "enrollment_id",
            sa.String(),
            sa.ForeignKey("sequence_enrollments.id"),
            nullable=False,
        ),
        sa.Column("step_index", sa.Integer(), nullable=False),
        sa.Column("outcome", sa.String(16), nullable=False),
        sa.Column("opens_tracked", sa.Boolean(), server_default="0"),
        sa.Column("opened", sa.Boolean(), server_default="0"),
        sa.Column("scheduled_at", sa.DateTime(), nullable=True),
        sa.Column("sent_at", sa.DateTime(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_index(
        "ix_sequence_step_logs_enrollment_id", "sequence_step_logs", ["enrollment_id"]
    )

    # ── outreach_daily_metrics ─────────────────────────────────────────────
    op.create_table(
        "outreach_daily_metrics",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("metric_name", sa.String(64), nullable=False),
        sa.Column("metric_value", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("date", "metric_name", name="uq_daily_metric_date_name"),
    )

    # ── lead_timeline ──────────────────────────────────────────────────────
    op.create_table(
        "lead_timeline",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("lead_id", sa.String(), sa.ForeignKey("leads.id"), nullable=False),
        sa.Column("from_status", sa.String(32), nullable=True),
        sa.Column("to_status", sa.String(32), nullable=False),
        sa.Column("triggered_by", sa.String(64), nullable=False),
        sa.Column("occurred_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_lead_timeline_lead_id", "lead_timeline", ["lead_id"])

    # ── processed_email_uids ───────────────────────────────────────────────
    op.create_table(
        "processed_email_uids",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("mailbox", sa.String(255), nullable=False),
        sa.Column("uid", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("mailbox", "uid", name="uq_processed_email_uid"),
    )

    # ── leads: add outreach-pipeline columns ──────────────────────────────
    with op.batch_alter_table("leads") as batch_op:
        batch_op.add_column(sa.Column("website", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("linkedin_url", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("intent_score", sa.Integer(), nullable=True))
        batch_op.add_column(
            sa.Column("needs_review", sa.Boolean(), nullable=True, server_default="0")
        )
        batch_op.add_column(
            sa.Column("email_invalid", sa.Boolean(), nullable=True, server_default="0")
        )


def downgrade() -> None:
    # Remove new leads columns
    with op.batch_alter_table("leads") as batch_op:
        batch_op.drop_column("email_invalid")
        batch_op.drop_column("needs_review")
        batch_op.drop_column("intent_score")
        batch_op.drop_column("linkedin_url")
        batch_op.drop_column("website")

    op.drop_table("processed_email_uids")
    op.drop_index("ix_lead_timeline_lead_id", "lead_timeline")
    op.drop_table("lead_timeline")
    op.drop_table("outreach_daily_metrics")
    op.drop_index("ix_sequence_step_logs_enrollment_id", "sequence_step_logs")
    op.drop_table("sequence_step_logs")
    op.drop_index("ix_sequence_enrollments_sequence_id", "sequence_enrollments")
    op.drop_index("ix_sequence_enrollments_lead_id", "sequence_enrollments")
    op.drop_table("sequence_enrollments")
    op.drop_table("sequences")
