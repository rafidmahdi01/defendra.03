# Defendra.AI - Quick Demo Deployment

Deploy a fully functional web demo in 10 minutes. No client installation needed.

## One-Click Deploy to Render

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://dashboard.render.com/blueprints)

### Quick Steps

1. **Push to GitHub**
   ```bash
   git init && git add . && git commit -m "Demo deployment"
   git remote add origin https://github.com/YOUR_USERNAME/defendra.git
   git push -u origin main
   ```

2. **Deploy on Render**
   - Go to [Render Blueprints](https://dashboard.render.com/blueprints)
   - Click "New Blueprint Instance"
   - Select your repository
   - Click "Apply"

3. **Create Admin User**
   ```bash
   curl -X POST https://your-backend.onrender.com/api/auth/bootstrap-admin \
     -H "Content-Type: application/json" \
     -d '{"email":"admin@demo.com","full_name":"Demo Admin","password":"Demo123!","role":"admin"}'
   ```

4. **Share with Client**
   - Frontend URL: `https://your-app.onrender.com`
   - Login: `admin@demo.com` / `Demo123!`

## What's Deployed

| Service | Purpose | Free Tier |
|---------|---------|-----------|
| MySQL | Database | 90 days free |
| Backend | FastAPI | 750 hrs/month |
| Frontend | React SPA | 750 hrs/month |

## Demo Features

- ✅ Dashboard with real-time analytics
- ✅ Device monitoring and management
- ✅ Log collection and search
- ✅ Alert management
- ✅ User authentication
- ✅ WebSocket real-time updates

## Cost

**Free tier** - Services spin down after 15 min inactivity. First request takes ~30 seconds to wake up.

**Paid option** - $7/month per service for always-on demo.

## Detailed Guide

See [docs/DEMO_DEPLOYMENT.md](docs/DEMO_DEPLOYMENT.md) for:
- Manual deployment steps
- Environment variable configuration
- Troubleshooting guide
- Security best practices

## Need Help?

- [Render Documentation](https://render.com/docs)
- [Open an Issue](https://github.com/YOUR_USERNAME/defendra/issues)
