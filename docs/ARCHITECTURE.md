# Architecture

## Goal

Keep the product narrow and dependable:

- one persona
- one public AI feature: chat, with text and speech I/O modes for chatbot answers
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
  -> JSON, SSE response, streaming audio response, or JSON answer plus audio
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
| `app/providers/openai_speech_provider.py` | OpenAI text-to-speech provider adapter |
| `app/providers/elevenlabs_speech_provider.py` | ElevenLabs cloned-voice provider adapter |
| `app/providers/local_speech_provider.py` | Self-hosted local voice-cloning provider adapter |

## Cost-Control Design

The app avoids unnecessary paid generation in four places:

1. Query normalization and request-size limits reject oversized prompts early.
2. `query_guard.py` blocks obvious prompt-injection and hidden-prompt requests locally.
3. `relevance_validator.py` prevents unsupported questions from reaching the provider.
4. `prompt_budget.py` trims history and evidence before generation.

Knowledge ingestion is also cheap by design because category labels are generated locally in `app/contexts/knowledge_categorizer.py`.

Speech output is intentionally a second step after chat. Clients call `/chat` to get the grounded answer, then call `/speech` with that answer text when audio playback is needed.

For one-call voice UX, clients can call `/text-to-speech` to get the chatbot answer and base64 audio together, or `/speech-to-speech` to upload user audio, transcribe it, generate the grounded answer, and receive answer audio in the same JSON response.

Self-hosted voice cloning is isolated behind `LocalSpeechProvider`, which calls the separate `Self-Host` service instead of loading heavy ML models into the main backend process. That service now prefers CosyVoice for persona-style speech and keeps F5-TTS as a fallback.

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
