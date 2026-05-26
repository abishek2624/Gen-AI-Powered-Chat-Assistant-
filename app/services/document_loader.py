import json
from pathlib import Path
from app.models.document import SourceDocument


class DocumentLoader:
    def __init__(self, docs_path: Path):
        self.docs_path = docs_path

    def load(self) -> list[SourceDocument]:
        if not self.docs_path.exists():
            raise FileNotFoundError(f"Knowledge base file not found: {self.docs_path}")

        with self.docs_path.open("r", encoding="utf-8") as file:
            payload = json.load(file)

        documents = payload.get("documents", payload)
        return [SourceDocument(**document) for document in documents]
