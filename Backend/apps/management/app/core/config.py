from functools import lru_cache
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


# Get the path to the .env file
env_file = Path(__file__).resolve().parent.parent.parent / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(env_file), extra="ignore")
    
    project_name: str = "Management API"
    database_url: str
    jwt_algorithm: str = "HS256"
    jwt_secret: str
    mail_username: str
    mail_password: str
    mail_from: str
    mail_port: int = 587
    mail_server: str = "smtp.gmail.com"
    mail_from_name: str = "Your App"
    mail_starttls: bool = True
    mail_ssl_tls: bool = False
    use_credentials: bool = True
    validate_certs: bool = True
    reset_password_url: str = "http://localhost:5173/reset-password"


@lru_cache()
def get_settings() -> Settings:
    return Settings()