import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "OfficeFlow API"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    # Storage settings
    BASE_DIR: str = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    STORAGE_DIR: str = os.path.join(BASE_DIR, "storage")
    UPLOAD_DIR: str = os.path.join(STORAGE_DIR, "uploads")
    OUTPUT_DIR: str = os.path.join(STORAGE_DIR, "outputs")
    JOB_DB_PATH: str = os.path.join(STORAGE_DIR, "jobs.sqlite3")
    DATABASE_URL: str = ""
    REDIS_URL: str = ""
    JWT_SECRET_KEY: str = "change-me-in-production-use-a-32-byte-secret"
    JWT_EXPIRE_MINUTES: int = 60 * 24
    AUTH_REQUIRED: bool = False
    
    # CORS
    BACKEND_CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]

    class Config:
        case_sensitive = True

settings = Settings()

# Auto create storage directories
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
os.makedirs(settings.OUTPUT_DIR, exist_ok=True)
