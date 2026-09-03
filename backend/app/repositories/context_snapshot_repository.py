import uuid
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.context_snapshot import ContextSnapshot


class ContextSnapshotRepository:
    """Data access for context snapshots."""

    @staticmethod
    async def create(
        session: AsyncSession,
        conversation_id: uuid.UUID,
        request_message_id: uuid.UUID | None,
        assistant_message_id: uuid.UUID | None,
        request_start_message_id: uuid.UUID | None,
        request_end_message_id: uuid.UUID | None,
        request_token_count: int,
        current_start_message_id: uuid.UUID | None,
        current_end_message_id: uuid.UUID | None,
        current_token_count: int,
        context_limit_tokens: int,
    ) -> ContextSnapshot:
        snapshot = ContextSnapshot(
            id=uuid.uuid4(),
            conversation_id=conversation_id,
            request_message_id=request_message_id,
            assistant_message_id=assistant_message_id,
            request_start_message_id=request_start_message_id,
            request_end_message_id=request_end_message_id,
            request_token_count=request_token_count,
            current_start_message_id=current_start_message_id,
            current_end_message_id=current_end_message_id,
            current_token_count=current_token_count,
            context_limit_tokens=context_limit_tokens,
        )
        session.add(snapshot)
        await session.flush()
        return snapshot

    @staticmethod
    async def get_latest_by_conversation(
        session: AsyncSession,
        conversation_id: uuid.UUID,
    ) -> ContextSnapshot | None:
        result = await session.execute(
            select(ContextSnapshot)
            .where(ContextSnapshot.conversation_id == conversation_id)
            .order_by(desc(ContextSnapshot.created_at))
            .limit(1)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def list_by_conversation(
        session: AsyncSession,
        conversation_id: uuid.UUID,
    ) -> list[ContextSnapshot]:
        result = await session.execute(
            select(ContextSnapshot)
            .where(ContextSnapshot.conversation_id == conversation_id)
            .order_by(ContextSnapshot.created_at)
        )
        return list(result.scalars().all())
