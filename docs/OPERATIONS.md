# Operations

## Runtime Model

- FastAPI app served by Uvicorn
- PostgreSQL for knowledge, chat history, and feedback
- LLM provider selected by environment variables
- Production should run with `DEBUG=false`

## Hetzner Deployment Runbook

Use secure secrets storage for the host, SSH key path, passphrase, and domain. Do not store live credentials in the repo.

### Deploy latest code

1. Run tests locally.
2. Push the branch you want to deploy.
3. SSH to the Hetzner server.
4. Pull the latest code in the app directory.
5. Refresh the virtualenv dependencies if required.
6. Restart the systemd service.
7. Call `/api/v1/health`.

Example remote commands:

```bash
cd /srv/personal-ai-representative
git pull origin main
source .venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart ai-combination
curl -s http://127.0.0.1:8000/api/v1/health
```

If your production service has already been renamed, replace `ai-combination` with the real service name.

## Health Checks

- Local: `curl -s http://127.0.0.1:8000/api/v1/health`
- Public: `curl -s https://your-domain/api/v1/health`
- App info: `curl -s http://127.0.0.1:8000/api/v1/info`

## Logs

```bash
journalctl -u ai-combination -n 100 --no-pager
journalctl -u ai-combination -f
```

## Rollback

```bash
cd /srv/personal-ai-representative
git log --oneline -n 5
git checkout <last-known-good-commit>
source .venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart ai-combination
```

## Scaling Notes

### First scaling moves

- Increase server memory so embedding and reranker models stay warm.
- Put PostgreSQL on a managed instance if the app and DB currently share one host.
- Keep one app instance per warm model set before introducing horizontal scale.

### When traffic grows

- Run multiple Uvicorn workers behind Nginx or a process manager.
- Move session history and rate-limit state to shared backing services if multiple app nodes are added.
- Add API-level request metrics and latency dashboards.
- Consider precomputing and storing embeddings if retrieval latency becomes noticeable.

## Security Rules

- `.env` stays off git.
- Server credentials stay in a password manager or secret store.
- Do not place SSH passphrases, root passwords, or live host details in markdown files.
