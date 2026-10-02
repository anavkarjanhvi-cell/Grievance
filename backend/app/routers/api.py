"""
FastAPI routers — complaint CRUD, analytics, uploads, chatbot, reports.
"""
import json
import os
import uuid
import csv
import io
import numpy as np
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.models import Complaint, User, Message, get_db
from app.schemas import ComplaintCreate, ComplaintOut, StatusUpdate
from app.ai.engine import GrievanceAI
from app.config import SEED_COMPLAINTS, DEPARTMENTS, UPLOAD_DIR, MAX_UPLOAD_SIZE, ALLOWED_IMAGE_EXT, ALLOWED_VIDEO_EXT
from app.routers.auth import get_current_user, require_admin

router = APIRouter()

# Single shared AI instance (module-level, reused across requests)
ai = GrievanceAI()


@router.post("/complaints", response_model=ComplaintOut, tags=["Complaints"])
def create_complaint(payload: ComplaintCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """
    Submit a new complaint. The backend:
      1. normalizes the text
      2. classifies the department
      3. scores priority
      4. checks for duplicates against existing complaints
      5. persists everything
    """
    normalized, lang = ai.normalize(payload.text)
    department, _confidence = ai.classify_with_confidence(normalized)
    score, label = ai.score_priority(normalized, department)

    # Duplicate detection — compare against all existing normalized texts
    existing = db.query(Complaint).order_by(Complaint.created_at.asc()).all()
    existing_texts = [c.normalized_text for c in existing]
    dup_idx = ai.find_duplicate(normalized, existing_texts)
    duplicate_of = existing[dup_idx].id if dup_idx is not None else None

    complaint = Complaint(
        citizen_name=payload.citizen_name,
        phone=payload.phone,
        original_text=payload.text,
        normalized_text=normalized,
        language_detected=lang,
        department=department,
        priority_score=score,
        priority_label=label,
        latitude=payload.latitude,
        longitude=payload.longitude,
        city=payload.city,
        state=payload.state,
        locality=payload.locality,
        status="Submitted",
        duplicate_of=duplicate_of,
        attachments=json.dumps(payload.attachments) if payload.attachments else None,
        user_id=user.id if user else None,
    )
    db.add(complaint)
    db.commit()
    db.refresh(complaint)

    # Re-run clustering to assign duplicate_group ids across the whole set
    _recompute_clusters(db)
    db.refresh(complaint)
    return complaint


@router.get("/complaints", response_model=list[ComplaintOut], tags=["Complaints"])
def list_complaints(
    department: str | None = None,
    priority: str | None = None,
    status: str | None = None,
    limit: int = 200,
    db: Session = Depends(get_db),
):
    q = db.query(Complaint)
    if department:
        q = q.filter(Complaint.department == department)
    if priority:
        q = q.filter(Complaint.priority_label == priority)
    if status:
        q = q.filter(Complaint.status == status)
    return q.order_by(Complaint.created_at.desc()).limit(limit).all()


@router.get("/complaints/{complaint_id}", response_model=ComplaintOut, tags=["Complaints"])
def get_complaint(complaint_id: int, db: Session = Depends(get_db)):
    c = db.get(Complaint, complaint_id)
    if not c:
        raise HTTPException(404, "Complaint not found")
    return c


# --------------------------------------------------------------------------- #
# MESSAGES (admin <-> citizen on a complaint)
# --------------------------------------------------------------------------- #
@router.get("/complaints/{complaint_id}/messages", tags=["Messages"])
def get_messages(complaint_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Get all messages on a complaint. Admins can see all; citizens see their own."""
    complaint = db.get(Complaint, complaint_id)
    if not complaint:
        raise HTTPException(404, "Complaint not found")
    # If citizen, ensure they own it
    if user.role == "citizen" and complaint.user_id and complaint.user_id != user.id:
        raise HTTPException(403, "You can only view messages on your own complaints")
    msgs = db.query(Message).filter(Message.complaint_id == complaint_id).order_by(Message.created_at.asc()).all()
    return [{"id": m.id, "complaint_id": m.complaint_id, "sender_role": m.sender_role,
             "sender_name": m.sender_name, "text": m.text,
             "created_at": m.created_at.isoformat() if m.created_at else None} for m in msgs]


@router.post("/complaints/{complaint_id}/messages", tags=["Messages"])
def send_message(complaint_id: int, text: str = Query(...), db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Send a message on a complaint. Both admin and citizen can send."""
    complaint = db.get(Complaint, complaint_id)
    if not complaint:
        raise HTTPException(404, "Complaint not found")
    # Citizens can only message their own complaints
    if user.role == "citizen" and complaint.user_id and complaint.user_id != user.id:
        raise HTTPException(403, "You can only message on your own complaints")
    msg = Message(
        complaint_id=complaint_id,
        sender_id=user.id,
        sender_role=user.role,
        sender_name=user.full_name,
        text=text,
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return {"id": msg.id, "complaint_id": msg.complaint_id, "sender_role": msg.sender_role,
            "sender_name": msg.sender_name, "text": msg.text,
            "created_at": msg.created_at.isoformat() if msg.created_at else None}


# --------------------------------------------------------------------------- #
# MY COMPLAINTS (citizen view)
# --------------------------------------------------------------------------- #
@router.get("/my-complaints", tags=["Complaints"])
def my_complaints(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Get all complaints submitted by the logged-in citizen, with messages and status."""
    q = db.query(Complaint)
    if user.role == "citizen":
        q = q.filter(Complaint.user_id == user.id)
    complaints = q.order_by(Complaint.created_at.desc()).all()
    result = []
    for c in complaints:
        msgs = db.query(Message).filter(Message.complaint_id == c.id).order_by(Message.created_at.asc()).all()
        result.append({
            "id": c.id,
            "text": c.original_text,
            "department": c.department,
            "priority_label": c.priority_label,
            "priority_score": c.priority_score,
            "status": c.status,
            "city": c.city,
            "locality": c.locality,
            "duplicate_of": c.duplicate_of,
            "attachments": c.attachments,
            "created_at": c.created_at.isoformat() if c.created_at else None,
            "messages": [{"id": m.id, "sender_role": m.sender_role, "sender_name": m.sender_name,
                           "text": m.text, "created_at": m.created_at.isoformat() if m.created_at else None} for m in msgs],
        })
    return {"complaints": result, "total": len(result)}


# --------------------------------------------------------------------------- #
# ADMIN-ONLY: update status
# --------------------------------------------------------------------------- #
@router.patch("/complaints/{complaint_id}/status", response_model=ComplaintOut, tags=["Complaints"])
def update_status(complaint_id: int, payload: StatusUpdate, db: Session = Depends(get_db), user: User = Depends(require_admin)):
    c = db.get(Complaint, complaint_id)
    if not c:
        raise HTTPException(404, "Complaint not found")
    c.status = payload.status
    c.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(c)
    return c


@router.get("/analytics", tags=["Analytics"])
def analytics(db: Session = Depends(get_db)):
    """Aggregated dashboard metrics."""
    all_c = db.query(Complaint).all()
    total = len(all_c)
    by_dept: dict[str, int] = {d: 0 for d in DEPARTMENTS}
    by_prio: dict[str, int] = {"Urgent": 0, "High": 0, "Normal": 0, "Low": 0}
    by_status: dict[str, int] = {}
    dups = 0
    coords: list[tuple[float, float]] = []
    city_counts: dict[str, int] = {}

    for c in all_c:
        by_dept[c.department] = by_dept.get(c.department, 0) + 1
        by_prio[c.priority_label] = by_prio.get(c.priority_label, 0) + 1
        by_status[c.status] = by_status.get(c.status, 0) + 1
        if c.duplicate_of is not None:
            dups += 1
        if c.latitude is not None and c.longitude is not None:
            coords.append((c.latitude, c.longitude))
        if c.city:
            city_counts[c.city] = city_counts.get(c.city, 0) + 1

    # geo hotspots via DBSCAN
    hotspot_labels = ai.find_hotspots(coords) if coords else []
    hotspots: list[dict] = []
    for label in set(hotspot_labels):
        if label == -1:
            continue
        indices = [i for i, l in enumerate(hotspot_labels) if l == label]
        lat = float(np.mean([coords[i][0] for i in indices]))
        lng = float(np.mean([coords[i][1] for i in indices]))
        hotspots.append({
            "cluster_id": int(label),
            "count": len(indices),
            "lat": lat,
            "lng": lng,
        })
    hotspots.sort(key=lambda h: h["count"], reverse=True)

    top_cities = sorted(city_counts.items(), key=lambda x: x[1], reverse=True)[:5]

    return {
        "total": total,
        "by_department": by_dept,
        "by_priority": by_prio,
        "by_status": by_status,
        "duplicates_detected": dups,
        "top_hotspots": hotspots,
        "top_cities": [{"city": c, "count": n} for c, n in top_cities],
    }


@router.get("/map-data", tags=["Analytics"])
def map_data(db: Session = Depends(get_db)):
    """GeoJSON-ish data for the GIS dashboard."""
    pts = []
    for c in db.query(Complaint).all():
        if c.latitude is not None and c.longitude is not None:
            pts.append({
                "id": c.id,
                "lat": c.latitude,
                "lng": c.longitude,
                "city": c.city,
                "department": c.department,
                "priority": c.priority_label,
                "status": c.status,
                "text": c.original_text,
                "is_duplicate": c.duplicate_of is not None,
            })
    return {"points": pts}


@router.get("/duplicates", tags=["Analytics"])
def duplicate_groups(db: Session = Depends(get_db)):
    """Return complaint groups that are semantically similar (duplicate clusters)."""
    all_c = db.query(Complaint).order_by(Complaint.created_at.asc()).all()
    if not all_c:
        return {"groups": []}
    texts = [c.normalized_text for c in all_c]
    labels = ai.cluster_complaints(texts)
    groups: dict[int, list[int]] = {}
    for cid, label in zip([c.id for c in all_c], labels):
        groups.setdefault(int(label), []).append(cid)
    # only return groups with >1 member
    out = [
        {"cluster_id": k, "complaint_ids": v}
        for k, v in sorted(groups.items()) if len(v) > 1
    ]
    return {"groups": out}


@router.get("/priority-queue", tags=["Queue"])
def priority_queue(db: Session = Depends(get_db)):
    """
    Return complaints sorted by priority (Urgent first), then by recency.
    Only unresolved complaints are included. Each item has a queue rank.
    """
    PRIORITY_ORDER = {"Urgent": 0, "High": 1, "Normal": 2, "Low": 3}
    all_c = db.query(Complaint).filter(
        Complaint.status != "Resolved"
    ).all()
    # sort: priority label first, then score descending, then created_at ascending (oldest first within same priority)
    all_c.sort(key=lambda c: (PRIORITY_ORDER.get(c.priority_label, 9), -c.priority_score, c.created_at))
    queue = []
    for rank, c in enumerate(all_c, 1):
        queue.append({
            "rank": rank,
            "id": c.id,
            "text": c.original_text,
            "department": c.department,
            "priority_score": c.priority_score,
            "priority_label": c.priority_label,
            "status": c.status,
            "city": c.city,
            "locality": c.locality,
            "created_at": c.created_at.isoformat() if c.created_at else None,
            "duplicate_of": c.duplicate_of,
            "citizen_name": c.citizen_name,
        })
    return {"queue": queue, "total": len(queue)}


# --------------------------------------------------------------------------- #
# FILE UPLOAD
# --------------------------------------------------------------------------- #
@router.post("/upload", tags=["Upload"])
async def upload_file(file: UploadFile = File(...)):
    """
    Upload an image or video file. Returns the URL path that can be
    attached to a complaint.
    """
    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in ALLOWED_IMAGE_EXT and ext not in ALLOWED_VIDEO_EXT:
        raise HTTPException(400, f"File type .{ext} not allowed. Supported: {ALLOWED_IMAGE_EXT | ALLOWED_VIDEO_EXT}")

    content = await file.read()
    if len(content) > MAX_UPLOAD_SIZE:
        raise HTTPException(400, f"File too large. Max {MAX_UPLOAD_SIZE // 1024 // 1024}MB")

    file_type = "image" if ext in ALLOWED_IMAGE_EXT else "video"
    unique_name = f"{uuid.uuid4().hex[:12]}.{ext}"
    file_path = UPLOAD_DIR / unique_name
    with open(file_path, "wb") as f:
        f.write(content)

    return {
        "filename": file.filename,
        "stored_as": unique_name,
        "type": file_type,
        "url": f"/uploads/{unique_name}",
        "size": len(content),
    }


# --------------------------------------------------------------------------- #
# AI CHATBOT
# --------------------------------------------------------------------------- #
CHATBOT_RESPONSES = [
    {
        "keywords": ["how", "submit", "file", "register", "lodge", "complaint"],
        "response": "To submit a complaint, go to the Citizen Portal (home page), fill in your name, phone, describe the issue, pick your location on the map, and click 'Submit Complaint'. The AI will automatically classify it, assign priority, and check for duplicates — all in real time!",
    },
    {
        "keywords": ["duplicate", "similar", "same", "already", "existing"],
        "response": "Our AI uses TF-IDF embeddings and cosine similarity to detect duplicate complaints. When you submit a complaint that is semantically similar (>=82% match) to an existing one, it gets flagged as a duplicate and linked to the original. This helps authorities avoid working on the same issue twice.",
    },
    {
        "keywords": ["priority", "urgent", "score", "how priorit"],
        "response": "Priority is scored 0-100 using a 3-tier keyword system: Critical keywords (fire, accident, collapse) add 35-45 points, High urgency keywords (dengue, bleeding, children) add 15-28 points, and Moderate keywords (broken, daily, urgent) add 5-15 points. The department also has a base score (Fire Dept starts at 45, Education at 15). Score >=75 = Urgent, 50-74 = High, 25-49 = Normal, <25 = Low.",
    },
    {
        "keywords": ["department", "route", "classify", "which dept"],
        "response": "The AI uses TF-IDF + Logistic Regression to classify your complaint into one of 9 departments: Municipal Corporation, Public Works, Water Board, Electricity, Police, Health, Transport, Education, or Fire Department. The model is trained on 50+ Indian-context complaint phrases.",
    },
    {
        "keywords": ["hotspot", "map", "gis", "location", "geo"],
        "response": "The GIS Hotspot Map page shows all complaints on an interactive Leaflet map. DBSCAN clustering groups complaints that are geographically close (within ~1km) into hotspot areas, shown as blue circles. Red markers = Urgent, amber = High, green = Normal, grey = Low.",
    },
    {
        "keywords": ["track", "status", "my complaint", "where"],
        "response": "You can track your complaint status on the Authority Dashboard. Use the status filter to see complaints in different stages: Submitted, Acknowledged, In Progress, or Resolved. Each complaint has a unique ID that you can use to search.",
    },
    {
        "keywords": ["hinglish", "hindi", "language", "type in"],
        "response": "Yes! You can type complaints in Hinglish (Hindi in English script). The system understands words like 'bijli' (electricity), 'sadak' (road), 'gaddha' (pothole), 'aag' (fire), 'kachra' (garbage) and automatically normalizes them to English before processing.",
    },
    {
        "keywords": ["upload", "photo", "video", "picture", "image", "attach"],
        "response": "You can upload photos or videos with your complaint! On the citizen portal, click the 'Upload Photo/Video' button before submitting. Supported formats: JPG, PNG, GIF, WebP, MP4, WebM, MOV. Max file size: 10MB.",
    },
    {
        "keywords": ["report", "export", "download", "save", "csv"],
        "response": "You can export a CSV report of all complaints from the Dashboard or Analytics page. Click the 'Export Report' button to download a spreadsheet with all complaint details including ID, text, department, priority score, status, and location.",
    },
    {
        "keywords": ["queue", "order", "sequence", "first"],
        "response": "The Priority Queue page shows all unresolved complaints sorted by urgency — Urgent first, then High, Normal, and Low. Each complaint has a rank number so authorities know exactly what to address first.",
    },
    {
        "keywords": ["hello", "hi", "hey", "namaste", "help", "start"],
        "response": "Hello! I'm GrievanceAI Assistant. I can help you with how to submit a complaint, how AI classification works, how priority is scored, how duplicate detection works, how to track complaints, how to upload photos/videos, and how to export reports. Just ask me anything!",
    },
    {
        "keywords": ["thank", "thanks", "great", "awesome", "nice"],
        "response": "You're welcome! If you have any more questions, feel free to ask. I'm here to help you with the GrievanceAI platform.",
    },
]


@router.post("/chatbot", tags=["Chatbot"])
def chatbot(query: str = Query(..., description="User's question")):
    """
    AI chatbot — answers questions about the grievance platform.
    Uses keyword matching to find the most relevant response.
    """
    query_lower = query.lower().strip()
    best_match = None
    best_score = 0

    for entry in CHATBOT_RESPONSES:
        score = sum(1 for kw in entry["keywords"] if kw in query_lower)
        if score > best_score:
            best_score = score
            best_match = entry

    if best_match and best_score > 0:
        return {"reply": best_match["response"], "matched": True}

    fallback = (
        "I'm not sure I understood that. Here are some things you can ask me: "
        "how do I submit a complaint, how does priority scoring work, how does duplicate detection work, "
        "can I type in Hinglish, how do I upload photos, how do I export a report, what departments are available."
    )
    return {"reply": fallback, "matched": False}


# --------------------------------------------------------------------------- #
# REPORT EXPORT
# --------------------------------------------------------------------------- #
@router.get("/report", tags=["Report"])
def export_report(db: Session = Depends(get_db)):
    """Export all complaints as a CSV file."""
    all_c = db.query(Complaint).order_by(Complaint.created_at.desc()).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "ID", "Citizen Name", "Phone", "Complaint Text", "Department",
        "Priority Score", "Priority Label", "Status", "City", "State",
        "Locality", "Latitude", "Longitude", "Duplicate Of",
        "Has Attachments", "Created At", "Updated At",
    ])

    for c in all_c:
        writer.writerow([
            c.id, c.citizen_name, c.phone or "", c.original_text,
            c.department.replace("_", " "), c.priority_score, c.priority_label,
            c.status, c.city or "", c.state or "", c.locality or "",
            c.latitude or "", c.longitude or "",
            c.duplicate_of or "",
            "Yes" if c.attachments else "No",
            c.created_at.strftime("%Y-%m-%d %H:%M") if c.created_at else "",
            c.updated_at.strftime("%Y-%m-%d %H:%M") if c.updated_at else "",
        ])

    output.seek(0)
    filename = f"grievance_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.post("/seed", tags=["Dev"])
def seed(db: Session = Depends(get_db)):
    """Populate the DB with realistic Indian-context sample complaints."""
    created = 0
    for text, dept, lat, lng, city, state in SEED_COMPLAINTS:
        normalized, lang = ai.normalize(text)
        # use stored dept (ground truth) for seed, but still score priority
        score, label = ai.score_priority(normalized, dept)
        c = Complaint(
            citizen_name="Seed Citizen",
            phone="9000000000",
            original_text=text,
            normalized_text=normalized,
            language_detected=lang,
            department=dept,
            priority_score=score,
            priority_label=label,
            latitude=lat,
            longitude=lng,
            city=city,
            state=state,
            locality=city,
            status="Submitted",
        )
        db.add(c)
        created += 1
    db.commit()
    _recompute_clusters(db)
    return {"seeded": created}


# --------------------------------------------------------------------------- #
def _recompute_clusters(db: Session):
    """Re-cluster all complaints and persist duplicate_group ids."""
    all_c = db.query(Complaint).order_by(Complaint.created_at.asc()).all()
    if not all_c:
        return
    texts = [c.normalized_text for c in all_c]
    labels = ai.cluster_complaints(texts)
    for c, label in zip(all_c, labels):
        c.duplicate_group = int(label)
    db.commit()
