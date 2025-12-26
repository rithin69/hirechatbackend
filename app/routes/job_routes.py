from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import or_

from .. import models, schemas
from ..auth import get_current_hiring_manager, get_current_user
from ..database import get_db

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("", response_model=List[schemas.JobOut])
def list_jobs(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    if current_user.role == "hiring_manager":
        return db.query(models.Job).filter(
            models.Job.hiring_manager_id == current_user.id
        ).order_by(models.Job.created_at.desc()).all()
    else:
        return db.query(models.Job).filter(
            models.Job.status == "open"
        ).order_by(models.Job.created_at.desc()).all()


@router.post("", response_model=schemas.JobOut, status_code=status.HTTP_201_CREATED)
def create_job(
    job_in: schemas.JobCreate,
    db: Session = Depends(get_db),
    hiring_manager: models.User = Depends(get_current_hiring_manager),
):
    db_job = models.Job(**job_in.dict(), hiring_manager_id=hiring_manager.id)
    db.add(db_job)
    db.commit()
    db.refresh(db_job)
    return db_job


@router.get("/{job_id}", response_model=schemas.JobOut)
def get_job(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    job = db.get(models.Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if current_user.role == "hiring_manager" and job.hiring_manager_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to view this job")
    
    return job


@router.patch("/{job_id}/close", response_model=schemas.JobOut)
def close_job(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_hiring_manager),
):
    job = db.get(models.Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job.hiring_manager_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to close this job")
    
    job.status = "closed"
    db.commit()
    db.refresh(job)
    return job


@router.get("/{job_id}/applications")
def get_job_applications(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Get all applications for a specific job (hiring managers only)"""
    if current_user.role != models.UserRole.HIRING_MANAGER:
        raise HTTPException(status_code=403, detail="Only hiring managers can view applications")
    
    job = db.get(models.Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job.hiring_manager_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to view applications for this job")
    
    applications = (
        db.query(models.Application)
        .filter(models.Application.job_id == job_id)
        .all()
    )
    
    result = []
    for app in applications:
        applicant = db.get(models.User, app.applicant_id)
        result.append({
            "id": app.id,
            "applicant_name": applicant.full_name if applicant else "Unknown",
            "applicant_email": applicant.email if applicant else "Unknown",
            "cover_letter": app.cover_letter,
            "cv_filename": app.cv_filename,
            "status": app.status,
            "created_at": app.created_at,
        })
    
    return result
