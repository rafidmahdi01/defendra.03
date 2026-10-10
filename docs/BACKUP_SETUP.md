# Dual Backup System - Quick Setup

## What Was Enhanced

✅ **User PC Backup**:
- Saves files locally to `client/backups/{timestamp}/`
- **NEW**: Automatically sends to recovery service for cloud storage
- Tracks both local and cloud status

✅ **Server-Side Centralization**:
- Recovery service receives all device backups
- **NEW**: Automatically uploads to S3/cloud
- Manages backup metadata per device

---

## Step 1: Verify Recovery Automation Service

The service must run on port 8001:

```bash
cd recovery_automation
run.bat              # Windows
# or
python -m uvicorn app.main:app --host 0.0.0.0 --port 8001
```

Expected output:
```
INFO:     Uvicorn running on http://0.0.0.0:8001
INFO:     Application startup complete
```

---

## Step 2: Configure Client Backup

The client automatically:
1. Creates local backup every **1 hour** (configurable)
2. Sends to recovery_automation service
3. Logs backup status

Check `client/.env`:
```env
BACKUP_INTERVAL=3600           # 1 hour in seconds
SERVER_URL=http://127.0.0.1:8000
```

---

## Step 3: Configure Cloud Storage (S3)

Recovery automation needs AWS credentials for cloud storage.

### Option A: AWS S3

Edit `recovery_automation/.env`:
```env
AWS_ACCESS_KEY_ID=your_aws_key
AWS_SECRET_ACCESS_KEY=your_aws_secret
AWS_BUCKET_NAME=defendra-backups
AWS_REGION=us-east-1
```

### Option B: Simulate (Default)

S3 uploads are simulated in development. No config needed.

---

## Step 4: Start Everything

**Terminal 1: Defendra Backend**
```bash
cd backend
python main.py
# or
python -m uvicorn api.router:app --reload --port 8000
```

**Terminal 2: Recovery Automation**
```bash
cd recovery_automation
run.bat
```

**Terminal 3: Client**
```bash
cd client
python main.py
# or
start.bat
```

---

## Step 5: Test Backup

### Manual Backup (Immediate)

```bash
# Test local backup
curl -X POST http://127.0.0.1:8001/backup/create \
  -H "Content-Type: application/json" \
  -d '{
    "paths": ["C:/Users/Kanij/Downloads/maria-file-main/client/data/important"],
    "label": "test_backup",
    "device_id": "device_test_1"
  }'
```

### View Backups

```bash
# List all backups
curl http://127.0.0.1:8001/backup/list

# View backup stats
curl http://127.0.0.1:8001/backup/stats

# Get device-specific backups
curl http://127.0.0.1:8001/backup/device/device_test_1
```

### Server-Side Sync (Centralize to Cloud)

```bash
# Sync all backups to cloud
curl -X POST http://127.0.0.1:8001/backup/sync-centralized
```

---

## What Happens During Backup

### Timeline

```
Time  Event
────────────────────────────────────────────────
T+0   Client: Start backup
T+1   Client: Copy files → backups/{timestamp}/
T+2   Client: Send to recovery_automation
T+3   Server: Receive backup, create ZIP
T+4   Server: Upload ZIP to S3/cloud
T+5   Server: Update metadata with s3_uri
T+6   Server: Return backup_id to client
T+7   Client: Log backup event to Defendra
T+8   Done! Files in 3 places:
      - User PC: backups/{timestamp}/
      - Recovery service: backups/backup_*.zip
      - Cloud: s3://bucket/device_id/backup_*.zip
```

---

## Folder Structure

### Client Side
```
client/
├── backups/
│   ├── 20240727_120000/          ← Local backup
│   │   ├── file1.txt
│   │   └── file2.txt
│   ├── 20240727_130000/
│   │   └── ...
│   └── cloud_sync.json           ← Backup history
│
├── data/
│   └── important/                ← Source files
│       ├── file1.txt
│       └── file2.txt
```

### Server Side
```
recovery_automation/
├── backups/
│   ├── backup_67890.zip          ← ZIP archive
│   ├── backup_67890.meta.json    ← Metadata
│   ├── backup_67891.zip
│   └── backup_67891.meta.json
│
└── logs/
    └── app.log                   ← Detailed logs
```

### Cloud Storage (S3)
```
s3://defendra-backups/
├── device_12345/
│   ├── backup_67890.zip
│   └── backup_67891.zip
├── device_67890/
│   └── backup_...
└── device_11111/
    └── backup_...
```

---

## Monitoring Backup Progress

### Check Client Logs
```bash
# View client backup logs
tail -f client/logs/backup.log
```

### Check Server Logs
```bash
# View recovery automation logs
tail -f recovery_automation/logs/app.log
```

### Check Backup Status via API
```bash
# Real-time stats
watch -n 5 'curl -s http://127.0.0.1:8001/backup/stats | jq'
```

---

## Enable/Disable Scheduling

### Enable Auto-Backup (every hour)
```bash
curl -X POST http://127.0.0.1:8001/backup/schedule \
  -H "Content-Type: application/json" \
  -d '{
    "enabled": true,
    "interval_minutes": 60,
    "paths": ["C:/Users/Kanij/Downloads/maria-file-main/client/data/important"],
    "label": "auto_backup"
  }'
```

### Change Interval (every 30 minutes)
```bash
curl -X POST http://127.0.0.1:8001/backup/schedule \
  -H "Content-Type: application/json" \
  -d '{
    "enabled": true,
    "interval_minutes": 30
  }'
```

### Stop Auto-Backup
```bash
curl -X DELETE http://127.0.0.1:8001/backup/schedule
```

---

## Restore Backup

### Restore Latest Backup
```bash
curl -X POST http://127.0.0.1:8001/backup/restore \
  -H "Content-Type: application/json" \
  -d '{
    "target_dir": "C:/restore_location/"
  }'
```

### Restore Specific Backup
```bash
curl -X POST http://127.0.0.1:8001/backup/restore \
  -H "Content-Type: application/json" \
  -d '{
    "backup_id": "backup_67890",
    "target_dir": "C:/restore_location/"
  }'
```

---

## Backup Locations

| Location | Purpose | Readable By |
|----------|---------|-----------|
| `client/backups/{timestamp}/` | Local copy on user PC | User via file explorer |
| `recovery_automation/backups/` | Server cache (ZIP + metadata) | Defendra admin |
| `s3://defendra-backups/` | Cloud storage | Authorized devices, Defendra admin |

---

## Expected Results

After setup and first backup:

✅ Files copied to `client/backups/{timestamp}/`
✅ ZIP created in `recovery_automation/backups/`
✅ Uploaded to S3 cloud (if configured)
✅ Metadata with backup_id and s3_uri recorded
✅ Backup event logged to Defendra server
✅ Stats show: 1 backup synced to cloud

---

## Troubleshooting

### Backup Not Creating
1. Ensure `client/data/important/` has files
2. Check recovery_automation service is running on port 8001
3. Verify network: `curl http://127.0.0.1:8001/health`

### Upload to Cloud Failing
1. Check AWS credentials in `.env`
2. Verify S3 bucket exists and is accessible
3. Check logs: `recovery_automation/logs/app.log`

### High Disk Usage
1. Reduce retention: `BACKUP_RETENTION_DAYS=30`
2. Manual cleanup: `DELETE http://127.0.0.1:8001/backup`
3. Check ZIP sizes: `ls -lh recovery_automation/backups/`

---

## Files Modified

✅ `client/modules/backup_manager.py` - Dual backup (local + cloud)
✅ `recovery_automation/app/services/backup_service.py` - New sync & stats endpoints
✅ `recovery_automation/app/routes/backup_routes.py` - New API endpoints
✅ `BACKUP_SYSTEM.md` - Full documentation (created)
✅ `BACKUP_SETUP.md` - This file (created)

---

## Next Steps

1. ✅ Start recovery_automation service
2. ✅ Configure S3 credentials (optional)
3. ✅ Test manual backup
4. ✅ Enable auto-backup schedule
5. ✅ Monitor backup stats
6. ✅ Test restore functionality
7. ✅ Verify cloud sync

All done! Your system now has automatic dual-layer backup. 🎉
