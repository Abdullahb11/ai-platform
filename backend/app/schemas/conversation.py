import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator


class ConversationBase(BaseModel):
    title: str | None = None

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str | None) -> str | None:
        if value is None:
            return None

        title = value.strip()
        if not title:
            raise ValueError("title must not be blank")
        if len(title) > 255:
            raise ValueError("title must be at most 255 characters")
        return title


class ConversationCreate(ConversationBase):
    pass


class ConversationUpdate(BaseModel):
    title: str

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str) -> str:
        title = value.strip()
        if not title:
            raise ValueError("title must not be blank")
        if len(title) > 255:
            raise ValueError("title must be at most 255 characters")
        return title


class ConversationResponse(ConversationBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: datetime
    updated_at: datetime


class ConversationListResponse(BaseModel):
    items: list[ConversationResponse]
    next_cursor: str | None = None


# ── Context schemas ────────────────────────────────────────────────────────────

class ContextWindowDetail(BaseModel):
    """Token count and boundary information for one context view (request or current)."""
    token_count: int
    percent_used: float
    start_message_id: str | None = None
    end_message_id: str | None = None
    message_count: int


class ContextInfo(BaseModel):
    """
    Full context metadata for a chat response.

    request  — what Gemini actually received for this generation
    current  — the post-response active context (request + assistant response, bounded)

    current.percent_used is always <= 100 because current context is always bounded
    by APP_CONTEXT_WINDOW_TOKENS.
    """
    limit_tokens: int
    request: ContextWindowDetail
    current: ContextWindowDetail
    snapshot_id: str | None = None
