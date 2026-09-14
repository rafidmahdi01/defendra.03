CREATE DATABASE IF NOT EXISTS cyber_resilience_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE cyber_resilience_db;

CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    full_name VARCHAR(150) NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    role VARCHAR(30) NOT NULL DEFAULT 'user',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX ix_users_email (email),
    INDEX ix_users_role (role)
);

CREATE TABLE IF NOT EXISTS devices (
    id INT AUTO_INCREMENT PRIMARY KEY,
    hostname VARCHAR(150) NOT NULL,
    ip_address VARCHAR(45) NOT NULL,
    mac_address VARCHAR(32) NULL UNIQUE,
    os_name VARCHAR(120) NULL,
    agent_version VARCHAR(50) NULL,
    status VARCHAR(30) NOT NULL DEFAULT 'offline',
    cpu_usage FLOAT NOT NULL DEFAULT 0,
    ram_usage FLOAT NOT NULL DEFAULT 0,
    location VARCHAR(120) NULL,
    last_seen DATETIME NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX ix_devices_hostname (hostname),
    INDEX ix_devices_ip_address (ip_address),
    INDEX ix_devices_status_last_seen (status, last_seen)
);

CREATE TABLE IF NOT EXISTS logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    device_id INT NOT NULL,
    category VARCHAR(80) NOT NULL,
    severity VARCHAR(30) NOT NULL DEFAULT 'info',
    source VARCHAR(120) NULL,
    message TEXT NOT NULL,
    raw_payload JSON NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_logs_device FOREIGN KEY (device_id) REFERENCES devices(id) ON DELETE CASCADE,
    INDEX ix_logs_device_created (device_id, created_at),
    INDEX ix_logs_search (category, severity, created_at)
);

CREATE TABLE IF NOT EXISTS alerts (
    id INT AUTO_INCREMENT PRIMARY KEY,
    device_id INT NULL,
    title VARCHAR(180) NOT NULL,
    description TEXT NOT NULL,
    severity VARCHAR(30) NOT NULL DEFAULT 'low',
    status VARCHAR(30) NOT NULL DEFAULT 'open',
    rule_name VARCHAR(120) NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    acknowledged_at DATETIME NULL,
    resolved_at DATETIME NULL,
    CONSTRAINT fk_alerts_device FOREIGN KEY (device_id) REFERENCES devices(id) ON DELETE SET NULL,
    INDEX ix_alerts_status_severity (status, severity),
    INDEX ix_alerts_device_created (device_id, created_at)
);

CREATE TABLE IF NOT EXISTS connectivity_queue (
    id INT AUTO_INCREMENT PRIMARY KEY,
    device_id INT NOT NULL,
    payload JSON NOT NULL,
    status VARCHAR(30) NOT NULL DEFAULT 'pending',
    retry_count INT NOT NULL DEFAULT 0,
    last_error TEXT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    synced_at DATETIME NULL,
    CONSTRAINT fk_connectivity_queue_device FOREIGN KEY (device_id) REFERENCES devices(id) ON DELETE CASCADE,
    INDEX ix_connectivity_queue_status (status),
    INDEX ix_connectivity_queue_device (device_id)
);

CREATE TABLE IF NOT EXISTS system_events (
    id INT AUTO_INCREMENT PRIMARY KEY,
    event_type VARCHAR(100) NOT NULL,
    message TEXT NOT NULL,
    metadata_json JSON NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX ix_system_events_type_created (event_type, created_at)
);

CREATE TABLE IF NOT EXISTS audit_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NULL,
    action VARCHAR(120) NOT NULL,
    resource_type VARCHAR(80) NULL,
    resource_id VARCHAR(80) NULL,
    ip_address VARCHAR(45) NULL,
    user_agent VARCHAR(255) NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_audit_logs_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL,
    INDEX ix_audit_logs_user_created (user_id, created_at),
    INDEX ix_audit_logs_action (action)
);

CREATE TABLE IF NOT EXISTS notifications (
    id INT AUTO_INCREMENT PRIMARY KEY,
    alert_id INT NULL,
    channel VARCHAR(40) NOT NULL DEFAULT 'email',
    recipient VARCHAR(255) NOT NULL,
    subject VARCHAR(180) NOT NULL,
    body TEXT NOT NULL,
    sent BOOLEAN NOT NULL DEFAULT FALSE,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    sent_at DATETIME NULL,
    CONSTRAINT fk_notifications_alert FOREIGN KEY (alert_id) REFERENCES alerts(id) ON DELETE SET NULL,
    INDEX ix_notifications_sent (sent),
    INDEX ix_notifications_alert (alert_id)
);
