# 🛡️ Defendra Security Suite v2.0

A comprehensive, enterprise-grade security and backup solution with:
- **Threat Detection** (USB, Email, Processes)
- **Dual-Layer Backup** (Local + Cloud)
- **Browser Security** (Extension with dark theme)
- **Centralized Recovery** (One-click restore)
- **Real-time Dashboard** (Fleet management)

---

## ✨ What's New in v2.0

✅ **Enhanced Backup System**
- Local backup on user PC (every hour)
- Automatic cloud sync via recovery service
- Server-side centralized management
- Per-device backup retrieval
- Disaster recovery (one-click restore)

✅ **Modern Browser Extension**
- Dark theme matching app UI
- Cyan accent colors (#00d9a3)
- Settings & Permissions page
- Screenshot capture (user consent)
- Real-time event monitoring

✅ **Improved Installation**
- Single-command setup (`install.bat`)
- Automatic dependency installation
- Browser extension auto-registration
- Complete configuration guide

✅ **Recovery Automation Service**
- Runs on port 8001
- Centralized backup management
- S3/cloud integration
- Backup statistics & monitoring
- Device-specific backups

---

## 🚀 Quick Start (5 Minutes)

### 1️⃣ Run Installer
```bash
cd client_agent
install.bat
```

### 2️⃣ Start Services (3 Terminals)
```bash
# Terminal 1
cd backend
python main.py

# Terminal 2
cd recovery_automation
run.bat

# Terminal 3
cd client
python main.py
```

### 3️⃣ Install Browser Extension
1. Open `chrome://extensions`
2. Enable Developer mode
3. Click "Load unpacked"
4. Select `maria-file-main/extension`

📖 **See [INSTALLATION.md](INSTALLATION.md) for detailed setup**

---

## 📁 Project Structure

```
maria-file-main/
├── backend/                    # Main API server (port 8000)
├── client/                     # Client service with dual backup
├── client_agent/               # Threat scanner & installer
├── recovery_automation/        # Centralized backup service (port 8001)
├── extension/                  # Browser extension (dark theme + cyan UI)
├── frontend/                   # React dashboard
├── docs/                       # Documentation
├── INSTALLATION.md             # Complete installation guide
├── BACKUP_SYSTEM.md            # Backup architecture
├── BACKUP_SETUP.md             # Backup configuration
└── README.md                   # This file
```

---

## 🎯 Features

### Threat Detection
- **USB Monitoring**: Real-time USB device detection
- **Email Scanning**: Gmail IMAP with AI analysis
- **Process Monitoring**: Suspicious process detection
- **Behavior Analysis**: ML-powered threat classification

### Backup & Recovery
- **Local Storage**: User PC backups every hour
- **Cloud Sync**: Automatic S3/cloud upload
- **Centralized**: Server manages all device backups
- **Recovery**: One-click restore from any backup
- **Retention**: Automatic pruning (90 days default)

### Browser Security
- **Overlay Detection**: Identifies malicious page overlays
- **Password Field Monitoring**: Detects unauthorized input fields
- **DOM Churn Detection**: Rapid DOM mutation analysis
- **Screenshot Capture**: User-authorized screenshots
- **Real-time Events**: Live threat notifications

### Dashboard
- Device fleet overview
- Real-time threat alerts
- Backup status monitoring
- Recovery management
- User activity logs

---

## 📡 API Services

### Backend (Port 8000)
```bash
GET  /health              # Health check
POST /api/logs            # Send event logs
GET  /api/devices         # List devices
GET  /api/alerts          # Get alerts
```

### Recovery Automation (Port 8001)
```bash
POST /backup/create              # Create backup
GET  /backup/list                # List all backups
GET  /backup/device/{id}         # Device backups
GET  /backup/stats               # Statistics
POST /backup/restore             # Restore backup
POST /backup/sync-centralized    # Cloud sync all
```

---

## 🔧 Configuration

### Environment Variables

**client/.env**
```env
SERVER_URL=http://127.0.0.1:8000
BACKUP_INTERVAL=3600              # 1 hour
RECOVERY_SERVICE_URL=http://127.0.0.1:8001
```

**recovery_automation/.env**
```env
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret
AWS_BUCKET_NAME=defendra-backups
BACKUP_RETENTION_DAYS=90
```

**client_agent/.env**
```env
EMAIL_ADDRESS=your_email@gmail.com
EMAIL_PASSWORD=your_app_password
API_TOKEN=your_api_token
```

---

## 📊 Monitoring

### Check Backup Status
```bash
curl http://127.0.0.1:8001/backup/stats
```

### View All Backups
```bash
curl http://127.0.0.1:8001/backup/list
```

### Get Device Backups
```bash
curl http://127.0.0.1:8001/backup/device/device_12345
```

### Centralize to Cloud
```bash
curl -X POST http://127.0.0.1:8001/backup/sync-centralized
```

---

## 📚 Documentation

| Document | Purpose |
|----------|---------|
| [INSTALLATION.md](INSTALLATION.md) | Complete installation & setup guide |
| [BACKUP_SYSTEM.md](BACKUP_SYSTEM.md) | Backup architecture & API reference |
| [BACKUP_SETUP.md](BACKUP_SETUP.md) | Backup configuration & management |
| [docs/API_DOCUMENTATION.md](docs/API_DOCUMENTATION.md) | Full API reference |
| [docs/DATABASE_SCHEMA.md](docs/DATABASE_SCHEMA.md) | Database structure |
| [docs/DEPLOYMENT_GUIDE.md](docs/DEPLOYMENT_GUIDE.md) | Production deployment |

---

## 🧪 Testing

### Test Backup System
```bash
# Create test file
mkdir client\data\important
echo "Test" > client\data\important\test.txt

# Create backup
curl -X POST http://127.0.0.1:8001/backup/create \
  -H "Content-Type: application/json" \
  -d '{"paths": ["C:/path/to/important"], "device_id": "test"}'

# Verify
curl http://127.0.0.1:8001/backup/list
```

### Test Browser Extension
1. Click extension icon → Should show dark UI
2. Click "Settings & Permissions" → Should show options page
3. Refresh events → Should load recent security events

### Test Threat Scanning
```bash
cd client_agent
python main.py
# Should display: Monitoring for threats...
```

---

## 🔐 Security

- ✅ Encrypted backups (S3 server-side)
- ✅ Device ID tracking (per-device isolation)
- ✅ Token-based API auth
- ✅ HTTPS support (production)
- ✅ Automatic backup pruning
- ✅ Environment variable secrets

---

## 🛠️ Troubleshooting

### Backend Not Starting
```bash
netstat -ano | findstr :8000    # Check if port in use
pip install fastapi uvicorn     # Install dependencies
python -m uvicorn api.router:app --port 8000
```

### Recovery Service Error
```bash
pip install fastapi uvicorn boto3
cd recovery_automation
python -m uvicorn app.main:app --port 8001
```

### Backup Not Working
```bash
# Verify source folder exists
dir client\data\important

# Test API
curl http://127.0.0.1:8001/health

# Check logs
type recovery_automation\logs\app.log
```

### Extension Not Loading
```bash
# Verify extension folder
dir extension

# Reload in Chrome
# chrome://extensions → Find Defendra → Click Reload
```

---

## 📋 System Requirements

- **OS**: Windows 10/11
- **Python**: 3.11+
- **RAM**: 4GB minimum
- **Disk**: 5GB free space
- **Browser**: Chrome/Edge with extension support

---

## 🚢 Deployment

### Development
```bash
./start.bat              # Start all services
```

### Production
See [docs/DEPLOYMENT_GUIDE.md](docs/DEPLOYMENT_GUIDE.md) for:
- HTTPS/SSL setup
- Database configuration
- Load balancing
- Cloud deployment options

---

## 🤝 Contributing

To add features or fix bugs:
1. Create a feature branch
2. Make your changes
3. Test thoroughly
4. Submit a pull request

---

## 📄 License

[Your License Here]

---

## 📞 Support

- 📖 Check [INSTALLATION.md](INSTALLATION.md) for setup issues
- 📊 Review logs in `*/logs/` folders
- 🔧 See troubleshooting section above
- 📚 Refer to documentation files

---

## 🎉 What You Can Do Now

✅ **Automatic Backups** - Every hour to local + cloud
✅ **Disaster Recovery** - Restore any backup with one click
✅ **Threat Scanning** - Real-time USB, email, process monitoring
✅ **Browser Safety** - Extension detects overlays & suspicious activity
✅ **Fleet Management** - Manage multiple devices from dashboard
✅ **Compliance** - Audit logs & backup retention policies

---

**Version**: 2.0 (Dual Backup Enhanced)
**Last Updated**: 2026-07-27
**Status**: Production Ready ✅

Start with [INSTALLATION.md](INSTALLATION.md) for complete setup instructions.
