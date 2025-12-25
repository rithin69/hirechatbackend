from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import engine, Base
from . import models  # registers models with this Base
from .routes import auth_routes, job_routes, application_routes, chat_routes

# Create all tables once, on import
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Kodamai Job Portal")

origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
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

@app.get("/")
def root():
    return {"message": "Kodamai Job Portal API ✅"}
