import openai
from sqlalchemy.orm import Session
from typing import Dict
from ..config import settings
from .. import models
from .email_service import send_email  # NEW: Import email service
import logging

logger = logging.getLogger(__name__)
openai.api_key = settings.openai_api_key

def generate_and_send_email(  # RENAMED from generate_email_draft
    application_id: int,
    email_type: str,
    db: Session,
    hiring_manager_id: int,
    send_immediately: bool = True  # NEW parameter
) -> Dict[str, str]:
    """
    Generate email drafts and send them
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
        "ai_score": app.ai_score if app.ai_score else 0,
        "ai_summary": app.ai_summary if app.ai_summary else "No summary available",
        "ai_reasoning": app.ai_reasoning if app.ai_reasoning else "No reasoning available"
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

DO NOT include "Hi [Name]" or "Best regards" - just the main body content.
Format: Line 1: "Subject: [your subject]" then the body.""",

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

DO NOT include "Hi [Name]" or "Best regards" - just the main body content.
Format: Line 1: "Subject: [your subject]" then the body.""",

        "interview": f"""Write a professional interview invitation email.

Candidate: {context['applicant_name']}
Position: {context['job_title']}
Company: {context['company_name']}

Write an email that:
- Confirms interview invitation
- Provides interview format details
- Asks them to confirm attendance
- Is clear and professional

DO NOT include "Hi [Name]" or "Best regards" - just the main body content.
Format: Line 1: "Subject: [your subject]" then the body."""
    }
    
    prompt = prompts.get(email_type, prompts["shortlist"])
    
    try:
        logger.info(f"Generating {email_type} email for application {application_id}")
        
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
                # Body is everything after subject line
                body = '\n'.join(lines[i+1:]).strip()
                break
        
        if not subject:
            subject = f"Update on your application for {job.title}"
        if not body:
            body = content
        
        # Clean up body - remove any leftover greetings/signatures
        body = body.replace("Hi " + context['applicant_name'], "").strip()
        body = body.replace("Dear " + context['applicant_name'], "").strip()
        
        # Save draft to database
        draft = models.EmailDraft(
            application_id=application_id,
            draft_type=email_type,
            subject=subject,
            body=body,
            created_by=hiring_manager_id,
            sent=False  # Will update if sending succeeds
        )
        db.add(draft)
        db.commit()
        db.refresh(draft)
        
        # NEW: Send email if requested
        email_result = {"success": False}
        if send_immediately:
            logger.info(f"Sending email to {applicant.email}")
            email_result = send_email(
                to_email=applicant.email,
                to_name=applicant.full_name,
                subject=subject,
                body=body
            )
            
            # Update draft status if sent successfully
            if email_result.get("success"):
                draft.sent = True
                db.commit()
                logger.info(f"Email sent successfully to {applicant.email}")
        
        return {
            "draft_id": draft.id,
            "subject": subject,
            "body": body,
            "email_type": email_type,
            "email_sent": email_result.get("success", False),  # NEW
            "recipient_email": applicant.email,  # NEW
            "message": "Email sent successfully!" if email_result.get("success") else f"Failed: {email_result.get('error', 'Not sent')}"  # NEW
        }
        
    except Exception as e:
        logger.error(f"Error generating/sending email: {e}")
        return {
            "error": f"Failed to generate/send email: {str(e)}"
        }
