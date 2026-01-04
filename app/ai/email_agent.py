import openai
from sqlalchemy.orm import Session
from typing import Dict
from ..config import Settings
from .. import models

settings = Settings()
openai.api_key = settings.openai_api_key

def generate_email_draft(
    application_id: int,
    email_type: str,
    db: Session,
    hiring_manager_id: int
) -> Dict[str, str]:
    """
    Generate email drafts for different scenarios
    email_type: "rejection", "shortlist", "interview"
    """
    
    # Get application and related data
    app = db.get(models.Application, application_id)
    if not app:
        return {"error": "Application not found"}
    
    applicant = db.get(models.User, app.applicant_id)
    job = db.get(models.Job, app.job_id)
    manager = db.get(models.User, hiring_manager_id)
    
    # Prepare context
    context = {
        "applicant_name": applicant.full_name,
        "job_title": job.title,
        "company_name": "HireChat",
        "manager_name": manager.full_name if manager else "Hiring Team",
        "ai_score": app.ai_score,
        "ai_summary": app.ai_summary,
        "ai_reasoning": app.ai_reasoning
    }
    
    # Different prompts for different email types
    prompts = {
        "rejection": f"""Write a professional, empathetic rejection email for a job candidate.

Candidate: {context['applicant_name']}
Position: {context['job_title']}
Company: {context['company_name']}

The candidate scored {context['ai_score']}/100 in our AI screening. Reason: {context['ai_reasoning']}

Write a kind, constructive email that:
- Thanks them for applying
- Explains we've moved forward with other candidates
- Encourages them to apply for future roles
- Is warm and professional

Format: Provide subject line and body separately.""",

        "shortlist": f"""Write a professional email inviting a candidate to the next stage.

Candidate: {context['applicant_name']}
Position: {context['job_title']}
Company: {context['company_name']}

The candidate scored {context['ai_score']}/100. Summary: {context['ai_summary']}

Write an email that:
- Congratulates them on being shortlisted
- Explains next steps
- Asks for their availability for an interview
- Is professional and enthusiastic

Format: Provide subject line and body separately.""",

        "interview": f"""Write a professional interview invitation email.

Candidate: {context['applicant_name']}
Position: {context['job_title']}
Company: {context['company_name']}

Write an email that:
- Confirms interview invitation
- Provides interview format details
- Asks them to confirm attendance
- Is clear and professional

Format: Provide subject line and body separately."""
    }
    
    prompt = prompts.get(email_type, prompts["shortlist"])
    
    try:
        response = openai.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {"role": "system", "content": "You are an expert HR professional writing recruiting emails."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7
        )
        
        content = response.choices[0].message.content
        
        # Parse subject and body
        lines = content.split('\n')
        subject = ""
        body = ""
        
        for i, line in enumerate(lines):
            if "subject:" in line.lower():
                subject = line.split(':', 1)[1].strip()
            elif subject and line.strip():
                body = '\n'.join(lines[i:]).strip()
                break
        
        if not subject:
            subject = f"Update on your application for {job.title}"
        if not body:
            body = content
        
        # Save draft to database
        draft = models.EmailDraft(
            application_id=application_id,
            draft_type=email_type,
            subject=subject,
            body=body,
            created_by=hiring_manager_id
        )
        db.add(draft)
        db.commit()
        db.refresh(draft)
        
        return {
            "draft_id": draft.id,
            "subject": subject,
            "body": body,
            "email_type": email_type
        }
        
    except Exception as e:
        print(f"Error generating email: {e}")
        return {
            "error": f"Failed to generate email: {str(e)}"
        }
