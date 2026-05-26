from pydantic import BaseModel


class SourceDocument(BaseModel):
    id: str
    title: str
    source: str
    content: str


class DocumentChunk(BaseModel):
    id: str
    text: str
    title: str
    source: str
    document_id: str
    chunk_id: int
