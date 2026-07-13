from app.clients.gemini_client import GeminiClient
from app.stores.conversation_store import conversation_store

class AIService:
    """
    Business logic layer for AI services.
    Coordinates AI tasks and manages conversation state via the store.
    """
    def __init__(self):
        self.gemini_client = GeminiClient()

    def get_chat_response(self, message: str) -> str:
        """
        Receives user prompt, updates history, requests content from Gemini,
        updates history with model response, and returns the response.
        """
        # 1. Load conversation history and append the user message
        conversation_store.add_message(role="user", content=message)
        history = conversation_store.get_history()

        # 2. Send the entire history to Gemini Client
        assistant_response = self.gemini_client.generate_text_from_history(history)

        # 3. Append the assistant response to store
        conversation_store.add_message(role="model", content=assistant_response)

        # 4. Return only the latest response text
        return assistant_response
