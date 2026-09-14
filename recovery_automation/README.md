# Defendra — Recovery & Automation Module

Production-style Python module that integrates with the **existing Defendra backend** via HTTP. It does **not** modify `backend/main.py`, authentication, dashboard, or database schemas.

Runs as a **standalone FastAPI service** on port **8001** by default.

## Features

| Feature | Endpoints |
|---------|-----------|
| Backup (ZIP, local, optional S3) | `POST /backup/create`, `GET /backup/list`, `POST /backup/restore` |
| Recovery / emergency | `POST /recovery/emergency` |
| Automated incident response | `POST /automation/threat-detected` |
| Notifications | `POST /notify/send` |
| Isolation (simulation) | `POST /recovery/isolate` |
| Limp mode | `POST /recovery/limp-mode/enable` |
| Health | `GET /health` |

## Architecture

```text
recovery_automation/
├── app/
│   ├── main.py                 # FastAPI entry (port 8001)
│   ├── services/               # Business logic
│   ├── routes/                 # HTTP routes
│   ├── integrations/           # Defendra API client + S3
│   ├── utils/                  # Config, logging, helpers
│   └── models/                 # Pydantic schemas
├── backups/                    # Local ZIP archives
├── logs/app.log                # Centralized logs
├── requirements.txt
└── .env.example
```

## Prerequisites

- **Defendra backend** running at `http://127.0.0.1:8000`
- Python 3.11+
- Valid Defendra credentials (`DEFENDRA_API_EMAIL` / `DEFENDRA_API_PASSWORD`) for alert APIs

## Quick Start

### Windows (recommended — no `activate` needed)

Double-click **`run.bat`** or in PowerShell / CMD:

```bat
cd recovery_automation
run.bat
```

If PowerShell blocks `activate.ps1`, use **`run.ps1`** instead:

```powershell
cd recovery_automation
.\run.ps1
```

Or run uvicorn directly (never needs `activate`):

```powershell
cd recovery_automation
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8001
```

### Optional: fix PowerShell script policy (one time)

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

Then `.venv\Scripts\activate` will work.

### Linux / macOS

```bash
cd recovery_automation
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --host 0.0.0.0 --port 8001
```

Open API docs: **http://127.0.0.1:8001/docs**

## Integration with Existing Defendra APIs

| Spec (assumed) | Actual Defendra route | Client method |
|----------------|----------------------|---------------|
| `GET /api/devices` | `GET /api/devices` | `get_devices()` |
| `GET /api/device/{id}` | Filter from device list | `fetch_device()` |
| `GET /api/logs` | `GET /api/logs` | `get_logs()` |
| `POST /api/alerts` | `POST /api/alerts` | `send_alert()` |
| `POST /api/threats/report` | `POST /api/alerts` + log | `report_incident()` |
| `POST /api/dashboard/update` | `POST /api/logs` (audit) | `update_dashboard()` |

## Sample API Requests

### Create backup

```bash
curl -X POST http://127.0.0.1:8001/backup/create \
  -H "Content-Type: application/json" \
  -d "{\"paths\": [\"./data\"], \"label\": \"manual\", \"device_id\": \"PC-01\"}"
```

### List backups

```bash
curl http://127.0.0.1:8001/backup/list
```

### Restore latest backup

```bash
curl -X POST http://127.0.0.1:8001/backup/restore \
  -H "Content-Type: application/json" \
  -d "{}"
```

### Threat-detected automation workflow

```bash
curl -X POST http://127.0.0.1:8001/automation/threat-detected \
  -H "Content-Type: application/json" \
  -d "{\"device_id\": \"PC-01\", \"threat_type\": \"ransomware\", \"severity\": \"critical\"}"
```

Workflow steps:

1. Log incident locally
2. `POST /api/alerts` on Defendra
3. Create backup ZIP
4. Simulate device isolation (no destructive commands)
5. Send notifications (console / email / Telegram placeholder)
6. `POST /api/logs` for dashboard audit trail
7. Enable limp mode on critical severity

### Send notification

```bash
curl -X POST http://127.0.0.1:8001/notify/send \
  -H "Content-Type: application/json" \
  -d "{\"subject\": \"Test\", \"message\": \"Recovery module online\", \"channels\": [\"console\"]}"
```

### Emergency recovery

```bash
curl -X POST http://127.0.0.1:8001/recovery/emergency \
  -H "Content-Type: application/json" \
  -d "{\"device_id\": \"PC-01\", \"create_snapshot\": true}"
```

### Simulate isolation

```bash
curl -X POST http://127.0.0.1:8001/recovery/isolate \
  -H "Content-Type: application/json" \
  -d "{\"device_id\": \"PC-01\", \"reason\": \"manual_test\"}"
```

## Safety

- **Isolation** is simulation-only (in-memory state, read-only `psutil` process scan).
- **No firewall**, `iptables`, or process-kill commands.
- **Rclone** and **Telegram** are placeholders unless explicitly enabled in `.env`.

## Optional: Mount into Defendra (without editing main.py)

Create a launcher that imports the existing app and mounts this router:

```python
# recovery_automation/bootstrap.py (optional — not required)
from main import app  # Defendra backend main
from recovery_automation.app.routes import backup_router, automation_router, ...

app.include_router(backup_router)
```

Or keep this module on **port 8001** and call it from agents/webhooks.

## Logging

All actions log to `logs/app.log` with rotation (5 × 5 MB).

## Environment

See `.env.example` for full variable list.
