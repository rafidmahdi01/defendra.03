# Defendra Client Server

Modular Python endpoint security client that communicates with the Defendra backend over REST.

## Features

| Module | Purpose |
|--------|---------|
| `core/api_client.py` | `send_log()`, `send_alert()`, `fetch_commands()`, registration, heartbeat, offline sync |
| `modules/device_monitor.py` | Hostname, IP, OS, heartbeat |
| `modules/usb_scanner.py` | USB detection + hash scan |
| `modules/email_scanner.py` | Pre-click email heuristics |
| `modules/behavior_monitor.py` | CPU spikes + suspicious processes |
| `modules/backup_manager.py` | Local backup + cloud sync logging |
| `modules/alert_system.py` | Dashboard alerts via API (no local pop-ups by default) |
| `modules/command_handler.py` | Admin commands (isolate, scan, backup) |
| `core/network_monitor.py` | Offline queue flush when server returns |

## Backend connection

The client server talks to the Defendra API at `SERVER_URL` (default `http://127.0.0.1:8000`).

On startup, `main.py` runs a connection handshake:

1. Wait for `GET /health`
2. Bootstrap admin account (first run)
3. Login with `API_EMAIL` / `API_PASSWORD`
4. Register device via `POST /api/devices/workstation/link`
5. Sync any offline queue + send heartbeat

**Run everything together** (recommended):

```bat
start.bat
```

from the project root — starts backend, frontend, and the client server.

**Run client only** (backend must already be running):

```bat
client\start.bat
```

Credentials in `client/.env` must match a Defendra user (default: `admin@defendra.com` / `Admin@1234`).

## Quick start

```bash
cd client
pip install -r requirements.txt
copy .env.example .env
# Edit .env with your Defendra admin credentials

python main.py
```

Ensure the Defendra backend is running on `http://127.0.0.1:8000`.

## Offline mode

When the server is unreachable, logs and alerts are stored in `data/offline_queue.json`.  
When connectivity returns, the network monitor syncs via `POST /api/sync/offline-logs`.

## Local testing

- **Backup:** files in `data/important/` are copied to `backups/`
- **Commands:** create `data/pending_commands.json`:

```json
[{"type": "backup", "source": "local_test"}]
```

Or set device status to `isolated` in the admin dashboard.

## vs `client_agent/`

This folder is a clean, modular rewrite for coursework/production-style structure.  
The older `client_agent/` detection layer remains for reference.
