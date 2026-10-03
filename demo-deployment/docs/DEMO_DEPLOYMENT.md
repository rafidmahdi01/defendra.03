# Defendra.AI Demo Deployment Guide

This guide walks you through deploying a fully functional web demo of Defendra.AI that you can share with clients without requiring them to install anything.

## Prerequisites

1. **GitHub Account** - To host your code repository
2. **Render.com Account** (free) - For hosting the demo
   - Sign up at https://dashboard.render.com
   - Connect your GitHub account

## Quick Start (One-Click Deploy)

### Step 1: Push Code to GitHub

```bash
# Initialize git if not already done
git init

# Add all files
git add .

# Commit
git commit -m "Prepare for demo deployment"

# Add your GitHub remote
git remote add origin https://github.com/YOUR_USERNAME/defendra.git

# Push to GitHub
git push -u origin main
```

### Step 2: Deploy Using Render Blueprint

1. Go to https://dashboard.render.com/blueprints
2. Click **"New Blueprint Instance"**
3. Select your GitHub repository
4. Render will detect the `render.yaml` file
5. Review the services and click **"Apply"**

Render will automatically create:
- MySQL database
- Backend API service
- Frontend web service

### Step 3: Configure Environment Variables

After deployment starts, configure these in the Render dashboard:

#### Backend Service (`defendra-backend`)

| Variable | Value | Notes |
|----------|-------|-------|
| `JWT_SECRET_KEY` | Generate a 64+ character random string | Use `openssl rand -base64 48` |
| `ALLOWED_ORIGINS` | `https://your-frontend-url.onrender.com` | Update with your actual frontend URL |
| `HUGGINGFACE_API_KEY` | Your HuggingFace token | Optional, for Sentinel AI chat |

#### Frontend Service (`defendra-frontend`)

| Variable | Value | Notes |
|----------|-------|-------|
| `VITE_API_URL` | `https://your-backend-url.onrender.com` | Update with your actual backend URL |
| `VITE_WS_URL` | `wss://your-backend-url.onrender.com/ws/dashboard` | WebSocket URL |

### Step 4: Create First Admin User

After all services are deployed (usually 5-10 minutes):

1. Go to your backend URL: `https://your-backend-url.onrender.com/health`
2. Verify it returns `{"status": "ok", ...}`
3. Create the first admin using one of these methods:

#### Option A: Use the Login Page Bootstrap

1. Go to your frontend URL
2. Click "Bootstrap Admin" or use the first-time setup flow

#### Option B: Use curl/PowerShell

```powershell
# PowerShell
$backendUrl = "https://your-backend-url.onrender.com"
$body = @{
    email = "admin@demo.com"
    full_name = "Demo Admin"
    password = "DemoPassword123!"
    role = "admin"
} | ConvertTo-Json

Invoke-RestMethod -Uri "$backendUrl/api/auth/bootstrap-admin" -Method POST -Body $body -ContentType "application/json"
```

```bash
# Bash/curl
curl -X POST https://your-backend-url.onrender.com/api/auth/bootstrap-admin \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@demo.com","full_name":"Demo Admin","password":"DemoPassword123!","role":"admin"}'
```

### Step 5: Test Your Demo

1. Navigate to your frontend URL
2. Log in with the admin credentials
3. Verify all features work:
   - ✅ Dashboard with analytics
   - ✅ Device management
   - ✅ Log collection and search
   - ✅ Alert management
   - ✅ Real-time updates

## Alternative: Manual Deployment

If you prefer to deploy services manually:

### Deploy Backend

1. In Render dashboard, click **"New"** → **"Web Service"**
2. Connect your GitHub repo
3. Select the `backend` directory
4. Set environment to **Docker**
5. Add environment variables from `backend/.env.example`
6. Deploy

### Deploy Database

1. Click **"New"** → **"Private Service"**
2. Select Docker environment
3. Use the `database/Dockerfile`
4. Configure MySQL credentials

### Deploy Frontend

1. Click **"New"** → **"Web Service"**
2. Connect your GitHub repo
3. Select the `frontend` directory
4. Set environment to **Docker**
5. Set `VITE_API_URL` environment variable

## Demo Credentials

For demo purposes, consider using these test credentials:
- **Email:** `demo@defendra.ai`
- **Password:** `Demo123!`

You can create demo users with limited access for clients to test.

## Troubleshooting

### Backend won't start
- Check logs in Render dashboard
- Verify `DATABASE_URL` is correct
- Ensure `JWT_SECRET_KEY` is set

### Frontend shows "Cannot reach API"
- Verify `VITE_API_URL` matches your backend URL
- Check `ALLOWED_ORIGINS` includes your frontend URL
- Backend may be spinning up (wait 60 seconds)

### Database connection fails
- MySQL service must be running first
- Check internal hostname (`defendra-mysql`)
- Verify credentials match

### WebSocket not working
- Ensure `VITE_WS_URL` uses `wss://` (not `ws://`)
- Check backend logs for WebSocket errors

## Cost Management

### Free Tier Limits (Render)
- Services spin down after 15 minutes of inactivity
- 750 hours/month per service
- First request after spin-down takes ~30-60 seconds

### Keeping Demo Active
If you need the demo always available:
1. Upgrade to paid plan ($7/month per service)
2. Use a cron job to ping the service every 10 minutes
3. Deploy on Railway ($5/month for small apps)

## Security Notes

For production demos:
1. Use strong, unique passwords
2. Enable HTTPS only
3. Set up proper CORS origins
4. Consider rate limiting
5. Don't commit sensitive credentials to git

## Support

- Render docs: https://render.com/docs
- Project issues: https://github.com/YOUR_USERNAME/defendra/issues
