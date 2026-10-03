# Firebase Setup Guide for Defendra.AI Demo

This guide walks you through setting up Firebase/Firestore for the Defendra.AI demo deployment on Render.com.

## Prerequisites
- Google account
- Access to [Firebase Console](https://console.firebase.google.com)

## Step 1: Create Firebase Project

1. Go to [Firebase Console](https://console.firebase.google.com)
2. Click **"Add project"** or **"Create a project"**
3. Enter project name: `defendra-demo` (or your preferred name)
4. Disable Google Analytics (not needed for demo)
5. Click **"Create project"**

## Step 2: Enable Firestore Database

1. In the Firebase Console, select your project
2. Click **"Build"** in the left sidebar
3. Click **"Firestore Database"**
4. Click **"Create database"**
5. Select **"Start in production mode"** (we'll set rules next)
6. Choose a location close to your Render region (e.g., `us-central` for Oregon)
7. Click **"Enable"**

### Configure Firestore Security Rules

1. In Firestore, click the **"Rules"** tab
2. Replace the default rules with:

```javascript
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    // Allow authenticated users to read/write their own data
    match /{document=**} {
      allow read, write: if request.auth != null;
    }
  }
}
```

3. Click **"Publish"**

## Step 3: Create Service Account

1. In Firebase Console, click the **gear icon** (⚙️) next to "Project Overview"
2. Click **"Project settings"**
3. Click the **"Service accounts"** tab
4. Click **"Generate new private key"**
5. Click **"Generate key"** to download the JSON file
6. Save the file as `firebase-key.json` (keep it secure!)

## Step 4: Encode Credentials for Render

Render requires environment variables as strings. We need to base64-encode the Firebase credentials.

### Windows PowerShell:
```powershell
[Convert]::ToBase64String([System.Text.Encoding]::UTF8.GetBytes((Get-Content firebase-key.json -Raw)))
```

### Linux/Mac:
```bash
base64 -i firebase-key.json
```

### Manual (any platform):
1. Copy the entire contents of `firebase-key.json`
2. Go to https://www.base64encode.org/
3. Paste the JSON content
4. Click **"Encode"**
5. Copy the encoded output

**Save this encoded string** - you'll need it when deploying to Render.

## Step 5: Get Your Project ID

1. In Firebase Console, go to **Project settings**
2. Copy the **"Project ID"** (e.g., `defendra-demo-12345`)
3. Save this - you'll need it for Render deployment

## Step 6: Deploy to Render

Now you're ready to deploy using the Blueprint:

1. Push your code (with updated `render.yaml`) to GitHub
2. Go to [Render Dashboard](https://dashboard.render.com/blueprints)
3. Click **"New Blueprint Instance"**
4. Select your GitHub repository
5. When prompted for environment variables:
   - **FIREBASE_PROJECT_ID**: Enter your project ID from Step 5
   - **FIREBASE_CREDENTIALS_JSON**: Paste the base64-encoded string from Step 4
   - **JWT_SECRET_KEY**: Generate a strong random string (64+ characters)
   - **HUGGINGFACE_API_KEY**: (optional) Get from https://huggingface.co/settings/tokens

6. Click **"Apply"** to start deployment

## Firestore Collections Structure

The application will automatically create these collections:

- **users** - User accounts and profiles
- **devices** - Registered endpoint devices
- **alerts** - Security alerts and incidents
- **logs** - System audit logs
- **dashboard_snapshots** - Dashboard state for Sentinel AI

## Free Tier Limits

Firebase Spark (free) plan includes:
- **Storage**: 1 GB
- **Reads**: 50,000/day
- **Writes**: 20,000/day
- **Deletes**: 20,000/day

Perfect for demos and small deployments!

## Creating the First Admin User

After deployment completes, create an admin user:

### Using PowerShell:
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

### Using curl (Linux/Mac):
```bash
curl -X POST https://defendra-backend.onrender.com/api/auth/bootstrap-admin \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@demo.com",
    "full_name": "Demo Admin",
    "password": "Demo123!",
    "role": "admin"
  }'
```

## Troubleshooting

### "Permission denied" errors
- Check Firestore Security Rules are published
- Verify JWT authentication is working
- Check that `FIREBASE_PROJECT_ID` matches your actual project

### "Service account not found"
- Verify `FIREBASE_CREDENTIALS_JSON` is correctly base64-encoded
- Make sure there are no extra spaces or newlines in the encoded string
- Try re-encoding the JSON file

### "Project not found"
- Double-check the `FIREBASE_PROJECT_ID` in Render environment variables
- Ensure the service account belongs to the correct project

### Check Backend Logs
View logs in Render Dashboard:
1. Go to your **defendra-backend** service
2. Click the **"Logs"** tab
3. Look for Firebase initialization messages

## Security Best Practices

For production deployments:
- ✅ Use more restrictive Firestore rules
- ✅ Enable Firebase App Check
- ✅ Rotate service account keys regularly
- ✅ Use Firebase IAM roles with least privilege
- ✅ Enable audit logging in Firebase
- ✅ Monitor usage in Firebase Console

## Next Steps

1. ✅ Complete Firebase setup
2. ✅ Deploy to Render with Blueprint
3. ✅ Create admin user
4. ✅ Test login at frontend URL
5. 🎉 Share demo with client!

---

**Support**: For Firebase-specific issues, see [Firebase Documentation](https://firebase.google.com/docs/firestore)
