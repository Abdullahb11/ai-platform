import uuid
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.ai_service import AIService
from app.db.database import get_db
from app.schemas.conversation import ContextInfo, ContextWindowDetail

router = APIRouter()


class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[uuid.UUID] = None


class UsageMetadata(BaseModel):
    input_tokens: int
    output_tokens: int
    total_tokens: int


class ChatResponse(BaseModel):
    """
    Response shape for POST /chat.

    response        — assistant text
    conversation_id — conversation UUID string
    usage           — Gemini generation token usage (input/output/total)
    context         — application context window metadata:
                      .limit_tokens   — configured APP_CONTEXT_WINDOW_TOKENS
                      .request        — what Gemini received for this generation
                      .current        — post-response active context state
    """
    response: str
    conversation_id: str
    usage: Optional[UsageMetadata] = None
    context: Optional[ContextInfo] = None


def get_ai_service() -> AIService:
    return AIService()


@router.post("/chat", response_model=ChatResponse, tags=["Chat"])
async def chat(
    request: ChatRequest,
    session: AsyncSession = Depends(get_db),
    ai_service: AIService = Depends(get_ai_service),
):
    """
    Send a user message and receive an assistant response.

    Creates a new conversation if no conversation_id is provided.

    Returns:
    - response: assistant text
    - usage: Gemini token usage for this request
    - context.request: the exact context sent to Gemini (bounded by limit)
    - context.current: post-response active context state (also bounded)

    Errors:
    - 404: conversation_id not found
    - 422: message alone exceeds configured context window limit
    - 503: Gemini token counting API unavailable
    """
    try:
        result = await ai_service.get_chat_response(
            session=session,
            message=request.message,
            conversation_id=str(request.conversation_id) if request.conversation_id else None,
        )
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    usage_data = result.get("usage")
    context_data = result.get("context")

    context_obj: Optional[ContextInfo] = None
    if context_data:
        context_obj = ContextInfo(
            limit_tokens=context_data["limit_tokens"],
            request=ContextWindowDetail(**context_data["request"]),
            current=ContextWindowDetail(**context_data["current"]),
            snapshot_id=context_data.get("snapshot_id"),
        )

    return ChatResponse(
        response=result["response"],
        conversation_id=result["conversation_id"],
        usage=UsageMetadata(**usage_data) if usage_data else None,
        context=context_obj,
    )
