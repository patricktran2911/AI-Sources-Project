# AI Sources — Personal Chatbot API

A production-ready, multi-provider AI backend with RAG (Retrieval-Augmented
Generation), per-user knowledge management, and pluggable feature services
(chat, summarize, suggest).  Built with **FastAPI + asyncpg + sentence-transformers**.

---

## Table of Contents

1. [Architecture](#architecture)
2. [Project Structure](#project-structure)
3. [Setup — Local (Docker)](#setup--local-docker)
4. [Setup — AWS RDS](#setup--aws-rds)
5. [Environment Variables](#environment-variables)
6. [Step-by-Step Feature Guide](#step-by-step-feature-guide)
   - [Chat](#1-chat)
   - [Knowledge Management](#2-knowledge-management)
   - [Seed User Data (CLI)](#3-seed-user-data-cli)
   - [Summarize](#4-summarize)
   - [Suggest](#5-suggest)
   - [System Endpoints](#6-system-endpoints)
7. [Test Lab UI](#test-lab-ui)
8. [Testing](#testing)
9. [Deployment](#deployment)

---

## Architecture

```
HTTP Request
    │
    ▼
┌─────────────────────────────────────────────────────┐
│ FastAPI  (main.py)                                  │
│  • CORS middleware                                  │
│  • Rate-limiter middleware  (IP-based, in-memory)   │
│  • AppError → JSON handler                         │
└────────────┬────────────────────────────────────────┘
             │ Typed Depends() from app.core.dependencies
             ▼
┌─────────────────────────────────────────────────────┐
│ Route Handlers  (app/api/ + app/features/*/routes)  │
│  /chat  /chat/stream  /summarize  /suggest          │
│  /knowledge/add  /knowledge/{user_id}               │
│  /contexts  /features  /health  /info               │
└────────────┬────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────┐
│ Orchestrator  (app/orchestration/orchestrator.py)   │
│  1. detect_context()  — keyword + embedding routing │
│  2. KnowledgeRepository.get_chunks()  — load KB     │
│  3. EmbeddingRetriever.retrieve()  — semantic search│
│  4. RelevanceValidator.validate()  — cross-encoder  │
│  5. FeatureRegistry.get(feature).run()  — LLM call  │
└────────────┬────────────────────────────────────────┘
             │
    ┌────────┴─────────┐
    ▼                  ▼
┌──────────┐    ┌─────────────────────────────────────┐
│ LLM      │    │ PostgreSQL  (asyncpg connection pool)│
│ Provider │    │  knowledge_chunks table             │
│  OpenAI  │    │  (global + per-user rows)           │
│  Gemini  │    └─────────────────────────────────────┘
│ Anthropic│
└──────────┘
```

### Layer Responsibilities

| Layer | Location | Responsibility |
|-------|----------|----------------|
| Routes | `app/api/`, `app/features/*/routes.py` | HTTP validation, typed dep injection, response serialisation |
| Orchestrator | `app/orchestration/orchestrator.py` | Full pipeline coordination, context detection |
| Feature services | `app/features/` | Per-feature prompt assembly + LLM call |
| Prompt builder | `app/prompt/prompt_builder.py` | System + RAG prompt construction |
| Repository | `app/repository/knowledge_repo.py` | All SQL — read + write knowledge chunks |
| Retriever | `app/retrieval/embedding_retriever.py` | Sentence-transformer semantic search |
| Validator | `app/validation/relevance_validator.py` | Cross-encoder relevance gating |
| Providers | `app/providers/` | Thin wrappers over OpenAI / Gemini / Anthropic SDKs |
| Dependencies | `app/core/dependencies.py` | FastAPI `Annotated[..., Depends(...)]` typed aliases |

---

## Project Structure

```
.
├── main.py                      # App factory + lifespan startup
├── pyproject.toml
├── requirements.txt
├── data/                        # Seed JSON files (loaded once at startup)
│   ├── general/general.json
│   ├── portfolio/portfolio.json
│   ├── profile/profile.json
│   └── projects/projects.json
├── static/
│   ├── test_chat.html           # Simple chat UI (served at /)
│   └── test_all.html            # Full API test lab (served at /test)
├── app/
│   ├── api/
│   │   ├── ai_routes.py         # Router aggregator
│   │   ├── health.py            # /health + /info
│   │   ├── knowledge_routes.py  # /knowledge/…
│   │   └── meta.py              # /contexts + /features
│   ├── contexts/
│   │   ├── context_registry.py  # Loads context configs from data/
│   │   └── context_router.py    # Keyword-boost + embedding routing
│   ├── core/
│   │   ├── config.py            # Settings (pydantic-settings)
│   │   ├── dependencies.py      # Typed FastAPI Depends aliases
│   │   ├── exceptions.py        # Domain exceptions → HTTP errors
│   │   ├── logging.py           # Structured logging setup
│   │   ├── rate_limiter.py      # Sliding-window IP rate limiter
│   │   └── schemas.py           # All Pydantic request/response models
│   ├── database/
│   │   ├── connection.py        # asyncpg pool factory (RDS/Docker)
│   │   ├── migrations.py        # Schema migrations + JSON seed
│   │   └── seed_user.py         # CLI: seed all JSON data as a user
│   ├── features/
│   │   ├── base.py              # AbstractFeature interface
│   │   ├── registry.py          # Lazy feature instantiation
│   │   ├── session_store.py     # In-memory conversation history
│   │   ├── chatbot/             # Chat feature (streaming + standard)
│   │   ├── summarizer/          # Summarize feature
│   │   └── suggester/           # Suggest feature
│   ├── orchestration/
│   │   └── orchestrator.py      # Pipeline coordinator
│   ├── prompt/
│   │   └── prompt_builder.py    # System prompt + RAG context assembly
│   ├── providers/
│   │   ├── base.py              # BaseLLMProvider ABC
│   │   ├── factory.py           # Provider selection from settings
│   │   ├── openai_provider.py
│   │   ├── gemini_provider.py
│   │   └── anthropic_provider.py
│   ├── repository/
│   │   └── knowledge_repo.py    # All SQL — knowledge_chunks CRUD
│   ├── retrieval/
│   │   └── embedding_retriever.py
│   └── validation/
│       └── relevance_validator.py
└── tests/
    ├── conftest.py
    ├── test_chat.py
    ├── test_chat_stream.py
    ├── test_features.py
    ├── test_health.py
    ├── test_knowledge.py
    └── test_units.py
```

---

## Setup — Local (Docker)

### Step 1: Start PostgreSQL

```bash
docker run -d \
  --name ai-postgres \
  -e POSTGRES_USER=aiuser \
  -e POSTGRES_PASSWORD=aipassword \
  -e POSTGRES_DB=ai_sources \
  -p 5433:5432 \
  postgres:16-alpine
```

### Step 2: Configure environment

```bash
cp .env.example .env
```

Edit `.env`:

```dotenv
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...

DATABASE_URL=postgresql://aiuser:aipassword@localhost:5433/ai_sources

DEBUG=true
HOST=0.0.0.0
PORT=8000
```

### Step 3: Install dependencies & run

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS/Linux

pip install -r requirements.txt
uvicorn main:app --reload
```

The server auto-runs database migrations and seeds data from `data/` on first start.

- Chat UI: <http://localhost:8000>
- Test Lab: <http://localhost:8000/test>
- OpenAPI docs: <http://localhost:8000/docs>

---

## Setup — AWS RDS

Set in `.env` (or ECS task definition / EC2 environment):

```dotenv
AWS_SECRET_NAME=prod
AWS_REGION=us-east-1
# DATABASE_URL is ignored when AWS_SECRET_NAME is set.
```

The app reads DB credentials from **AWS Secrets Manager** and builds the DSN
automatically on startup.

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_PROVIDER` | `openai` | Active provider: `openai`, `gemini`, or `anthropic` |
| `OPENAI_API_KEY` | — | OpenAI API key |
| `GEMINI_API_KEY` | — | Google Gemini API key |
| `ANTHROPIC_API_KEY` | — | Anthropic Claude API key |
| `DATABASE_URL` | — | asyncpg DSN (used when `AWS_SECRET_NAME` is unset) |
| `AWS_SECRET_NAME` | — | Secrets Manager secret name (overrides `DATABASE_URL`) |
| `AWS_REGION` | `us-east-1` | AWS region for Secrets Manager |
| `DEBUG` | `false` | Enable debug logging + uvicorn reload |
| `HOST` | `0.0.0.0` | Bind address |
| `PORT` | `8000` | Bind port |
| `RATE_LIMIT_MAX_REQUESTS` | `20` | Max POST requests per window per IP |
| `RATE_LIMIT_WINDOW_SECONDS` | `60` | Rate-limit window in seconds |
| `DATA_DIR` | `data/` | Directory scanned for JSON seed files |

---

## Step-by-Step Feature Guide

All API endpoints are prefixed with **`/api/v1/ai`**.

---

### 1. Chat

The chat feature uses RAG to answer questions using knowledge stored in the
database.  It supports both standard (full response) and streaming (SSE) modes.

#### Step 1 — Send a message (standard mode)

```bash
curl -X POST http://localhost:8000/api/v1/ai/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Tell me about your projects",
    "context": "auto",
    "session_id": "my-session-1",
    "user_id": "patrick_tran"
  }'
```

| Field | Required | Description |
|-------|----------|-------------|
| `message` | yes | The question or message |
| `context` | no | `"auto"` (default) to auto-detect, or a specific context name |
| `session_id` | no | Enables multi-turn conversation history |
| `user_id` | no | Scopes to per-user knowledge (in addition to global) |

**Response:**

```json
{
  "success": true,
  "data": { "answer": "Here are my projects...", "supported": true },
  "meta": { "context": "projects", "chunks_used": 3 }
}
```

#### Step 2 — Stream responses (SSE)

```bash
curl -N -X POST http://localhost:8000/api/v1/ai/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"message": "What is your background?", "user_id": "patrick_tran"}'
```

Returns `text/event-stream`:

```
data: {"token": "I"}
data: {"token": " am"}
data: {"token": " a"}
...
data: {"done": true, "supported": true, "context": "profile"}
```

#### How auto-context works

When `context` is `"auto"` (or omitted), the orchestrator:
1. Scores your message against each context using keyword hints (2× boost) and
   embedding similarity (mean of top-3 chunks).
2. Picks the highest-scoring context (falls back to `"general"`).

Available contexts: `profile`, `projects`, `portfolio`, `general`.

---

### 2. Knowledge Management

The knowledge system lets you add, list, and delete per-user or global
knowledge chunks that feed the RAG pipeline.

#### Step 1 — Add knowledge

```bash
curl -X POST http://localhost:8000/api/v1/ai/knowledge/add \
  -H "Content-Type: application/json" \
  -d '{
    "text": "I am a backend engineer with 5 years of Python experience.\n\nI built a mobile app called FanFly for iOS.\n\nMy portfolio website is deployed on AWS.",
    "user_id": "patrick_tran"
  }'
```

| Field | Required | Description |
|-------|----------|-------------|
| `text` | yes | Free-form text (up to 20,000 chars). Paragraphs separated by blank lines are split into individual chunks. |
| `user_id` | no | Omit to store as **global** knowledge (visible to all). |
| `context` | no | Force all chunks into a specific context. **Omit to auto-detect per-chunk.** |

**Per-chunk auto-detection:** When `context` is omitted, each chunk is routed
independently.  A paragraph about projects goes into `projects`, one about your
profile goes into `profile`, etc.

**Response:**

```json
{
  "success": true,
  "chunks_added": 3,
  "contexts": ["portfolio", "profile", "projects"],
  "chunks": [
    { "id": "c3f1...", "context": "profile",   "category": "Backend Engineer", "text": "I am a backend..." },
    { "id": "a7b2...", "context": "projects",  "category": "Mobile App",       "text": "I built a mobile..." },
    { "id": "d9e4...", "context": "portfolio",  "category": "AWS Deployment",   "text": "My portfolio..." }
  ]
}
```

> **Tip:** Send a long text with mixed topics and leave `context` blank — the
> system will correctly categorize each paragraph into the right context.

#### Step 2 — List knowledge

```bash
# All chunks for a user
curl http://localhost:8000/api/v1/ai/knowledge/patrick_tran

# Filter by context
curl http://localhost:8000/api/v1/ai/knowledge/patrick_tran?context=profile
```

**Response:**

```json
{
  "success": true,
  "user_id": "patrick_tran",
  "total": 56,
  "chunks": [
    { "id": "...", "context": "profile", "category": "...", "text": "..." },
    ...
  ]
}
```

#### Step 3 — Delete a chunk

```bash
curl -X DELETE http://localhost:8000/api/v1/ai/knowledge/patrick_tran/c3f1a-chunk-id
```

**Response:**

```json
{ "success": true, "deleted": true, "chunk_id": "c3f1a-chunk-id" }
```

#### User vs Global Knowledge

| Scope | How to add | Visible to |
|-------|-----------|------------|
| **Per-user** | Include `user_id` in request | Only that user (merged with global at query time) |
| **Global** | Omit `user_id` | All users |

---

### 3. Seed User Data (CLI)

Bulk-load all JSON files under `data/` as a specific user. This is useful for
bootstrapping a user's knowledge base with the pre-existing profile, projects,
portfolio, and general data.

```bash
py -3.12 -m app.database.seed_user patrick_tran
```

**What it does:**

1. Reads every `data/<context>/*.json` file (profile, projects, portfolio, general).
2. Inserts each chunk as `user_id=patrick_tran` with `ON CONFLICT DO NOTHING`.
3. Global seed data (`user_id=NULL`) is **not affected** — both coexist.

**Output:**

```
INFO    general       2 chunk(s)
INFO    portfolio     7 chunk(s)
INFO    profile       36 chunk(s)
INFO    projects      11 chunk(s)
INFO  Seeded 56 total chunk(s) for user_id='patrick_tran'
```

After seeding, chat queries with `user_id=patrick_tran` will draw from both the
user's personal knowledge and the global seed data.

---

### 4. Summarize

Generate a summary of provided text, optionally scoped to a context.

```bash
curl -X POST http://localhost:8000/api/v1/ai/summarize \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Summarize the key features of the PIM project",
    "context": "projects"
  }'
```

**Response:**

```json
{
  "success": true,
  "data": { "answer": "The PIM project is...", "supported": true },
  "meta": { "context": "projects", "chunks_used": 3 }
}
```

---

### 5. Suggest

Get AI-powered suggestions based on knowledge context.

```bash
curl -X POST http://localhost:8000/api/v1/ai/suggest \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What technologies should I learn next?",
    "context": "profile"
  }'
```

**Response:**

```json
{
  "success": true,
  "data": { "answer": "Based on your profile...", "supported": true },
  "meta": { "context": "profile", "chunks_used": 3 }
}
```

---

### 6. System Endpoints

#### Health check

```bash
curl http://localhost:8000/api/v1/health
```

```json
{ "status": "ok", "db": "ok" }
```

Returns `"db": "degraded"` when the database is unreachable (still HTTP 200).

#### App info

```bash
curl http://localhost:8000/api/v1/info
```

```json
{ "app": "AI Combination Server", "version": "0.1.0", "provider": "openai" }
```

#### List contexts

```bash
curl http://localhost:8000/api/v1/ai/contexts
```

```json
{ "contexts": ["general", "portfolio", "profile", "projects"] }
```

#### List features

```bash
curl http://localhost:8000/api/v1/ai/features
```

```json
{ "features": ["chat", "suggest", "summarize"] }
```

---

## Test Lab UI

A comprehensive in-browser test lab is available at:

```
http://localhost:8000/test
```

It provides 6 tabs:

| Tab | What it tests |
|-----|---------------|
| **Chat** | Standard and streaming chat with context/session/user controls |
| **Add Knowledge** | Add free-form text with auto or manual context |
| **List Knowledge** | Browse and delete per-user chunks |
| **Summarize** | Run the summarize endpoint |
| **Suggest** | Run the suggest endpoint |
| **System** | Health, info, contexts, features |

---

## Testing

```bash
# Run all tests (61 tests)
py -3.12 -m pytest tests/ -q

# Verbose output
py -3.12 -m pytest tests/ -v

# Specific test file
py -3.12 -m pytest tests/test_knowledge.py -v
```

The suite uses `pytest-asyncio` with a live asyncpg pool pointed at the Docker
database.  All tests must pass before deploying.

---

## Deployment

### Docker Compose

```yaml
services:
  api:
    build: .
    env_file: .env
    ports:
      - "8000:8000"
    depends_on: [db]

  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: aiuser
      POSTGRES_PASSWORD: aipassword
      POSTGRES_DB: ai_sources
    volumes:
      - pgdata:/var/lib/postgresql/data

volumes:
  pgdata:
```

### Switch to AWS production DB

```dotenv
AWS_SECRET_NAME=prod
AWS_REGION=us-east-1
DEBUG=false
```

Restart the server — credentials are fetched from Secrets Manager automatically.
