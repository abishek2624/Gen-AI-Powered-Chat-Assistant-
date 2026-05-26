from pydantic import BaseModel, Field, field_validator


class ChatRequest(BaseModel):
    sessionId: str = Field(..., min_length=1, max_length=128)
    message: str = Field(..., max_length=2000)

    @field_validator("message")
    @classmethod
    def message_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Message field is required")
        return value.strip()


class ChatResponse(BaseModel):
    reply: str
    tokensUsed: int
    retrievedChunks: int
    averageSimilarity: float = 0.0
    similarityScores: list[float] = []
    sourceDocuments: list[str] = []
    embeddingModel: str = ""
    llmModel: str = ""
    vectorDb: str = "ChromaDB"
    searchTimeMs: int = 0


class ErrorResponse(BaseModel):
    error: str
