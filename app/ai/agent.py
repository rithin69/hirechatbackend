import openai
from sqlalchemy.orm import Session
from sqlalchemy import func
from ..database import SessionLocal
from .. import models
from ..config import Settings

settings = Settings()
openai.api_key = settings.openai_api_key

def get_database_context(hiring_manager_id: int, db: Session) -> str:
    """Gather relevant database context for the AI agent"""
    
    # Get all jobs for this manager
    jobs = db.query(models.Job).filter(
        models.Job.hiring_manager_id == hiring_manager_id
    ).all()
    
    job_ids = [j.id for j in jobs]
    
    # Get all applications
    applications = db.query(models.Application).filter(
        models.Application.job_id.in_(job_ids)
    ).all() if job_ids else []
    
    # Build context string
    context = f"Total jobs: {len(jobs)}\n"
    context += f"Open jobs: {len([j for j in jobs if j.status == 'open'])}\n"
    context += f"Closed jobs: {len([j for j in jobs if j.status == 'closed'])}\n"
    context += f"Total applications: {len(applications)}\n\n"
    
    context += "Jobs:\n"
    for job in jobs:
        app_count = len([a for a in applications if a.job_id == job.id])
        context += f"- {job.title} [{job.status}] - {job.location} | £{job.salary_min}-{job.salary_max} | {app_count} applications\n"
    
    context += "\nApplications:\n"
    for app in applications[:20]:  # Limit to recent 20
        applicant = db.get(models.User, app.applicant_id)
        job = db.get(models.Job, app.job_id)
        context += f"- {applicant.full_name if applicant else 'Unknown'} applied to {job.title if job else 'Unknown'} "
        context += f"[Status: {app.status}]"
        if app.ai_score:
            context += f" [AI Score: {app.ai_score}/100]"
        context += "\n"
    
    return context

def query_database_with_ai(question: str, hiring_manager_id: int) -> str:
    """
    Enhanced AI agent using OpenAI GPT to answer questions about jobs and applications
    """
    db = SessionLocal()
    
    try:
        # Get database context
        db_context = get_database_context(hiring_manager_id, db)
        
        # Create prompt
        system_prompt = """You are an AI recruitment assistant helping a hiring manager. 
You have access to their job postings and applications data. 
Answer their questions clearly and helpfully based on the provided data.
If you don't have enough information, say so politely."""

        user_prompt = f"""Here's the current data:

{db_context}

Question: {question}

Please provide a clear, helpful answer."""

        # Call OpenAI
        response = openai.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.5,
            max_tokens=500
        )
        
        answer = response.choices[0].message.content
        return answer
        
    except Exception as e:
        print(f"Error in AI query: {e}")
        return f"I encountered an error processing your question: {str(e)}\n\nPlease try rephrasing or contact support."
        
    finally:
        db.close()
