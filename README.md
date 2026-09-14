# Defendra.AI

Production-oriented desktop and web dashboard for device monitoring, log collection, alert management, offline synchronization, and cyber resilience analytics.

## Architecture

```text
project-root/
├── backend/          FastAPI, SQLAlchemy, JWT, RBAC, WebSockets
├── frontend/         React, Tailwind CSS, Recharts, Axios, Router
├── electron/         Desktop shell and preload bridge
├── database/         MySQL schema
├── deploy/           Nginx and systemd production config
├── docs/             API, database, and deployment documentation
└── docker-compose.yml
```

## Quick Start With Docker

```bash
docker compose up --build
```

Open `http://localhost`, bootstrap the first admin, then log in.

## Local Development

Backend:

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
uvicorn main:app --reload
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

Electron:

```bash
npm install
npm run frontend:dev
npm run electron:dev
```

Build desktop installer:

```bash
npm run electron:build
```

## First Admin

The normal `POST /api/auth/register` route is admin-only. On first run, use the login page bootstrap mode or call:

```bash
curl -X POST http://127.0.0.1:8000/api/auth/bootstrap-admin \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"admin@example.com\",\"full_name\":\"Security Admin\",\"password\":\"ChangeMe123!\",\"role\":\"admin\"}"
```

## Core Features

- JWT authentication with admin/user roles.
- Device inventory, heartbeat, online/offline detection, and telemetry.
- Log ingestion, filtering, search, CSV export, and raw JSON payload storage.
- Automatic alert generation from critical log signals.
- Real-time dashboard updates over `/ws/dashboard`.
- Offline log queue sync endpoint and frontend queue persistence helper.
- Recharts analytics and cybersecurity-themed dark UI.
- Electron packaging for desktop distribution.
- Docker, Nginx, systemd, AWS EC2, and DigitalOcean deployment guidance.

## Documentation

- `docs/API_DOCUMENTATION.md`
- `docs/DATABASE_SCHEMA.md`
- `docs/DEPLOYMENT_GUIDE.md`
