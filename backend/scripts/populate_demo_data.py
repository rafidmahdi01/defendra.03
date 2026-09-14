"""
Populate demo data for Defendra showcase.
This script adds realistic sample devices, critical alerts, and recent alerts.
All sample data is tagged with 'sample_data': True for easy cleanup later.
"""

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Add parent directory to path to import backend modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.firebase import get_firestore


def populate_demo_data():
    """Populate Firebase with realistic demo data."""
    db = get_firestore()
    now = datetime.now(timezone.utc)
    
    print("🚀 Starting demo data population...\n")
    
    # Sample device data - realistic corporate workstations
    sample_devices = [
        {
            "hostname": "EXEC-WS-001",
            "ip_address": "192.168.1.105",
            "mac_address": "00:1B:44:11:3A:B7",
            "os_name": "Windows 11 Pro",
            "agent_version": "defendra-desktop-2.4.1",
            "location": "New York, US",
            "status": "online",
            "cpu_usage": 45.2,
            "ram_usage": 62.8,
            "last_seen": now - timedelta(minutes=2),
            "created_at": now - timedelta(days=45),
            "updated_at": now - timedelta(minutes=2),
            "user_id": None,
            "user_email": "john.martinez@company.com",
            "user_full_name": "John Martinez",
            "sample_data": True,
        },
        {
            "hostname": "DEV-LAPTOP-042",
            "ip_address": "192.168.1.89",
            "mac_address": "A4:5E:60:C2:8F:1D",
            "os_name": "Ubuntu 22.04 LTS",
            "agent_version": "defendra-desktop-2.4.0",
            "location": "London, UK",
            "status": "online",
            "cpu_usage": 78.9,
            "ram_usage": 85.3,
            "last_seen": now - timedelta(minutes=5),
            "created_at": now - timedelta(days=120),
            "updated_at": now - timedelta(minutes=5),
            "user_id": None,
            "user_email": "sarah.chen@company.com",
            "user_full_name": "Sarah Chen",
            "sample_data": True,
        },
        {
            "hostname": "FINANCE-PC-17",
            "ip_address": "192.168.2.34",
            "mac_address": "B8:27:EB:45:9A:2C",
            "os_name": "Windows 10 Enterprise",
            "agent_version": "defendra-desktop-2.3.8",
            "location": "Singapore, SG",
            "status": "isolated",
            "cpu_usage": 23.1,
            "ram_usage": 48.5,
            "last_seen": now - timedelta(minutes=15),
            "created_at": now - timedelta(days=200),
            "updated_at": now - timedelta(minutes=15),
            "user_id": None,
            "user_email": "alex.wong@company.com",
            "user_full_name": "Alex Wong",
            "sample_data": True,
        },
        {
            "hostname": "HR-WORKSTATION-09",
            "ip_address": "192.168.3.156",
            "mac_address": "DC:A6:32:8E:F1:49",
            "os_name": "macOS Sonoma 14.2",
            "agent_version": "defendra-desktop-2.4.1",
            "location": "Toronto, CA",
            "status": "online",
            "cpu_usage": 32.6,
            "ram_usage": 54.7,
            "last_seen": now - timedelta(minutes=1),
            "created_at": now - timedelta(days=90),
            "updated_at": now - timedelta(minutes=1),
            "user_id": None,
            "user_email": "emma.johnson@company.com",
            "user_full_name": "Emma Johnson",
            "sample_data": True,
        },
        {
            "hostname": "SECURITY-SERVER-01",
            "ip_address": "10.0.5.12",
            "mac_address": "E4:5F:01:8B:3C:7A",
            "os_name": "Windows Server 2022",
            "agent_version": "defendra-desktop-2.4.1",
            "location": "Frankfurt, DE",
            "status": "online",
            "cpu_usage": 18.4,
            "ram_usage": 41.2,
            "last_seen": now - timedelta(minutes=3),
            "created_at": now - timedelta(days=180),
            "updated_at": now - timedelta(minutes=3),
            "user_id": None,
            "user_email": "admin@company.com",
            "user_full_name": "System Administrator",
            "sample_data": True,
        },
        {
            "hostname": "SALES-LAPTOP-22",
            "ip_address": "192.168.1.201",
            "mac_address": "2C:F0:5D:A9:B1:E8",
            "os_name": "Windows 11 Home",
            "agent_version": "defendra-desktop-2.4.0",
            "location": "Sydney, AU",
            "status": "offline",
            "cpu_usage": 0.0,
            "ram_usage": 0.0,
            "last_seen": now - timedelta(hours=8),
            "created_at": now - timedelta(days=60),
            "updated_at": now - timedelta(hours=8),
            "user_id": None,
            "user_email": "michael.brown@company.com",
            "user_full_name": "Michael Brown",
            "sample_data": True,
        },
        {
            "hostname": "IT-ADMIN-DESK-05",
            "ip_address": "192.168.4.88",
            "mac_address": "F8:BC:12:7D:9E:3F",
            "os_name": "Fedora 39",
            "agent_version": "defendra-desktop-2.4.1",
            "location": "Seattle, US",
            "status": "online",
            "cpu_usage": 56.7,
            "ram_usage": 71.9,
            "last_seen": now - timedelta(minutes=4),
            "created_at": now - timedelta(days=250),
            "updated_at": now - timedelta(minutes=4),
            "user_id": None,
            "user_email": "lisa.patel@company.com",
            "user_full_name": "Lisa Patel",
            "sample_data": True,
        },
    ]
    
    # Add devices to Firestore
    device_refs = []
    print("📱 Adding sample devices...")
    for device_data in sample_devices:
        ref = db.collection("devices").document()
        ref.set(device_data)
        device_refs.append(ref.id)
        print(f"  ✓ Added device: {device_data['hostname']} ({device_data['location']})")
    
    print(f"\n✅ Created {len(device_refs)} sample devices\n")
    
    # Critical alerts - serious security incidents
    critical_alerts = [
        {
            "device_id": device_refs[2],  # FINANCE-PC-17 (isolated)
            "title": "Ransomware Activity Detected",
            "description": "Suspicious file encryption behavior detected. Multiple files being encrypted rapidly with .locked extension. System has been automatically isolated to prevent lateral movement.",
            "severity": "critical",
            "status": "open",
            "rule_name": "ransomware_detection",
            "created_at": now - timedelta(minutes=18),
            "acknowledged_at": None,
            "resolved_at": None,
            "sample_data": True,
        },
        {
            "device_id": device_refs[1],  # DEV-LAPTOP-042
            "title": "Unauthorized Network Scanning Detected",
            "description": "System is performing aggressive port scanning across the internal network. Detected scanning of ports 22, 23, 445, 3389 on 254 IP addresses in the last 10 minutes.",
            "severity": "critical",
            "status": "acknowledged",
            "rule_name": "network_scan_detection",
            "created_at": now - timedelta(hours=2),
            "acknowledged_at": now - timedelta(hours=1, minutes=45),
            "resolved_at": None,
            "sample_data": True,
        },
        {
            "device_id": device_refs[0],  # EXEC-WS-001
            "title": "Privilege Escalation Attempt",
            "description": "Detected attempt to escalate privileges using CVE-2024-38063 exploit. Process 'svchost.exe' attempted to gain SYSTEM-level access from user context.",
            "severity": "critical",
            "status": "open",
            "rule_name": "privilege_escalation",
            "created_at": now - timedelta(minutes=35),
            "acknowledged_at": None,
            "resolved_at": None,
            "sample_data": True,
        },
        {
            "device_id": device_refs[4],  # SECURITY-SERVER-01
            "title": "Brute Force Attack on Admin Account",
            "description": "Multiple failed login attempts detected on administrator account. 347 failed attempts from IP 203.45.67.89 in the last hour. Account temporarily locked.",
            "severity": "critical",
            "status": "acknowledged",
            "rule_name": "brute_force_detection",
            "created_at": now - timedelta(hours=3),
            "acknowledged_at": now - timedelta(hours=2, minutes=30),
            "resolved_at": None,
            "sample_data": True,
        },
        {
            "device_id": device_refs[6],  # IT-ADMIN-DESK-05
            "title": "Data Exfiltration Detected",
            "description": "Large volume of data (2.4 GB) transferred to unknown external IP 198.51.100.42 via HTTPS. Transfer occurred over encrypted channel to non-whitelisted destination.",
            "severity": "critical",
            "status": "open",
            "rule_name": "data_exfiltration",
            "created_at": now - timedelta(minutes=12),
            "acknowledged_at": None,
            "resolved_at": None,
            "sample_data": True,
        },
    ]
    
    print("🚨 Adding critical alerts...")
    critical_count = 0
    for alert_data in critical_alerts:
        ref = db.collection("alerts").document()
        ref.set(alert_data)
        critical_count += 1
        device_hostname = sample_devices[[d_ref for d_ref in device_refs].index(alert_data['device_id'])]['hostname']
        print(f"  ✓ Critical: {alert_data['title']} on {device_hostname}")
    
    print(f"\n✅ Created {critical_count} critical alerts\n")
    
    # Recent alerts - medium and low severity
    recent_alerts = [
        {
            "device_id": device_refs[3],  # HR-WORKSTATION-09
            "title": "Suspicious USB Device Connected",
            "description": "Unknown USB mass storage device connected. Device ID: VID_0781&PID_5567. Device not on approved hardware whitelist.",
            "severity": "medium",
            "status": "open",
            "rule_name": "usb_device_monitor",
            "created_at": now - timedelta(minutes=25),
            "acknowledged_at": None,
            "resolved_at": None,
            "sample_data": True,
        },
        {
            "device_id": device_refs[0],  # EXEC-WS-001
            "title": "Malicious Email Attachment Blocked",
            "description": "Email attachment 'invoice_Q4.pdf.exe' blocked. Detected as trojan malware (Win32/TrojanDownloader). Sender: billing@legitimate-company.xyz",
            "severity": "medium",
            "status": "resolved",
            "rule_name": "email_threat_detection",
            "created_at": now - timedelta(hours=5),
            "acknowledged_at": now - timedelta(hours=4, minutes=45),
            "resolved_at": now - timedelta(hours=4, minutes=30),
            "sample_data": True,
        },
        {
            "device_id": device_refs[2],  # FINANCE-PC-17
            "title": "Credential Phishing Email Detected",
            "description": "From: microsoft-account-security@outlook-verification.net\nSubject: Your account requires immediate verification\nConfidence: 98%\nDetection: Spoofed Microsoft 365 sign-in page requesting credentials and MFA approval.",
            "severity": "critical",
            "status": "open",
            "rule_name": "email_threat",
            "created_at": now - timedelta(minutes=12),
            "acknowledged_at": None,
            "resolved_at": None,
            "sample_data": True,
        },
        {
            "device_id": device_refs[1],  # DEV-LAPTOP-042
            "title": "Invoice Payment Fraud Attempt",
            "description": "From: accounts-payable@vendor-invoices.co\nSubject: Updated bank details for March payment\nConfidence: 91%\nDetection: Sender domain is newly registered and requests an urgent change to supplier banking information.",
            "severity": "high",
            "status": "acknowledged",
            "rule_name": "email_threat",
            "created_at": now - timedelta(hours=1, minutes=20),
            "acknowledged_at": now - timedelta(hours=1),
            "resolved_at": None,
            "sample_data": True,
        },
        {
            "device_id": device_refs[5],  # SALES-LAPTOP-22
            "title": "Executive Impersonation Email Quarantined",
            "description": "From: ceo@company-support-mail.com\nSubject: Urgent wire transfer request\nConfidence: 96%\nDetection: Display-name spoofing and urgent payment language matched executive impersonation indicators.",
            "severity": "high",
            "status": "resolved",
            "rule_name": "email_threat",
            "created_at": now - timedelta(hours=3),
            "acknowledged_at": now - timedelta(hours=2, minutes=50),
            "resolved_at": now - timedelta(hours=2, minutes=35),
            "sample_data": True,
        },
        {
            "device_id": device_refs[3],  # HR-WORKSTATION-09
            "title": "Suspicious Password Reset Email",
            "description": "From: helpdesk@defendra-reset.com\nSubject: Password expires today\nConfidence: 84%\nDetection: Lookalike support domain and shortened link lead to an untrusted password reset destination.",
            "severity": "medium",
            "status": "open",
            "rule_name": "email_threat",
            "created_at": now - timedelta(hours=7),
            "acknowledged_at": None,
            "resolved_at": None,
            "sample_data": True,
        },
        {
            "device_id": device_refs[1],  # DEV-LAPTOP-042
            "title": "High CPU Usage Detected",
            "description": "System CPU usage has been above 85% for the last 45 minutes. Process 'python.exe' consuming 78% CPU. Possible cryptocurrency mining activity.",
            "severity": "medium",
            "status": "acknowledged",
            "rule_name": "resource_monitor",
            "created_at": now - timedelta(minutes=50),
            "acknowledged_at": now - timedelta(minutes=45),
            "resolved_at": None,
            "sample_data": True,
        },
        {
            "device_id": device_refs[5],  # SALES-LAPTOP-22
            "title": "Device Offline for Extended Period",
            "description": "Device has not reported heartbeat for 8 hours. Last known location: Sydney, AU. May indicate device theft or network connectivity issues.",
            "severity": "medium",
            "status": "open",
            "rule_name": "heartbeat_monitor",
            "created_at": now - timedelta(hours=8),
            "acknowledged_at": None,
            "resolved_at": None,
            "sample_data": True,
        },
        {
            "device_id": device_refs[3],  # HR-WORKSTATION-09
            "title": "Software Update Available",
            "description": "Critical security update available for Defendra Agent. Current version: 2.4.1, Latest version: 2.4.2. Update includes fixes for 3 security vulnerabilities.",
            "severity": "low",
            "status": "open",
            "rule_name": "update_monitor",
            "created_at": now - timedelta(days=1),
            "acknowledged_at": None,
            "resolved_at": None,
            "sample_data": True,
        },
        {
            "device_id": device_refs[4],  # SECURITY-SERVER-01
            "title": "Firewall Rule Modification",
            "description": "Firewall configuration changed. New inbound rule created allowing traffic on port 4444 from any source. Rule created by user 'admin'.",
            "severity": "medium",
            "status": "acknowledged",
            "rule_name": "firewall_monitor",
            "created_at": now - timedelta(hours=6),
            "acknowledged_at": now - timedelta(hours=5, minutes=30),
            "resolved_at": None,
            "sample_data": True,
        },
        {
            "device_id": device_refs[6],  # IT-ADMIN-DESK-05
            "title": "Unauthorized Software Installation",
            "description": "Unapproved software detected: 'TeamViewer v15.43.7'. Software installation policy violation. Remote access tools require security approval.",
            "severity": "medium",
            "status": "open",
            "rule_name": "software_whitelist",
            "created_at": now - timedelta(minutes=40),
            "acknowledged_at": None,
            "resolved_at": None,
            "sample_data": True,
        },
        {
            "device_id": device_refs[2],  # FINANCE-PC-17
            "title": "Multiple Login Failures",
            "description": "User 'alex.wong@company.com' has 5 consecutive failed login attempts in the last 10 minutes. Account locked for security.",
            "severity": "low",
            "status": "resolved",
            "rule_name": "login_monitor",
            "created_at": now - timedelta(hours=12),
            "acknowledged_at": now - timedelta(hours=11, minutes=45),
            "resolved_at": now - timedelta(hours=11, minutes=30),
            "sample_data": True,
        },
        {
            "device_id": device_refs[0],  # EXEC-WS-001
            "title": "Suspicious Website Accessed",
            "description": "Browser accessed known phishing domain: secure-bank-login-verify.xyz. Domain flagged in threat intelligence feed. Connection blocked by web filter.",
            "severity": "medium",
            "status": "resolved",
            "rule_name": "web_filter",
            "created_at": now - timedelta(days=2),
            "acknowledged_at": now - timedelta(days=2, hours=-1),
            "resolved_at": now - timedelta(days=2, hours=-2),
            "sample_data": True,
        },
        {
            "device_id": device_refs[1],  # DEV-LAPTOP-042
            "title": "Antivirus Definition Outdated",
            "description": "Antivirus signatures are 3 days old. Last update failed due to network timeout. System may be vulnerable to recent malware variants.",
            "severity": "low",
            "status": "open",
            "rule_name": "antivirus_monitor",
            "created_at": now - timedelta(hours=18),
            "acknowledged_at": None,
            "resolved_at": None,
            "sample_data": True,
        },
    ]
    
    print("⚠️  Adding recent alerts...")
    recent_count = 0
    for alert_data in recent_alerts:
        ref = db.collection("alerts").document()
        ref.set(alert_data)
        recent_count += 1
        severity_icon = "🔴" if alert_data['severity'] == "critical" else "🟡" if alert_data['severity'] == "medium" else "🟢"
        print(f"  {severity_icon} {alert_data['severity'].capitalize()}: {alert_data['title']}")
    
    print(f"\n✅ Created {recent_count} recent alerts\n")
    
    # Summary
    print("=" * 60)
    print("📊 DEMO DATA POPULATION COMPLETE")
    print("=" * 60)
    print(f"✓ Total Devices: {len(device_refs)}")
    print(f"✓ Critical Alerts: {critical_count}")
    print(f"✓ Recent Alerts: {recent_count}")
    print(f"✓ Total Alerts: {critical_count + recent_count}")
    print("\n💡 All sample data is tagged with 'sample_data': True")
    print("   You can delete it later using delete_demo_data.py")
    print("=" * 60)


if __name__ == "__main__":
    try:
        populate_demo_data()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
