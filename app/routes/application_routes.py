from typing import List
import smtplib
from email.message import EmailMessage
import io
import logging
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
    UploadFile,
    File,
    Form,
)
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from .. import models, schemas
from ..auth import get_current_user
from ..database import get_db
from ..config import settings  # UPDATED: Use settings directly

router = APIRouter(prefix="/applications", tags=["applications"])
logger = logging.getLogger(__name__)

def send_application_email(to_email: str, job_title: str, application_id: int) -> None:
    """Send application confirmation email"""
    try:
        logger.info(f"Attempting to send email to {to_email} for job: {job_title}")
        
        msg = EmailMessage()
        msg["Subject"] = f"Application received for {job_title}"
        msg["From"] = settings.smtp_user
        msg["To"] = to_email
        
        body = (
            f"Hi,\n\n"
            f"Your application for the role \"{job_title}\" has been received.\n"
            f"We will review your application and get back to you.\n\n"
            f"Thanks,\n"
            f"HireChat Team\n"
        )
        
        msg.set_content(body, subtype="plain", charset="utf-8")
        
        # Send email
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
            logger.info(f"Connecting to SMTP server: {settings.smtp_host}:{settings.smtp_port}")
            server.starttls()
            logger.info(f"Logging in as: {settings.smtp_user}")
            server.login(settings.smtp_user, settings.smtp_password)
            server.send_message(msg)
            logger.info(f"Email sent successfully to {to_email}")
            
    except smtplib.SMTPAuthenticationError as e:
        logger.error(f"SMTP Authentication failed: {e}")
        logger.error(f"Check SMTP_USER and SMTP_PASSWORD environment variables")
        raise
    except smtplib.SMTPException as e:
        logger.error(f"SMTP Error: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error sending email: {e}")
        raise

@router.post("", status_code=status.HTTP_201_CREATED)
def create_application(
    job_id: int = Form(...),
    cover_letter: str = Form(...),
    cv: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Create a new job application"""
    job = db.get(models.Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Read CV content
    cv_content = cv.file.read()
    
    # Create application
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
    
    # Send confirmation email
    try:
        logger.info(f"Sending confirmation email to: {current_user.email}")
        send_application_email(
            to_email=current_user.email,
            job_title=job.title,
            application_id=db_application.id,
        )
    except Exception as e:
        # Log the error but don't fail the application
        logger.error(f"Failed to send application email: {e}")
        logger.error(f"Application created successfully (ID: {db_application.id}) but email failed")
    
    return {
        "id": db_application.id,
        "job_id": db_application.job_id,
        "status": db_application.status,
        "cv_filename": db_application.cv_filename,
    }

@router.get("/my-applications", response_model=List[schemas.ApplicationOut])
def list_my_applications(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """List all applications by current user"""
    return (
        db.query(models.Application)
        .filter(models.Application.applicant_id == current_user.id)
        .all()
    )

@router.get("/{application_id}/cv")
def download_cv(
    application_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Download CV for an application"""
    application = db.get(models.Application, application_id)
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")
    
    job = db.get(models.Job, application.job_id)
    
    # Check authorization
    if (
        current_user.role != models.UserRole.HIRING_MANAGER and
        application.applicant_id != current_user.id
    ):
        raise HTTPException(status_code=403, detail="Not authorized to download this CV")
    
    if not application.cv_content:
        raise HTTPException(status_code=404, detail="No CV uploaded for this application")
    
    return StreamingResponse(
        io.BytesIO(application.cv_content),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{application.cv_filename}"'
        },
    )
