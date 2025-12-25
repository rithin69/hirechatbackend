from functools import lru_cache
from pydantic_settings import BaseSettings
import os





class Settings(BaseSettings):
    app_name: str = "Kodamai Recruitr"
    backend_cors_origins: list[str] = ["http://localhost:5173"]

    # SQLite for now; you can swap to Postgres later
    database_url: str = "sqlite:///./recruitr.db"

    jwt_secret_key: str = "change_this_to_a_long_random_secret"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

     # Email settings
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = "rithinmenezes007@gmail.com"
    smtp_password: str  ="wjscfndisbqodopn"
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")

    class Config:
        env_file = ".env"




   
