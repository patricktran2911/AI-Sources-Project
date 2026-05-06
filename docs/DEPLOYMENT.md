# Deployment Runbook

This project deploys as two services:

- `AI Sources Project`: public FastAPI chatbot/RAG backend.
- `Self-Host`: private GPU voice service that keeps consented reference audio on the owner's PC.

## Required Secrets

Set these before exposing the API:

```env
APP_API_KEY=change-this-before-deploying
CORS_ALLOW_ORIGINS=https://your-chat-ui.example.com
DATABASE_URL=postgresql://...
OPENAI_API_KEY=...
LOCAL_TTS_API_KEY=the-same-value-as-LOCAL_AI_API_KEY
```

Set these on the local GPU PC:

```env
LOCAL_AI_API_KEY=the-same-value-as-LOCAL_TTS_API_KEY
VOICE_REFERENCE_AUDIO_PATH=C:\path\to\approved\voice-samples\patrick.wav
VOICE_REFERENCE_DIR=C:\path\to\approved\voice-samples
VOICE_REFERENCE_TEXT=The exact transcript spoken in the reference clip.
VOICE_ALLOW_REQUEST_REFERENCE_OVERRIDE=false
```

## Main Backend

```powershell
cd "E:\DevProj\AI Personal Projects\AI Sources Project"
py -3.12 -m pip install -r requirements.txt
py -3.12 _deploy.py
py -3.12 -m uvicorn main:app --host 0.0.0.0 --port 8000
```

For container hosting, build from `Dockerfile` and provide the same environment variables through the platform's secret manager.

## Local Voice Service

```powershell
cd "E:\DevProj\AI Personal Projects\Self-Host"
py -3.10 -m venv .venv
.\.venv\Scripts\activate
python -m pip install --upgrade pip
pip install torch==2.8.0+cu128 torchaudio==2.8.0+cu128 --extra-index-url https://download.pytorch.org/whl/cu128
pip install -r requirements.txt
.\run.ps1
```

Run CosyVoice beside it if `VOICE_ENGINE=auto` or `VOICE_ENGINE=cosyvoice`:

```powershell
cd "E:\DevProj\AI Personal Projects\CosyVoice"
conda activate cosyvoice
python runtime\python\fastapi\server.py --port 50000 --model_dir pretrained_models\Fun-CosyVoice3-0.5B
```

Expose `Self-Host` only through a private tunnel or HTTPS tunnel, and keep `LOCAL_AI_API_KEY` set.

## Smoke Checks

```powershell
curl http://localhost:8000/api/v1/health
curl -H "Authorization: Bearer %APP_API_KEY%" http://localhost:8000/api/v1/ai/voice/local-health
curl -H "Authorization: Bearer %LOCAL_AI_API_KEY%" http://localhost:7861/v1/capabilities
```
