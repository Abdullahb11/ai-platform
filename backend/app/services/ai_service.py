from app.clients.gemini_client import GeminiClient
from app.stores.conversation_store import conversation_store


class AIService:
    """
    Business logic layer for AI services.
    Coordinates AI tasks and manages conversation state via the store.
    """
    def __init__(self):
        self.gemini_client = GeminiClient()

    def get_chat_response(self, conversation_id: str, message: str) -> str:
        """
        Receives a conversation_id and user message.
        Retrieves that conversation's history, appends the user message,
        sends the full history to Gemini, appends the assistant response,
        and returns the response text.

        Raises ValueError if the conversation_id does not exist.
        """
        # 1. Verify the conversation exists
        history = conversation_store.get_history(conversation_id)
        if history is None:
            raise ValueError(f"Conversation '{conversation_id}' not found")

        # 2. Append the user message to the conversation
        conversation_store.add_message(conversation_id, role="user", content=message)

        # 3. Re-fetch history (now includes the new user message)
        history = conversation_store.get_history(conversation_id)

        # 4. Send the entire conversation history to Gemini Client
        assistant_response = self.gemini_client.generate_text_from_history(history)

        # 5. Append the assistant response to the same conversation
        conversation_store.add_message(conversation_id, role="model", content=assistant_response)

        # 6. Return only the latest response text
        return assistant_response
