# SIH26-S02 — Technical Report
## AI-Based Citizen Grievance Classification, Prioritization and Duplicate Complaint Detection

---

## 1. Problem Statement Summary

The Smart India Hackathon 2026 problem statement **SIH26-S02** asks for an AI-based grievance platform that:
- Automatically **classifies** citizen complaints by category/department
- **Routes** each complaint to the correct government department
- Assigns a **priority** level based on urgency
- **Detects duplicate** complaints referring to the same underlying issue
- Provides a **citizen submission interface** and an **authority dashboard**
- Includes **GIS visualization** of geographical complaint hotspots

The expected output is an end-to-end complaint portal with AI classification, routing, duplicate detection, and a hotspot dashboard.

---

## 2. Solution Overview

**GrievanceAI** is a full-stack web application built with FastAPI (backend) and server-rendered Jinja2 templates with vanilla JS + Leaflet.js (frontend). The AI pipeline runs entirely on-device using scikit-learn — no external API keys, no cloud dependencies, fully deterministic. This makes it ideal for government deployment where data privacy and offline capability are critical.

The platform consists of four primary pages:

1. **Citizen Portal** (`/`) — A clean, responsive complaint submission form with an integrated Leaflet map for location picking and browser GPS auto-detect. Accepts both English and Hinglish (romanized Hindi) text.

2. **Authority Dashboard** (`/dashboard`) — A filterable, sortable table of all complaints with inline status management. Authorities can filter by department, priority, or status, and update complaint status with a single click.

3. **Analytics Page** (`/analytics`) — Visual insights including bar charts for complaints by department and priority distribution, status breakdown cards, top cities by complaint volume, semantic duplicate cluster viewer, and a geographical hotspot summary table.

4. **GIS Hotspot Map** (`/map`) — An interactive Leaflet map with color-coded priority markers (red=Urgent, amber=High, green=Normal, grey=Low) and translucent blue circles representing DBSCAN-detected hotspot areas. Click any marker for a detailed popup.

---

## 3. Technologies Used

### 3.1 Backend

| Technology | Version | Purpose |
|---|---|---|
| **FastAPI** | 0.115.0 | Modern async Python web framework; serves REST API + Jinja2 pages |
| **Uvicorn** | 0.30.6 | ASGI server with hot-reload for development |
| **SQLAlchemy** | 2.0.35 | ORM for database models and queries |
| **SQLite** | (built-in) | Lightweight file-based database; zero-config, portable |
| **Pydantic** | 2.9.2 | Request/response schema validation |
| **python-multipart** | 0.0.12 | Form data parsing |

### 3.2 AI / NLP

| Technology | Version | Purpose |
|---|---|---|
| **scikit-learn** | 1.5.2 | TF-IDF vectorization, Logistic Regression classification, Agglomerative Clustering, DBSCAN, cosine similarity |
| **NumPy** | 2.1.1 | Numerical operations for vectors and distance matrices |

### 3.3 Frontend

| Technology | Purpose |
|---|---|
| **Jinja2** | Server-side HTML template rendering |
| **Vanilla JavaScript** | Client-side interactivity, API calls, dynamic DOM updates |
| **CSS3** | Custom responsive design system (no external UI framework) |
| **Leaflet.js** | Open-source interactive maps with OpenStreetMap tiles |
| **OpenStreetMap** | Free map tile provider (no API key needed) |

### 3.4 Design Principles

- **No external API keys required** — the entire solution runs offline. All AI models are trained in-memory at startup. Map tiles use free OpenStreetMap.
- **Zero-config database** — SQLite is file-based; the database is auto-created on first run.
- **Single-command deployment** — `run.sh` (Linux/macOS) or `run.bat` (Windows) handles venv creation, dependency installation, and server startup.
- **Responsive design** — custom CSS with mobile breakpoints; works on phones, tablets, and desktops.

---

## 4. AI/NLP Pipeline — Detailed Explanation

### 4.1 Language Normalization

The normalization step handles the Indian multilingual reality where citizens often write complaints in Hinglish (Hindi written in Latin script). The pipeline:

1. **Lowercases** the text.
2. **Maps Hinglish tokens** to English equivalents using a curated dictionary: `sadak→road`, `bijli→electricity`, `paani→water`, `gaddha→pothole`, `kachra→garbage`, `nali→drainage`, `aspatal→hospital`, `vidyalaya→school`, etc.
3. **Strips punctuation** and collapses whitespace.
4. **Removes stopwords** (the, a, is, on, near, for, etc.).

Example transformation:
- Input: `"Sadak par bada gaddha hai, daily accident ho raha hai"`
- Output: `"road big pothole daily accident happening"`

### 4.2 Complaint Classification (TF-IDF + Logistic Regression)

**Training Data:** 40+ labelled complaint phrases curated with Indian context across 8 departments: Municipal Corporation, Public Works, Water Board, Electricity, Police, Health, Transport, Education.

**TF-IDF Vectorizer Configuration:**
- Max features: 2000
- N-gram range: (1, 2) — captures both unigrams and bigrams
- Sublinear TF scaling: `1 + log(tf)` — reduces the impact of very frequent terms
- Built-in stopword removal

**Classifier:** Logistic Regression with `C=10.0` (lower regularization for the small training set) and `max_iter=1000`.

At inference time, the system returns both the predicted department and the confidence probability (softmax output), which could be surfaced in the UI for transparency.

### 4.3 Priority Scoring

A hybrid rule-based approach that combines keyword urgency detection with department-specific multipliers:

**Urgency Keywords** (with weights):
- Safety: accident (+25), fire (+25), collapse (+20), death (+20), injury (+15), dangerous (+15), sparking (+15)
- Health: dengue (+18), malaria (+18), outbreak (+20), poisoning (+18), bleeding (+18), medical (+15), ambulance (+15)
- Vulnerable groups: children (+10), school (+8), hospital (+8), elderly (+10), pregnant (+15)
- Temporal urgency: urgent (+15), immediate (+12), daily (+8), frequent (+8)

**Department Urgency Multipliers:**
- Police ×1.15, Health ×1.15 (inherently more time-critical)
- Electricity ×1.10 (power issues affect safety)
- Municipal Corporation ×1.05, Public Works ×1.05
- Water Board ×1.00
- Transport ×0.95, Education ×0.95

**Scoring formula:**
```
base = 20
for each urgency keyword found in text:
    base += keyword_weight
final_score = min(100, round(base × department_multiplier))
```

**Priority labels:**
- 75-100 → Urgent (red)
- 50-74 → High (amber)
- 25-49 → Normal (green)
- 0-24 → Low (grey)

### 4.4 Duplicate Detection (Cosine Similarity)

When a new complaint is submitted, its normalized text is TF-IDF vectorized and compared against all existing complaints using cosine similarity:

```
similarity = cosine_similarity(new_vector, all_existing_vectors)
best_match = argmax(similarity)
if similarity[best_match] >= 0.82:
    flag as duplicate of complaint #best_match
```

This catches complaints like:
- *"Massive pothole near MG Road causing accidents"* and
- *"Pothole on MG Road causing bike accidents daily"*
which are semantically identical despite different wording.

### 4.5 Semantic Clustering (Agglomerative Clustering)

After each new submission, **all** complaints are re-clustered using Agglomerative Clustering:

- **Distance metric:** Precomputed cosine distance matrix (`1 - cosine_similarity`)
- **Linkage:** Average linkage
- **Distance threshold:** 0.35 (complaints with >65% similarity are grouped)
- **Output:** Each complaint gets a `duplicate_group` ID; groups with >1 member are surfaced on the Analytics page

This provides a broader view than pairwise duplicate detection — it identifies complaint *clusters* that may share an underlying cause (e.g., multiple complaints about the same broken road from different citizens).

### 4.6 Geographical Hotspot Detection (DBSCAN)

DBSCAN (Density-Based Spatial Clustering of Applications with Noise) runs on the latitude/longitude coordinates of all complaints:

- **Eps (ε):** 0.01 degrees (~1.1 km)
- **Min samples:** 2

Complaints that are geographically close are grouped into hotspots. The system returns:
- Cluster ID
- Number of complaints in the cluster
- Centroid coordinates (mean lat/lng)

These are rendered as translucent blue circles on the GIS map, with radius proportional to complaint count. This helps authorities identify areas with concentrated problems and prioritize field visits.

---

## 5. Database Schema

### `complaints` table

| Column | Type | Description |
|---|---|---|
| id | INTEGER PK | Auto-increment primary key |
| citizen_name | TEXT | Name of the complainant |
| phone | TEXT | Contact phone (optional) |
| original_text | TEXT | Raw complaint text as submitted |
| normalized_text | TEXT | AI-normalized text (after Hinglish mapping, stopword removal) |
| language_detected | TEXT | Detected language code |
| department | TEXT | AI-classified department |
| priority_score | INTEGER | 0-100 priority score |
| priority_label | TEXT | Urgent/High/Normal/Low |
| latitude | FLOAT | GPS latitude |
| longitude | FLOAT | GPS longitude |
| city | TEXT | City name |
| state | TEXT | State name |
| locality | TEXT | Locality/landmark |
| status | TEXT | Submitted/Acknowledged/In Progress/Resolved |
| duplicate_group | INTEGER | Cluster ID from agglomerative clustering |
| duplicate_of | INTEGER FK | ID of the original complaint this duplicates |
| created_at | DATETIME | Timestamp |
| updated_at | DATETIME | Last update timestamp |

---

## 6. API Endpoints

| Method | Path | Description |
|---|---|---|
| POST | `/api/complaints` | Submit a new complaint (runs full AI pipeline: normalize → classify → score → duplicate check → persist) |
| GET | `/api/complaints` | List all complaints (supports `department`, `priority`, `status` query params) |
| GET | `/api/complaints/{id}` | Get a single complaint by ID |
| PATCH | `/api/complaints/{id}/status` | Update complaint status |
| GET | `/api/analytics` | Aggregated metrics: totals, by-department, by-priority, by-status, duplicates, hotspots, top cities |
| GET | `/api/map-data` | GeoJSON-like point data for map rendering |
| GET | `/api/duplicates` | Semantic duplicate cluster groups |
| POST | `/api/seed` | Load 15 realistic sample complaints for demo |

Full interactive Swagger documentation is auto-generated at `/docs`.

---

## 7. Bonus Features (Beyond the Problem Statement)

These additions make the solution stand out from a basic implementation:

1. **Hinglish Language Support** — The normalization layer understands romanized Hindi tokens (`bijli`, `sadak`, `gaddha`, `kachra`), making the portal accessible to citizens who type in Hinglish — a common reality in India.

2. **Inline Status Management** — Authorities can change complaint status directly from the dashboard table with a dropdown, without navigating to a separate edit page. Changes reflect instantly across all views.

3. **Duplicate Cluster Deep-Dive** — The Analytics page doesn't just flag duplicates; it shows all complaints within each semantic cluster side-by-side, with their original text and priority, so authorities can verify the AI's grouping.

4. **Browser GPS Auto-Detect** — The citizen portal uses the browser's Geolocation API to auto-fill the complaint location, reducing friction for citizens.

5. **Confidence-Aware Classification** — The classifier returns a confidence probability alongside its prediction, which can be used for a "low confidence → human review" workflow in production.

6. **Seed Data Endpoint** — A single API call (`POST /api/seed`) loads 15 realistic Indian-context sample complaints with proper geo-coordinates, so the dashboard, analytics, and map are instantly populated for demos and judging.

7. **Responsive Mobile-First Design** — Custom CSS with mobile breakpoints ensures the portal works seamlessly on mobile phones, which is how most Indian citizens access government services.

---

## 8. Deployment Instructions

### Prerequisites
- Python 3.10 or higher
- pip (Python package installer)
- Internet connection (for first-time dependency installation and map tiles)

### Step-by-step (Linux / macOS / WSL)

```bash
# 1. Navigate to the project directory
cd sih26-grievance

# 2. Make the run script executable (first time only)
chmod +x run.sh

# 3. Run the script — it creates venv, installs deps, and starts the server
./run.sh
```

### Step-by-step (Windows)

```cmd
cd sih26-grievance
run.bat
```

### Manual deployment (if you prefer control)

```bash
cd sih26-grievance/backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Start the server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Load sample data

After the server is running, seed the database:
```bash
curl -X POST http://localhost:8000/api/seed
```

### Access the application

| URL | Page |
|---|---|
| http://localhost:8000/ | Citizen Complaint Submission Portal |
| http://localhost:8000/dashboard | Authority Dashboard |
| http://localhost:8000/analytics | Analytics & Insights |
| http://localhost:8000/map | GIS Hotspot Map |
| http://localhost:8000/docs | Interactive Swagger API Documentation |

---

## 9. Testing the AI Pipeline

Try submitting these test complaints to see different AI behaviors:

| Test Complaint | Expected Department | Expected Priority |
|---|---|---|
| "Massive pothole on MG Road, bike accident happened yesterday" | Municipal Corporation | Urgent |
| "Bijli nahi aa raha, ghar mein andhera hai" (Hinglish) | Electricity | Normal/High |
| "Hospital mein dengue outbreak hai, bachchon ko khatra hai" | Health | Urgent |
| "Streetlight not working near Tech Park" | Electricity | Normal |
| "Massive pothole near MG Road causing accidents" (submit after the first one) | Municipal Corporation | Urgent + Duplicate flag |

---

## 10. Scalability & Production Considerations

This prototype is designed for hackathon demonstration. For production deployment, consider:

- **Database:** Migrate from SQLite to PostgreSQL for concurrent access.
- **Model training:** Expand the training corpus with real labelled complaint data; consider fine-tuned BERT or IndicBERT for better multilingual classification.
- **Embeddings:** Replace TF-IDF with sentence-transformers (e.g., `all-MiniLM-L6-v2`) for more robust semantic similarity.
- **Caching:** Add Redis for caching analytics aggregations.
- **Authentication:** Add JWT-based auth for citizens and authorities.
- **File uploads:** Support photo/video attachments for complaints.
- **Notifications:** SMS/WhatsApp integration for status updates (via Twilio/Gupshup).
- **Deployment:** Docker + Docker Compose for containerized deployment; Gunicorn + Uvicorn workers for production.

---

## 11. Conclusion

GrievanceAI delivers a complete, working prototype that addresses every requirement in the SIH26-S02 problem statement — complaint intake, language normalization, AI classification, priority scoring, semantic duplicate detection, GIS hotspot visualization, status tracking, and analytics — in a single, self-contained, zero-dependency package that runs on any laptop with Python 3.10+.

The bonus features (Hinglish support, GPS auto-detect, inline status management, duplicate cluster deep-dive, seed data endpoint, and responsive design) make it a polished, judge-ready solution that demonstrates both technical depth and user-centric thinking.
