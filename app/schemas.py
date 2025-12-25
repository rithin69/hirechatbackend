from typing import List, Optional
from pydantic import BaseModel, EmailStr
from datetime import datetime
from enum import Enum

class UserRole(str, Enum):
    APPLICANT = "applicant"
    HIRING_MANAGER = "hiring_manager"

class UserBase(BaseModel):
    email: EmailStr
    full_name: str

class UserCreate(UserBase):
    password: str
    role: UserRole  # ← THIS WAS MISSING

class UserOut(UserBase):
    id: int
    role: UserRole
    is_active: bool

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

# Job Schemas
class JobBase(BaseModel):
    title: str
    description: str
    location: str
    salary_min: float
    salary_max: float

class JobCreate(JobBase):
    pass

class JobOut(JobBase):
    id: int
    status: str
    hiring_manager_id: int
    created_at: datetime

    class Config:
        from_attributes = True

# Application Schemas
class ApplicationBase(BaseModel):
    job_id: int
    cover_letter: str

class ApplicationCreate(ApplicationBase):
    pass

class ApplicationOut(ApplicationBase):
    id: int
    applicant_id: int
    cv_filename: str
    status: str = "pending"
    created_at: datetime

    class Config:
        from_attributes = True

# Message Schemas
class MessageBase(BaseModel):
    content: str

class MessageCreate(MessageBase):
    pass

class MessageOut(MessageBase):
    id: int
    application_id: int
    sender_id: int
    created_at: datetime

    class Config:
        from_attributes = True
