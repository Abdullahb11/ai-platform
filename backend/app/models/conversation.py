import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, Index, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.database import Base


class Conversation(Base):
    __tablename__ = "conversations"
    __table_args__ = (
        Index("ix_conversations_updated_at_id", "updated_at", "id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4
    )
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    messages: Mapped[list["Message"]] = relationship(
        back_populates="conversation", cascade="all, delete-orphan"
    )
    context_snapshots: Mapped[list["ContextSnapshot"]] = relationship(  # noqa: F821
        back_populates="conversation",
        cascade="all, delete-orphan",
        foreign_keys="ContextSnapshot.conversation_id",
    )
