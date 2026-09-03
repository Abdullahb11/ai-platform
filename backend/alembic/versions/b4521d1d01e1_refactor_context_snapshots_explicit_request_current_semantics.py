"""refactor context_snapshots for explicit request and current context semantics

Revision ID: b4521d1d01e1
Revises: 4534f0bc56cf
Create Date: 2026-09-02

The previous context_snapshots schema only represented a single "selected context"
(the request context). It was semantically ambiguous:
  - trigger_message_id pointed to the assistant response
  - end_message_id pointed to the last user message

This migration replaces the ambiguous columns with explicit semantics
for BOTH the request context AND the post-response current context:

  request_message_id    — the user message that triggered this Gemini request
  assistant_message_id  — the assistant response that Gemini produced
  request_start_message_id — first message Gemini received (oldest in request context)
  request_end_message_id   — last message Gemini received (= request_message_id)
  request_token_count      — authoritative count of the request context
  current_start_message_id — first message in post-response active context
  current_end_message_id   — last message in post-response active context (= assistant_message_id)
  current_token_count      — authoritative count of the current/post-response context
  context_limit_tokens     — configured limit at the time of this request (unchanged)

All FK references remain to messages.id with SET NULL on delete.
The old columns (trigger_message_id, start_message_id, end_message_id,
context_token_count) are dropped.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b4521d1d01e1"
down_revision: Union[str, Sequence[str], None] = "4534f0bc56cf"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Replace ambiguous context_snapshot columns with explicit request/current semantics."""

    # ── Drop old ambiguous columns ────────────────────────────────────────────
    op.drop_column("context_snapshots", "trigger_message_id")
    op.drop_column("context_snapshots", "start_message_id")
    op.drop_column("context_snapshots", "end_message_id")
    op.drop_column("context_snapshots", "context_token_count")

    # ── Add explicit request-context columns ──────────────────────────────────
    op.add_column(
        "context_snapshots",
        sa.Column("request_message_id", sa.Uuid(), nullable=True),
    )
    op.create_foreign_key(
        "fk_context_snapshots_request_message_id",
        "context_snapshots",
        "messages",
        ["request_message_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.add_column(
        "context_snapshots",
        sa.Column("assistant_message_id", sa.Uuid(), nullable=True),
    )
    op.create_foreign_key(
        "fk_context_snapshots_assistant_message_id",
        "context_snapshots",
        "messages",
        ["assistant_message_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.add_column(
        "context_snapshots",
        sa.Column("request_start_message_id", sa.Uuid(), nullable=True),
    )
    op.create_foreign_key(
        "fk_context_snapshots_request_start_message_id",
        "context_snapshots",
        "messages",
        ["request_start_message_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.add_column(
        "context_snapshots",
        sa.Column("request_end_message_id", sa.Uuid(), nullable=True),
    )
    op.create_foreign_key(
        "fk_context_snapshots_request_end_message_id",
        "context_snapshots",
        "messages",
        ["request_end_message_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.add_column(
        "context_snapshots",
        sa.Column("request_token_count", sa.Integer(), nullable=False, server_default="0"),
    )

    # ── Add explicit current/post-response context columns ────────────────────
    op.add_column(
        "context_snapshots",
        sa.Column("current_start_message_id", sa.Uuid(), nullable=True),
    )
    op.create_foreign_key(
        "fk_context_snapshots_current_start_message_id",
        "context_snapshots",
        "messages",
        ["current_start_message_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.add_column(
        "context_snapshots",
        sa.Column("current_end_message_id", sa.Uuid(), nullable=True),
    )
    op.create_foreign_key(
        "fk_context_snapshots_current_end_message_id",
        "context_snapshots",
        "messages",
        ["current_end_message_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.add_column(
        "context_snapshots",
        sa.Column("current_token_count", sa.Integer(), nullable=False, server_default="0"),
    )

    # Remove server defaults now that they are only needed for the ALTER TABLE
    op.alter_column("context_snapshots", "request_token_count", server_default=None)
    op.alter_column("context_snapshots", "current_token_count", server_default=None)


def downgrade() -> None:
    """Restore the original ambiguous columns."""
    # Drop new explicit columns
    op.drop_constraint("fk_context_snapshots_current_end_message_id", "context_snapshots", type_="foreignkey")
    op.drop_column("context_snapshots", "current_end_message_id")
    op.drop_constraint("fk_context_snapshots_current_start_message_id", "context_snapshots", type_="foreignkey")
    op.drop_column("context_snapshots", "current_start_message_id")
    op.drop_column("context_snapshots", "current_token_count")

    op.drop_constraint("fk_context_snapshots_request_end_message_id", "context_snapshots", type_="foreignkey")
    op.drop_column("context_snapshots", "request_end_message_id")
    op.drop_constraint("fk_context_snapshots_request_start_message_id", "context_snapshots", type_="foreignkey")
    op.drop_column("context_snapshots", "request_start_message_id")
    op.drop_constraint("fk_context_snapshots_assistant_message_id", "context_snapshots", type_="foreignkey")
    op.drop_column("context_snapshots", "assistant_message_id")
    op.drop_constraint("fk_context_snapshots_request_message_id", "context_snapshots", type_="foreignkey")
    op.drop_column("context_snapshots", "request_message_id")
    op.drop_column("context_snapshots", "request_token_count")

    # Restore old columns
    op.add_column(
        "context_snapshots",
        sa.Column("trigger_message_id", sa.Uuid(), nullable=True),
    )
    op.add_column(
        "context_snapshots",
        sa.Column("start_message_id", sa.Uuid(), nullable=True),
    )
    op.add_column(
        "context_snapshots",
        sa.Column("end_message_id", sa.Uuid(), nullable=True),
    )
    op.add_column(
        "context_snapshots",
        sa.Column("context_token_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.alter_column("context_snapshots", "context_token_count", server_default=None)
