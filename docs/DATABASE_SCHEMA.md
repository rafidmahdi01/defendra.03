# Database Schema

The MySQL schema is defined in `database/schema.sql`.

## Tables

- `users`: authentication identities, password hashes, roles, active flag, timestamps.
- `devices`: inventory, agent metadata, online/offline state, resource telemetry, last seen.
- `logs`: normalized device log entries with category, severity, source, message, JSON payload.
- `alerts`: incident records generated from log correlation or manual triage.
- `connectivity_queue`: persisted offline sync payloads with retry state and error capture.
- `system_events`: backend operational event history.
- `audit_logs`: user actions, resource identifiers, source IP, user agent.
- `notifications`: email notification preparation records tied to alerts.

## Index Strategy

Indexes target common dashboard and investigation queries:

- Device state: `devices(status, last_seen)`.
- Log drilldowns: `logs(device_id, created_at)` and `logs(category, severity, created_at)`.
- Alert triage: `alerts(status, severity)` and `alerts(device_id, created_at)`.
- Queue workers: `connectivity_queue(status)` and `connectivity_queue(device_id)`.
- Audit review: `audit_logs(user_id, created_at)` and `audit_logs(action)`.
