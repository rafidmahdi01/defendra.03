#!/bin/bash
# ============================================================
# Defendra.AI - Build Script for Demo Deployment
# ============================================================
# This script builds both frontend and backend for deployment
# Run from the project root directory
# ============================================================

set -e

echo ""
echo "========================================"
echo "  Defendra.AI Demo Build Script"
echo "========================================"
echo ""

# Check for required environment variables
if [ -z "$VITE_API_URL" ]; then
    echo "[WARN] VITE_API_URL not set. Using default: http://127.0.0.1:8000"
    export VITE_API_URL="http://127.0.0.1:8000"
fi

if [ -z "$VITE_WS_URL" ]; then
    echo "[WARN] VITE_WS_URL not set. Using default: ws://127.0.0.1:8000/ws/dashboard"
    export VITE_WS_URL="ws://127.0.0.1:8000/ws/dashboard"
fi

echo "Configuration:"
echo "  API URL: $VITE_API_URL"
echo "  WS URL:  $VITE_WS_URL"
echo ""

# ------------------------------------------------------------
# Build Frontend
# ------------------------------------------------------------
echo "[1/3] Building frontend..."
cd frontend

if [ ! -d "node_modules" ]; then
    echo "Installing frontend dependencies..."
    npm install
fi

echo "Building frontend with Vite..."
npm run build

echo "[OK] Frontend built successfully!"
cd ..

# ------------------------------------------------------------
# Prepare Backend
# ------------------------------------------------------------
echo ""
echo "[2/3] Preparing backend..."

if [ ! -d "backend/.venv" ]; then
    echo "Creating Python virtual environment..."
    cd backend
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
    cd ..
else
    echo "[OK] Virtual environment already exists"
fi

# ------------------------------------------------------------
# Create deployment package
# ------------------------------------------------------------
echo ""
echo "[3/3] Creating deployment package..."

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
PACKAGE_DIR="dist/defendra-demo-$TIMESTAMP"

mkdir -p dist
mkdir -p "$PACKAGE_DIR"

# Copy necessary files
echo "Copying files..."
cp -r backend "$PACKAGE_DIR/"
cp -r frontend/dist "$PACKAGE_DIR/frontend/"
cp -r database "$PACKAGE_DIR/"
cp -r electron "$PACKAGE_DIR/"
cp package.json "$PACKAGE_DIR/"
cp render.yaml "$PACKAGE_DIR/"
cp docker-compose.yml "$PACKAGE_DIR/"

# Create .env template
cat > "$PACKAGE_DIR/backend/.env" << EOF
# Defendra.AI Environment Configuration
DATABASE_URL=mysql+pymysql://crps_user:change-me@localhost:3306/cyber_resilience_db
JWT_SECRET_KEY=replace-with-64-char-random-string
ALLOWED_ORIGINS=http://localhost:5173,http://localhost
FIREBASE_PROJECT_ID=defendraai
EOF

echo ""
echo "========================================"
echo "  Build Complete!"
echo "========================================"
echo ""
echo "Deployment package created at:"
echo "  $(pwd)/$PACKAGE_DIR"
echo ""
echo "Next steps:"
echo "  1. Push code to GitHub"
echo "  2. Go to https://dashboard.render.com/blueprints"
echo "  3. Create new blueprint instance from your repo"
echo ""
echo "Or for manual deployment:"
echo "  1. Copy the package to your server"
echo "  2. Configure environment variables"
echo "  3. Run: docker compose up --build"
echo ""
