from typing import List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from openai import OpenAI
import os

from .. import models
from ..auth import get_current_user
from ..database import get_db
from ..ai.agent import query_database_with_ai
from ..config import Settings

router = APIRouter(prefix="/chat", tags=["chat"])
settings = Settings()


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatQuery(BaseModel):
    query: str
    history: List[ChatMessage] = []


class ChatAnswer(BaseModel):
    answer: str


@router.post("/query", response_model=ChatAnswer)
def chat_query(
    payload: ChatQuery,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Manager recruitment assistant endpoint"""
    if current_user.role != "hiring_manager":
        return ChatAnswer(
            answer="Only hiring managers can use the recruitment assistant."
        )
    
    answer = query_database_with_ai(payload.query, current_user.id)
    
    return ChatAnswer(answer=answer)


@router.post("/applicant-query", response_model=ChatAnswer)
def applicant_chat_query(
    payload: ChatQuery,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Applicant job search assistant endpoint"""
    print(f"[DEBUG] Applicant query received from user: {current_user.email}")
    
    if current_user.role != "applicant":
        return ChatAnswer(
            answer="Only applicants can use the job search assistant."
        )
    
    try:
        # Get all open jobs
        print("[DEBUG] Fetching jobs...")
        jobs = db.query(models.Job).filter(models.Job.status == "open").all()
        print(f"[DEBUG] Found {len(jobs)} jobs")
        
        # Get user's applications
        print("[DEBUG] Fetching applications...")
        applications = (
            db.query(models.Application)
            .filter(models.Application.applicant_id == current_user.id)
            .all()
        )
        print(f"[DEBUG] Found {len(applications)} applications")
        
        # Build context for OpenAI
        jobs_context = "\n".join([
            f"- {job.title} ({job.location}) - £{job.salary_min}-£{job.salary_max} - {job.description[:100]}"
            for job in jobs
        ]) if jobs else "No jobs currently available."
        
        applications_context = "\n".join([
            f"- Job ID {app.job_id}: Status = {app.status}, Applied on {app.created_at.strftime('%Y-%m-%d')}"
            for app in applications
        ]) if applications else "User hasn't applied to any jobs yet."
        
        system_prompt = f"""You are a helpful job search assistant for an applicant named {current_user.full_name}.

Available Jobs:
{jobs_context}

User's Applications:
{applications_context}

Help the user with:
- Finding suitable jobs
- Understanding job details (salary, location, requirements)
- Checking their application status
- Providing career advice
- Answering questions about the application process

Be friendly, concise, and encouraging. If asked about specific jobs, reference them by title and key details."""

        # Build message history
        messages = [{"role": "system", "content": system_prompt}]
        
        # Add conversation history (last 10 messages)
        for msg in payload.history[-10:]:
            messages.append({
                "role": msg.role,
                "content": msg.content
            })
        
        # Add current query
        messages.append({"role": "user", "content": payload.query})
        
        print("[DEBUG] Calling OpenAI...")
        
        # Call OpenAI using settings
        client = OpenAI(api_key=settings.openai_api_key)
        response = client.chat.completions.create(
            model=settings.openai_model,
            messages=messages,
            temperature=0.7,
            max_tokens=500
        )
        
        answer = response.choices[0].message.content
        print(f"[DEBUG] OpenAI response received: {answer[:50]}...")
        
        return ChatAnswer(answer=answer)
        
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        print(f"[ERROR] Full traceback:\n{error_detail}")
        raise HTTPException(
            status_code=500, 
            detail=f"AI assistant error: {str(e)}"
        )
