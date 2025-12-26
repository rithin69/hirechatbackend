from typing import List

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from .. import models
from ..auth import get_current_user
from ..database import get_db
from ..ai.agent import query_database_with_ai

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatQuery(BaseModel):
    query: str
    history: List[ChatMessage] = []


class ChatAnswer(BaseModel):
    answer: str


@router.post("/query", response_model=ChatAnswer)
def chat_query(
    payload: ChatQuery,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    
    if current_user.role != "hiring_manager":
        return ChatAnswer(
            answer="Only hiring managers can use the recruitment assistant."
        )
    
    answer = query_database_with_ai(payload.query, current_user.id)  # ✅ FIXED
    
    return ChatAnswer(answer=answer)
