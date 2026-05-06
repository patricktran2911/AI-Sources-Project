# Hetzner Docker Deployment

This is the lightweight production layout for the cloud backend:

- Hetzner runs the public FastAPI/RAG backend.
- Postgres runs either on the same host or in a managed database.
- Speech output uses OpenAI by default.
- A future `Self-Host` voice service can be enabled later by setting an external HTTPS URL and matching API key.

No personal-machine bridge or Windows startup task is part of this deployment.

## Server Setup

Install Docker and clone the repository to `/root/AI-Sources-Project`.

Copy the systemd unit:

```bash
sudo cp deploy/ai-sources-docker.service /etc/systemd/system/ai-sources-docker.service
sudo systemctl daemon-reload
sudo systemctl enable ai-sources-docker
```

Create `/root/AI-Sources-Project/.env` with production secrets:

```env
APP_API_KEY=replace-with-a-long-random-secret
CORS_ALLOW_ORIGINS=https://your-domain.example
POSTGRES_DB=ai_sources
POSTGRES_USER=aiuser
POSTGRES_PASSWORD=replace-with-a-long-random-password
POSTGRES_PORT=5433
DEBUG=false
AWS_SECRET_NAME=
RDS_IAM_AUTH=false
LLM_PROVIDER=openai
OPENAI_API_KEY=replace-if-using-openai
SPEECH_PROVIDER=openai
LOCAL_TTS_URL=
LOCAL_TTS_API_KEY=
```

Start or update:

```bash
sudo systemctl start ai-sources-docker
sudo systemctl status ai-sources-docker --no-pager
docker compose -f deploy/docker-compose.app.yml logs --tail=100 app
curl -s http://127.0.0.1:8000/api/v1/health
```

The app-only compose file is intended for the current Hetzner host, where Postgres already runs separately on `127.0.0.1:5433`. The app container uses host networking so it can reach that local database. Uvicorn is bound to `127.0.0.1:8000`; keep Nginx/Caddy in front of it for HTTPS.

Use `deploy/docker-compose.prod.yml` only for a fresh all-in-one host where this stack should create its own Postgres volume.

## Updating

```bash
cd /root/AI-Sources-Project
git pull
sudo systemctl restart ai-sources-docker
curl -s http://127.0.0.1:8000/api/v1/health
```

## Future Self-Host Voice

When `Self-Host` is deployed somewhere reachable by Hetzner, configure:

```env
SPEECH_PROVIDER=local
LOCAL_TTS_URL=https://self-host.example.com/v1/voice/synthesize
LOCAL_TTS_API_KEY=the-same-value-as-LOCAL_AI_API_KEY
```

Verify before enabling traffic:

```bash
curl -s https://self-host.example.com/health
curl -s -H "Authorization: Bearer $APP_API_KEY" http://127.0.0.1:8000/api/v1/ai/voice/local-health
```

Keep `SPEECH_PROVIDER=openai` until the hosted Self-Host service is stable, secured, and reachable from the cloud backend.
