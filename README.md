# Personal AI Representative

FastAPI backend for a single purpose: a personal AI agent chatbot that represents one person using approved knowledge only.

## What This Project Does

- Answers profile, project, portfolio, and availability questions about one configured persona.
- Uses RAG with hybrid retrieval and a relevance gate so unsupported questions do not trigger an expensive OpenAI call.
- Keeps prompt costs bounded with local guardrails, prompt compaction, and strict request limits.
- Lets the team add knowledge through the API without spending extra LLM tokens for chunk categorization.

## Product Boundary

This service is intentionally chatbot-first, with speech output for approved chatbot answers.

- Public AI endpoints: `/chat`, `/chat/stream`, `/speech`
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
  -> JSON, SSE response, or streaming audio
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
- Voice test: `http://localhost:8000/voice-test`
- OpenAPI: `http://localhost:8000/docs`
- Health: `http://localhost:8000/api/v1/health`

## Important Environment Variables

| Variable | Purpose |
|---|---|
| `PERSONA_NAME` | Person the chatbot represents |
| `PERSONA_ALIASES` | Alternate names the chatbot should recognize |
| `LLM_PROVIDER` | `openai`, `anthropic`, or `gemini` |
| `OPENAI_MODEL` | OpenAI chat model |
| `SPEECH_PROVIDER` | Speech synthesis provider: `openai`, `elevenlabs`, or `local` |
| `OPENAI_TTS_MODEL` | OpenAI speech model |
| `OPENAI_TTS_VOICE` | Built-in OpenAI voice name |
| `OPENAI_TTS_VOICE_ID` | Optional custom OpenAI voice ID once your voice is created |
| `OPENAI_TTS_INSTRUCTIONS` | Default delivery style for generated speech |
| `ELEVENLABS_API_KEY` | ElevenLabs API key when using `SPEECH_PROVIDER=elevenlabs` |
| `ELEVENLABS_VOICE_ID` | ElevenLabs cloned voice ID |
| `ELEVENLABS_MODEL` | ElevenLabs speech model |
| `LOCAL_TTS_URL` | Local self-hosted TTS server URL when using `SPEECH_PROVIDER=local` |
| `LOCAL_TTS_REFERENCE_AUDIO_PATH` | Reference voice sample path for local voice cloning |
| `LOCAL_TTS_REFERENCE_TEXT` | Transcript of the reference voice sample |
| `LOCAL_TTS_MODEL` | Local F5-TTS model name |
| `MAX_SPEECH_INPUT_CHARS` | Max text size accepted by `/speech` |
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
- speech output behavior
- knowledge ingestion and deletion
- prompt budgeting and compaction
- guardrails for prompt injection
- repository and session-store behavior

## Team Docs

- `docs/ARCHITECTURE.md`
- `docs/LOCAL_TTS.md`
- `docs/TEAM_GUIDE.md`
- `docs/OPERATIONS.md`

Local GPU-only services live in the sibling `E:\DevProj\AI Personal Projects\Self-Host` repo and are not deployed with this backend.

## Deployment

Production notes and the Hetzner runbook live in `docs/OPERATIONS.md`.

If you prefer containers, a `Dockerfile` and `.dockerignore` are included for image-based deployment as well.
