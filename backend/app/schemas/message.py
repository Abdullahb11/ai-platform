import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class MessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    role: str
    content: str
    created_at: datetime


class MessageListResponse(BaseModel):
    items: list[MessageResponse]
    next_cursor: str | None = None
