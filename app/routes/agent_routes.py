from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import Dict
from pydantic import BaseModel
from .. import models
from ..auth import get_current_hiring_manager, get_current_user
from ..database import get_db
from ..ai.cv_analysis import process_application_with_ai
from ..ai.email_agent import generate_email_draft

router = APIRouter(prefix="/ai", tags=["ai"])

class ProcessApplicationRequest(BaseModel):
    application_id: int

class EmailDraftRequest(BaseModel):
    application_id: int
    email_type: str  # "rejection", "shortlist", "interview"

@router.post("/analyze-application")
def analyze_application(
    request: ProcessApplicationRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_hiring_manager),
):
    """
    Trigger AI analysis on a specific application
    """
    # Verify the application belongs to one of manager's jobs
    app = db.get(models.Application, request.application_id)
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
    
    job = db.get(models.Job, app.job_id)
    if job.hiring_manager_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Process in background
    background_tasks.add_task(process_application_with_ai, request.application_id, db)
    
    return {"message": "AI analysis started", "application_id": request.application_id}

@router.post("/generate-email")
def create_email_draft(
    request: EmailDraftRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_hiring_manager),
):
    """
    Generate email draft for an application
    """
    # Verify authorization
    app = db.get(models.Application, request.application_id)
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
    
    job = db.get(models.Job, app.job_id)
    if job.hiring_manager_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Generate draft
    result = generate_email_draft(
        request.application_id,
        request.email_type,
        db,
        current_user.id
    )
    
    if "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])
    
    return result

@router.get("/application/{application_id}/analysis")
def get_application_analysis(
    application_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_hiring_manager),
):
    """
    Get AI analysis results for an application
    """
    app = db.get(models.Application, application_id)
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
    
    job = db.get(models.Job, app.job_id)
    if job.hiring_manager_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    if not app.ai_processed:
        return {"message": "Not yet analyzed by AI", "processed": False}
    
    import json
    skills = json.loads(app.skills_extracted) if app.skills_extracted else []
    
    return {
        "processed": True,
        "score": app.ai_score,
        "summary": app.ai_summary,
        "recommendation": app.ai_recommendation,
        "reasoning": app.ai_reasoning,
        "skills": skills,
        "processed_at": app.ai_processed_at
    }

@router.get("/application/{application_id}/email-drafts")
def get_email_drafts(
    application_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_hiring_manager),
):
    """
    Get all email drafts for an application
    """
    app = db.get(models.Application, application_id)
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
    
    job = db.get(models.Job, app.job_id)
    if job.hiring_manager_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    drafts = db.query(models.EmailDraft).filter(
        models.EmailDraft.application_id == application_id
    ).order_by(models.EmailDraft.created_at.desc()).all()
    
    return [{
        "id": d.id,
        "draft_type": d.draft_type,
        "subject": d.subject,
        "body": d.body,
        "sent": d.sent,
        "created_at": d.created_at
    } for d in drafts]
