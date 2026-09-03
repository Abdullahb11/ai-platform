"""add context_snapshots table and messages.token_count

Revision ID: 4534f0bc56cf
Revises: 7df6f3e9a4c1
Create Date: 2026-09-02

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "4534f0bc56cf"
down_revision: Union[str, Sequence[str], None] = "7df6f3e9a4c1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add nullable token_count to messages.
    # Existing rows remain NULL — we never fabricate token counts for historical messages.
    op.add_column(
        "messages",
        sa.Column("token_count", sa.Integer(), nullable=True),
    )

    # Create the context_snapshots table.
    # References messages by FK (SET NULL on delete so snapshot survives if a message is removed).
    op.create_table(
        "context_snapshots",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("conversation_id", sa.Uuid(), nullable=False),
        sa.Column("trigger_message_id", sa.Uuid(), nullable=True),
        sa.Column("start_message_id", sa.Uuid(), nullable=True),
        sa.Column("end_message_id", sa.Uuid(), nullable=True),
        sa.Column("context_token_count", sa.Integer(), nullable=False),
        sa.Column("context_limit_tokens", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["conversation_id"],
            ["conversations.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["trigger_message_id"],
            ["messages.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["start_message_id"],
            ["messages.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["end_message_id"],
            ["messages.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_context_snapshots_conversation_id",
        "context_snapshots",
        ["conversation_id"],
        unique=False,
    )
    op.create_index(
        "ix_context_snapshots_created_at",
        "context_snapshots",
        ["created_at"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_context_snapshots_created_at", table_name="context_snapshots")
    op.drop_index("ix_context_snapshots_conversation_id", table_name="context_snapshots")
    op.drop_table("context_snapshots")
    op.drop_column("messages", "token_count")
