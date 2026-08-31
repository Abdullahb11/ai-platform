import uuid
from datetime import datetime
from sqlalchemy import and_, desc, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.conversation import Conversation


class ConversationRepository:
    """Data access for conversations."""

    @staticmethod
    async def create(session: AsyncSession, title: str | None = None) -> Conversation:
        conversation = Conversation(id=uuid.uuid4(), title=title)
        session.add(conversation)
        await session.flush()
        return conversation

    @staticmethod
    async def get_by_id(session: AsyncSession, conversation_id: uuid.UUID) -> Conversation | None:
        result = await session.execute(
            select(Conversation).where(Conversation.id == conversation_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def list(
        session: AsyncSession,
        limit: int,
        cursor_updated_at: datetime | None = None,
        cursor_id: uuid.UUID | None = None,
    ) -> list[Conversation]:
        """Return recent conversations, with an optional keyset cursor."""
        statement = select(Conversation)

        if cursor_updated_at is not None and cursor_id is not None:
            statement = statement.where(
                or_(
                    Conversation.updated_at < cursor_updated_at,
                    and_(
                        Conversation.updated_at == cursor_updated_at,
                        Conversation.id < cursor_id,
                    ),
                )
            )

        result = await session.execute(
            statement
            .order_by(desc(Conversation.updated_at), desc(Conversation.id))
            .limit(limit)
        )
        return list(result.scalars().all())

    @staticmethod
    async def update_title(
        session: AsyncSession,
        conversation: Conversation,
        title: str,
    ) -> Conversation:
        conversation.title = title
        await session.flush()
        return conversation

    @staticmethod
    async def delete(session: AsyncSession, conversation: Conversation) -> None:
        """Delete a conversation; PostgreSQL cascades deletion to its messages."""
        await session.delete(conversation)
        await session.flush()

    @staticmethod
    async def touch(session: AsyncSession, conversation_id: uuid.UUID) -> None:
        """Explicitly record message activity for recent-conversation ordering."""
        await session.execute(
            update(Conversation)
            .where(Conversation.id == conversation_id)
            .values(updated_at=func.now())
        )
