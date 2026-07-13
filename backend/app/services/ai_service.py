from app.clients.gemini_client import GeminiClient

class AIService:
    """
    Business logic layer for AI services.
    Coordinates AI tasks and delegates work to specific AI clients.
    """
    def __init__(self):
        self.gemini_client = GeminiClient()

    def get_chat_response(self, message: str) -> str:
        """
        Receives the user message, invokes the Gemini client, and returns response text.
        """
        return self.gemini_client.generate_text(message)
