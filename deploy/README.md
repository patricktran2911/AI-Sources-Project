# Hetzner Docker Deployment

This is the low-cost production layout:

- Hetzner runs the public FastAPI/RAG backend and Postgres in Docker.
- The RTX 4070 PC runs `Self-Host` for CosyVoice/F5-TTS.
- A reverse SSH tunnel exposes the PC voice service to Hetzner at `127.0.0.1:17861`.

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
OPENAI_API_KEY=replace-if-using-openai
LLM_PROVIDER=openai
SPEECH_PROVIDER=local
LOCAL_TTS_URL=http://127.0.0.1:17861/v1/voice/synthesize
LOCAL_TTS_API_KEY=replace-with-the-same-value-as-local-ai-api-key
```

Start or update:

```bash
sudo systemctl start ai-sources-docker
sudo systemctl status ai-sources-docker --no-pager
docker compose -f deploy/docker-compose.app.yml logs --tail=100 app
curl -s http://127.0.0.1:8000/api/v1/health
```

The app-only compose file is intended for the current Hetzner host, where Postgres already runs separately on `127.0.0.1:5433`. The app container uses host networking so it can reach both Postgres and the reverse SSH voice tunnel at `127.0.0.1:17861`. Uvicorn is bound to `127.0.0.1:8000`; keep Nginx/Caddy in front of it for HTTPS.

Use `deploy/docker-compose.prod.yml` only for a fresh all-in-one host where this stack should create its own Postgres volume.

## Updating

```bash
cd /root/AI-Sources-Project
git pull
sudo systemctl restart ai-sources-docker
curl -s http://127.0.0.1:8000/api/v1/health
```

## Reverse SSH Voice Tunnel

On the RTX 4070 PC, start `Self-Host` on `127.0.0.1:7861`, then start the tunnel:

```powershell
cd "E:\DevProj\AI Personal Projects\Self-Host"
$env:HETZNER_TUNNEL_HOST="patrick@5.78.76.197"
.\start_hetzner_tunnel.ps1
```

Register it as a Windows scheduled task after the SSH login works:

```powershell
.\register_tunnel_task.ps1
```

On Hetzner, verify:

```bash
curl -s http://127.0.0.1:17861/v1/capabilities
curl -s -H "Authorization: Bearer $APP_API_KEY" http://127.0.0.1:8000/api/v1/ai/voice/local-health
```
