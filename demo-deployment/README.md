# Defendra.AI Demo Deployment

This folder contains all files needed to deploy a web-based demo of Defendra.AI.

## Quick Start

1. **Push your code to GitHub**
2. **Deploy on Render.com:**
   - Go to https://dashboard.render.com/blueprints
   - Click "New Blueprint Instance"
   - Select your repository
   - Click "Apply"

3. **Create admin user** (after deployment completes):
   ```bash
   curl -X POST https://your-backend.onrender.com/api/auth/bootstrap-admin \
     -H "Content-Type: application/json" \
     -d '{"email":"admin@demo.com","full_name":"Demo Admin","password":"Demo123!","role":"admin"}'
   ```

4. **Share with client:**
   - URL: `https://your-frontend.onrender.com`
   - Login: `admin@demo.com` / `Demo123!`

## Folder Contents

```
demo-deployment/
├── README.md                    # This file
├── QUICK_DEPLOY.md              # Quick deployment guide
├── render.yaml                  # Render.com blueprint (copy to project root)
├── config/
│   ├── .env.production          # Backend environment template
│   ├── frontend.env.production  # Frontend environment template
│   └── database.Dockerfile      # MySQL Docker config
├── docs/
│   └── DEMO_DEPLOYMENT.md       # Detailed deployment guide
└── scripts/
    ├── build-for-demo.bat       # Windows build script
    ├── build-for-demo.sh        # Linux/Mac build script
    └── quick-deploy.bat         # Opens Render deployment page
```

## How to Use

### Option 1: One-Click Deploy (Recommended)

1. Copy `render.yaml` to your project root:
   ```
   copy demo-deployment\render.yaml .
   ```

2. Commit and push to GitHub:
   ```bash
   git add render.yaml
   git commit -m "Add deployment config"
   git push
   ```

3. Follow the Quick Start steps above

### Option 2: Manual Configuration

1. Copy environment files:
   ```
   copy demo-deployment\config\.env.production backend\.env
   copy demo-deployment\config\frontend.env.production frontend\.env.production
   ```

2. Edit the files with your actual URLs

3. Deploy each service manually on Render

## Cleanup

To remove all demo deployment files:
```bash
# From project root
rm -rf demo-deployment/
```

Or on Windows:
```cmd
rmdir /s /q demo-deployment
```

## Cost

**Free tier (Render.com):**
- 750 hours/month per service
- Services sleep after 15 min inactivity
- First request takes ~30 seconds to wake up

**Paid ($7/month per service):**
- Always on
- No cold starts

## Support

- Render docs: https://render.com/docs
- Detailed guide: `docs/DEMO_DEPLOYMENT.md`
