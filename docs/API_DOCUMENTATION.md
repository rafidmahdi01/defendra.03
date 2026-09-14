# API Documentation

Base URL: `http://127.0.0.1:8000`

## Authentication

Create the first administrator:

```bash
curl -X POST http://127.0.0.1:8000/api/auth/bootstrap-admin \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","full_name":"Security Admin","password":"ChangeMe123!","role":"admin"}'
```

Login:

```bash
curl -X POST http://127.0.0.1:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"ChangeMe123!"}'
```

Use the returned token as `Authorization: Bearer <token>`.

## Endpoints

- `POST /api/auth/login` - authenticate and return a JWT.
- `POST /api/auth/register` - admin-only user registration.
- `GET /api/devices` - list monitored devices.
- `POST /api/devices` - register a device.
- `PUT /api/devices/{id}` - update device inventory/status.
- `DELETE /api/devices/{id}` - delete a device.
- `POST /api/devices/{id}/heartbeat` - update online/offline telemetry.
- `POST /api/logs` - receive logs from clients.
- `GET /api/logs` - list/filter logs.
- `GET /api/logs/search?q=value` - search logs.
- `GET /api/logs/export` - export CSV logs.
- `GET /api/alerts` - list alerts.
- `POST /api/alerts` - create an alert manually.
- `PUT /api/alerts/{id}` - acknowledge or resolve an alert.
- `GET /api/analytics/overview` - dashboard counters.
- `GET /api/analytics/trends` - time-series analytics.
- `POST /api/sync/offline-logs` - upload queued offline logs.
- `WS /ws/dashboard` - realtime dashboard events.

## Example Device Log

```bash
curl -X POST http://127.0.0.1:8000/api/logs \
  -H "Content-Type: application/json" \
  -d '{"device_id":1,"category":"endpoint","severity":"critical","source":"agent","message":"Possible ransomware activity detected"}'
```
