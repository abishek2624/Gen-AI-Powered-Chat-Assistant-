import logging
from pathlib import Path
from typing import Any

import chromadb
from chromadb.config import Settings as ChromaSettings

from app.config import get_settings
from app.models.document import DocumentChunk


logger = logging.getLogger(__name__)


class ChromaVectorStore:
    def __init__(self, persist_path: Path | None = None):
        settings = get_settings()
        self.persist_path = persist_path or settings.chroma_path
        self.collection_name = settings.collection_name
        self.client = chromadb.PersistentClient(
            path=str(self.persist_path),
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    def has_vectors(self) -> bool:
        return self.collection.count() > 0

    def upsert_chunks(self, chunks: list[DocumentChunk], embeddings: list[list[float]]) -> None:
        if not chunks:
            return
        self.collection.upsert(
            ids=[chunk.id for chunk in chunks],
            embeddings=embeddings,
            documents=[chunk.text for chunk in chunks],
            metadatas=[
                {
                    "document_title": chunk.title,
                    "chunk_id": chunk.chunk_id,
                    "source_document": chunk.source,
                    "document_id": chunk.document_id,
                }
                for chunk in chunks
            ],
        )
        logger.info("Stored %s chunks in Chroma collection '%s'", len(chunks), self.collection_name)

    def search(self, query_embedding: list[float], top_k: int) -> list[dict[str, Any]]:
        result = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            include=["documents", "metadatas", "distances"],
        )

        matches: list[dict[str, Any]] = []
        documents = result.get("documents", [[]])[0]
        metadatas = result.get("metadatas", [[]])[0]
        distances = result.get("distances", [[]])[0]

        for document, metadata, distance in zip(documents, metadatas, distances):
            similarity = max(0.0, 1.0 - float(distance))
            matches.append(
                {
                    "text": document,
                    "metadata": metadata,
                    "distance": float(distance),
                    "similarity": similarity,
                }
            )
        return matches
