"""
SQLAlchemy models for the grievance platform.
"""
import hashlib
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, Text, Float, DateTime, ForeignKey
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

from app.config import DB_URL

engine = create_engine(DB_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(Text, unique=True, nullable=False, index=True)
    email = Column(Text, unique=True, nullable=False)
    password_hash = Column(Text, nullable=False)
    full_name = Column(Text, nullable=False)
    role = Column(Text, default="citizen")  # "citizen" or "admin"
    phone = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    def verify_password(self, password: str) -> bool:
        return _hash_password(password) == self.password_hash

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "full_name": self.full_name,
            "role": self.role,
            "phone": self.phone,
        }


class Complaint(Base):
    __tablename__ = "complaints"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # link to submitter

    citizen_name = Column(Text, nullable=False)
    phone = Column(Text, nullable=True)
    original_text = Column(Text, nullable=False)
    normalized_text = Column(Text, nullable=False)
    language_detected = Column(Text, default="en")

    department = Column(Text, nullable=False)
    priority_score = Column(Integer, default=0)
    priority_label = Column(Text, default="Low")

    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    city = Column(Text, nullable=True)
    state = Column(Text, nullable=True)
    locality = Column(Text, nullable=True)

    status = Column(Text, default="Submitted")
    duplicate_group = Column(Integer, nullable=True)
    duplicate_of = Column(Integer, ForeignKey("complaints.id"), nullable=True)

    # File attachments — JSON string of list of {"filename", "type", "url"}
    attachments = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    parent = relationship("Complaint", remote_side=[id], backref="duplicates")


class Message(Base):
    """Admin-to-citizen messages on a specific complaint."""
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    complaint_id = Column(Integer, ForeignKey("complaints.id"), nullable=False, index=True)
    sender_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    sender_role = Column(Text, nullable=False)  # "admin" or "citizen"
    sender_name = Column(Text, nullable=False)
    text = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


def init_db():
    Base.metadata.create_all(bind=engine)

    # Create default admin user if not exists
    db = SessionLocal()
    try:
        admin = db.query(User).filter(User.username == "admin").first()
        if not admin:
            admin = User(
                username="admin",
                email="admin@grievance.gov.in",
                password_hash=_hash_password("admin123"),
                full_name="System Administrator",
                role="admin",
                phone="9000000000",
            )
            db.add(admin)
            db.commit()
            print("[DB] Default admin created — username: admin, password: admin123")
    finally:
        db.close()
