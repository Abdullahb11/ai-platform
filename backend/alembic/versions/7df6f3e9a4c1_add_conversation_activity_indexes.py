"""add conversation activity indexes

Revision ID: 7df6f3e9a4c1
Revises: 3517d49806f5
Create Date: 2026-08-31
"""

from typing import Sequence, Union

from alembic import op


revision: str = "7df6f3e9a4c1"
down_revision: Union[str, Sequence[str], None] = "3517d49806f5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "ix_conversations_updated_at_id",
        "conversations",
        ["updated_at", "id"],
        unique=False,
    )
    op.create_index(
        "ix_messages_conversation_created_at_id",
        "messages",
        ["conversation_id", "created_at", "id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_messages_conversation_created_at_id", table_name="messages")
    op.drop_index("ix_conversations_updated_at_id", table_name="conversations")
