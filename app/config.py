from functools import lru_cache
from pydantic_settings import BaseSettings
import os


class Settings(BaseSettings):
    app_name: str = "Kodamai Recruitr"
    backend_cors_origins: list[str] = [
        "http://localhost:5173",
        "https://hirechat-fza5e9g0b0bne7ek.ukwest-01.azurewebsites.net"
    ]

    # ✅ Use persistent storage on Azure
    database_url: str = os.getenv(
        "DATABASE_URL",
        "sqlite:////home/site/data/recruitr.db"  # 4 slashes for absolute path
    )

    jwt_secret_key: str = os.getenv("JWT_SECRET_KEY", "change_this_to_a_long_random_secret")
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    smtp_host: str = os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_port: int = int(os.getenv("SMTP_PORT", "587"))
    smtp_user: str = os.getenv("SMTP_USER", "rithinmenezes007@gmail.com")
    smtp_password: str = os.getenv("SMTP_PASSWORD", "wjscfndisbqodopn")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")

    class Config:
        env_file = ".env"


@lru_cache()
def get_settings():
    return Settings()


settings = get_settings()
