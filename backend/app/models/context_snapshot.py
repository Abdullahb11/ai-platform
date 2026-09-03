import uuid
from datetime import datetime
from sqlalchemy import Integer, DateTime, ForeignKey, Index, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.database import Base


class ContextSnapshot(Base):
    """
    Records both the request context sent to Gemini AND the resulting post-response
    current context for each generation request.

    Snapshots reference existing messages by ID only — no content is duplicated.

    Semantics
    ---------
    request_message_id       — the user message that triggered this Gemini request
    assistant_message_id     — the assistant message that Gemini produced

    request_start_message_id — first message Gemini actually received (oldest in window)
    request_end_message_id   — last message Gemini received (always = request_message_id)
    request_token_count      — authoritative token count of the request context

    current_start_message_id — first message in post-response active context
    current_end_message_id   — last message in post-response active context
                               (always = assistant_message_id)
    current_token_count      — authoritative token count of the current context

    context_limit_tokens     — configured APP_CONTEXT_WINDOW_TOKENS at the time of request
    """
    __tablename__ = "context_snapshots"
    __table_args__ = (
        Index("ix_context_snapshots_conversation_id", "conversation_id"),
        Index("ix_context_snapshots_created_at", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4
    )
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False
    )

    # ── Request context ───────────────────────────────────────────────────────
    request_message_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("messages.id", ondelete="SET NULL"), nullable=True
    )
    assistant_message_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("messages.id", ondelete="SET NULL"), nullable=True
    )
    request_start_message_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("messages.id", ondelete="SET NULL"), nullable=True
    )
    request_end_message_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("messages.id", ondelete="SET NULL"), nullable=True
    )
    request_token_count: Mapped[int] = mapped_column(Integer, nullable=False)

    # ── Post-response / current context ──────────────────────────────────────
    current_start_message_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("messages.id", ondelete="SET NULL"), nullable=True
    )
    current_end_message_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("messages.id", ondelete="SET NULL"), nullable=True
    )
    current_token_count: Mapped[int] = mapped_column(Integer, nullable=False)

    # ── Shared ────────────────────────────────────────────────────────────────
    context_limit_tokens: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    conversation: Mapped["Conversation"] = relationship(  # noqa: F821
        back_populates="context_snapshots",
        foreign_keys=[conversation_id],
    )
