import os
from dataclasses import dataclass
from typing import List, Dict
from google import genai
from google.genai import types


@dataclass
class GenerationResult:
    """Result of a Gemini generate_content call."""
    text: str
    input_tokens: int
    output_tokens: int
    total_tokens: int


class GeminiClient:
    """
    Client wrapper for direct interactions with the Google Gen AI SDK.
    Responsible for: building Content objects, generating text, and counting tokens.
    """
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        self.model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable is not set")

        # Initialize the Google Gen AI client
        self.client = genai.Client(api_key=api_key)

    # ── Shared helper ────────────────────────────────────────────────────────

    @staticmethod
    def build_contents(history: List[Dict[str, str]]) -> list[types.Content]:
        """
        Convert a list of {"role": ..., "content": ...} dicts to Gemini Content objects.
        Reused by both generate_text_from_history and context selection / token counting.
        """
        contents = []
        for msg in history:
            mapped_role = "model" if msg["role"] in ("assistant", "model") else "user"
            contents.append(
                types.Content(
                    role=mapped_role,
                    parts=[types.Part.from_text(text=msg["content"])],
                )
            )
        return contents

    # ── Token counting ───────────────────────────────────────────────────────

    def count_tokens(self, contents: list[types.Content]) -> int:
        """
        Count the tokens for the given contents using the Gemini token-counting API.
        Returns the total token count authoritative for the application context budget.
        Raises RuntimeError if the API call fails.
        """
        try:
            response = self.client.models.count_tokens(
                model=self.model_name,
                contents=contents,
            )
            return response.total_tokens
        except Exception as exc:
            raise RuntimeError(f"Gemini token counting failed: {exc}") from exc

    # ── Text generation ──────────────────────────────────────────────────────

    def generate_text_from_history(self, history: List[Dict[str, str]]) -> GenerationResult:
        """
        Send the conversation history to the Gemini model and return a GenerationResult
        containing the response text and token usage metadata.
        """
        contents = self.build_contents(history)

        response = self.client.models.generate_content(
            model=self.model_name,
            contents=contents,
        )

        text = response.text or ""

        # Extract usage metadata safely
        usage = response.usage_metadata
        input_tokens = getattr(usage, "prompt_token_count", 0) or 0
        output_tokens = getattr(usage, "candidates_token_count", 0) or 0
        total_tokens = getattr(usage, "total_token_count", 0) or (input_tokens + output_tokens)

        return GenerationResult(
            text=text,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
        )
