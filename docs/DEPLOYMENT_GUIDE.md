# Deployment Guide

## Docker

```bash
docker compose up --build
```

Services:

- Frontend: `http://localhost`
- Backend API: `http://localhost:8000`
- MySQL: `localhost:3306`

## AWS EC2 or DigitalOcean Droplet

1. Provision Ubuntu 24.04 with at least 2 vCPU and 4 GB RAM.
2. Install dependencies:

```bash
sudo apt update
sudo apt install -y python3-venv python3-pip nodejs npm mysql-server nginx git
```

3. Create MySQL database and user, then run `database/schema.sql`.
4. Copy the project to `/opt/crps`.
5. Configure `/opt/crps/backend/.env` with production credentials and a strong JWT secret.
6. Install backend:

```bash
cd /opt/crps/backend
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
```

7. Build frontend:

```bash
cd /opt/crps/frontend
npm install
npm run build
sudo mkdir -p /var/www/crps/frontend
sudo cp -r dist/* /var/www/crps/frontend/
```

8. Install systemd service:

```bash
sudo cp /opt/crps/deploy/crps.service /etc/systemd/system/crps.service
sudo systemctl daemon-reload
sudo systemctl enable --now crps
```

9. Configure Nginx:

```bash
sudo cp /opt/crps/deploy/nginx.conf /etc/nginx/sites-available/crps
sudo ln -s /etc/nginx/sites-available/crps /etc/nginx/sites-enabled/crps
sudo nginx -t
sudo systemctl reload nginx
```

10. Enable TLS with Certbot before production traffic.

## Production Security Checklist

- Replace all default passwords and `JWT_SECRET_KEY`.
- Use HTTPS only and restrict CORS to trusted domains.
- Keep MySQL private to the server or VPC.
- Run the API behind Nginx with WebSocket upgrade headers.
- Rotate credentials and review `audit_logs` regularly.
- Back up MySQL and test restores.
- Use least-privilege roles for administrators and operators.
