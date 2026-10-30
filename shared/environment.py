import os
from pathlib import Path
from urllib.parse import urlparse, unquote
from dotenv import load_dotenv

# Path to root .env
ROOT_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = ROOT_DIR / ".env"

# Do not override existing system environment variables so Docker config takes precedence
load_dotenv(dotenv_path=ENV_PATH, override=False)

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

    # Database Configuration (PostgreSQL DATABASE_URL only)
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/jobportal_db",
    ).strip()

    if DATABASE_URL.lower().startswith("sqlite:"):
        raise ValueError("SQLite is unsupported. Please configure a PostgreSQL database URL (postgresql://...).")
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = "postgresql://" + DATABASE_URL[len("postgres://"):]

    # Derived attributes parsed from DATABASE_URL for backwards compatibility
    try:
        _parsed = urlparse(DATABASE_URL)
        DB_ENGINE: str = "postgres"
        POSTGRES_USER: str = unquote(_parsed.username or "postgres")
        POSTGRES_PASSWORD: str = unquote(_parsed.password or "postgres")
        POSTGRES_HOST: str = _parsed.hostname or "localhost"
        POSTGRES_PORT: int = _parsed.port or 5432
        POSTGRES_DB: str = _parsed.path.lstrip("/") or "jobportal_db"
    except Exception:
        DB_ENGINE = "postgres"
        POSTGRES_USER = "postgres"
        POSTGRES_PASSWORD = "postgres"
        POSTGRES_HOST = "localhost"
        POSTGRES_PORT = 5432
        POSTGRES_DB = "jobportal_db"


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

    # Frontend URLs (Local, Develop, Production)
    if APP_ENV == "production":
        _DEFAULT_JOBSEEKER_URL = "https://lamviec360.com"
        _DEFAULT_COMPANY_URL = "https://company.lamviec360.com"
        _DEFAULT_ADMIN_URL = "https://superadmin.lamviec360.com"
    elif APP_ENV in ("uat", "staging"):
        _DEFAULT_JOBSEEKER_URL = "https://uat.lamviec360.com"
        _DEFAULT_COMPANY_URL = "https://company-uat.lamviec360.com"
        _DEFAULT_ADMIN_URL = "https://admin-uat.lamviec360.com"
    elif APP_ENV in ("develop", "development", "dev"):
        _DEFAULT_JOBSEEKER_URL = "https://devjobseeker.lamviec360.com"
        _DEFAULT_COMPANY_URL = "https://devcompany.lamviec360.com"
        _DEFAULT_ADMIN_URL = "https://devsuperadmin.lamviec360.com"
    else:
        _DEFAULT_JOBSEEKER_URL = "http://localhost:3001"
        _DEFAULT_COMPANY_URL = "http://localhost:3002"
        _DEFAULT_ADMIN_URL = "http://localhost:3003"

    JOBSEEKER_WEB_URL: str = os.getenv("JOBSEEKER_WEB_URL", _DEFAULT_JOBSEEKER_URL).strip().strip("'\"")
    COMPANY_WEB_URL: str = os.getenv("COMPANY_WEB_URL", _DEFAULT_COMPANY_URL).strip().strip("'\"")
    ADMIN_WEB_URL: str = os.getenv("ADMIN_WEB_URL", _DEFAULT_ADMIN_URL).strip().strip("'\"")

    # OAuth Identity Providers (Google, Zalo, LinkedIn, Facebook)
    GOOGLE_CLIENT_ID: str = os.getenv("GOOGLE_CLIENT_ID", "").strip().strip("'\"")
    GOOGLE_CLIENT_SECRET: str = os.getenv("GOOGLE_CLIENT_SECRET", "").strip().strip("'\"")
    GOOGLE_REDIRECT_URI: str = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:3001/oauth-callback?provider=google").strip().strip("'\"")

    ZALO_APP_ID: str = os.getenv("ZALO_APP_ID", "").strip().strip("'\"")
    ZALO_APP_SECRET: str = os.getenv("ZALO_APP_SECRET", "").strip().strip("'\"")
    ZALO_REDIRECT_URI: str = os.getenv("ZALO_REDIRECT_URI", "http://localhost:3001/oauth-callback?provider=zalo").strip().strip("'\"")

    LINKEDIN_CLIENT_ID: str = os.getenv("LINKEDIN_CLIENT_ID", "").strip().strip("'\"")
    LINKEDIN_CLIENT_SECRET: str = os.getenv("LINKEDIN_CLIENT_SECRET", "").strip().strip("'\"")
    LINKEDIN_REDIRECT_URI: str = os.getenv("LINKEDIN_REDIRECT_URI", "http://localhost:3001/oauth-callback?provider=linkedin").strip().strip("'\"")

    FACEBOOK_APP_ID: str = os.getenv("FACEBOOK_APP_ID", "").strip().strip("'\"")
    FACEBOOK_APP_SECRET: str = os.getenv("FACEBOOK_APP_SECRET", "").strip().strip("'\"")
    FACEBOOK_REDIRECT_URI: str = os.getenv("FACEBOOK_REDIRECT_URI", "http://localhost:3001/oauth-callback?provider=facebook").strip().strip("'\"")

env = EnvironmentConfig()
