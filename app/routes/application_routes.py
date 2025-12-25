from typing import List
import smtplib
from email.message import EmailMessage

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
    UploadFile,
    File,
    Form,
)
from sqlalchemy.orm import Session

from .. import models, schemas
from ..auth import get_current_user
from ..database import get_db
from ..config import Settings

router = APIRouter(prefix="/applications", tags=["applications"])

settings = Settings()


def send_application_email(to_email: str, job_title: str, application_id: int) -> None:
    msg = EmailMessage()
    msg["Subject"] = f"Application received for {job_title}"
    msg["From"] = settings.smtp_user
    msg["To"] = to_email

    body = (
        f"Hi,\n\n"
        f"Your application (ID: {application_id}) for the role \"{job_title}\" has been received.\n"
        f"We will review your application and get back to you.\n\n"
        f"Thanks,\n"
        f"Kodamai Recruitr\n"
    )

    msg.set_content(body, subtype="plain", charset="utf-8")
    msg.replace_header("Subject", str(msg["Subject"]))

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
        server.starttls()
        server.login(settings.smtp_user, settings.smtp_password)
        server.send_message(msg)


@router.post("", status_code=status.HTTP_201_CREATED)
def create_application(
    job_id: int = Form(...),
    cover_letter: str = Form(...),
    cv: UploadFile = File(...),
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


@router.get("/my-applications", response_model=List[schemas.ApplicationOut])
def list_my_applications(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    return (
        db.query(models.Application)
        .filter(models.Application.applicant_id == current_user.id)
        .all()
    )



