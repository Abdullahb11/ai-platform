from fastapi import APIRouter, Depends
from pydantic import BaseModel
from app.services.ai_service import AIService

router = APIRouter()

class ChatRequest(BaseModel):
    message: str

class ChatResponse(BaseModel):
    response: str

def get_ai_service() -> AIService:
    return AIService()

@router.post("/chat", response_model=ChatResponse, tags=["Chat"])
async def chat(request: ChatRequest, ai_service: AIService = Depends(get_ai_service)):
    """
    API endpoint that accepts a user message and delegates to the AI Service.
    """
    response_text = ai_service.get_chat_response(request.message)
    return ChatResponse(response=response_text)
