# AI Combination Server

A scalable, modular Python AI backend platform built with FastAPI.

## Quick Start

```bash
# 1. Create virtual environment
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS/Linux

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
copy .env.example .env
# Edit .env with your API keys

# 4. Run the server
uvicorn main:app --reload
```

The server starts at **http://localhost:8000**.  
Interactive docs at **http://localhost:8000/docs**.

## Architecture

```
app/
├─ api/             # Thin FastAPI route handlers
├─ orchestration/   # Coordinates the full AI pipeline
├─ features/        # One service per AI feature (chat, summarize, suggest, …)
├─ contexts/        # Per-context behaviour (profile, projects, portfolio, …)
├─ retrieval/       # Semantic search with sentence-transformers
├─ validation/      # Cross-encoder reranking & relevance gating
├─ prompt/          # Builds compact prompts for the LLM
├─ providers/       # Abstract LLM providers (OpenAI, Anthropic, Gemini)
├─ repository/      # Knowledge storage (JSON files → future DB/vector DB)
└─ core/            # Config, logging, exceptions, schemas
data/               # Knowledge JSON files organised by context
```

## API Endpoints

| Method | Path                     | Description              |
| ------ | ------------------------ | ------------------------ |
| GET    | `/api/v1/health`         | Health check             |
| GET    | `/api/v1/info`           | App info                 |
| POST   | `/api/v1/ai/chat`        | Chat with RAG            |
| POST   | `/api/v1/ai/summarize`   | Summarise retrieved data |
| POST   | `/api/v1/ai/suggest`     | Get suggestions          |
| GET    | `/api/v1/ai/contexts`    | List available contexts  |
| GET    | `/api/v1/ai/features`    | List available features  |

### Example Request

```bash
curl -X POST http://localhost:8000/api/v1/ai/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "Tell me about the PIM project", "context": "projects"}'
```

## Adding New Features

1. Create a new class in `app/features/` extending `BaseFeature`
2. Register it in `app/features/registry.py`
3. Add a route in `app/api/ai_routes.py`

## Adding New Contexts

1. Add a `ContextConfig` in `app/contexts/context_registry.py`
2. Create a `data/<context_name>/` folder with JSON knowledge files

## Environment Variables

See [.env.example](.env.example) for all configuration options.
