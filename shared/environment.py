import os
from pathlib import Path
from dotenv import load_dotenv

# Path to root .env
ROOT_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = ROOT_DIR / ".env"

load_dotenv(dotenv_path=ENV_PATH, override=True)

class EnvironmentConfig:
    APP_ENV: str = os.getenv("APP_ENV", "local").lower()
    APP_NAME: str = os.getenv("APP_NAME", "JobPortalMultiGateway")

    # Gateway Ports & Hosts
    HOST: str = os.getenv("HOST", "0.0.0.0")
    JOBSEEKER_SERVICE_HOST: str = os.getenv("JOBSEEKER_HOST", "0.0.0.0")
    COMPANY_SERVICE_HOST: str = os.getenv("COMPANY_HOST", "0.0.0.0")
    ADMIN_SERVICE_HOST: str = os.getenv("ADMIN_HOST", "0.0.0.0")

    JOBSEEKER_PORT: int = int(os.getenv("JOBSEEKER_PORT", "8001"))
    COMPANY_PORT: int = int(os.getenv("COMPANY_PORT", "8002"))
    ADMIN_PORT: int = int(os.getenv("ADMIN_PORT", "8003"))

    JOBSEEKER_SERVICE_PORT: int = JOBSEEKER_PORT
    COMPANY_SERVICE_PORT: int = COMPANY_PORT
    ADMIN_SERVICE_PORT: int = ADMIN_PORT

    # Database Engine & Credentials
    DB_ENGINE: str = os.getenv("DB_ENGINE", "sqlite").lower()
    
    # PostgreSQL Configuration
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "postgres")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "postgres")
    POSTGRES_HOST: str = os.getenv("POSTGRES_HOST", "localhost")
    POSTGRES_PORT: int = int(os.getenv("POSTGRES_PORT", "5432"))
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "jobportal_db")

    # Resolved DATABASE_URL
    _env_db_url: str = os.getenv("DATABASE_URL", "").strip()
    if _env_db_url:
        DATABASE_URL: str = _env_db_url
    elif DB_ENGINE in ["postgres", "postgresql"]:
        DATABASE_URL: str = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
    else:
        DATABASE_URL: str = "sqlite:///./jobportal.db"

    # JWT
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "super-secret-jwt-key-for-job-portal-platform-360")
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))
    REFRESH_TOKEN_EXPIRE_DAYS: int = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "30"))

    # CORS
    _cors_raw: str = os.getenv("CORS_ORIGINS", "*")
    CORS_ORIGINS: list[str] = [orig.strip() for orig in _cors_raw.split(",") if orig.strip()] if _cors_raw != "*" else ["*"]

    # Uploads
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "./uploads")
    MAX_FILE_SIZE_MB: int = int(os.getenv("MAX_FILE_SIZE_MB", "10"))

    # Seeds
    SEED_ADMIN_EMAIL: str = os.getenv("SEED_ADMIN_EMAIL", "admin@example.com")
    SEED_ADMIN_PASSWORD: str = os.getenv("SEED_ADMIN_PASSWORD", "Password123!")

    # Email / SMTP Configuration
    SMTP_HOST: str = os.getenv("SMTP_HOST", "").strip().strip("'\"")
    SMTP_PORT: int = int(str(os.getenv("SMTP_PORT", "587")).strip().strip("'\""))
    SMTP_USER: str = os.getenv("SMTP_USER", "").strip().strip("'\"")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "").strip().strip("'\"")
    SMTP_TLS: bool = str(os.getenv("SMTP_TLS", "true")).strip().strip("'\"").lower() in ("true", "1", "yes")
    FROM_EMAIL: str = (
        os.getenv("SMTP_FROM_EMAIL") or os.getenv("FROM_EMAIL") or os.getenv("SMTP_USER") or "noreply@jobportal.com"
    ).strip().strip("'\"")
    FROM_NAME: str = (
        os.getenv("SMTP_FROM_NAME") or os.getenv("FROM_NAME") or "LamViec360 Career Portal"
    ).strip().strip("'\"")

    # Frontend URLs
    JOBSEEKER_WEB_URL: str = os.getenv("JOBSEEKER_WEB_URL", "http://localhost:3000").strip().strip("'\"")
    COMPANY_WEB_URL: str = os.getenv("COMPANY_WEB_URL", "http://localhost:3001").strip().strip("'\"")
    ADMIN_WEB_URL: str = os.getenv("ADMIN_WEB_URL", "http://localhost:3002").strip().strip("'\"")

env = EnvironmentConfig()
