from datetime import datetime
from typing import Dict, List


class ConversationManager:
    def __init__(self):
        self.conversation_history: List[Dict] = []

    def add_exchange(self, user_input: str, llm_response: str):
        """Add a conversation exchange to history"""
        self.conversation_history.append(
            {"user_input": user_input, "llm_response": llm_response}
        )

    def get_context(self, num_previous: int = 5) -> str:
        """Get the last n exchanges as context"""
        recent_history = (
            self.conversation_history[-num_previous:]
            if self.conversation_history
            else []
        )
        return "\n".join(
            [
                f"User: {ex['user_input']}\nAssistant: {ex['llm_response']}"
                for ex in recent_history
            ]
        )

    def clear_history(self):
        """Clear conversation history"""
        self.conversation_history = []
