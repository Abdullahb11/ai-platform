from typing import List, Dict

class ConversationStore:
    """
    In-memory store for maintaining conversation history.
    Stores messages only, with no API, business, or client logic.
    """
    def __init__(self):
        self._history: List[Dict[str, str]] = []

    def get_history(self) -> List[Dict[str, str]]:
        """
        Retrieve the current list of messages in the conversation.
        """
        return self._history

    def add_message(self, role: str, content: str):
        """
        Append a new message to the conversation history.
        role: "user" or "model"
        content: message text
        """
        self._history.append({"role": role, "content": content})

    def clear(self):
        """
        Clear the conversation history.
        """
        self._history = []

# Global singleton store for keeping exactly ONE conversation in memory
conversation_store = ConversationStore()
