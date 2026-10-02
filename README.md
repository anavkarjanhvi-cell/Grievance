# SIH26 — AI-Based Citizen Grievance Portal 🏛️

**Problem Statement:** SIH26-S02 — AI-Based Citizen Grievance Classification, Prioritization and Duplicate Complaint Detection.

An end-to-end grievance portal that automatically **classifies** complaints, **routes** them to the correct department, **assigns priority**, **detects duplicates** referring to the same underlying issue, and shows **geographical hotspots** on an interactive GIS dashboard.

---

## ✨ Features

| Feature | How it works |
|---|---|
| **Citizen Submission Portal** | Clean, responsive form with location picker (Leaflet map + auto-detect GPS). Accepts English and Hinglish text. |
| **AI Classification** | TF-IDF + Logistic Regression classifies each complaint into 8 departments. |
| **Language Normalization** | Hinglish→English token mapping, stopword removal, punctuation cleaning. |
| **Priority Scoring** | Keyword-based urgency detection (accident, fire, medical, children…) × department urgency multiplier → 0-100 score with Urgent/High/Normal/Low labels. |
| **Duplicate Detection** | Cosine similarity over TF-IDF embeddings flags near-duplicate complaints. Agglomerative clustering groups semantically similar complaints. |
| **GIS Hotspot Dashboard** | DBSCAN clustering on lat/lng identifies geographical complaint clusters. Interactive Leaflet map with color-coded priority markers and hotspot overlays. |
| **Authority Dashboard** | Filterable, sortable table. Update complaint status with one click. |
| **Analytics Page** | Bar charts for department & priority distribution, status breakdown, top cities, duplicate cluster viewer. |
| **Auto Swagger API Docs** | Available at `/docs` — fully interactive. |

### 🌟 Bonus features (beyond the problem statement)

1. **Hinglish support** — the system understands romanized Hindi (`bijli`, `sadak`, `gaddha`, `kachra`) and normalizes it.
2. **One-click status management** — authorities can change status inline from the dashboard table.
3. **Duplicate cluster deep-dive** — the analytics page shows all complaints within each semantic cluster side-by-side.
4. **Auto-detect GPS** — citizen portal uses browser geolocation.
5. **Seed endpoint** — `POST /api/seed` loads 15 realistic Indian-context sample complaints instantly for demo.
6. **Responsive design** — works on mobile, tablet, and desktop.

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────┐
│                 FRONTEND                     │
│  (Jinja2 Templates + Vanilla JS + Leaflet)   │
│                                              │
│  /              Citizen Submission Portal    │
│  /dashboard     Authority Dashboard          │
│  /analytics     Analytics & Charts           │
│  /map           GIS Hotspot Map              │
└──────────────────┬──────────────────────────┘
                   │ HTTP / JSON
┌──────────────────▼──────────────────────────┐
│                BACKEND (FastAPI)              │
│                                              │
│  ┌─────────┐  ┌──────────┐  ┌────────────┐ │
│  │ Routers │  │ Schemas  │  │  AI Engine │ │
│  │ (CRUD)  │  │(Pydantic)│  │(scikit-learn)│ │
│  └─────────┘  └──────────┘  └────────────┘ │
│         │                         │          │
│         └──────────┬──────────────┘          │
│                    ▼                         │
│           ┌────────────────┐                 │
│           │  SQLite (SQLA)  │                 │
│           └────────────────┘                 │
└──────────────────────────────────────────────┘
```

---

## 🚀 Quick Start (Local Deployment)

### Prerequisites
- Python 3.10+
- pip

### Option A — One-command (Linux/macOS/WSL)
```bash
cd sih26-grievance
chmod +x run.sh
./run.sh
```

### Option B — Manual step-by-step
```bash
cd sih26-grievance/backend
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### Option C — Windows
```cmd
cd sih26-grievance
run.bat
```

### Seed sample data
Once the server is running, open a new terminal:
```bash
curl -X POST http://localhost:8000/api/seed
```
Or simply visit `http://localhost:8000/api/seed` in your browser.

### Access the application
| URL | Page |
|---|---|
| http://localhost:8000/ | Citizen Portal |
| http://localhost:8000/dashboard | Authority Dashboard |
| http://localhost:8000/analytics | Analytics & Charts |
| http://localhost:8000/map | GIS Hotspot Map |
| http://localhost:8000/docs | Swagger API Docs |

---

## 📁 Project Structure

```
sih26-grievance/
├── run.sh                  # Linux/macOS deployment script
├── run.bat                 # Windows deployment script
├── README.md
├── REPORT.md               # Detailed technical report
├── backend/
│   ├── requirements.txt
│   ├── data/               # SQLite DB (auto-created)
│   └── app/
│       ├── main.py         # FastAPI entrypoint + page routes
│       ├── config.py       # Configuration & constants
│       ├── models.py       # SQLAlchemy ORM models
│       ├── schemas.py      # Pydantic validation schemas
│       ├── routers/
│       │   └── api.py      # REST API endpoints
│       └── ai/
│           └── engine.py   # NLP classification, priority, duplicate, clustering
└── frontend/
    ├── templates/          # Jinja2 HTML pages
    │   ├── citizen.html
    │   ├── dashboard.html
    │   ├── analytics.html
    │   └── map.html
    └── static/
        ├── css/style.css
        └── js/app.js
```

---

## 🧠 AI/NLP Pipeline (Detailed)

### 1. Language Normalization
- Lowercasing → Hinglish token mapping → punctuation stripping → stopword removal.
- Example: `"Sadak par bada gaddha hai, accident ho raha hai"` → `"road big pothole accident happening"`

### 2. Classification (TF-IDF + Logistic Regression)
- **TF-IDF Vectorizer:** 2000 max features, unigrams + bigrams, sublinear TF.
- **Logistic Regression:** trained on 40+ labelled Indian-context complaint phrases across 8 departments.
- Returns predicted department + confidence probability.

### 3. Priority Scoring (Rule-based + Keyword Weighting)
- Base score: 20.
- Urgency keywords add weight (accident: +25, fire: +25, dengue: +18, children: +10, etc.)
- Department urgency multiplier (Police ×1.15, Health ×1.15, Education ×0.95…)
- Final score: `min(100, base × multiplier)` → mapped to Urgent/High/Normal/Low.

### 4. Duplicate Detection (Cosine Similarity)
- New complaint's TF-IDF vector is compared against all existing complaints.
- If cosine similarity ≥ 0.82, it's flagged as a duplicate of the best match.

### 5. Semantic Clustering (Agglomerative)
- All complaints re-clustered after each new submission.
- Precomputed cosine distance matrix → average linkage → distance threshold 0.35.
- Groups complaints referring to the same underlying issue.

### 6. Geographical Hotspots (DBSCAN)
- DBSCAN on lat/lng coordinates (eps ≈ 1km).
- Hotspot circles rendered on the map with size proportional to complaint count.

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Backend Framework | FastAPI 0.115 |
| ORM | SQLAlchemy 2.0 |
| Database | SQLite |
| AI / NLP | scikit-learn 1.5 (TF-IDF, Logistic Regression, Agglomerative Clustering, DBSCAN) |
| Validation | Pydantic 2.9 |
| Frontend | Jinja2 templates, Vanilla JS, CSS3 |
| GIS / Maps | Leaflet.js 1.9 + OpenStreetMap tiles |
| Server | Uvicorn |

---

## 📡 API Endpoints

| Method | Path | Description |
|---|---|---|
| POST | `/api/complaints` | Submit a new complaint (triggers full AI pipeline) |
| GET | `/api/complaints` | List complaints (supports dept/priority/status filters) |
| GET | `/api/complaints/{id}` | Get single complaint |
| PATCH | `/api/complaints/{id}/status` | Update complaint status |
| GET | `/api/analytics` | Aggregated dashboard metrics |
| GET | `/api/map-data` | GeoJSON points for map rendering |
| GET | `/api/duplicates` | Semantic duplicate cluster groups |
| POST | `/api/seed` | Load 15 sample Indian-context complaints |

Full interactive docs at `http://localhost:8000/docs`.

---

## 📄 License
This prototype is built for **Smart India Hackathon 2026** (SIH26-S02).
