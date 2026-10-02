"""
AI engine for grievance classification, priority scoring, duplicate detection.

Pure Python + scikit-learn. No external API keys required, fully offline,
deterministic — perfect for a hackathon prototype that must run on any laptop.

Capabilities
------------
1. Language normalization — collapses mixed-case/Hinglish-style text to a
   clean lowercase form, strips punctuation, collapses whitespace, and maps
   common Hinglish/Hindi-romanized tokens to English synonyms.
2. Classification — TF-IDF + Logistic Regression trained on a small labelled
   corpus of Indian-context complaint phrases per department.
3. Priority scoring — rule-based keyword weighting (danger, accident,
   medical, fire, children) combined with department urgency multipliers.
4. Semantic similarity & duplicate detection — cosine similarity over the
   same TF-IDF vectors; a complaint is flagged as a duplicate of an earlier
   one when similarity >= threshold.
5. Clustering / hotspot detection — Agglomerative clustering groups
   semantically similar complaints; DBSCAN on lat/lng finds geo hotspots.
"""
import re
import json
import math
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.cluster import AgglomerativeClustering, DBSCAN

from app.config import (
    DEPARTMENTS,
    DUPLICATE_SIMILARITY_THRESHOLD,
    PRIORITY_URGENT,
    PRIORITY_HIGH,
    PRIORITY_NORMAL,
)

# --------------------------------------------------------------------------- #
# 1. LANGUAGE NORMALIZATION
# --------------------------------------------------------------------------- #
HINGLISH_MAP = {
    "sadak": "road", "paani": "water", "bijli": "electricity",
    "light": "streetlight", "street light": "streetlight",
    "ganda": "garbage", "kachra": "garbage",
    "nali": "drainage", "nal": "drainage",
    "hospital": "hospital", "aspatal": "hospital",
    "school": "school", "vidyalaya": "school",
    "bus": "bus", "traffik": "traffic",
    "police": "police", "chowki": "police",
    "toot": "broken", "toota": "broken",
    "khada": "pothole", "gaddha": "pothole",
    # Emergency Hinglish words
    "aag": "fire", "aagi": "fire", "fire": "fire",
    "hadsa": "accident", "durghatna": "accident",
    "khatarnak": "dangerous", "khatra": "danger",
    "bachchon": "children", "bachcha": "child", "bacche": "children",
    "bachao": "save", "suraksha": "safety",
    "maut": "death", "jaan": "life",
    "choot": "injury", "khun": "bleeding",
    "bimari": "disease", "beemari": "disease",
    "bache": "children", "baccha": "child",
    "zikra": "short circuit",
    "current": "electricity", "taar": "wire",
    "latak": "leaning", "jhuka": "leaning",
}

STOPWORDS = {
    "the", "a", "an", "is", "are", "was", "were", "of", "to", "in", "on",
    "near", "at", "for", "and", "or", "not", "this", "that", "it", "has",
    "have", "had", "been", "very", "from", "with", "by", "my", "our", "we",
}

# --------------------------------------------------------------------------- #
# 2. TRAINING CORPUS (per department, Indian context)
# --------------------------------------------------------------------------- #
TRAINING_DATA = [
    # Municipal Corporation
    ("pothole on road causing accidents", "Municipal_Corporation"),
    ("garbage not collected in my area", "Municipal_Corporation"),
    ("sewage overflow on the street", "Municipal_Corporation"),
    ("drainage water flooding the road", "Municipal_Corporation"),
    ("street cleaning not done regularly", "Municipal_Corporation"),
    ("public toilet not maintained", "Municipal_Corporation"),
    ("dumping yard causing bad smell", "Municipal_Corporation"),
    ("roadside hoardings illegal", "Municipal_Corporation"),
    ("stray dog menace in the locality", "Municipal_Corporation"),
    ("park maintenance poor condition", "Municipal_Corporation"),

    # Public Works
    ("broken road divider needs repair", "Public_Works"),
    ("damaged road surface urgent repair", "Public_Works"),
    ("bridge crack needs inspection", "Public_Works"),
    ("flyover construction delayed", "Public_Works"),
    ("footpath broken and dangerous", "Public_Works"),
    ("roadside wall collapsed", "Public_Works"),

    # Water Board
    ("water supply irregular in my area", "Water_Board"),
    ("no water for three days", "Water_Board"),
    ("dirty water coming from tap", "Water_Board"),
    ("water pipe leakage on main road", "Water_Board"),
    ("tanker water not delivered", "Water_Board"),
    ("borewell motor not working", "Water_Board"),

    # Electricity
    ("streetlight not working", "Electricity"),
    ("frequent power cuts every evening", "Electricity"),
    ("electric pole leaning dangerously", "Electricity"),
    ("transformer sparking and unsafe", "Electricity"),
    ("no electricity in my house", "Electricity"),
    ("meter bill incorrect amount", "Electricity"),

    # Police
    ("traffic signal not working", "Police"),
    ("traffic jam caused by parked trucks", "Police"),
    ("noise complaint late night party", "Police"),
    ("suspicious activity in neighborhood", "Police"),
    ("theft incident in my street", "Police"),
    ("illegal parking blocking ambulance", "Police"),

    # Health
    ("hospital lacking basic medicines", "Health"),
    ("dengue outbreak in locality", "Health"),
    ("primary health centre no doctor", "Health"),
    ("food poisoning from street vendor", "Health"),
    ("garbage causing mosquito breeding", "Health"),
    ("ambulance not arriving on time", "Health"),

    # Transport
    ("bus frequency very low on route", "Transport"),
    ("auto rickshaw overcharging passengers", "Transport"),
    ("metro station escalator not working", "Transport"),
    ("bus stop shelter damaged", "Transport"),
    ("license renewal delayed", "Transport"),

    # Education
    ("school building roof leaking", "Education"),
    ("teacher absent regularly", "Education"),
    ("midday meal not provided", "Education"),
    ("school toilet dirty and unusable", "Education"),
    ("college admission fee issue", "Education"),
    ("playground equipment broken", "Education"),

    # Fire Department
    ("fire in residential building people trapped", "Fire_Department"),
    ("building fire spreading quickly", "Fire_Department"),
    ("short circuit caused fire in apartment", "Fire_Department"),
    ("gas leak in kitchen dangerous", "Fire_Department"),
    ("factory fire explosion hazard", "Fire_Department"),
    ("electric wire sparking fire risk", "Fire_Department"),
    ("building collapse people trapped inside", "Fire_Department"),
    ("structure collapsed rescue needed urgently", "Fire_Department"),

    # Police - additional emergency data
    ("serious accident on highway bleeding", "Police"),
    ("traffic accident vehicles collided", "Police"),
    ("road accident bike collided", "Police"),
    ("emergency accident victim needs help", "Police"),
]

# --------------------------------------------------------------------------- #
# 3. PRIORITY SCORING
# --------------------------------------------------------------------------- #
# Tier 1: Life-threatening / critical (these alone push a complaint to Urgent)
CRITICAL_KEYWORDS = {
    "accident": 35, "fire": 40, "death": 40, "deadly": 40,
    "electrocution": 40, "electric shock": 35, "explosion": 40,
    "collapse": 35, "collapsed": 35, "drowning": 40,
    "bleeding": 30, "gas leak": 40, "building collapse": 45,
    "structure collapse": 45, "live wire": 40, "short circuit": 30,
}

# Tier 2: High urgency (health hazards, safety risks, vulnerable groups)
HIGH_URGENCY_KEYWORDS = {
    "injury": 22, "injured": 22, "dangerous": 20, "hazard": 20,
    "hazardous": 20, "unsafe": 18, "risk": 15, "risky": 15,
    "leaning": 20, "crack": 18, "sparking": 25, "spark": 22,
    "dengue": 25, "malaria": 25, "outbreak": 28, "epidemic": 30,
    "poisoning": 25, "contamination": 22, "contaminated": 22,
    "medical": 18, "ambulance": 20, "emergency": 25,
    "fever": 15, "infection": 18, "sewage": 15,
    "flooding": 18, "flood": 18, "overflow": 12,
    "children": 15, "child": 15, "school": 12, "hospital": 10,
    "elderly": 12, "pregnant": 18, "baby": 18, "infant": 18,
    "patient": 12,
}

# Tier 3: Moderate urgency (service disruption, recurring issues)
MODERATE_KEYWORDS = {
    "urgent": 15, "immediate": 12, "daily": 10, "frequent": 10,
    "every day": 10, "every evening": 10, "regularly": 8,
    "weeks": 10, "month": 12, "days": 8,
    "not working": 8, "broken": 10, "damaged": 10,
    "leak": 10, "leakage": 10, "block": 8, "blocked": 8,
    "no water": 12, "no electricity": 12, "power cut": 10,
    "not collected": 8, "overflow": 10, "smelly": 8,
    "accident": 10, "bike": 5, "car": 5,
    "pothole": 8, "dark": 8, "stray": 5,
}

# Department base urgency — departments dealing with life/safety start higher
DEPARTMENT_BASE_SCORE = {
    "Fire_Department": 45,
    "Police": 35,
    "Health": 35,
    "Electricity": 30,
    "Municipal_Corporation": 25,
    "Public_Works": 25,
    "Water_Board": 20,
    "Transport": 15,
    "Education": 15,
}

# Department urgency multiplier (applied after keyword bonuses)
DEPARTMENT_URGENCY_MULTIPLIER = {
    "Fire_Department": 1.25,
    "Police": 1.20,
    "Health": 1.20,
    "Electricity": 1.15,
    "Municipal_Corporation": 1.10,
    "Public_Works": 1.10,
    "Water_Board": 1.05,
    "Transport": 1.00,
    "Education": 1.00,
}


class GrievanceAI:
    """
    Encapsulates the full NLP pipeline. Initialize once at app startup;
    reuse across requests (the vectorizer and classifier are stateless
    after fit).
    """

    def __init__(self):
        self.vectorizer = TfidfVectorizer(
            max_features=2000,
            ngram_range=(1, 2),
            sublinear_tf=True,
            stop_words=list(STOPWORDS),
        )
        self.classifier = LogisticRegression(max_iter=1000, C=10.0)
        self._fit()

    # ---- internal -------------------------------------------------------
    def _fit(self):
        texts = [t for t, _ in TRAINING_DATA]
        labels = [l for _, l in TRAINING_DATA]
        X = self.vectorizer.fit_transform(texts)
        self.classifier.fit(X, labels)

    # ---- public API -----------------------------------------------------
    @staticmethod
    def normalize(text: str) -> tuple[str, str]:
        """Return (normalized_text, detected_language_label)."""
        lower = text.lower().strip()
        # replace Hinglish tokens
        for hin, eng in HINGLISH_MAP.items():
            lower = re.sub(rf"\b{re.escape(hin)}\b", eng, lower)
        lower = re.sub(r"[^a-z0-9\s]", " ", lower)
        lower = re.sub(r"\s+", " ", lower).strip()
        # crude language detection: if many non-English mapped tokens found
        lang = "en"
        return lower, lang

    def vectorize(self, text: str):
        """Return TF-IDF vector for a single text."""
        return self.vectorizer.transform([text])

    def vector_to_json(self, vec) -> str:
        """Serialize a sparse TF-IDF vector to compact JSON for storage."""
        arr = vec.toarray()[0]
        nonzero = arr[arr > 0]
        return json.dumps(nonzero.tolist())

    def classify(self, text: str) -> str:
        """Predict department."""
        vec = self.vectorize(text)
        return str(self.classifier.predict(vec)[0])

    def classify_with_confidence(self, text: str) -> tuple[str, float]:
        vec = self.vectorize(text)
        proba = self.classifier.predict_proba(vec)[0]
        idx = int(np.argmax(proba))
        return str(self.classifier.classes_[idx]), float(proba[idx])

    def score_priority(self, text: str, department: str) -> tuple[int, str]:
        """
        Compute a 0-100 priority score and a label.
        Uses a 3-tier keyword system:
          Tier 1 (Critical) — life-threatening: accident, fire, collapse...
          Tier 2 (High)      — health hazards, vulnerable groups, safety risks
          Tier 3 (Moderate)  — service disruption, recurring issues
        Combined with department base score + urgency multiplier.
        """
        # Start from department base (Police/Health start at 35, Education at 15)
        base = DEPARTMENT_BASE_SCORE.get(department, 20)

        # Tier 1: Critical keywords (life-threatening)
        for kw, weight in CRITICAL_KEYWORDS.items():
            if kw in text:
                base += weight

        # Tier 2: High urgency keywords
        for kw, weight in HIGH_URGENCY_KEYWORDS.items():
            if kw in text:
                base += weight

        # Tier 3: Moderate keywords
        for kw, weight in MODERATE_KEYWORDS.items():
            if kw in text:
                base += weight

        # Apply department urgency multiplier
        mult = DEPARTMENT_URGENCY_MULTIPLIER.get(department, 1.0)
        score = min(100, int(round(base * mult)))

        if score >= PRIORITY_URGENT:
            label = "Urgent"
        elif score >= PRIORITY_HIGH:
            label = "High"
        elif score >= PRIORITY_NORMAL:
            label = "Normal"
        else:
            label = "Low"
        return score, label

    def similarity(self, text_a: str, text_b: str) -> float:
        va = self.vectorize(text_a)
        vb = self.vectorize(text_b)
        return float(cosine_similarity(va, vb)[0][0])

    def find_duplicate(
        self, text: str, existing_texts: list[str], threshold: float = DUPLICATE_SIMILARITY_THRESHOLD
    ) -> int | None:
        """
        Return index of the first existing text that is a near-duplicate,
        or None.
        """
        if not existing_texts:
            return None
        vec_new = self.vectorize(text)
        vec_existing = self.vectorizer.transform(existing_texts)
        sims = cosine_similarity(vec_new, vec_existing)[0]
        best_idx = int(np.argmax(sims))
        if sims[best_idx] >= threshold:
            return best_idx
        return None

    def cluster_complaints(self, texts: list[str]) -> list[int]:
        """
        Agglomerative clustering on TF-IDF vectors to group semantically
        similar complaints (used for duplicate-group assignment & analytics).
        Returns a list of cluster labels aligned with `texts`.
        """
        if len(texts) < 2:
            return [0] * len(texts)
        X = self.vectorizer.transform(texts)
        # cosine distance = 1 - cosine similarity
        dist = 1 - cosine_similarity(X)
        np.fill_diagonal(dist, 0.0)
        clusterer = AgglomerativeClustering(
            n_clusters=None,
            distance_threshold=0.35,
            metric="precomputed",
            linkage="average",
        )
        labels = clusterer.fit_predict(dist)
        return labels.tolist()

    def find_hotspots(
        self, coords: list[tuple[float, float]], min_samples: int = 2
    ) -> list[int]:
        """
        DBSCAN on lat/lng to find geographical complaint hotspots.
        Returns a list of cluster labels (-1 = noise) aligned with coords.
        """
        if len(coords) < 2:
            return [-1] * len(coords)
        # ~1km eps; lat/lng approx conversion
        eps = 0.01
        db = DBSCAN(eps=eps, min_samples=min_samples)
        labels = db.fit_predict(np.array(coords))
        return labels.tolist()
