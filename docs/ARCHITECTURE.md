# Architecture

## Goal

Keep the product narrow and dependable:

- one persona
- one public AI feature: chat
- one grounded answer path
- predictable OpenAI cost per request

## Request Flow

```text
HTTP request
  -> FastAPI route
  -> Orchestrator
     -> local query guard
     -> context detection
     -> knowledge lookup
     -> hybrid retrieval
     -> relevance validation
     -> prompt builder + budget compaction
     -> provider call
  -> JSON or SSE response
```

## Main Modules

| Module | Responsibility |
|---|---|
| `main.py` | App startup, lifecycle wiring, middleware |
| `app/api/` | HTTP routes and response shaping |
| `app/orchestration/orchestrator.py` | End-to-end chat pipeline |
| `app/orchestration/query_guard.py` | Local prompt-injection and abuse guard |
| `app/contexts/context_registry.py` | Context-specific instructions and budgets |
| `app/repository/knowledge_repo.py` | PostgreSQL access |
| `app/retrieval/` | Dense, BM25, and hybrid retrieval |
| `app/validation/relevance_validator.py` | Cross-encoder reranking and gating |
| `app/prompt/prompt_builder.py` | Prompt assembly |
| `app/prompt/prompt_budget.py` | History and evidence compaction |
| `app/providers/` | LLM provider adapters |

## Cost-Control Design

The app avoids unnecessary paid generation in four places:

1. Query normalization and request-size limits reject oversized prompts early.
2. `query_guard.py` blocks obvious prompt-injection and hidden-prompt requests locally.
3. `relevance_validator.py` prevents unsupported questions from reaching the provider.
4. `prompt_budget.py` trims history and evidence before generation.

Knowledge ingestion is also cheap by design because category labels are generated locally in `app/contexts/knowledge_categorizer.py`.

## Data Model

### `knowledge_chunks`

- source of truth for persona knowledge
- stores global and per-user chunks
- powers retrieval and chat grounding

### `chat_sessions`

- optional persisted conversation history
- only recent turns are carried into prompts

### `feedback`

- user rating data for response quality review

## Architectural Rules

- Do not add new public AI endpoints unless the product scope changes.
- Prefer local logic before any provider call.
- Keep SQL inside the repository layer.
- Treat the prompt budget as a hard product requirement, not a best effort.
- Add tests for every user-visible contract change.
