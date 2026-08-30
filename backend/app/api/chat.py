from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from app.services.ai_service import AIService

router = APIRouter()


class ChatRequest(BaseModel):
    conversation_id: str
    message: str


class ChatResponse(BaseModel):
    response: str


def get_ai_service() -> AIService:
    return AIService()


@router.post("/chat", response_model=ChatResponse, tags=["Chat"])
async def chat(request: ChatRequest, ai_service: AIService = Depends(get_ai_service)):
    """
    API endpoint that accepts a conversation_id and user message,
    then delegates to the AI Service.
    """
    try:
        response_text = ai_service.get_chat_response(request.conversation_id, request.message)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return ChatResponse(response=response_text)
