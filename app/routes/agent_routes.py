from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import Dict
from pydantic import BaseModel
from .. import models
from ..auth import get_current_hiring_manager
from ..database import get_db
from ..ai.cv_analysis import process_application_with_ai
from ..ai.email_agent import generate_and_send_email  # UPDATED: Changed import name

router = APIRouter(prefix="/ai", tags=["ai"])

class ProcessApplicationRequest(BaseModel):
    application_id: int

class EmailDraftRequest(BaseModel):
    application_id: int
    email_type: str
    send_immediately: bool = True  # NEW

@router.post("/analyze-application")
def analyze_application(
    request: ProcessApplicationRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_hiring_manager),
):
    app = db.get(models.Application, request.application_id)
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
    
    job = db.get(models.Job, app.job_id)
    if job.hiring_manager_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    background_tasks.add_task(process_application_with_ai, request.application_id, db)
    
    return {"message": "AI analysis started", "application_id": request.application_id}

@router.post("/generate-email")
def create_and_send_email(  # Function can keep same name
    request: EmailDraftRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_hiring_manager),
):
    """
    Generate and send email to candidate
    """
    app = db.get(models.Application, request.application_id)
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
    
    job = db.get(models.Job, app.job_id)
    if job.hiring_manager_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # UPDATED: Call the new function
    result = generate_and_send_email(
        request.application_id,
        request.email_type,
        db,
        current_user.id,
        send_immediately=request.send_immediately
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
