import openai
from sqlalchemy.orm import Session
from typing import Dict, Any
import json
import PyPDF2
import io
from ..config import Settings
from .. import models
from datetime import datetime 

settings = Settings()
openai.api_key = settings.openai_api_key

def extract_text_from_pdf(cv_content: bytes) -> str:
    """Extract text from PDF CV"""
    try:
        pdf_reader = PyPDF2.PdfReader(io.BytesIO(cv_content))
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text()
        return text
    except Exception as e:
        print(f"Error extracting PDF text: {e}")
        return ""

def analyze_cv_with_ai(cv_text: str, job_description: str, job_title: str) -> Dict[str, Any]:
    """
    Use OpenAI to analyze CV against job requirements
    Returns: score, summary, recommendation, reasoning, skills
    """
    
    prompt = f"""You are an expert recruiter analyzing a CV for a job position.

**Job Title:** {job_title}

**Job Description:**
{job_description}

**Candidate's CV:**
{cv_text}

Please analyze this CV and provide:
1. A match score (0-100) based on how well the candidate fits the role
2. A brief summary (2-3 sentences) of the candidate's key qualifications
3. A recommendation: "shortlist", "review", or "reject"
4. Reasoning for your recommendation (2-3 sentences)
5. List of key skills extracted from the CV

Respond in JSON format:
{{
  "score": 85,
  "summary": "...",
  "recommendation": "shortlist",
  "reasoning": "...",
  "skills": ["JavaScript", "React", "Node.js", "AWS"]
}}
"""

    try:
        response = openai.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {"role": "system", "content": "You are an expert recruiter and HR professional."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            response_format={"type": "json_object"}
        )
        
        result = json.loads(response.choices[0].message.content)
        return result
        
    except Exception as e:
        print(f"Error in CV analysis: {e}")
        return {
            "score": 50,
            "summary": "Unable to analyze CV automatically. Manual review required.",
            "recommendation": "review",
            "reasoning": f"Error during AI analysis: {str(e)}",
            "skills": []
        }

def process_application_with_ai(application_id: int, db: Session) -> Dict[str, Any]:
    """
    Main function to process an application with AI
    """
    # Get application details
    app = db.get(models.Application, application_id)
    if not app:
        return {"error": "Application not found"}
    
    # Get job details
    job = db.get(models.Job, app.job_id)
    if not job:
        return {"error": "Job not found"}
    
    # Extract text from CV
    cv_text = extract_text_from_pdf(app.cv_content)
    if not cv_text:
        cv_text = "Unable to extract text from CV"
    
    # Analyze with AI
    analysis = analyze_cv_with_ai(cv_text, job.description, job.title)
    
    # Update application with AI results
    app.cv_parsed_text = cv_text
    app.ai_score = analysis.get("score", 50)
    app.ai_summary = analysis.get("summary", "")
    app.ai_recommendation = analysis.get("recommendation", "review")
    app.ai_reasoning = analysis.get("reasoning", "")
    app.skills_extracted = json.dumps(analysis.get("skills", []))
    app.ai_processed = True
    app.ai_processed_at = datetime.now()
    
    # Auto-update status based on recommendation
    if analysis.get("recommendation") == "shortlist" and analysis.get("score", 0) >= 80:
        app.status = "shortlisted"
    elif analysis.get("recommendation") == "reject" and analysis.get("score", 0) < 40:
        app.status = "rejected"
    else:
        app.status = "reviewing"
    
    db.commit()
    db.refresh(app)
    
    return {
        "application_id": application_id,
        "score": app.ai_score,
        "recommendation": app.ai_recommendation,
        "status": app.status,
        "summary": app.ai_summary
    }
