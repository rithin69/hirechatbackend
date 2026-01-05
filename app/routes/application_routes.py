from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks, status
from sqlalchemy.orm import Session
from typing import List

# Import your dependencies
from ..database import get_db
from ..auth import get_current_user
from .. import models
from ..ai.cv_analysis import process_application_with_ai

# Try to import email function - adjust the path based on your actual file
try:
    from ..email_agent import send_application_email
except ImportError:
    # If email_agent doesn't exist, define a placeholder or import from correct location
    def send_application_email(*args, **kwargs):
        pass

# CREATE THE ROUTER
router = APIRouter(prefix="/applications", tags=["applications"])

@router.post("", status_code=status.HTTP_201_CREATED)
def create_application(
    job_id: int = Form(...),
    cover_letter: str = Form(...),
    cv: UploadFile = File(...),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    job = db.get(models.Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    cv_content = cv.file.read()
    
    db_application = models.Application(
        job_id=job_id,
        cover_letter=cover_letter,
        applicant_id=current_user.id,
        cv_filename=cv.filename,
        cv_content=cv_content,
    )
    
    db.add(db_application)
    db.commit()
    db.refresh(db_application)
    
    background_tasks.add_task(process_application_with_ai, db_application.id, db)
    
    try:
        send_application_email(
            to_email=current_user.email,
            job_title=job.title,
            application_id=db_application.id,
        )
    except Exception as e:
        print(f"Error sending email: {e}")
    
    return {
        "id": db_application.id,
        "job_id": db_application.job_id,
        "status": db_application.status,
        "cv_filename": db_application.cv_filename,
    }
