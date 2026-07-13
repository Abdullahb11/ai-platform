import os
from google import genai

class GeminiClient:
    """
    Client wrapper for direct interactions with the Google Gen AI SDK.
    Only responsible for setting up the client and generating text content.
    """
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        self.model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable is not set")
            
        # Initialize the Google Gen AI client
        self.client = genai.Client(api_key=api_key)

    def generate_text(self, prompt: str) -> str:
        """
        Sends a prompt to the Gemini model and returns the generated text.
        """
        response = self.client.models.generate_content(
            model=self.model_name,
            contents=prompt
        )
        
        if not response.text:
            return ""
        return response.text
