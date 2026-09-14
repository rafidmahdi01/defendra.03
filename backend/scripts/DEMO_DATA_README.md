# Demo Data Scripts for Defendra

This directory contains scripts to populate and clean up realistic sample data for showcasing Defendra's capabilities.

## 📋 Overview

The demo data includes:

- **7 Sample Devices**: Realistic corporate workstations from different locations
  - Windows, Linux, and macOS systems
  - Various status states (online, offline, isolated)
  - Different CPU/RAM usage patterns
  - Global locations (US, UK, Singapore, Canada, Germany, Australia)

- **5 Critical Alerts**: Serious security incidents
  - Ransomware activity detection
  - Unauthorized network scanning
  - Privilege escalation attempts
  - Brute force attacks
  - Data exfiltration

- **10 Recent Alerts**: Medium and low severity alerts
  - USB device monitoring
  - Email threat detection
  - Resource monitoring
  - Software updates and installations
  - Firewall modifications
  - And more...

## 🚀 Quick Start

### Windows Users (Easiest Method)

**To Add Demo Data:**
1. Double-click `populate_demo.bat`
2. Press any key to confirm
3. Wait for completion

**To Remove Demo Data:**
1. Double-click `delete_demo.bat`
2. Press any key to confirm
3. Wait for completion

### Manual Execution (All Platforms)

**To Add Demo Data:**
```bash
cd backend
python scripts/populate_demo_data.py
```

**To Remove Demo Data:**
```bash
cd backend
python scripts/delete_demo_data.py
```

## 📊 Sample Data Details

### Devices

| Hostname | Location | OS | Status | User |
|----------|----------|----|---------| -----|
| EXEC-WS-001 | New York, US | Windows 11 Pro | Online | John Martinez |
| DEV-LAPTOP-042 | London, UK | Ubuntu 22.04 LTS | Online | Sarah Chen |
| FINANCE-PC-17 | Singapore, SG | Windows 10 Enterprise | Isolated | Alex Wong |
| HR-WORKSTATION-09 | Toronto, CA | macOS Sonoma 14.2 | Online | Emma Johnson |
| SECURITY-SERVER-01 | Frankfurt, DE | Windows Server 2022 | Online | System Administrator |
| SALES-LAPTOP-22 | Sydney, AU | Windows 11 Home | Offline | Michael Brown |
| IT-ADMIN-DESK-05 | Seattle, US | Fedora 39 | Online | Lisa Patel |

### Critical Alerts (Status: Open/Acknowledged)

1. **Ransomware Activity Detected** - FINANCE-PC-17
   - Files being encrypted with .locked extension
   - System automatically isolated

2. **Unauthorized Network Scanning** - DEV-LAPTOP-042
   - Aggressive port scanning detected
   - Scanning 254 IP addresses

3. **Privilege Escalation Attempt** - EXEC-WS-001
   - CVE-2024-38063 exploit detected
   - Attempted SYSTEM-level access

4. **Brute Force Attack** - SECURITY-SERVER-01
   - 347 failed login attempts
   - Account temporarily locked

5. **Data Exfiltration** - IT-ADMIN-DESK-05
   - 2.4 GB transferred to unknown IP
   - Non-whitelisted destination

### Recent Alerts (Various Severities)

Includes realistic scenarios like:
- Suspicious USB devices
- Malicious email attachments
- High CPU usage
- Offline devices
- Software updates needed
- Firewall modifications
- Unauthorized software
- Login failures
- Phishing attempts
- Outdated antivirus

## 🏷️ How It Works

All sample data is tagged with a `sample_data: True` field in Firebase. This ensures:

1. ✅ Easy identification of demo data
2. ✅ Safe deletion without affecting real data
3. ✅ Clean separation between demo and production data

## ⚠️ Important Notes

### Before Running

1. **Ensure Firebase is configured** in `backend/.env`:
   ```
   FIREBASE_CREDENTIALS_PATH=path/to/your/service-account.json
   # OR
   FIRESTORE_EMULATOR_HOST=localhost:8080
   ```

2. **Backend dependencies installed**:
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

3. **Python 3.8+ is available** on your system

### Safety Features

- ✅ Only deletes data tagged with `sample_data: True`
- ✅ Uses batch operations for efficiency
- ✅ Respects Firestore batch limits (500 operations)
- ✅ Provides detailed console output
- ✅ Error handling and reporting

### Timing Considerations

The sample alerts are created with realistic timestamps:
- Critical alerts: 12 minutes to 3 hours ago
- Recent alerts: 25 minutes to 2 days ago
- Device last_seen: 1 minute to 8 hours ago

This makes the demo feel live and active!

## 🔧 Troubleshooting

### "Firebase not configured" Error

**Solution**: Set up Firebase credentials in `backend/.env`:
```bash
FIREBASE_CREDENTIALS_PATH=C:/path/to/serviceAccount.json
```

### "Module not found" Error

**Solution**: Install dependencies:
```bash
cd backend
pip install -r requirements.txt
```

### "Permission denied" Error

**Solution**: Ensure your Firebase service account has read/write permissions for Firestore.

### Script Doesn't Run on Windows

**Solution**: Make sure Python is in your PATH:
```bash
python --version
```

If not found, add Python to your system PATH or use the full path:
```bash
C:\Python312\python.exe scripts\populate_demo_data.py
```

## 🎯 Demo Scenarios

### Scenario 1: Security Operations Center (SOC)

Perfect for showcasing:
- Real-time alert monitoring
- Critical incident response
- Device status tracking
- Geographic fleet distribution

### Scenario 2: Ransomware Response

Features:
- Isolated device (FINANCE-PC-17)
- Active ransomware alert
- Shows containment capabilities

### Scenario 3: Compliance & Monitoring

Demonstrates:
- Multi-platform support (Windows, Linux, macOS)
- Software compliance monitoring
- Login attempt tracking
- Resource utilization

## 🧹 Cleanup Best Practices

### When to Clean Up

- ✅ After completing your demo
- ✅ Before showing real production data
- ✅ When testing with actual devices
- ✅ Before going live with real users

### Verification After Cleanup

After running `delete_demo.bat`, verify:
```bash
# Check in Firebase Console:
# - Devices collection should not have entries with sample_data: true
# - Alerts collection should not have entries with sample_data: true
```

## 📝 Customization

Want to modify the sample data?

1. Edit `populate_demo_data.py`
2. Modify the `sample_devices` or alert arrays
3. Run the population script
4. Use the cleanup script to remove old samples first if needed

### Example: Adding a Device

```python
{
    "hostname": "YOUR-DEVICE-NAME",
    "ip_address": "192.168.1.100",
    "mac_address": "AA:BB:CC:DD:EE:FF",
    "os_name": "Your OS",
    "agent_version": "defendra-desktop-2.4.1",
    "location": "Your City, Country",
    "status": "online",
    "cpu_usage": 25.0,
    "ram_usage": 50.0,
    "last_seen": now - timedelta(minutes=5),
    "created_at": now - timedelta(days=30),
    "updated_at": now - timedelta(minutes=5),
    "user_id": None,
    "user_email": "user@example.com",
    "user_full_name": "User Name",
    "sample_data": True,  # IMPORTANT: Always keep this!
}
```

## 🤝 Support

If you encounter issues:

1. Check the error messages in the console
2. Verify Firebase configuration
3. Ensure all dependencies are installed
4. Check Python version (3.8+ required)

## 📄 License

Part of the Defendra project. Use these scripts freely for demo and testing purposes.

---

**Happy Demoing! 🎉**
