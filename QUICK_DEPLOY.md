# Quick Deploy Guide

## Option 1: Render.com (Recommended for Demo)

### Prerequisites
- GitHub account
- Render.com account (free tier available)
- Firebase account (free tier)

### Deploy Steps

#### Part A: Setup Firebase (5 minutes)

1. **Create Firebase Project**
   - Go to https://console.firebase.google.com
   - Click "Create a project"
   - Name: `defendra-demo`
   - Disable Google Analytics
   - Click "Create project"

2. **Enable Firestore Database**
   - Click "Build" → "Firestore Database"
   - Click "Create database"
   - Select "Start in production mode"
   - Choose location (e.g., `us-central`)
   - Click "Enable"

3. **Update Firestore Rules**
   - Click "Rules" tab
   - Replace with:
   ```javascript
   rules_version = '2';
   service cloud.firestore {
     match /databases/{database}/documents {
       match /{document=**} {
         allow read, write: if request.auth != null;
       }
     }
   }
   ```
   - Click "Publish"

4. **Generate Service Account Key**
   - Click ⚙️ → "Project settings"
   - Click "Service accounts" tab
   - Click "Generate new private key"
   - Save as `firebase-key.json`

5. **Encode Credentials**
   
   **Windows PowerShell:**
   ```powershell
   [Convert]::ToBase64String([System.Text.Encoding]::UTF8.GetBytes((Get-Content firebase-key.json -Raw)))
   ```
   
   **Linux/Mac:**
   ```bash
   base64 -i firebase-key.json
   ```
   
   **Save the output** - you'll need it in Part B.

6. **Copy Project ID**
   - In Firebase Console → Project settings
   - Copy the "Project ID" (e.g., `defendra-demo-12345`)

#### Part B: Deploy to Render (10 minutes)

1. **Push to GitHub**
   ```powershell
   git init
   git add .
   git commit -m "Initial commit"
   git remote add origin https://github.com/yourusername/defendra-demo.git
   git push -u origin main
   ```

2. **Deploy with Render Blueprint**
   - Go to https://dashboard.render.com/blueprints
   - Click "New Blueprint Instance"
   - Select your GitHub repository
   - Configure environment variables when prompted:
     - **FIREBASE_PROJECT_ID**: Paste your project ID from Part A step 6
     - **FIREBASE_CREDENTIALS_JSON**: Paste the base64 string from Part A step 5
     - **JWT_SECRET_KEY**: Generate a strong random string (64+ chars)
     - **HUGGINGFACE_API_KEY**: (Optional) Get from https://huggingface.co/settings/tokens
   - Click "Apply" to deploy

3. **Wait for Deployment**
   - Backend: ~5-8 minutes
   - Frontend: ~3-5 minutes
   - Watch the logs for any errors

4. **Create Admin User**
   
   **Windows PowerShell:**
   ```powershell
   $body = @{
       email = "admin@demo.com"
       full_name = "Demo Admin"
       password = "Demo123!"
       role = "admin"
   } | ConvertTo-Json

   Invoke-RestMethod -Uri "https://defendra-backend.onrender.com/api/auth/bootstrap-admin" `
       -Method POST `
       -Body $body `
       -ContentType "application/json"
   ```

5. **Access Your Demo**
   - Frontend: `https://defendra-frontend.onrender.com`
   - Backend API: `https://defendra-backend.onrender.com`
   - Login: `admin@demo.com` / `Demo123!`

### Resource Usage

| Service | Purpose | Free Tier |
|---------|---------|-----------|
| Firebase Firestore | Database | 1GB + 50K reads/day |
| Backend | FastAPI | 750 hrs/month |
| Frontend | React SPA | 750 hrs/month |

**Note:** Free tier services spin down after 15 minutes of inactivity. First request may take 30-60 seconds.