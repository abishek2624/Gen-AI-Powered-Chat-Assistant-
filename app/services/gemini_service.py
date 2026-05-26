import logging
from typing import Any

import httpx
from fastapi import HTTPException

from app.config import get_settings


logger = logging.getLogger(__name__)


class GeminiService:
    def __init__(self):
        self.settings = get_settings()
        self.timeout = self.settings.request_timeout_seconds

    def _headers(self) -> dict[str, str]:
        return {
            "Content-Type": "application/json",
            "x-goog-api-key": self.settings.gemini_api_key,
        }

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        embeddings: list[list[float]] = []
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for text in texts:
                embeddings.append(await self._embed_one(client, text))
        logger.info("Gemini embedded %s text chunks", len(embeddings))
        return embeddings

    async def embed_query(self, text: str) -> list[float]:
        return (await self.embed_texts([text]))[0]

    async def _embed_one(self, client: httpx.AsyncClient, text: str) -> list[float]:
        model = self.settings.gemini_embedding_model
        url = f"{self.settings.gemini_base_url}/models/{model}:embedContent"
        payload = {
            "model": f"models/{model}",
            "content": {"parts": [{"text": text}]},
        }
        response = await client.post(url, headers=self._headers(), json=payload)
        self._raise_for_gemini_error(response)
        return response.json()["embedding"]["values"]

    async def generate(self, prompt: str) -> tuple[str, int]:
        model = self.settings.gemini_chat_model
        url = f"{self.settings.gemini_base_url}/models/{model}:generateContent"
        payload = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.2,
                "maxOutputTokens": self.settings.llm_max_tokens,
                "responseMimeType": "text/plain",
            },
        }
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(url, headers=self._headers(), json=payload)

        self._raise_for_gemini_error(response)
        data = response.json()
        reply = self._extract_text(data)
        tokens_used = data.get("usageMetadata", {}).get("totalTokenCount", 0)
        logger.info("Gemini tokens used: %s", tokens_used)
        return reply.strip(), tokens_used

    @staticmethod
    def _extract_text(data: dict[str, Any]) -> str:
        candidates = data.get("candidates", [])
        if not candidates:
            return ""
        parts = candidates[0].get("content", {}).get("parts", [])
        return "".join(part.get("text", "") for part in parts)

    @staticmethod
    def _raise_for_gemini_error(response: httpx.Response) -> None:
        if response.status_code < 400:
            return

        try:
            message = response.json().get("error", {}).get("message", response.text)
        except ValueError:
            message = response.text

        if response.status_code in {401, 403}:
            raise HTTPException(status_code=401, detail=f"Invalid Gemini API key: {message}")
        if response.status_code == 429:
            raise HTTPException(status_code=429, detail=f"Gemini rate limit or quota exceeded: {message}")
        if response.status_code >= 500:
            raise HTTPException(status_code=502, detail=f"Gemini provider error: {message}")
        raise HTTPException(status_code=400, detail=f"Gemini request failed: {message}")
