import logging
from time import perf_counter

from fastapi import HTTPException

from app.config import get_settings
from app.prompts.rag_prompt import RAG_PROMPT_TEMPLATE
from app.services.chat_storage import chat_storage
from app.services.chunking import TokenChunker
from app.services.conversation_memory import conversation_memory
from app.services.document_loader import DocumentLoader
from app.services.gemini_service import GeminiService
from app.vectorstore.chroma_store import ChromaVectorStore


logger = logging.getLogger(__name__)
FALLBACK_RESPONSE = "I could not find enough information in the knowledge base to answer this question."
MAX_CONTEXT_CHUNKS = 3
RELATIVE_SIMILARITY_MARGIN = 0.08


class RAGService:
    def __init__(self):
        self.settings = get_settings()
        self.gemini_service = GeminiService()
        self.vector_store = ChromaVectorStore()
        self.index_error: str | None = None

    async def initialize(self) -> None:
        if self.vector_store.has_vectors():
            logger.info("Chroma collection already contains indexed chunks")
            self.index_error = None
            return
        if not self.settings.gemini_api_key:
            logger.warning("GEMINI_API_KEY is not configured; vector index will build on first configured run")
            self.index_error = "GEMINI_API_KEY is not configured"
            return

        try:
            documents = DocumentLoader(self.settings.docs_path).load()
            chunks = TokenChunker().split(documents)
            embeddings = await self.gemini_service.embed_texts([chunk.text for chunk in chunks])
            self.vector_store.upsert_chunks(chunks, embeddings)
            self.index_error = None
            logger.info("Indexed %s documents into %s chunks", len(documents), len(chunks))
        except HTTPException:
            self.index_error = "Unable to build vector index because the Gemini provider request failed"
            logger.exception("Vector index initialization failed")

    async def answer(self, session_id: str, message: str) -> dict:
        if not self.settings.gemini_api_key:
            raise HTTPException(status_code=500, detail="GEMINI_API_KEY is not configured")
        if not self.vector_store.has_vectors():
            await self.initialize()
        if not self.vector_store.has_vectors():
            raise HTTPException(
                status_code=503,
                detail=self.index_error or "Vector index is not available",
            )

        query_embedding = await self.gemini_service.embed_query(message)
        search_started = perf_counter()
        candidate_count = max(self.settings.retrieval_top_k, MAX_CONTEXT_CHUNKS) + 2
        matches = self.vector_store.search(query_embedding, candidate_count)
        search_time_ms = round((perf_counter() - search_started) * 1000)
        accepted_matches = self._select_context_chunks(matches)
        logger.info(
            "Similarity scores for session %s: %s",
            session_id,
            [round(match["similarity"], 4) for match in matches],
        )

        if not accepted_matches:
            conversation_memory.add_pair(session_id, message, FALLBACK_RESPONSE)
            chat_storage.save_pair(session_id, message, FALLBACK_RESPONSE)
            return self._build_response(FALLBACK_RESPONSE, 0, [], search_time_ms)

        retrieved_context = self._format_context(accepted_matches)
        prompt = RAG_PROMPT_TEMPLATE.format(
            retrieved_context=retrieved_context,
            conversation_history=conversation_memory.get_history(session_id),
            user_question=message,
        )
        reply, tokens_used = await self.gemini_service.generate(prompt)
        conversation_memory.add_pair(session_id, message, reply)
        chat_storage.save_pair(session_id, message, reply)
        return self._build_response(reply, tokens_used, accepted_matches, search_time_ms)

    @staticmethod
    def _format_context(matches: list[dict]) -> str:
        blocks = []
        for index, match in enumerate(matches, start=1):
            metadata = match["metadata"]
            blocks.append(
                f"[Chunk {index} | Title: {metadata['document_title']} | "
                f"Source: {metadata['source_document']} | Similarity: {match['similarity']:.3f}]\n"
                f"{match['text']}"
            )
        return "\n\n".join(blocks)

    def _select_context_chunks(self, matches: list[dict]) -> list[dict]:
        if not matches:
            return []

        ranked_matches = sorted(matches, key=lambda match: match["similarity"], reverse=True)
        best_similarity = ranked_matches[0]["similarity"]
        dynamic_floor = max(
            self.settings.similarity_threshold,
            best_similarity - RELATIVE_SIMILARITY_MARGIN,
        )
        return [
            match
            for match in ranked_matches
            if match["similarity"] >= dynamic_floor
        ][:MAX_CONTEXT_CHUNKS]

    def _build_response(
        self,
        reply: str,
        tokens_used: int,
        matches: list[dict],
        search_time_ms: int,
    ) -> dict:
        similarities = [round(match["similarity"], 4) for match in matches]
        sources = sorted(
            {
                match["metadata"].get("source_document", "Unknown source")
                for match in matches
            }
        )
        average_similarity = round(sum(similarities) / len(similarities), 4) if similarities else 0.0
        return {
            "reply": reply,
            "tokensUsed": tokens_used,
            "retrievedChunks": len(matches),
            "averageSimilarity": average_similarity,
            "similarityScores": similarities,
            "sourceDocuments": sources,
            "embeddingModel": self.settings.gemini_embedding_model,
            "llmModel": self.settings.gemini_chat_model,
            "vectorDb": "ChromaDB cosine",
            "searchTimeMs": search_time_ms,
        }

rag_service = RAGService()
