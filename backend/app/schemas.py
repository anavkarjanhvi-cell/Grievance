"""
Pydantic schemas for request/response validation.
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


# --------------------------------------------------------------------------- #
# Auth
# --------------------------------------------------------------------------- #
class UserRegister(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: str = Field(..., max_length=120)
    password: str = Field(..., min_length=6, max_length=100)
    full_name: str = Field(..., min_length=2, max_length=120)
    phone: Optional[str] = None
    role: str = Field(default="citizen", pattern="^(citizen|admin)$")


class UserLogin(BaseModel):
    username: str
    password: str


class UserOut(BaseModel):
    id: int
    username: str
    email: str
    full_name: str
    role: str
    phone: Optional[str]

    class Config:
        from_attributes = True


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# --------------------------------------------------------------------------- #
# Complaints
# --------------------------------------------------------------------------- #
class ComplaintCreate(BaseModel):
    citizen_name: str = Field(..., min_length=2, max_length=120)
    phone: Optional[str] = None
    text: str = Field(..., min_length=10, max_length=5000)
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    city: Optional[str] = None
    state: Optional[str] = None
    locality: Optional[str] = None
    attachments: Optional[list[dict]] = None  # list of {"filename", "type", "url"}


class ComplaintOut(BaseModel):
    id: int
    user_id: Optional[int]
    citizen_name: str
    phone: Optional[str]
    original_text: str
    normalized_text: str
    language_detected: str
    department: str
    priority_score: int
    priority_label: str
    latitude: Optional[float]
    longitude: Optional[float]
    city: Optional[str]
    state: Optional[str]
    locality: Optional[str]
    status: str
    duplicate_group: Optional[int]
    duplicate_of: Optional[int]
    attachments: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class StatusUpdate(BaseModel):
    status: str
