import re
from app.models.document import DocumentChunk, SourceDocument


class TokenChunker:
    """Approximate token chunking without adding heavyweight tokenizer dependencies."""

    def __init__(self, chunk_tokens: int = 420, overlap_tokens: int = 60):
        self.chunk_tokens = chunk_tokens
        self.overlap_tokens = overlap_tokens

    def split(self, documents: list[SourceDocument]) -> list[DocumentChunk]:
        chunks: list[DocumentChunk] = []
        for document in documents:
            words = re.findall(r"\S+", document.content)
            start = 0
            chunk_index = 0
            while start < len(words):
                end = min(start + self.chunk_tokens, len(words))
                text = " ".join(words[start:end])
                chunks.append(
                    DocumentChunk(
                        id=f"{document.id}-{chunk_index}",
                        text=text,
                        title=document.title,
                        source=document.source,
                        document_id=document.id,
                        chunk_id=chunk_index,
                    )
                )
                if end == len(words):
                    break
                start = max(end - self.overlap_tokens, start + 1)
                chunk_index += 1
        return chunks
