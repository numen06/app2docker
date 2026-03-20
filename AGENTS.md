# AGENTS.md

## Cursor Cloud specific instructions

### Project overview

App2Docker is a visual platform for one-click Docker image builds. It consists of:

- **Backend**: Python/FastAPI (port 8000), SQLite database, entry point `backend/app.py`
- **Frontend**: Vue 3 + Vite (port 3000), proxies `/api` to backend via Vite dev server

### Running services

1. **Backend**: `cd /workspace && PYTHONPATH=/workspace ./venv/bin/python backend/app.py` (port 8000)
2. **Frontend dev server**: `cd /workspace/frontend && npx vite --host 0.0.0.0 --port 3000` (port 3000)
3. **Docker daemon**: Must be running (`sudo dockerd &`) — required for core image build functionality

### Important notes

- Default login: `admin` / `admin`. First login forces a password change.
- The frontend `package-lock.json` exists, so use `npm install` (not pnpm/yarn) for frontend deps.
- The backend uses a Python venv at `./venv`. Always use `./venv/bin/python` to run backend code.
- Docker daemon needs `fuse-overlayfs` storage driver and `iptables-legacy` in Cloud Agent VMs (nested container environment). Config at `/etc/docker/daemon.json`.
- After `dockerd` starts, you may need `sudo chmod 666 /var/run/docker.sock` for the non-root user to access Docker.
- SQLite database is auto-created at `data/app2docker.db` on first startup.
- The backend auto-registers a local Agent WebSocket client on startup; connection errors are non-fatal.
- API docs available at `http://localhost:8000/docs` (Swagger UI).
