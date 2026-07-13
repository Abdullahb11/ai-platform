import os
from typing import List, Dict
from google import genai
from google.genai import types

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

    def generate_text_from_history(self, history: List[Dict[str, str]]) -> str:
        """
        Sends the entire conversation history to the Gemini model and returns the generated text response.
        """
        # Convert store history format to GenAI types
        contents = []
        for msg in history:
            role = msg["role"]
            content = msg["content"]
            # Map role to expected SDK roles (user -> user, model/assistant -> model)
            mapped_role = "model" if role in ("assistant", "model") else "user"
            contents.append(
                types.Content(
                    role=mapped_role,
                    parts=[types.Part.from_text(text=content)]
                )
            )

        response = self.client.models.generate_content(
            model=self.model_name,
            contents=contents
        )
        
        if not response.text:
            return ""
        return response.text
