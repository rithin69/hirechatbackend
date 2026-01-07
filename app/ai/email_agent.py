import openai
from sqlalchemy.orm import Session
from typing import Dict
from ..config import settings
from .. import models
from .email_service import send_email
import logging
import re

logger = logging.getLogger(__name__)
openai.api_key = settings.openai_api_key


def generate_and_send_email(
    application_id: int,
    email_type: str,
    db: Session,
    hiring_manager_id: int,
    send_immediately: bool = True,
) -> Dict[str, str]:
    """
    Generate email and send it.
    email_type: "rejection", "shortlist", "interview"
    """

    # Get application and related data
    app = db.get(models.Application, application_id)
    if not app:
        return {"error": "Application not found"}

    applicant = db.get(models.User, app.applicant_id)
    job = db.get(models.Job, app.job_id)
    manager = db.get(models.User, hiring_manager_id)

    if not applicant or not job:
        return {"error": "Applicant or job not found"}

    context = {
        "applicant_name": applicant.full_name,
        "job_title": job.title,
        "company_name": "HireChat",
        "manager_name": manager.full_name if manager else "Hiring Team",
        "ai_score": app.ai_score if app.ai_score else 0,
        "ai_summary": app.ai_summary or "No summary available",
        "ai_reasoning": app.ai_reasoning or "No reasoning available",
    }

    prompts = {
        "rejection": f"""You are an expert HR professional writing a concise, empathetic rejection email.

Candidate: {context['applicant_name']}
Position: {context['job_title']}
Company: {context['company_name']}
AI score: {context['ai_score']}/100
AI reasoning: {context['ai_reasoning']}

Write an email that:
- Thanks them for applying.
- States that we are moving forward with other candidates.
- Encourages them to consider future roles if appropriate.
- Is warm, respectful, and to the point.

Important formatting rules:
- Do NOT start with any greeting (no "Hi", "Hello", "Dear").
- Do NOT include the candidate name in a greeting.
- Do NOT include any closing signature (no names, roles, "Best regards", etc.).
- Do NOT use placeholders like "[insert date and time]" or "[Your Name]" or "[Your Position]".

Output format:
Line 1: Subject: <subject text>
Line 2 onwards: email body only, no greeting and no signature.
""",

        "shortlist": f"""You are an expert HR professional writing a shortlist notification email.

Candidate: {context['applicant_name']}
Position: {context['job_title']}
Company: {context['company_name']}
AI score: {context['ai_score']}/100
AI summary: {context['ai_summary']}

Write an email that:
- Congratulates the candidate on being shortlisted.
- Explains that they are moving to the next stage.
- Asks for their availability for an interview.
- Is professional and positive.

Important formatting rules:
- Do NOT start with any greeting (no "Hi", "Hello", "Dear").
- Do NOT include the candidate name in a greeting.
- Do NOT include any closing signature (no names, roles, "Best regards", etc.).
- Do NOT use placeholders like "[insert date and time]" or "[Your Name]" or "[Your Position]".

Output format:
Line 1: Subject: <subject text>
Line 2 onwards: email body only, no greeting and no signature.
""",

        "interview": f"""You are an expert HR professional writing an interview invitation email.

Candidate: {context['applicant_name']}
Position: {context['job_title']}
Company: {context['company_name']}

Write an email that:
- Clearly invites the candidate to an interview for the role.
- States that the interview will be held virtually and last around one hour.
- Asks them to reply with their availability instead of using a hard-coded date/time.
- Is clear, respectful and professional.

Important formatting rules:
- Do NOT start with any greeting (no "Hi", "Hello", "Dear").
- Do NOT include the candidate name in a greeting.
- Do NOT include any closing signature (no names, roles, "Best regards", etc.).
- Do NOT use placeholders like "[insert date and time]" or similar.
- Do NOT use placeholders like "[Your Name]" or "[Your Position]".

Use neutral wording such as "at a time that works for you" instead of placeholders.

Output format:
Line 1: Subject: <subject text>
Line 2 onwards: email body only, no greeting and no signature.
""",
    }

    prompt = prompts.get(email_type, prompts["shortlist"])

    try:
        logger.info(f"Generating {email_type} email for application {application_id}")

        response = openai.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert HR professional writing concise, professional recruiting emails.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,
        )

        content = response.choices[0].message.content or ""

        # Parse "Subject:" and body
        lines = [l for l in content.split("\n") if l.strip() != ""]
        subject = ""
        body_lines = []

        for i, line in enumerate(lines):
            if line.lower().startswith("subject:"):
                subject = line.split(":", 1)[1].strip()
                body_lines = lines[i + 1 :]
                break

        if not subject:
            subject = f"Update on your application for {job.title}"

        body = "\n".join(body_lines).strip() or content.strip()

        # Hard cleanup of placeholders and stray template bits
        # remove [insert ...], [Your Name], [Your Position], etc.
        body = re.sub(r"\[.*?date.*?\]", "", body, flags=re.IGNORECASE)
        body = re.sub(r"\[.*?time.*?\]", "", body, flags=re.IGNORECASE)
        body = re.sub(r"\[.*?your name.*?\]", "", body, flags=re.IGNORECASE)
        body = re.sub(r"\[.*?your position.*?\]", "", body, flags=re.IGNORECASE)

        # Remove explicit "Hi <name>" / "Dear <name>" if model ignored the rules
        for prefix in ("Hi", "Hello", "Dear"):
            pattern = rf"^{prefix}\s+{re.escape(context['applicant_name'])}[,\s]*"
            body = re.sub(pattern, "", body, flags=re.IGNORECASE).strip()

        # Also trim generic "Hi," / "Hello," / "Dear,"
        body = re.sub(r"^(Hi|Hello|Dear)[,\s]+\n?", "", body, flags=re.IGNORECASE).strip()

        # Collapse multiple blank lines
        body = re.sub(r"\n\s*\n\s*\n+", "\n\n", body).strip()

        # Save draft
        draft = models.EmailDraft(
            application_id=application_id,
            draft_type=email_type,
            subject=subject,
            body=body,
            created_by=hiring_manager_id,
            sent=False,
        )
        db.add(draft)
        db.commit()
        db.refresh(draft)

        email_result: Dict[str, str] = {"success": False}
        if send_immediately:
            logger.info(f"Sending email to {applicant.email}")
            email_result = send_email(
                to_email=applicant.email,
                to_name=applicant.full_name,
                subject=subject,
                body=body,
            )

            if email_result.get("success"):
                draft.sent = True
                db.commit()
                logger.info(f"Email sent successfully to {applicant.email}")

        return {
            "draft_id": draft.id,
            "subject": subject,
            "body": body,
            "email_type": email_type,
            "email_sent": email_result.get("success", False),
            "recipient_email": applicant.email,
            "message": "Email sent successfully!"
            if email_result.get("success")
            else f"Failed: {email_result.get('error', 'Not sent')}",
        }

    except Exception as e:
        logger.error(f"Error generating/sending email: {e}")
        return {"error": f"Failed to generate/send email: {str(e)}"}
