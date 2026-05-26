# Production Gemini RAG Chat Assistant

A complete GenAI-powered chat assistant built with FastAPI, Gemini, ChromaDB, and a vanilla HTML/CSS/JavaScript frontend. The assistant answers only from retrieved knowledge-base context and refuses questions that are not supported by the indexed documents.

## Architecture

```text
Browser UI
  -> POST /api/chat
  -> FastAPI route validation
  -> Query embedding with Gemini
  -> ChromaDB cosine similarity search
  -> Top matching chunks filtered by threshold
  -> Prompt assembled with retrieved context and short session history
  -> Gemini grounded response
  -> In-memory conversation window + SQLite chat persistence
```

## Project Structure

```text
project/
├── app/
│   ├── routes/
│   ├── services/
│   ├── models/
│   ├── vectorstore/
│   ├── prompts/
│   ├── utils/
│   └── main.py
├── frontend/
│   ├── index.html
│   ├── styles.css
│   └── app.js
├── docs.json
├── requirements.txt
├── .env.example
└── README.md
```

## RAG Workflow

1. `docs.json` is loaded at startup.
2. Documents are split into overlapping chunks of about 300-500 tokens.
3. Each chunk is embedded with Gemini `gemini-embedding-001`.
4. Chunks, embeddings, and metadata are stored in persistent ChromaDB.
5. A user question is embedded before the LLM is called.
6. ChromaDB performs cosine similarity search and returns the top 3 chunks.
7. Results below `SIMILARITY_THRESHOLD` are discarded.
8. Retrieved context is injected into the prompt.
9. Gemini `gemini-2.5-flash` generates a concise grounded answer.

## Embedding Strategy

The app uses Gemini `gemini-embedding-001` for semantic document and query embeddings. Chunk metadata includes:

- document title
- chunk id
- source document
- document id

ChromaDB is configured with `hnsw:space=cosine`, so retrieval uses cosine similarity. Chroma returns cosine distance; the app converts it to similarity as `1 - distance` and logs similarity scores for observability.

## Conversation Memory

The app stores the last 5 user/assistant message pairs per `sessionId` in memory and includes them in the prompt. Retrieved context remains the source of truth, and the prompt explicitly prevents conversation history from overriding the knowledge base. Chat pairs are also persisted to SQLite in `app/vectorstore/chat_history.sqlite3`.

## Setup

Use Python 3.11 or 3.12 for the smoothest install experience with ChromaDB native dependencies.

```bash
cd project
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

Edit `.env` and set your Gemini key:

```text
GEMINI_API_KEY=your-gemini-api-key
GEMINI_EMBEDDING_MODEL=gemini-embedding-001
GEMINI_CHAT_MODEL=gemini-2.5-flash
```

Run the app:

```bash
python -m uvicorn app.main:app --reload
```

Open:

```text
http://127.0.0.1:8000
```

On the first run with a valid Gemini API key, the app builds the Chroma vector index from `docs.json`. Later runs reuse the persistent index.

## API Documentation

### Health

```http
GET /health
```

Response:

```json
{
  "status": "healthy"
}
```

### Chat

```http
POST /api/chat
Content-Type: application/json

{
  "sessionId": "abc123",
  "message": "How can I reset my password?"
}
```

Response:

```json
{
  "reply": "Users can reset a forgotten password from the sign-in page by selecting Forgot password and following the secure reset link sent by email.",
  "tokensUsed": 120,
  "retrievedChunks": 3
}
```

Error response:

```json
{
  "error": "Message field is required"
}
```

## Error Handling

The backend returns structured JSON errors for validation failures, missing Gemini API configuration, invalid Gemini API keys, timeouts, rate limits, upstream provider errors, and unexpected server errors. Similarity scores and token usage are logged.

## Optional JWT Authentication

JWT auth is disabled by default for local development. To enable it:

```text
ENABLE_AUTH=true
JWT_SECRET=replace-with-a-long-random-secret
```

Then call `/api/chat` with:

```http
Authorization: Bearer <jwt>
```

## Screenshots

Add screenshots here after running the frontend:

- Chat landing state
- Grounded answer with retrieved chunk count
- Out-of-scope fallback response

## Future Improvements

- Add streaming responses with Server-Sent Events.
- Add admin endpoints to re-index selected documents.
- Store conversation memory in Redis for multi-worker deployments.
- Add source citations in the UI.
- Add automated tests with mocked Gemini embeddings and chat responses.
- Add document upload and access-control-aware retrieval.
