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
