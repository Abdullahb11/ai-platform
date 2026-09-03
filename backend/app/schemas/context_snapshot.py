import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class ContextSnapshotResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    conversation_id: uuid.UUID

    # Request context
    request_message_id: uuid.UUID | None = None
    assistant_message_id: uuid.UUID | None = None
    request_start_message_id: uuid.UUID | None = None
    request_end_message_id: uuid.UUID | None = None
    request_token_count: int

    # Post-response current context
    current_start_message_id: uuid.UUID | None = None
    current_end_message_id: uuid.UUID | None = None
    current_token_count: int

    context_limit_tokens: int
    created_at: datetime


class ContextHistoryResponse(BaseModel):
    """Snapshot history for GET /conversations/{id}/context."""
    latest: ContextSnapshotResponse | None = None
    snapshots: list[ContextSnapshotResponse] = []
