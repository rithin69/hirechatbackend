import smtplib
from email.message import EmailMessage
from ..config import settings
import logging

logger = logging.getLogger(__name__)

def send_email(to_email: str, to_name: str, subject: str, body: str) -> dict:
    """
    Send email using SMTP (Gmail)
    """
    try:
        logger.info(f"Sending email to {to_email} with subject: {subject}")
        
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = settings.smtp_user
        msg["To"] = to_email
        
        # Format body with greeting and signature
        formatted_body = f"Hi {to_name},\n\n{body}\n\nBest regards,\nHireChat Team"
        
        msg.set_content(formatted_body, subtype="plain", charset="utf-8")
        
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
            server.starttls()
            server.login(settings.smtp_user, settings.smtp_password)
            server.send_message(msg)
        
        logger.info(f"Email sent successfully to {to_email}")
        
        return {
            "success": True,
            "message": "Email sent successfully"
        }
        
    except Exception as e:
        logger.error(f"Error sending email: {e}")
        return {
            "success": False,
            "error": str(e)
        }
