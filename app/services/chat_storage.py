import sqlite3
from datetime import datetime, timezone
from pathlib import Path


class ChatStorage:
    def __init__(self, db_path: Path = Path("app/vectorstore/chat_history.sqlite3")):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _initialize(self) -> None:
        with sqlite3.connect(self.db_path) as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS chat_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )

    def save_pair(self, session_id: str, user_message: str, assistant_reply: str) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with sqlite3.connect(self.db_path) as connection:
            connection.executemany(
                "INSERT INTO chat_messages (session_id, role, content, created_at) VALUES (?, ?, ?, ?)",
                [
                    (session_id, "user", user_message, now),
                    (session_id, "assistant", assistant_reply, now),
                ],
            )


chat_storage = ChatStorage()
