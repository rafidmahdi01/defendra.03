# Defendra Dual Backup System

## Overview

The enhanced backup system provides **dual-layer backup** with automatic cloud synchronization:

```
┌─────────────────────────────────────────────────────────────┐
│                     BACKUP ARCHITECTURE                      │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  USER PC (Client)                                            │
│  ├─ data/important/          (Source files)                  │
│  │                                                            │
│  ├─ LOCAL BACKUP              CLOUD BACKUP                   │
│  │  backups/                  (Every backup triggers cloud   │
│  │  ├─ 20240727_120000/        upload to recovery service)   │
│  │  ├─ 20240727_130000/                                      │
│  │  └─ cloud_sync.json         Records: backup_id, s3_uri   │
│  │                                                            │
│  └─ sends backup to ──────────────────────────────────────┐  │
│                                                            │  │
└────────────────────────────────────────────────────────────┼──┘
                                                              │
                                                              │
    RECOVERY AUTOMATION SERVICE (Server Port 8001)           │
    ├─ /backup/create (receives from client)  ◄──────────────┘
    ├─ /backup/sync-centralized (server-side)
    ├─ /backup/device/{device_id}
    ├─ /backup/stats
    │
    ├─ Creates ZIP archive
    ├─ Uploads to S3/Cloud Storage
    ├─ Records metadata (backup_id, s3_uri, device_id)
    │
    └─ backups/ folder with centralized cache
       ├─ device_1/
       │  ├─ backup_1.zip
       │  └─ backup_1.meta.json
       ├─ device_2/
       │  ├─ backup_1.zip
       │  └─ backup_1.meta.json
       └─ cloud_index.json (all S3 URIs)
```

---

## Backup Layers

### Layer 1: Local PC Backup (User PC)
- **Location**: `client/backups/{timestamp}/`
- **Trigger**: Scheduled (every 1 hour) or manual
- **What**: Copy files from `data/important/`
- **Status**: Tracked in `client/backups/cloud_sync.json`

### Layer 2: Cloud Backup (via Recovery Service)
- **Endpoint**: `POST http://127.0.0.1:8001/backup/create`
- **Process**:
  1. Client sends local backup path to recovery service
  2. Service creates ZIP archive
  3. Service uploads to S3/cloud storage
  4. Service records backup metadata (backup_id, s3_uri, device_id)
- **Result**: Backup file in cloud + metadata in recovery service

### Layer 3: Server-Side Centralization (Recovery Service)
- **Endpoint**: `POST http://127.0.0.1:8001/backup/sync-centralized`
- **Purpose**: Ensure all user PC backups are synced to cloud
- **Run**: Periodically or on-demand
- **Result**: All backups with device_id → cloud storage

---

## Data Flow

### User PC Backup Process

```python
# client/modules/backup_manager.py
def run_backup(trigger: str = "manual"):
    # 1. LOCAL BACKUP
    local_path = backup_dir / timestamp
    copy files from data/important/ → local_path
    → saved: client/backups/20240727_120000/
    
    # 2. CLOUD BACKUP (NEW)
    POST http://127.0.0.1:8001/backup/create
    {
        "paths": ["/path/to/local_backup"],
        "label": "scheduled_20240727_120000",
        "device_id": "device_12345"
    }
    
    # 3. LOG EVENT
    client.send_log(
        category="backup",
        payload={
            "local_files": 150,
            "local_path": "C:/...backups/20240727_120000",
            "cloud_backup_id": "backup_67890",
            "cloud_status": "success",
            "s3_uri": "s3://defendra-backups/device_12345/backup_67890.zip"
        }
    )
```

### Server-Side Backup Centralization

```python
# recovery_automation/app/services/backup_service.py
def sync_centralized_backups():
    # Get all backups created by all devices
    for backup in all_backups:
        if not backup.s3_uri:
            # Upload to cloud
            s3_uri = upload_to_s3(backup)
            update_metadata(backup_id, s3_uri)
    
    return {
        "total_backups": 150,
        "synced_to_cloud": 150,
        "failed": 0,
        "total_size_bytes": 5368709120
    }
```

---

## Configuration

### Client (.env)

```env
# Backup interval (seconds)
BACKUP_INTERVAL=3600           # 1 hour default

# Server URL for recovery service
RECOVERY_SERVICE_URL=http://127.0.0.1:8001

# Source folder for important files
# Files in data/important/ will be backed up
```

### Recovery Automation (.env)

```env
# S3 Configuration
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret
AWS_BUCKET_NAME=defendra-backups
AWS_REGION=us-east-1

# Backup paths on server
BACKUP_ROOT_PATH=./backups
DEFAULT_BACKUP_PATHS=C:/Users/.../data/important

# Retention
BACKUP_RETENTION_DAYS=90

# Schedule
BACKUP_SCHEDULE_ENABLED=true
BACKUP_SCHEDULE_INTERVAL_MINUTES=60

# Rclone (optional)
RCLONE_ENABLED=false
RCLONE_REMOTE=gdrive:/Defendra
```

---

## API Endpoints

### Client Endpoints (via recovery_automation)

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/backup/create` | Create backup from paths |
| GET | `/backup/list` | List all backups |
| GET | `/backup/stats` | Get backup statistics |
| POST | `/backup/restore` | Restore a backup |
| DELETE | `/backup` | Delete all backups |

### Server Centralization Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/backup/sync-centralized` | **NEW**: Sync all backups to cloud |
| GET | `/backup/device/{device_id}` | **NEW**: Get backups for device |
| GET | `/backup/stats` | **NEW**: Cloud vs local statistics |

---

## Example Usage

### Manual Backup (User PC)

```bash
# POST http://127.0.0.1:8001/backup/create
{
  "paths": ["C:/Users/Kanij/data/important"],
  "label": "manual_backup_20240727",
  "device_id": "device_12345"
}

# Response
{
  "backup_id": "bak_67890",
  "label": "manual_backup_20240727",
  "device_id": "device_12345",
  "created_at": "2024-07-27T12:00:00Z",
  "file_count": 245,
  "size_bytes": 1073741824,
  "s3_uri": "s3://defendra-backups/device_12345/bak_67890.zip",
  "cloud_status": "success"
}
```

### Server-Side Centralization

```bash
# POST http://127.0.0.1:8001/backup/sync-centralized

# Response
{
  "status": "completed",
  "total_backups": 15,
  "synced_to_cloud": 15,
  "failed": 0,
  "total_size_bytes": 21474836480,
  "timestamp": "2024-07-27T13:00:00Z"
}
```

### Get Device Backups

```bash
# GET http://127.0.0.1:8001/backup/device/device_12345

# Response
[
  {
    "backup_id": "bak_67890",
    "label": "scheduled_20240727_120000",
    "created_at": "2024-07-27T12:00:00Z",
    "file_count": 245,
    "size_bytes": 1073741824,
    "s3_uri": "s3://defendra-backups/device_12345/bak_67890.zip"
  },
  ...
]
```

### Get Backup Statistics

```bash
# GET http://127.0.0.1:8001/backup/stats

# Response
{
  "total_backups": 45,
  "cloud_backed": 45,
  "local_only": 0,
  "total_size_bytes": 53687091200,
  "unique_devices": 3,
  "devices": ["device_12345", "device_67890", "device_11111"]
}
```

---

## Scheduled Backups

### Auto-Backup Schedule

The client automatically backs up every hour (configurable):

```
User PC → Local Backup (backups/{timestamp}/)
       → Cloud Backup (via recovery_automation)
       → Log event to Defendra server
```

### Enable/Disable Scheduling

```bash
# Enable scheduled backups
POST http://127.0.0.1:8001/backup/schedule
{
  "enabled": true,
  "interval_minutes": 60,
  "paths": ["C:/Users/.../data/important"],
  "label": "auto_backup"
}

# Stop scheduled backups
DELETE http://127.0.0.1:8001/backup/schedule
```

---

## Backup Recovery

### Restore Latest Backup

```bash
# POST http://127.0.0.1:8001/backup/restore
{
  "target_dir": "C:/Users/Kanij/restore/"
}
```

### Restore Specific Backup

```bash
# POST http://127.0.0.1:8001/backup/restore
{
  "backup_id": "bak_67890",
  "target_dir": "C:/Users/Kanij/restore/"
}
```

---

## Monitoring

### Check Backup Status

```bash
# Get all backups
GET http://127.0.0.1:8001/backup/list

# Get device-specific backups
GET http://127.0.0.1:8001/backup/device/device_12345

# Get statistics
GET http://127.0.0.1:8001/backup/stats
```

### Backup History (Local JSON)

```json
# client/backups/cloud_sync.json
[
  {
    "timestamp": "20240727_120000",
    "trigger": "scheduled",
    "local_files": 150,
    "local_path": "C:/...backups/20240727_120000",
    "cloud_backup_id": "bak_67890",
    "cloud_status": "success",
    "s3_uri": "s3://defendra-backups/device_12345/bak_67890.zip"
  }
]
```

---

## Security & Retention

### Data Retention
- **Local**: Keep last 30 backups (configurable)
- **Cloud**: Keep last 90 backups (configurable)
- Automatic pruning of old backups

### Access Control
- Backups tied to device_id
- Server validates device identity
- S3 backups encrypted (optional)

### Backup Integrity
- ZIP integrity verification
- Metadata checksums
- Restore validation

---

## Troubleshooting

### Backup Failed to Upload
- Check recovery_automation service is running (port 8001)
- Verify S3 credentials in `.env`
- Check network connectivity to cloud

### Missing Backups
- Ensure `data/important/` folder exists and has files
- Check backup retention settings
- Verify file permissions

### Restore Issues
- Confirm backup_id exists: `GET /backup/list`
- Check target directory is writable
- Verify disk space available

---

## Summary

✅ **User PC**: Automatic local + cloud backup every hour
✅ **Server**: Centralized management of all device backups
✅ **Cloud**: All backups replicated to S3 for disaster recovery
✅ **Monitoring**: Real-time backup status and statistics
✅ **Recovery**: One-click restore from any backup
