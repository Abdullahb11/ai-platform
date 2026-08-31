import uuid
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.ai_service import AIService
from app.db.database import get_db

router = APIRouter()


class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[uuid.UUID] = None


class ChatResponse(BaseModel):
    response: str
    conversation_id: str


def get_ai_service() -> AIService:
    return AIService()


@router.post("/chat", response_model=ChatResponse, tags=["Chat"])
async def chat(
    request: ChatRequest,
    session: AsyncSession = Depends(get_db),
    ai_service: AIService = Depends(get_ai_service),
):
    """
    Accepts a user message and optional conversation_id.
    Creates a new persistent conversation if no ID is provided.
    Returns the assistant response and the conversation_id.
    """
    try:
        result = await ai_service.get_chat_response(
            session=session,
            message=request.message,
            conversation_id=str(request.conversation_id) if request.conversation_id else None,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return ChatResponse(
        response=result["response"],
        conversation_id=result["conversation_id"],
    )
