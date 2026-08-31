import uuid
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.clients.gemini_client import GeminiClient
from app.repositories.conversation_repository import ConversationRepository
from app.repositories.message_repository import MessageRepository


class AIService:
    """
    Business logic layer for AI services.
    Coordinates conversation persistence, history retrieval, and Gemini requests.
    """
    def __init__(self):
        self.gemini_client = GeminiClient()

    async def get_chat_response(
        self,
        session: AsyncSession,
        message: str,
        conversation_id: Optional[str] = None,
    ) -> dict:
        """
        Orchestrates the full chat flow:
        1. Resolve or create conversation
        2. Load existing history
        3. Persist user message
        4. Send history to Gemini
        5. Persist assistant response
        6. Return response + conversation_id

        Transaction behavior:
        - User message is committed before calling Gemini.
        - If Gemini fails, the user message remains (it was actually sent).
        - No fake assistant message is created on Gemini failure.
        """
        # 1. Resolve or create conversation
        if conversation_id:
            try:
                conv_uuid = uuid.UUID(conversation_id)
            except ValueError:
                raise ValueError(f"Invalid conversation_id format: '{conversation_id}'")

            conversation = await ConversationRepository.get_by_id(session, conv_uuid)
            if conversation is None:
                raise ValueError(f"Conversation '{conversation_id}' not found")
        else:
            conversation = await ConversationRepository.create(session)

        # 2. Load existing messages for history
        existing_messages = await MessageRepository.get_by_conversation(session, conversation.id)
        history = [{"role": msg.role, "content": msg.content} for msg in existing_messages]

        # 3. Persist user message and commit
        await MessageRepository.create(session, conversation.id, "user", message)
        await ConversationRepository.touch(session, conversation.id)
        await session.commit()

        # 4. Add user message to history for Gemini
        history.append({"role": "user", "content": message})

        # 5. Call Gemini with full conversation history
        assistant_response = self.gemini_client.generate_text_from_history(history)

        # 6. Persist assistant response and commit
        await MessageRepository.create(session, conversation.id, "assistant", assistant_response)
        await ConversationRepository.touch(session, conversation.id)
        await session.commit()

        return {
            "response": assistant_response,
            "conversation_id": str(conversation.id),
        }
