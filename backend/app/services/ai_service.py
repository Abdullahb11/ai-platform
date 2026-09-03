import os
import uuid
from typing import Optional
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.clients.gemini_client import GeminiClient
from app.repositories.conversation_repository import ConversationRepository
from app.repositories.message_repository import MessageRepository
from app.repositories.context_snapshot_repository import ContextSnapshotRepository
from app.services.context_selector import select_request_context, select_current_context


def _get_context_limit() -> int:
    """Read APP_CONTEXT_WINDOW_TOKENS from environment. Authoritative single source."""
    raw = os.getenv("APP_CONTEXT_WINDOW_TOKENS", "1000")
    try:
        value = int(raw)
        if value < 1:
            raise ValueError()
        return value
    except ValueError:
        raise RuntimeError(
            f"APP_CONTEXT_WINDOW_TOKENS must be a positive integer, got: '{raw}'"
        )


class AIService:
    """
    Business logic layer for AI services.

    Lifecycle
    ---------
    1.  Resolve or create conversation.
    2.  Load full persistent DB message history (never deleted).
    3.  Validate request context WITHOUT committing the user message yet.
    4.  Persist user message only after context validation passes.
    5.  Build bounded REQUEST CONTEXT (<= limit).
    6.  Call Gemini with exactly that request context.
    7.  Persist assistant response.
    8.  Build bounded CURRENT CONTEXT from request context + assistant response.
    9.  Persist context snapshot with explicit request and current context fields.
    10. Return enriched response with both context views.

    Transaction semantics
    ---------------------
    - Context validation (step 3) happens BEFORE committing the user message.
      If the user message alone exceeds the limit, we return HTTP 422 without
      writing anything to the database.
    - The user message is committed in step 4, AFTER validation passes.
    - If Gemini generation fails after step 4, the user message remains persisted
      (it was a valid, received message) but no snapshot is created.
    - The snapshot is only created after successful generation (step 9).
    """
    def __init__(self):
        self.gemini_client = GeminiClient()

    async def get_chat_response(
        self,
        session: AsyncSession,
        message: str,
        conversation_id: Optional[str] = None,
    ) -> dict:
        limit_tokens = _get_context_limit()

        # ── 1. Resolve or create conversation ────────────────────────────────
        if conversation_id:
            try:
                conv_uuid = uuid.UUID(conversation_id)
            except ValueError:
                raise ValueError(f"Invalid conversation_id format: '{conversation_id}'")

            conversation = await ConversationRepository.get_by_id(session, conv_uuid)
            if conversation is None:
                raise ValueError(f"Conversation '{conversation_id}' not found")
        else:
            conversation = await ConversationRepository.create(session)

        # ── 2. Load full DB history ───────────────────────────────────────────
        existing_messages = await MessageRepository.get_by_conversation(session, conversation.id)
        history = [
            {"id": str(msg.id), "role": msg.role, "content": msg.content}
            for msg in existing_messages
        ]

        # ── 3. Pre-validate: check request context BEFORE writing to DB ───────
        # We use a placeholder id for validation; real id assigned after persist.
        _PLACEHOLDER_ID = "00000000-0000-0000-0000-000000000000"
        try:
            select_request_context(
                gemini_client=self.gemini_client,
                history=history,
                new_message_id=_PLACEHOLDER_ID,
                new_message=message,
                limit_tokens=limit_tokens,
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc))
        except RuntimeError as exc:
            raise HTTPException(status_code=503, detail=str(exc))

        # ── 4. Persist user message (validation passed) ───────────────────────
        user_msg = await MessageRepository.create(session, conversation.id, "user", message)
        await ConversationRepository.touch(session, conversation.id)
        await session.commit()

        # ── 5. Build actual bounded REQUEST CONTEXT with real message id ──────
        try:
            req_ctx = select_request_context(
                gemini_client=self.gemini_client,
                history=history,
                new_message_id=str(user_msg.id),
                new_message=message,
                limit_tokens=limit_tokens,
            )
        except (ValueError, RuntimeError) as exc:
            # Extremely unlikely: second call should match first unless limit changed
            raise HTTPException(status_code=503, detail=str(exc))

        # ── 6. Call Gemini with exactly the selected request context ──────────
        generation = self.gemini_client.generate_text_from_history(req_ctx.selected)
        assistant_response = generation.text

        # ── 7. Persist assistant response ─────────────────────────────────────
        assistant_msg = await MessageRepository.create(
            session, conversation.id, "assistant", assistant_response
        )
        await ConversationRepository.touch(session, conversation.id)
        await session.commit()

        # ── 8. Build bounded CURRENT CONTEXT (request context + assistant) ────
        try:
            cur_ctx = select_current_context(
                gemini_client=self.gemini_client,
                request_context=req_ctx.selected,
                assistant_message_id=str(assistant_msg.id),
                assistant_message=assistant_response,
                limit_tokens=limit_tokens,
            )
        except (ValueError, RuntimeError) as exc:
            # Current context selection failure is non-fatal for the user's reply,
            # but we cannot produce a valid snapshot. Log and surface in response.
            cur_ctx = None
            cur_ctx_error = str(exc)
        else:
            cur_ctx_error = None

        # ── 9. Persist context snapshot ───────────────────────────────────────
        req_start_uuid = uuid.UUID(req_ctx.start_id) if req_ctx.start_id else None
        req_end_uuid = uuid.UUID(req_ctx.end_id) if req_ctx.end_id else None
        cur_start_uuid = uuid.UUID(cur_ctx.start_id) if cur_ctx and cur_ctx.start_id else None
        cur_end_uuid = uuid.UUID(cur_ctx.end_id) if cur_ctx and cur_ctx.end_id else None

        snapshot = await ContextSnapshotRepository.create(
            session=session,
            conversation_id=conversation.id,
            request_message_id=user_msg.id,
            assistant_message_id=assistant_msg.id,
            request_start_message_id=req_start_uuid,
            request_end_message_id=req_end_uuid,
            request_token_count=req_ctx.token_count,
            current_start_message_id=cur_start_uuid,
            current_end_message_id=cur_end_uuid,
            current_token_count=cur_ctx.token_count if cur_ctx else req_ctx.token_count,
            context_limit_tokens=limit_tokens,
        )
        await session.commit()

        # ── 10. Build enriched response ────────────────────────────────────────
        req_percent = round((req_ctx.token_count / limit_tokens) * 100, 1)
        cur_token_count = cur_ctx.token_count if cur_ctx else req_ctx.token_count
        cur_percent = round((cur_token_count / limit_tokens) * 100, 1)

        return {
            "response": assistant_response,
            "conversation_id": str(conversation.id),
            "usage": {
                "input_tokens": generation.input_tokens,
                "output_tokens": generation.output_tokens,
                "total_tokens": generation.total_tokens,
            },
            "context": {
                "limit_tokens": limit_tokens,
                "request": {
                    "token_count": req_ctx.token_count,
                    "percent_used": req_percent,
                    "start_message_id": req_ctx.start_id,
                    "end_message_id": req_ctx.end_id,
                    "message_count": req_ctx.message_count,
                },
                "current": {
                    "token_count": cur_token_count,
                    "percent_used": cur_percent,
                    "start_message_id": cur_ctx.start_id if cur_ctx else req_ctx.start_id,
                    "end_message_id": cur_ctx.end_id if cur_ctx else req_ctx.end_id,
                    "message_count": cur_ctx.message_count if cur_ctx else req_ctx.message_count,
                },
                "snapshot_id": str(snapshot.id),
                **({"current_context_error": cur_ctx_error} if cur_ctx_error else {}),
            },
        }
