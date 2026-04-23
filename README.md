# Personal AI Representative

FastAPI backend for a single purpose: a personal AI agent chatbot that represents one person using approved knowledge only.

## What This Project Does

- Answers profile, project, portfolio, and availability questions about one configured persona.
- Uses RAG with hybrid retrieval and a relevance gate so unsupported questions do not trigger an expensive OpenAI call.
- Keeps prompt costs bounded with local guardrails, prompt compaction, and strict request limits.
- Lets the team add knowledge through the API without spending extra LLM tokens for chunk categorization.

## Product Boundary

This service is intentionally chatbot-only.

- Public AI endpoints: `/chat`, `/chat/stream`
- Support endpoints: `/knowledge/*`, `/feedback`, `/contexts`, `/features`, `/health`, `/info`
- Retired endpoints: `/summarize`, `/suggest`

## Core Guardrails

- `MAX_USER_QUERY_CHARS` caps incoming user messages before the provider is called.
- Prompt injection attempts are blocked locally.
- Conversation history is compacted by message count and character budget.
- Retrieved evidence is compacted by chunk count and character budget.
- Unsupported queries are refused before generation when the relevance gate has no supporting chunks.
- Knowledge ingestion uses local keyword categorization instead of an LLM.

## Architecture At A Glance

```text
Client
  -> FastAPI routes
  -> Orchestrator
     -> Query guard
     -> Context router
     -> Knowledge repository
     -> Hybrid retriever
     -> Relevance validator
     -> Prompt builder + prompt budget
     -> LLM provider
  -> JSON or SSE response
```

## Quick Start

### 1. Configure the app

```bash
cp .env.example .env
```

Set at minimum:

- `OPENAI_API_KEY`
- `DATABASE_URL`
- `PERSONA_NAME`

### 2. Start PostgreSQL

```bash
docker compose up -d
```

### 3. Install dependencies

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### 4. Run the API

```bash
uvicorn main:app --reload
```

Useful local URLs:

- Chat UI: `http://localhost:8000/`
- QA lab: `http://localhost:8000/test`
- OpenAPI: `http://localhost:8000/docs`
- Health: `http://localhost:8000/api/v1/health`

## Important Environment Variables

| Variable | Purpose |
|---|---|
| `PERSONA_NAME` | Person the chatbot represents |
| `PERSONA_ALIASES` | Alternate names the chatbot should recognize |
| `LLM_PROVIDER` | `openai`, `anthropic`, or `gemini` |
| `OPENAI_MODEL` | OpenAI chat model |
| `MAX_CONTEXT_TOKENS` | Prompt token budget before generation |
| `MAX_OUTPUT_TOKENS` | Completion budget |
| `MAX_USER_QUERY_CHARS` | Max incoming user message size |
| `MAX_HISTORY_MESSAGES` | Max messages carried into the prompt |
| `MAX_EVIDENCE_CHUNKS` | Max retrieved chunks injected into the prompt |
| `RELEVANCE_THRESHOLD` | Cross-encoder gate threshold |
| `DATABASE_URL` | PostgreSQL DSN |

## Testing

Run the full suite:

```bash
py -3.12 -m pytest tests -q
```

Current coverage focus:

- chat and streaming behavior
- knowledge ingestion and deletion
- prompt budgeting and compaction
- guardrails for prompt injection
- repository and session-store behavior

## Team Docs

- `docs/ARCHITECTURE.md`
- `docs/TEAM_GUIDE.md`
- `docs/OPERATIONS.md`

## Deployment

Production notes and the Hetzner runbook live in `docs/OPERATIONS.md`.

If you prefer containers, a `Dockerfile` and `.dockerignore` are included for image-based deployment as well.
