from sqlalchemy.orm import Session
from sqlalchemy import func, distinct
from ..database import SessionLocal
from .. import models
from datetime import datetime, timedelta

def query_database_with_ai(question: str, hiring_manager_id: int) -> str:
  
    db = SessionLocal()
    try:
        q = question.lower().strip()
        
        if any(word in q for word in ["show", "list", "all"]) and "job" in q:
            jobs = db.query(models.Job).filter(
                models.Job.hiring_manager_id == hiring_manager_id
            ).all()
            
            if not jobs:
                return "You haven't created any jobs yet."
            
            open_jobs = [j for j in jobs if j.status == "open"]
            closed_jobs = [j for j in jobs if j.status == "closed"]
            
            if "open" in q:
                if not open_jobs:
                    return "You have no open jobs."
                result = f"Found {len(open_jobs)} open job(s):\n\n"
                for job in open_jobs:
                    result += f"• **{job.title}** - {job.location or 'No location'} | £{job.salary_min}-£{job.salary_max}\n"
                return result
            
            if "closed" in q:
                if not closed_jobs:
                    return "You have no closed jobs."
                result = f"Found {len(closed_jobs)} closed job(s):\n\n"
                for job in closed_jobs:
                    result += f"• **{job.title}** - {job.location or 'No location'} | £{job.salary_min}-£{job.salary_max}\n"
                return result
            
            result = f"You have {len(jobs)} total job(s) ({len(open_jobs)} open, {len(closed_jobs)} closed):\n\n"
            for job in jobs:
                status_tag = "✅ Open" if job.status == "open" else "🔒 Closed"
                result += f"• **{job.title}** [{status_tag}] - {job.location or 'No location'} | £{job.salary_min}-£{job.salary_max}\n"
            return result
        
        if "how many" in q and "application" in q:
            job_ids = [j.id for j in db.query(models.Job).filter(
                models.Job.hiring_manager_id == hiring_manager_id
            ).all()]
            
            if not job_ids:
                return "You haven't created any jobs yet, so there are no applications."
            
            count = db.query(models.Application).filter(
                models.Application.job_id.in_(job_ids)
            ).count()
            
            return f"You have {count} total application(s) across all your jobs."
        
        if ("applicant" in q or "application" in q) and "for" in q:
            parts = q.split("for")
            if len(parts) > 1:
                job_title = parts[1].strip().rstrip("?").strip()
                
                jobs = db.query(models.Job).filter(
                    models.Job.hiring_manager_id == hiring_manager_id,
                    models.Job.title.ilike(f"%{job_title}%")
                ).all()
                
                if not jobs:
                    return f"You don't have a job matching '{job_title}'"
                
                job = jobs[0]
                apps = db.query(models.Application).filter(
                    models.Application.job_id == job.id
                ).all()
                
                if not apps:
                    return f"No applications yet for **{job.title}**"
                
                result = f"Found {len(apps)} application(s) for **{job.title}**:\n\n"
                for app in apps:
                    applicant = db.query(models.User).filter(
                        models.User.id == app.applicant_id
                    ).first()
                    result += f"• **{applicant.full_name}** ({applicant.email if applicant else 'Unknown'})\n"
                    result += f"  Status: {app.status}\n"
                    result += f"  CV: {app.cv_filename or 'No CV'}\n\n"
                return result
        
        if "most" in q and ("applicant" in q or "application" in q):
            job_ids = [j.id for j in db.query(models.Job).filter(
                models.Job.hiring_manager_id == hiring_manager_id
            ).all()]
            
            if not job_ids:
                return "You haven't created any jobs yet."
            
            result = db.query(
                models.Job.title,
                func.count(models.Application.id).label('count')
            ).join(models.Application).filter(
                models.Job.id.in_(job_ids)
            ).group_by(models.Job.id).order_by(
                func.count(models.Application.id).desc()
            ).first()
            
            if result:
                return f"**{result[0]}** has the most applicants with {result[1]} application(s)."
            return "No applications yet on any of your jobs."
        
        if "recent" in q or "last week" in q or "new" in q:
            week_ago = datetime.now() - timedelta(days=7)
            jobs = db.query(models.Job).filter(
                models.Job.hiring_manager_id == hiring_manager_id,
                models.Job.created_at >= week_ago
            ).all()
            
            if not jobs:
                return "You haven't created any jobs in the last week."
            
            result = f"You created {len(jobs)} job(s) in the last week:\n\n"
            for job in jobs:
                result += f"• **{job.title}** - Created {job.created_at.strftime('%Y-%m-%d')}\n"
            return result
        
        if "highest" in q and "salary" in q:
            job = db.query(models.Job).filter(
                models.Job.hiring_manager_id == hiring_manager_id
            ).order_by(
                models.Job.salary_max.desc()
            ).first()
            
            if job:
                return f"**{job.title}** has your highest salary at £{job.salary_min}-£{job.salary_max}"
            return "You haven't created any jobs yet."
        
        return (
            "I can help you with:\n"
            "• 'Show me all my open jobs'\n"
            "• 'Show me closed jobs'\n"
            "• 'List applicants for [job title]'\n"
            "• 'How many applications do I have?'\n"
            "• 'Which job has the most applicants?'\n"
            "• 'Show me recent jobs'\n"
            "• 'Which job has the highest salary?'"
        )
        
    finally:
        db.close()
