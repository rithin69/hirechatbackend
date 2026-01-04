from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from .database import engine, Base
from . import models
from .routes import auth_routes, job_routes, application_routes, chat_routes
from .routes import agent_routes  # NEW

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("✅ Database tables created/verified successfully")
    except Exception as e:
        logger.warning(f"⚠️ Table creation skipped (likely already exists): {e}")
    
    yield
    logger.info("🛑 Application shutting down")

app = FastAPI(title="Hirechat Job Portal", lifespan=lifespan)

origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "https://hirechat-fza5e9g0b0bne7ek.ukwest-01.azurewebsites.net"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_routes.router)
app.include_router(job_routes.router)
app.include_router(application_routes.router)
app.include_router(chat_routes.router)
app.include_router(agent_routes.router)  # NEW

@app.get("/")
def root():
    return {"message": "Hirechat Job Portal API ✅ with AI Agents 🤖"}
