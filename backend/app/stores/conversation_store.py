import uuid
from typing import List, Dict, Optional


class ConversationStore:
    """
    In-memory store for maintaining multiple conversation histories.
    Each conversation is identified by a unique conversation_id (UUID).
    Stores messages only, with no API, business, or client logic.
    """
    def __init__(self):
        self._conversations: Dict[str, List[Dict[str, str]]] = {}

    def create_conversation(self) -> str:
        """
        Create a new empty conversation and return its unique ID.
        """
        conversation_id = str(uuid.uuid4())
        self._conversations[conversation_id] = []
        return conversation_id

    def get_history(self, conversation_id: str) -> Optional[List[Dict[str, str]]]:
        """
        Retrieve the message list for a given conversation.
        Returns None if the conversation_id does not exist.
        """
        if conversation_id not in self._conversations:
            return None
        return self._conversations[conversation_id]

    def add_message(self, conversation_id: str, role: str, content: str) -> bool:
        """
        Append a new message to a specific conversation's history.
        role: "user" or "model"
        content: message text
        Returns False if the conversation_id does not exist.
        """
        if conversation_id not in self._conversations:
            return False
        self._conversations[conversation_id].append({"role": role, "content": content})
        return True

    def list_conversations(self) -> List[str]:
        """
        Return a list of all existing conversation IDs.
        """
        return list(self._conversations.keys())


# Global singleton store for keeping multiple conversations in memory
conversation_store = ConversationStore()
