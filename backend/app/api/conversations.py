from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict
from app.stores.conversation_store import conversation_store

router = APIRouter()


class CreateConversationResponse(BaseModel):
    conversation_id: str


class ConversationListResponse(BaseModel):
    conversations: List[str]


class ConversationDetailResponse(BaseModel):
    conversation_id: str
    messages: List[Dict[str, str]]


@router.post("/conversations", response_model=CreateConversationResponse, tags=["Conversations"])
async def create_conversation():
    """
    Create a new conversation and return its unique ID.
    """
    conversation_id = conversation_store.create_conversation()
    return CreateConversationResponse(conversation_id=conversation_id)


@router.get("/conversations", response_model=ConversationListResponse, tags=["Conversations"])
async def list_conversations():
    """
    Return all existing runtime conversation IDs.
    """
    ids = conversation_store.list_conversations()
    return ConversationListResponse(conversations=ids)


@router.get("/conversations/{conversation_id}", response_model=ConversationDetailResponse, tags=["Conversations"])
async def get_conversation(conversation_id: str):
    """
    Return a specific conversation's message history.
    """
    messages = conversation_store.get_history(conversation_id)
    if messages is None:
        raise HTTPException(status_code=404, detail=f"Conversation '{conversation_id}' not found")
    return ConversationDetailResponse(conversation_id=conversation_id, messages=messages)
