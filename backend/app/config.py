"""
SIH26 Grievance AI — Configuration
Single-file settings so there is nothing to chase across the codebase.
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# --- Auth ------------------------------------------------------------------
JWT_SECRET = os.getenv("GRIV_JWT_SECRET", "sih26-grievance-secret-key-2026-secure")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_HOURS = 24

# --- Uploads ----------------------------------------------------------------
UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10 MB
ALLOWED_IMAGE_EXT = {"jpg", "jpeg", "png", "gif", "webp"}
ALLOWED_VIDEO_EXT = {"mp4", "webm", "mov", "avi"}

# --- Database ---------------------------------------------------------------
DB_PATH = os.getenv("GRIV_DB_PATH", str(BASE_DIR / "data" / "grievance.db"))
DB_URL = f"sqlite:///{DB_PATH}"

# --- Paths ------------------------------------------------------------------
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

FRONTEND_DIR = BASE_DIR.parent / "frontend"
TEMPLATES_DIR = FRONTEND_DIR / "templates"
STATIC_DIR = FRONTEND_DIR / "static"

# --- Departments ------------------------------------------------------------
DEPARTMENTS = [
    "Municipal_Corporation",
    "Public_Works",
    "Water_Board",
    "Electricity",
    "Police",
    "Health",
    "Transport",
    "Education",
    "Fire_Department",
]

# --- Priority thresholds ----------------------------------------------------
PRIORITY_URGENT = 75      # >= 75  -> Urgent
PRIORITY_HIGH = 50        # 50-74  -> High
PRIORITY_NORMAL = 25      # 25-49  -> Normal
# < 25                              -> Low

# --- Duplicate detection ----------------------------------------------------
DUPLICATE_SIMILARITY_THRESHOLD = 0.82

# --- Seed data (Indian context) --------------------------------------------
SEED_COMPLAINTS = [
    ("Massive pothole near MG Road causing accidents", "Municipal_Corporation", 12.9716, 77.5946, "Bengaluru", "Karnataka"),
    ("Streetlight not working on Brigade Road for a week", "Electricity", 12.9683, 77.6097, "Bengaluru", "Karnataka"),
    ("Water supply irregular in Jayanagar 4th block", "Water_Board", 12.9250, 77.5938, "Bengaluru", "Karnataka"),
    ("Garbage not collected in Indiranagar locality", "Municipal_Corporation", 12.9719, 77.6412, "Bengaluru", "Karnataka"),
    ("Broken road divider on Old Airport Road", "Public_Works", 12.9545, 77.6418, "Bengaluru", "Karnataka"),
    ("Pothole on MG Road causing bike accidents daily", "Municipal_Corporation", 12.9716, 77.5946, "Bengaluru", "Karnataka"),  # duplicate
    ("Hospital lacking basic medicines in rural area", "Health", 12.2958, 76.6394, "Mysuru", "Karnataka"),
    ("Bus frequency very low on route 500D", "Transport", 12.9352, 77.6245, "Bengaluru", "Karnataka"),
    ("School building roof leaking during rains", "Education", 13.0827, 80.2707, "Chennai", "Tamil Nadu"),
    ("No streetlights on the dark stretch near Tech Park", "Electricity", 12.9279, 77.5419, "Bengaluru", "Karnataka"),
    ("Sewage overflow on Anna Salai main road", "Municipal_Corporation", 13.0418, 80.2841, "Chennai", "Tamil Nadu"),
    ("Frequent power cuts in Adyar area every evening", "Electricity", 13.0067, 80.2206, "Chennai", "Tamil Nadu"),
    ("Drainage water flooding the street in Koramangala", "Municipal_Corporation", 12.9352, 77.6245, "Bengaluru", "Karnataka"),
    ("Traffic signal not working at Silk Board junction", "Police", 12.9176, 77.6223, "Bengaluru", "Karnataka"),
    ("Damaged road near Marine Drive needs urgent repair", "Public_Works", 18.9434, 72.8235, "Mumbai", "Maharashtra"),
]
