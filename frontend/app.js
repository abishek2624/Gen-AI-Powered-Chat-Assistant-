const chatMessages = document.getElementById("chatMessages");
const chatForm = document.getElementById("chatForm");
const messageInput = document.getElementById("messageInput");
const sendButton = document.getElementById("sendButton");
const loadingIndicator = document.getElementById("loadingIndicator");
const loadingTitle = document.getElementById("loadingTitle");
const loadingSubtitle = document.getElementById("loadingSubtitle");
const newChatButton = document.getElementById("newChatButton");
const chatHistory = document.getElementById("chatHistory");
const vectorStatus = document.getElementById("vectorStatus");
const activeSession = document.getElementById("activeSession");

const SESSION_KEY = "rag-chat-session-id";
const SESSIONS_KEY = "rag-chat-sessions";
const MESSAGES_KEY_PREFIX = "rag-chat-messages:";
const FALLBACK_REPLY = "I could not find enough information in the knowledge base to answer this question.";

const suggestedPrompts = [
  "How do I reset my password?",
  "How can I check invoices?",
  "How does multi-factor authentication work?",
  "What happens when document indexing fails?",
];

const knowledgeAreas = ["Account security", "Billing and invoices", "Document indexing", "API usage", "Privacy governance"];

function createSessionId() {
  return crypto.randomUUID ? crypto.randomUUID() : `${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function getSessionId() {
  let sessionId = localStorage.getItem(SESSION_KEY);
  if (!sessionId) {
    sessionId = createSessionId();
    localStorage.setItem(SESSION_KEY, sessionId);
  }
  return sessionId;
}

function updateActiveSessionLabel() {
  activeSession.textContent = getSessionId().slice(0, 8);
}

function getSessions() {
  return JSON.parse(localStorage.getItem(SESSIONS_KEY) || "[]");
}

function saveSessions(sessions) {
  localStorage.setItem(SESSIONS_KEY, JSON.stringify(sessions.slice(0, 12)));
}

function getStoredMessages(sessionId = getSessionId()) {
  return JSON.parse(localStorage.getItem(`${MESSAGES_KEY_PREFIX}${sessionId}`) || "[]");
}

function saveStoredMessages(messages, sessionId = getSessionId()) {
  localStorage.setItem(`${MESSAGES_KEY_PREFIX}${sessionId}`, JSON.stringify(messages));
}

function updateSessionTitle(message) {
  const sessionId = getSessionId();
  const sessions = getSessions().filter((session) => session.id !== sessionId);
  sessions.unshift({
    id: sessionId,
    title: message.slice(0, 58) || "New chat",
    updatedAt: Date.now(),
  });
  saveSessions(sessions);
  renderChatHistory();
}

function formatTime(date = new Date()) {
  return new Intl.DateTimeFormat(undefined, { hour: "2-digit", minute: "2-digit" }).format(date);
}

function formatDuration(ms) {
  if (ms < 1000) return `${Math.round(ms)} ms`;
  return `${(ms / 1000).toFixed(1)} s`;
}

function escapeHtml(value) {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function renderMarkdown(text) {
  let html = escapeHtml(text);
  html = html.replace(/```([\s\S]*?)```/g, "<pre><code>$1</code></pre>");
  html = html.replace(/`([^`]+)`/g, "<code>$1</code>");
  html = html.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
  html = html.replace(/\n- (.*)/g, "\n<li>$1</li>");
  html = html.replace(/(<li>.*<\/li>)/gs, "<ul>$1</ul>");
  return html
    .split(/\n{2,}/)
    .map((block) => (block.startsWith("<ul>") || block.startsWith("<pre>") ? block : `<p>${block.replace(/\n/g, "<br>")}</p>`))
    .join("");
}

function renderEmptyState() {
  chatMessages.innerHTML = `
    <div class="empty-state">
      <div class="empty-kicker">Production RAG assistant</div>
      <h3>Ask questions grounded in your knowledge base</h3>
      <p>This assistant retrieves semantic matches from the vector database before generating an answer, so responses stay tied to indexed documents.</p>
      <div class="knowledge-areas">
        ${knowledgeAreas.map((area) => `<span>${escapeHtml(area)}</span>`).join("")}
      </div>
      <div class="prompt-grid">
        ${suggestedPrompts.map((prompt) => `<button class="prompt-chip" type="button">${escapeHtml(prompt)}</button>`).join("")}
      </div>
    </div>
  `;

  chatMessages.querySelectorAll(".prompt-chip").forEach((button) => {
    button.addEventListener("click", () => {
      messageInput.value = button.textContent;
      autoResizeTextarea();
      messageInput.focus();
    });
  });
}

function renderStoredMessages() {
  const messages = getStoredMessages();
  chatMessages.innerHTML = "";
  if (!messages.length) {
    renderEmptyState();
    return;
  }
  messages.forEach((message) => addMessage(message, { persist: false }));
  scrollToBottom();
}

function renderChatHistory() {
  const sessions = getSessions();
  const activeId = getSessionId();
  if (!sessions.length) {
    chatHistory.innerHTML = '<div class="history-time">No previous chats yet.</div>';
    return;
  }

  chatHistory.innerHTML = sessions
    .map(
      (session) => `
        <button class="history-item ${session.id === activeId ? "active" : ""}" type="button" data-session-id="${session.id}">
          <div class="history-title">${escapeHtml(session.title)}</div>
          <div class="history-time">${new Date(session.updatedAt).toLocaleDateString()} ${formatTime(new Date(session.updatedAt))}</div>
        </button>
      `,
    )
    .join("");

  chatHistory.querySelectorAll(".history-item").forEach((button) => {
    button.addEventListener("click", () => {
      localStorage.setItem(SESSION_KEY, button.dataset.sessionId);
      updateActiveSessionLabel();
      renderChatHistory();
      renderStoredMessages();
    });
  });
}

function addMessage(message, options = { persist: true }) {
  const empty = chatMessages.querySelector(".empty-state");
  if (empty) empty.remove();

  const isUser = message.role === "user";
  const isError = message.role === "error";
  const row = document.createElement("article");
  row.className = `message-row ${isUser ? "user" : "assistant"} ${isError ? "error" : ""}`;

  const avatar = document.createElement("div");
  avatar.className = "avatar";
  avatar.textContent = isUser ? "YOU" : "AI";

  const card = document.createElement("div");
  card.className = "message-card";

  const content = document.createElement("div");
  content.className = "message-content";
  content.innerHTML = isUser || isError ? `<p>${escapeHtml(message.text)}</p>` : renderMarkdown(message.text);
  card.appendChild(content);

  const meta = document.createElement("div");
  meta.className = "message-meta";
  meta.innerHTML = `
    <span>${message.time || formatTime()}</span>
    <div class="meta-actions">${!isUser && !isError ? '<button class="copy-button" type="button">Copy</button>' : ""}</div>
  `;
  card.appendChild(meta);

  if (!isUser && !isError && message.rag) {
    card.appendChild(renderRetrievalPanel(message));
  }

  row.appendChild(avatar);
  row.appendChild(card);
  chatMessages.appendChild(row);

  const copyButton = row.querySelector(".copy-button");
  if (copyButton) {
    copyButton.addEventListener("click", async () => {
      await navigator.clipboard.writeText(message.text);
      copyButton.textContent = "Copied";
      setTimeout(() => {
        copyButton.textContent = "Copy";
      }, 1200);
    });
  }

  if (options.persist) {
    const messages = getStoredMessages();
    messages.push(message);
    saveStoredMessages(messages);
  }

  scrollToBottom();
}

function renderRetrievalPanel(message) {
  const details = document.createElement("details");
  details.className = "retrieval-panel";
  const scores = message.rag.similarityScores || [];
  const sources = message.rag.sourceDocuments || [];
  const formattedScores = scores.length ? scores.map((score) => Number(score).toFixed(3)).join(", ") : "No match";
  const sourceItems = sources.length
    ? sources.map((source) => `<li>${escapeHtml(source)}</li>`).join("")
    : "<li>No source passed threshold</li>";
  details.innerHTML = `
    <summary><span>Retrieval Details</span><strong>${message.rag.retrievedChunks} chunks</strong></summary>
    <div class="retrieval-grid">
      <div class="metric"><span>Chunks Retrieved</span><strong>${message.rag.retrievedChunks}</strong></div>
      <div class="metric"><span>Average Similarity</span><strong>${Number(message.rag.averageSimilarity || 0).toFixed(3)}</strong></div>
      <div class="metric"><span>Embedding Model</span><strong>${escapeHtml(message.rag.embeddingModel || "Gemini")}</strong></div>
      <div class="metric"><span>LLM Model</span><strong>${escapeHtml(message.rag.llmModel || "Gemini")}</strong></div>
      <div class="metric"><span>Vector DB</span><strong>${escapeHtml(message.rag.vectorDb || "ChromaDB")}</strong></div>
      <div class="metric"><span>Search Time</span><strong>${message.rag.searchTimeMs ?? 0} ms</strong></div>
      <div class="metric"><span>Total Latency</span><strong>${message.rag.latency}</strong></div>
      <div class="metric"><span>Tokens Used</span><strong>${message.rag.tokensUsed}</strong></div>
      <div class="source-list">
        <div class="source-heading">Sources</div>
        <ul>${sourceItems}</ul>
        <div class="score-line">Similarity scores: ${formattedScores}</div>
      </div>
    </div>
  `;
  return details;
}

function setLoading(isLoading, phase = "search") {
  loadingIndicator.hidden = !isLoading;
  sendButton.disabled = isLoading;
  messageInput.disabled = isLoading;

  if (!isLoading) return;

  if (phase === "generate") {
    loadingTitle.textContent = "Generating response...";
    loadingSubtitle.textContent = "Using retrieved context as the source of truth.";
  } else if (phase === "retrieve") {
    loadingTitle.textContent = "Retrieving relevant chunks...";
    loadingSubtitle.textContent = "Ranking semantic matches with cosine similarity.";
  } else {
    loadingTitle.textContent = "Searching knowledge base...";
    loadingSubtitle.textContent = "Embedding your question and checking the vector index.";
  }
}

async function sendMessage(message) {
  const start = performance.now();
  setLoading(true, "search");
  const retrieveTimer = setTimeout(() => setLoading(true, "retrieve"), 450);
  const generateTimer = setTimeout(() => setLoading(true, "generate"), 1100);

  try {
    const response = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ sessionId: getSessionId(), message }),
    });

    const payload = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(classifyError(payload.error || "Request failed"));
    }
    return {
      ...payload,
      latency: formatDuration(performance.now() - start),
    };
  } finally {
    clearTimeout(retrieveTimer);
    clearTimeout(generateTimer);
  }
}

function classifyError(errorMessage) {
  const message = errorMessage.toLowerCase();
  if (message.includes("timeout")) return "The request timed out while contacting the AI provider.";
  if (message.includes("api key") || message.includes("authorization")) return "The Gemini API key is missing or invalid.";
  if (message.includes("rate") || message.includes("quota")) return "The AI provider rate limit or quota was reached.";
  return errorMessage;
}

function scrollToBottom() {
  chatMessages.scrollTop = chatMessages.scrollHeight;
}

function autoResizeTextarea() {
  messageInput.style.height = "auto";
  messageInput.style.height = `${Math.min(messageInput.scrollHeight, 160)}px`;
}

chatForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const text = messageInput.value.trim();
  if (!text) return;

  const userMessage = { role: "user", text, time: formatTime() };
  addMessage(userMessage);
  updateSessionTitle(text);
  messageInput.value = "";
  autoResizeTextarea();

  try {
    const payload = await sendMessage(text);
    const assistantMessage = {
      role: payload.reply === FALLBACK_REPLY ? "error" : "assistant",
      text: payload.reply,
      time: formatTime(),
      rag: {
        retrievedChunks: payload.retrievedChunks,
        tokensUsed: payload.tokensUsed,
        latency: payload.latency,
        searchTimeMs: payload.searchTimeMs,
        averageSimilarity: payload.averageSimilarity,
        similarityScores: payload.similarityScores || [],
        sourceDocuments: payload.sourceDocuments || [],
        embeddingModel: payload.embeddingModel,
        llmModel: payload.llmModel,
        vectorDb: payload.vectorDb,
      },
    };
    addMessage(assistantMessage);
  } catch (error) {
    addMessage({ role: "error", text: error.message, time: formatTime() });
  } finally {
    setLoading(false);
    messageInput.focus();
  }
});

messageInput.addEventListener("input", autoResizeTextarea);

messageInput.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    chatForm.requestSubmit();
  }
});

newChatButton.addEventListener("click", () => {
  localStorage.setItem(SESSION_KEY, createSessionId());
  updateActiveSessionLabel();
  renderChatHistory();
  renderEmptyState();
  messageInput.value = "";
  autoResizeTextarea();
  messageInput.focus();
});

async function checkHealth() {
  try {
    const response = await fetch("/health");
    vectorStatus.textContent = response.ok ? "Online" : "Degraded";
    vectorStatus.className = response.ok ? "status-ok" : "status-warn";
  } catch {
    vectorStatus.textContent = "Offline";
    vectorStatus.className = "status-warn";
  }
}

getSessionId();
updateActiveSessionLabel();
renderChatHistory();
renderStoredMessages();
checkHealth();
