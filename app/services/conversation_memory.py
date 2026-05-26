from collections import defaultdict, deque

from app.config import get_settings


class ConversationMemory:
    def __init__(self):
        self.max_pairs = get_settings().conversation_pairs
        self._sessions: dict[str, deque[tuple[str, str]]] = defaultdict(lambda: deque(maxlen=self.max_pairs))

    def get_history(self, session_id: str) -> str:
        pairs = self._sessions[session_id]
        if not pairs:
            return "No prior conversation."
        return "\n".join(f"User: {user}\nAssistant: {assistant}" for user, assistant in pairs)

    def add_pair(self, session_id: str, user_message: str, assistant_reply: str) -> None:
        self._sessions[session_id].append((user_message, assistant_reply))

    def clear(self, session_id: str) -> None:
        self._sessions.pop(session_id, None)


conversation_memory = ConversationMemory()
