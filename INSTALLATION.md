# Defendra Security Suite - Complete Installation Guide

## 🎯 Overview

Defendra is a comprehensive security suite with:
- ✅ Threat scanning (USB, email, processes)
- ✅ Dual-layer backup (local + cloud)
- ✅ Browser security monitoring
- ✅ Centralized backup management
- ✅ One-click disaster recovery

---

## 📋 System Requirements

- **OS**: Windows 10/11
- **Python**: 3.11+ (installed and in PATH)
- **RAM**: 4GB minimum
- **Disk**: 5GB free space
- **Network**: Internet connection for cloud features

### Verify Prerequisites

```bash
# Check Python version
python --version

# Check pip
pip --version

# Check curl (for connectivity tests)
curl --version
```

---

## 🚀 Quick Installation (5 Minutes)

### Step 1: Run Installer

1. Open PowerShell as **Administrator**
2. Navigate to project folder:
   ```bash
   cd c:\Users\YourUser\Downloads\maria-file-main
   ```
3. Run installer:
   ```bash
   .\client_agent\install.bat
   ```

**What it does:**
- ✅ Installs all Python dependencies
- ✅ Creates backup folders
- ✅ Sets up recovery automation service
- ✅ Registers agent for Windows startup
- ✅ Prepares browser extension

### Step 2: Start Services (3 Terminals)

**Terminal 1: Backend**
```bash
cd backend
python main.py
# or
python -m uvicorn api.router:app --reload --port 8000
```

**Terminal 2: Recovery Automation (NEW)**
```bash
cd recovery_automation
run.bat
# Runs on port 8001
```

**Terminal 3: Client**
```bash
cd client
python main.py
# or
start.bat
```

**Optional Terminal 4: Client Agent (Legacy)**
```bash
cd client_agent
start.bat
```

### Step 3: Install Browser Extension

1. Open Chrome or Edge
2. Go to `chrome://extensions` (or `edge://extensions`)
3. Enable **Developer mode** (top right toggle)
4. Click **Load unpacked**
5. Select: `maria-file-main/extension`

---

## 📁 Installation Folder Structure

```
maria-file-main/
├── backend/                          # Main API server (port 8000)
│   ├── main.py
│   └── requirements.txt
│
├── client/                           # Client service
│   ├── main.py
│   ├── modules/
│   │   ├── backup_manager.py        # NEW: Dual backup
│   │   ├── alert_system.py
│   │   └── ...
│   ├── backups/                     # Local backup storage
│   ├── data/
│   │   └── important/               # Files to backup
│   └── .env
│
├── client_agent/                     # Legacy threat scanner
│   ├── main.py
│   ├── install.bat                  # UPDATED installer
│   ├── start.bat                    # UPDATED launcher
│   ├── uninstall.bat                # UPDATED uninstaller
│   ├── requirements.txt             # UPDATED dependencies
│   └── .env
│
├── recovery_automation/              # Server backup service (port 8001)
│   ├── app/
│   │   ├── main.py
│   │   ├── services/
│   │   │   ├── backup_service.py   # NEW: Centralized sync
│   │   │   └── ...
│   │   └── routes/
│   │       └── backup_routes.py    # NEW: API endpoints
│   ├── backups/                    # Server backup cache
│   ├── run.bat
│   └── .env
│
├── extension/                        # Browser extension
│   ├── popup.html                  # UPDATED: Dark theme
│   ├── popup.js
│   ├── background.js
│   ├── options.html                # UPDATED: Settings page
│   ├── options.js
│   ├── defendra-logo.png           # NEW: App logo
│   └── manifest.json               # UPDATED: Options page config
│
├── INSTALLATION.md                  # This file
├── BACKUP_SYSTEM.md                 # NEW: Backup architecture
└── BACKUP_SETUP.md                  # NEW: Backup setup guide
```

---

## 🔧 Configuration

### Client Configuration (client/.env)

```env
# Server
SERVER_URL=http://127.0.0.1:8000
API_EMAIL=your_email@example.com
API_PASSWORD=your_password

# Device
DEVICE_NAME=my-laptop
DEVICE_LOCATION=Office

# Backup (NEW)
BACKUP_INTERVAL=3600              # 1 hour
RECOVERY_SERVICE_URL=http://127.0.0.1:8001

# Logging
ENABLE_POPUP_ALERTS=false
```

### Recovery Automation (.env)

```env
# Server
DEFENDRA_API_URL=http://127.0.0.1:8000

# AWS S3 (Optional - for cloud backup)
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret
AWS_BUCKET_NAME=defendra-backups
AWS_REGION=us-east-1

# Backup Settings
BACKUP_ROOT_PATH=./backups
DEFAULT_BACKUP_PATHS=C:/Users/YourUser/Downloads/maria-file-main/client/data/important
BACKUP_RETENTION_DAYS=90

# Schedule
BACKUP_SCHEDULE_ENABLED=true
BACKUP_SCHEDULE_INTERVAL_MINUTES=60
```

### Client Agent (.env)

```env
# Email Scanning (Optional)
EMAIL_ADDRESS=your_email@gmail.com
EMAIL_PASSWORD=your_app_password

# API Keys (Optional)
GENAI_API_KEY=your_genai_key
```

---

## 🧪 Verification & Testing

### Test Backend Connection

```bash
curl http://127.0.0.1:8000/health
# Expected: {"status": "ok", "database": "connected"}
```

### Test Recovery Service

```bash
curl http://127.0.0.1:8001/health
# Expected: {"status": "ok", "module": "recovery_automation"}
```

### Test Backup System

```bash
# Create test files
mkdir client\data\important
echo "Test file" > client\data\important\test.txt

# Create backup manually
curl -X POST http://127.0.0.1:8001/backup/create ^
  -H "Content-Type: application/json" ^
  -d "{\"paths\": [\"C:/Users/YourUser/Downloads/maria-file-main/client/data/important\"], \"device_id\": \"test_device\"}"

# View backups
curl http://127.0.0.1:8001/backup/list

# Check stats
curl http://127.0.0.1:8001/backup/stats
```

### Test Browser Extension

1. Click extension icon
2. Should show dark theme with cyan accents
3. Click "Settings & Permissions" button
4. Should open options page with configuration

### Test Client Agent

```bash
cd client_agent
python main.py

# Should output:
# - Connected to backend
# - Starting threat scanners
# - Monitoring USB, email, processes
```

---

## 📊 Features Breakdown

### 1. Threat Scanning
- **USB Monitoring**: Detects new USB devices
- **Email Scanning**: Analyzes Gmail for suspicious messages
- **Process Monitoring**: Tracks suspicious processes
- **Behavior Analysis**: ML-based threat detection

**Location**: `client/modules/` and `client_agent/`

### 2. Local Backup (User PC)
- **Trigger**: Every 1 hour (configurable)
- **Storage**: `client/backups/{timestamp}/`
- **Source**: `client/data/important/`
- **Tracking**: `client/backups/cloud_sync.json`

**Location**: `client/modules/backup_manager.py`

### 3. Cloud Backup (Server)
- **Service**: `recovery_automation` (port 8001)
- **Upload**: To S3/cloud storage
- **Retention**: 90 days (configurable)
- **Access**: Per-device backup retrieval

**Location**: `recovery_automation/app/services/backup_service.py`

### 4. Browser Extension
- **Overlay Detection**: Identifies suspicious page overlays
- **Password Field Monitoring**: Detects unauthorized password inputs
- **DOM Churn Detection**: Identifies rapid page mutations
- **Screenshots**: User-authorized screen capture
- **Dark Theme**: Matches app UI (cyan accents)

**Location**: `extension/`

### 5. Dashboard Integration
- Real-time threat alerts
- Backup status monitoring
- Device fleet management
- Recovery controls

**Location**: `frontend/`

---

## 🎛️ Advanced Features

### Enable Scheduled Backups

```bash
curl -X POST http://127.0.0.1:8001/backup/schedule \
  -H "Content-Type: application/json" \
  -d "{\"enabled\": true, \"interval_minutes\": 60}"
```

### Centralized Cloud Sync

```bash
# Sync ALL device backups to cloud
curl -X POST http://127.0.0.1:8001/backup/sync-centralized
```

### Get Device Backups

```bash
curl http://127.0.0.1:8001/backup/device/device_12345
```

### Restore Backup

```bash
curl -X POST http://127.0.0.1:8001/backup/restore \
  -H "Content-Type: application/json" \
  -d "{\"backup_id\": \"bak_12345\", \"target_dir\": \"C:/restore\"}"
```

---

## 🔐 Security Features

✅ **Encrypted Backups**: S3 server-side encryption
✅ **Device Identification**: All backups tied to device_id
✅ **API Authentication**: Token-based access control
✅ **CORS Security**: Backend validates cross-origin requests
✅ **Data Retention**: Automatic pruning of old backups
✅ **Encrypted Passwords**: Environment variable protection

---

## 📝 Logs & Debugging

### Client Logs
```bash
# Real-time log view
tail -f client/logs/client.log

# Search for errors
grep ERROR client/logs/*.log
```

### Server Logs
```bash
# Backend logs (in console where you ran it)
# Recovery service logs
tail -f recovery_automation/logs/app.log
```

### Agent Logs
```bash
# Agent logs
tail -f client_agent/logs/agent.log
```

### Check Backup History

```bash
# View all backups made
type client/backups/cloud_sync.json

# Or via API
curl http://127.0.0.1:8001/backup/list | python -m json.tool
```

---

## 🛠️ Troubleshooting

### Issue: Backend won't start
```bash
# Check if port 8000 is in use
netstat -ano | findstr :8000

# Kill the process
taskkill /PID <PID> /F

# Try again
python -m uvicorn api.router:app --port 8000
```

### Issue: Recovery service won't start
```bash
# Check Python path
python -c "import fastapi; print('FastAPI OK')"

# Install missing dependencies
pip install fastapi uvicorn boto3

# Start with logging
python -m uvicorn app.main:app --host 0.0.0.0 --port 8001 --log-level debug
```

### Issue: Backup failing to upload
```bash
# Check network connectivity
ping s3.amazonaws.com

# Verify AWS credentials
echo %AWS_ACCESS_KEY_ID%

# Check recovery service health
curl http://127.0.0.1:8001/health

# View detailed logs
tail -f recovery_automation/logs/app.log | grep -i error
```

### Issue: Extension not loading
```bash
# Verify extension folder exists
dir extension

# Check manifest.json is valid
python -c "import json; json.load(open('extension/manifest.json'))"

# Reload extension in Chrome
# chrome://extensions -> Find Defendra -> Click Reload
```

### Issue: Backup files not appearing
```bash
# Create test folder
mkdir client\data\important

# Add test files
echo "Test" > client\data\important\test.txt

# Manually trigger backup
curl -X POST http://127.0.0.1:8001/backup/create ^
  -d "{\"paths\": [\"path/to/folder\"], \"device_id\": \"test\"}"

# Check local storage
dir recovery_automation\backups
```

---

## 🔄 Uninstallation

```bash
# Remove from startup
cd client_agent
uninstall.bat

# Stop services (Ctrl+C in each terminal)

# Optional: Clean up files
# Delete client_agent/ folder
# Delete recovery_automation/backups/ (keeps backups intact)
# Remove extension: chrome://extensions → Remove

# Backups are preserved at:
# - client/backups/
# - recovery_automation/backups/
```

---

## 📚 Additional Documentation

- [BACKUP_SYSTEM.md](BACKUP_SYSTEM.md) - Complete backup architecture
- [BACKUP_SETUP.md](BACKUP_SETUP.md) - Backup configuration guide
- [docs/API_DOCUMENTATION.md](docs/API_DOCUMENTATION.md) - API reference
- [docs/DEPLOYMENT_GUIDE.md](docs/DEPLOYMENT_GUIDE.md) - Production deployment

---

## 🎉 You're Done!

Your Defendra Security Suite is now installed and ready to:
1. ✅ Scan for threats
2. ✅ Backup files locally and to cloud
3. ✅ Monitor browser security
4. ✅ Recover from disasters
5. ✅ Manage devices from dashboard

**Next:** Access dashboard at `http://127.0.0.1:8000/dashboard` (if enabled)

---

## 📞 Support

For issues or questions, check the logs and refer to troubleshooting section above.

---

**Installation Updated**: 2026-07-27
**Version**: 2.0 (Dual Backup Enhanced)
