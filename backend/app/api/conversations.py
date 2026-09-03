import base64
import binascii
import json
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.repositories.conversation_repository import ConversationRepository
from app.repositories.message_repository import MessageRepository
from app.repositories.context_snapshot_repository import ContextSnapshotRepository
from app.schemas.conversation import (
    ConversationCreate,
    ConversationListResponse,
    ConversationResponse,
    ConversationUpdate,
)
from app.schemas.message import MessageListResponse
from app.schemas.context_snapshot import ContextHistoryResponse, ContextSnapshotResponse

router = APIRouter(prefix="/conversations", tags=["Conversations"])


def _encode_cursor(timestamp: datetime, record_id: uuid.UUID) -> str:
    payload = json.dumps({"timestamp": timestamp.isoformat(), "id": str(record_id)})
    return base64.urlsafe_b64encode(payload.encode("utf-8")).decode("ascii").rstrip("=")


def _decode_cursor(cursor: str) -> tuple[datetime, uuid.UUID]:
    try:
        padded = cursor + "=" * (-len(cursor) % 4)
        payload = json.loads(base64.urlsafe_b64decode(padded).decode("utf-8"))
        timestamp = datetime.fromisoformat(payload["timestamp"])
        record_id = uuid.UUID(payload["id"])
        if timestamp.tzinfo is None:
            raise ValueError("cursor timestamp must include a timezone")
        return timestamp, record_id
    except (
        KeyError,
        TypeError,
        ValueError,
        UnicodeDecodeError,
        json.JSONDecodeError,
        binascii.Error,
    ) as exc:
        raise HTTPException(status_code=422, detail="Invalid cursor") from exc


async def _get_conversation_or_404(
    session: AsyncSession, conversation_id: uuid.UUID
):
    conversation = await ConversationRepository.get_by_id(session, conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation


@router.post("", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    request: ConversationCreate,
    session: AsyncSession = Depends(get_db),
):
    conversation = await ConversationRepository.create(session, title=request.title)
    await session.commit()
    await session.refresh(conversation)
    return conversation


@router.get("", response_model=ConversationListResponse)
async def list_conversations(
    limit: int = Query(default=50, ge=1, le=100),
    cursor: str | None = None,
    session: AsyncSession = Depends(get_db),
):
    cursor_updated_at, cursor_id = _decode_cursor(cursor) if cursor else (None, None)
    conversations = await ConversationRepository.list(
        session,
        limit=limit + 1,
        cursor_updated_at=cursor_updated_at,
        cursor_id=cursor_id,
    )

    has_next_page = len(conversations) > limit
    items = conversations[:limit]
    next_cursor = (
        _encode_cursor(items[-1].updated_at, items[-1].id)
        if has_next_page and items
        else None
    )
    return ConversationListResponse(items=items, next_cursor=next_cursor)


@router.get("/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
):
    return await _get_conversation_or_404(session, conversation_id)


@router.get("/{conversation_id}/messages", response_model=MessageListResponse)
async def get_conversation_messages(
    conversation_id: uuid.UUID,
    limit: int = Query(default=100, ge=1, le=200),
    before: str | None = None,
    session: AsyncSession = Depends(get_db),
):
    await _get_conversation_or_404(session, conversation_id)
    before_created_at, before_id = _decode_cursor(before) if before else (None, None)
    messages = await MessageRepository.get_page_by_conversation(
        session,
        conversation_id=conversation_id,
        limit=limit + 1,
        before_created_at=before_created_at,
        before_id=before_id,
    )

    has_next_page = len(messages) > limit
    items = messages[-limit:] if has_next_page else messages
    next_cursor = (
        _encode_cursor(items[0].created_at, items[0].id)
        if has_next_page and items
        else None
    )
    return MessageListResponse(items=items, next_cursor=next_cursor)


@router.patch("/{conversation_id}", response_model=ConversationResponse)
async def update_conversation(
    conversation_id: uuid.UUID,
    request: ConversationUpdate,
    session: AsyncSession = Depends(get_db),
):
    conversation = await _get_conversation_or_404(session, conversation_id)
    conversation = await ConversationRepository.update_title(session, conversation, request.title)
    await session.commit()
    await session.refresh(conversation)
    return conversation


@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(
    conversation_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
):
    conversation = await _get_conversation_or_404(session, conversation_id)
    await ConversationRepository.delete(session, conversation)
    await session.commit()


@router.get("/{conversation_id}/context", response_model=ContextHistoryResponse)
async def get_conversation_context(
    conversation_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
):
    """
    Return the context snapshot history for a conversation.
    Provides the latest context status and all previous snapshots for the
    context inspection panel. Used on page load / conversation switch so the
    frontend does not need to call Gemini count_tokens separately.
    """
    await _get_conversation_or_404(session, conversation_id)
    snapshots = await ContextSnapshotRepository.list_by_conversation(session, conversation_id)
    latest = snapshots[-1] if snapshots else None
    return ContextHistoryResponse(
        latest=ContextSnapshotResponse.model_validate(latest) if latest else None,
        snapshots=[ContextSnapshotResponse.model_validate(s) for s in snapshots],
    )
