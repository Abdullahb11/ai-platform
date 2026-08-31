import uuid
from datetime import datetime
from sqlalchemy import and_, desc, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.message import Message


class MessageRepository:
    """Data access for messages."""

    @staticmethod
    async def create(
        session: AsyncSession,
        conversation_id: uuid.UUID,
        role: str,
        content: str,
    ) -> Message:
        message = Message(
            id=uuid.uuid4(),
            conversation_id=conversation_id,
            role=role,
            content=content,
        )
        session.add(message)
        await session.flush()
        return message

    @staticmethod
    async def get_by_conversation(
        session: AsyncSession,
        conversation_id: uuid.UUID,
    ) -> list[Message]:
        result = await session.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at, Message.id)
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_page_by_conversation(
        session: AsyncSession,
        conversation_id: uuid.UUID,
        limit: int,
        before_created_at: datetime | None = None,
        before_id: uuid.UUID | None = None,
    ) -> list[Message]:
        """Return a chronological page, using a cursor that points before older rows."""
        statement = select(Message).where(Message.conversation_id == conversation_id)

        if before_created_at is not None and before_id is not None:
            statement = statement.where(
                or_(
                    Message.created_at < before_created_at,
                    and_(
                        Message.created_at == before_created_at,
                        Message.id < before_id,
                    ),
                )
            )

        result = await session.execute(
            statement
            .order_by(desc(Message.created_at), desc(Message.id))
            .limit(limit)
        )
        return list(reversed(result.scalars().all()))
