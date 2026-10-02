#!/usr/bin/env bash
# ============================================================
#  SIH26 GrievanceAI — Local Deployment Script
#  Works on Linux / macOS / WSL (Bash)
# ============================================================
set -e

echo "========================================"
echo "  GrievanceAI — SIH26 Prototype"
echo "  Local Deployment Script"
echo "========================================"

# --- 1. Go to backend dir ----------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/backend"

# --- 2. Create virtualenv ----------------------------------
if [ ! -d "venv" ]; then
    echo ">> Creating Python virtual environment..."
    python3 -m venv venv
fi

# --- 3. Activate & install ---------------------------------
echo ">> Activating venv & installing dependencies..."
source venv/bin/activate
pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet
echo "   Dependencies installed."

# --- 4. Start server ---------------------------------------
echo ""
echo "========================================"
echo "  ✅ Server starting at: http://localhost:8000"
echo "  📖 API Docs (Swagger): http://localhost:8000/docs"
echo "  🏛️  Citizen Portal:    http://localhost:8000/"
echo "  📊 Dashboard:          http://localhost:8000/dashboard"
echo "  📈 Analytics:          http://localhost:8000/analytics"
echo "  🗺️  GIS Map:           http://localhost:8000/map"
echo "========================================"
echo ""
echo "TIP: After first launch, visit http://localhost:8000/api/seed"
echo "     (or click 'Seed Data' if shown) to load sample complaints."
echo ""

uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
