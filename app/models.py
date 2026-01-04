from sqlalchemy import (
    Column,
    Integer,
    String,
    ForeignKey,
    DateTime,
    Text,
    LargeBinary,
    Enum,
    Float,  # NEW
    Boolean,  # NEW
)
from sqlalchemy.sql import func
from enum import Enum as PyEnum
from .database import Base

class UserRole(str, PyEnum):
    APPLICANT = "applicant"
    HIRING_MANAGER = "hiring_manager"

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    full_name = Column(String, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(Enum(UserRole), default=UserRole.APPLICANT, nullable=False)
    is_active = Column(Integer, default=1, nullable=False)

class Job(Base):
    __tablename__ = "jobs"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    location = Column(String, nullable=False)
    salary_min = Column(Integer, nullable=False)
    salary_max = Column(Integer, nullable=False)
    status = Column(String, default="open")
    hiring_manager_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Application(Base):
    __tablename__ = "applications"
    
    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False)
    applicant_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    cover_letter = Column(Text, nullable=False)
    cv_filename = Column(String, nullable=False)
    cv_content = Column(LargeBinary)
    status = Column(String, default="pending")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # NEW: AI Analysis Fields
    cv_parsed_text = Column(Text, nullable=True)  # Extracted text from CV
    ai_score = Column(Float, nullable=True)  # 0-100 score
    ai_summary = Column(Text, nullable=True)  # AI-generated summary
    ai_recommendation = Column(String, nullable=True)  # "shortlist", "review", "reject"
    ai_reasoning = Column(Text, nullable=True)  # Why the recommendation
    skills_extracted = Column(Text, nullable=True)  # JSON string of skills
    ai_processed = Column(Boolean, default=False)  # Has AI analyzed this?
    ai_processed_at = Column(DateTime(timezone=True), nullable=True)

class Message(Base):
    __tablename__ = "messages"
    
    id = Column(Integer, primary_key=True, index=True)
    application_id = Column(Integer, ForeignKey("applications.id"), nullable=False)
    sender_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

# NEW: Email Draft Storage
class EmailDraft(Base):
    __tablename__ = "email_drafts"
    
    id = Column(Integer, primary_key=True, index=True)
    application_id = Column(Integer, ForeignKey("applications.id"), nullable=False)
    draft_type = Column(String, nullable=False)  # "rejection", "shortlist", "interview"
    subject = Column(String, nullable=False)
    body = Column(Text, nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    sent = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
