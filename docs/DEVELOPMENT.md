# Development Guide

## Architecture

`AI Sources Project` is the public FastAPI backend for Patrick's personal AI representative. It owns persona chat, retrieval, API contracts, speech orchestration, and persistence. Heavy voice synthesis is optional and delegated to the separate `Self-Host` service through `LocalSpeechProvider`.

```text
Client
  -> FastAPI route
  -> Orchestrator
  -> Guardrails, context routing, retrieval, relevance validation
  -> LLM provider
  -> JSON, SSE, streaming audio, or base64 audio response
```

## Setup

```powershell
cd "E:\DevProj\AI Personal Projects\AI Sources Project"
py -3.12 -m venv .venv
.\.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
```

Set at minimum:

- `APP_API_KEY`
- `DATABASE_URL`
- `OPENAI_API_KEY`
- `PERSONA_NAME`

Start local Postgres with `docker compose up -d`, then run:

```powershell
py -3.12 -m uvicorn main:app --reload
```

## API Contract

All AI routes are under `/api/v1/ai`.

| Endpoint | Purpose |
|---|---|
| `POST /text-to-text` | Text message in, grounded text answer out |
| `POST /chat` | Primary chatbot answer |
| `POST /chat/stream` | Streaming chatbot answer |
| `POST /speech` | Text in, audio stream out |
| `POST /speech-to-text` | Audio upload in, transcript out |
| `POST /text-to-speech` | Text message in, answer plus base64 audio out |
| `POST /speech-to-speech` | Audio upload in, transcript, answer, and base64 audio out |
| `POST /text-to-speech/stream` | NDJSON voice-chat stream: `meta`, `answer_delta`, `sentence`, `audio`, `done` |

## Environment Rules

- `SPEECH_PROVIDER=openai` is the safe default.
- Leave `LOCAL_TTS_URL` empty unless an external Self-Host deployment is ready.
- `SPEECH_PROVIDER=local` requires `LOCAL_TTS_URL` and a matching `LOCAL_TTS_API_KEY`.
- Never commit `.env`, credentials, generated audio, or private voice reference files.
- Keep prompt and retrieval budget variables conservative unless tests prove a wider budget is needed.

## Voice Safety

The main backend stores consent metadata only. Reference audio, checkpoints, and voice model artifacts belong on Self-Host. Before enabling local speech:

1. Deploy Self-Host somewhere reachable by this backend.
2. Set `LOCAL_AI_API_KEY` on Self-Host.
3. Set matching `LOCAL_TTS_API_KEY` here.
4. Verify Self-Host `/health` and `/v1/capabilities`.
5. Set `SPEECH_PROVIDER=local`.
6. Verify `/api/v1/ai/voice/local-health`.

## Testing

```powershell
py -3.12 -m pytest tests -q
```

Tests cover chat routing, retrieval behavior, speech endpoints, provider adapters, prompt budgets, session storage, and voice consent metadata. Add tests for any user-visible API behavior or provider contract change.

## Deployment

Use `deploy/README.md` for Hetzner Docker/systemd steps. The current cloud production default remains OpenAI speech. Future Self-Host integration should be enabled through environment variables only after the external service is secured and healthy.

## Restore From Backup

Before the production cleanup, a tag was created:

```powershell
git checkout backup/pre-clean-20260506
```

Tracked source archives and private local runtime archives are stored under:

```text
E:\DevProj\AI Personal Projects\_backups
```

Private archives may contain `.env` values or voice audio and should stay local.
