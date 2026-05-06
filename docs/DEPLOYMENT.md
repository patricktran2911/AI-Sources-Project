# Deployment Runbook

This project deploys as the public FastAPI chatbot/RAG backend. Heavy voice synthesis is optional and lives outside this repo in the separate `Self-Host` service.

## Required Secrets

Set these before exposing the API:

```env
APP_API_KEY=change-this-before-deploying
CORS_ALLOW_ORIGINS=https://your-chat-ui.example.com
DATABASE_URL=postgresql://...
OPENAI_API_KEY=...
SPEECH_PROVIDER=openai
```

Only set the local speech values after a hosted Self-Host service exists:

```env
SPEECH_PROVIDER=local
LOCAL_TTS_URL=https://self-host.example.com/v1/voice/synthesize
LOCAL_TTS_API_KEY=the-same-value-as-LOCAL_AI_API_KEY
```

## Main Backend

```powershell
cd "E:\DevProj\AI Personal Projects\AI Sources Project"
py -3.12 -m pip install -r requirements.txt
py -3.12 _deploy.py
py -3.12 -m uvicorn main:app --host 0.0.0.0 --port 8000
```

For container hosting, build from `Dockerfile` and provide the same environment variables through the platform's secret manager.

## Hetzner

The current Hetzner deployment should continue to use:

```env
SPEECH_PROVIDER=openai
LOCAL_TTS_URL=
LOCAL_TTS_API_KEY=
```

Deploy or restart with the systemd/Docker flow in `deploy/README.md`, then verify:

```bash
curl -s http://127.0.0.1:8000/api/v1/health
curl -s https://ai-dev.patrickcs-web.com/api/v1/health
```

## Future Self-Host Voice

Deploy `Self-Host` on a dedicated machine or cloud GPU host. Do not point Hetzner at a personal Windows workstation unless that is intentionally reintroduced later.

Required Self-Host values:

```env
LOCAL_AI_API_KEY=the-same-value-as-LOCAL_TTS_API_KEY
VOICE_REFERENCE_AUDIO_PATH=/srv/self-host/voice/reference/patrick.wav
VOICE_REFERENCE_DIR=/srv/self-host/voice/reference
VOICE_REFERENCE_TEXT=The exact transcript spoken in the reference clip.
VOICE_ALLOW_REQUEST_REFERENCE_OVERRIDE=false
```

Before switching this backend to `SPEECH_PROVIDER=local`, verify:

```bash
curl -s https://self-host.example.com/health
curl -s -H "Authorization: Bearer $LOCAL_TTS_API_KEY" https://self-host.example.com/v1/capabilities
```

Then set `LOCAL_TTS_URL`, set the matching API key, restart the backend, and call `/api/v1/ai/voice/local-health`.

## Smoke Checks

```powershell
curl http://localhost:8000/api/v1/health
curl -H "Authorization: Bearer %APP_API_KEY%" http://localhost:8000/api/v1/ai/features
curl -H "Authorization: Bearer %APP_API_KEY%" http://localhost:8000/api/v1/ai/voice/local-health
```

When `SPEECH_PROVIDER=openai`, `local-health` should report local voice as disabled.
