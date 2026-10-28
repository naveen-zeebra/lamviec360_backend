from typing import Generator
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from shared.environment import env
from shared.database.base import Base

engine_kwargs = {
    "pool_pre_ping": True,
    "pool_size": 10,
    "max_overflow": 20,
    "pool_recycle": 1800,
    "echo": False,
}

engine = create_engine(env.DATABASE_URL, **engine_kwargs)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db() -> None:
    """Create all database tables if they do not exist."""
    # Import all models to ensure they are registered with Base.metadata
    from shared.models import user, role, oauth_account, jobseeker, company, company_user, job, application, audit_log, admin_user, notification  # noqa: F401
    Base.metadata.create_all(bind=engine)

    # Safe idempotent migration for BR-301-11 acknowledgment columns, BR-101-08 job_availability, and JSP-FR-012 document encryption
    try:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE job_applications ADD COLUMN IF NOT EXISTS acknowledgment_sent BOOLEAN DEFAULT FALSE;"))
            conn.execute(text("ALTER TABLE job_applications ADD COLUMN IF NOT EXISTS acknowledgment_sent_at TIMESTAMP;"))
            conn.execute(text("ALTER TABLE jobseeker_profiles ADD COLUMN IF NOT EXISTS job_availability VARCHAR(50) DEFAULT 'open_to_work';"))
            conn.execute(text("ALTER TABLE jobseeker_profiles ADD COLUMN IF NOT EXISTS archive_pin_hash VARCHAR(255);"))
            conn.execute(text("ALTER TABLE jobseeker_profiles ADD COLUMN IF NOT EXISTS is_archive_locked BOOLEAN DEFAULT FALSE;"))
            conn.execute(text("ALTER TABLE jobseeker_documents ADD COLUMN IF NOT EXISTS is_encrypted BOOLEAN DEFAULT TRUE;"))
            conn.execute(text("ALTER TABLE jobseeker_documents ADD COLUMN IF NOT EXISTS is_password_protected BOOLEAN DEFAULT FALSE;"))
            conn.execute(text("ALTER TABLE jobseeker_documents ADD COLUMN IF NOT EXISTS password_hash VARCHAR(255);"))
            conn.execute(text("ALTER TABLE job_postings ADD COLUMN IF NOT EXISTS department VARCHAR(100);"))
            conn.execute(text("ALTER TABLE job_postings ADD COLUMN IF NOT EXISTS vacancies INTEGER DEFAULT 1;"))
            conn.execute(text("ALTER TABLE job_postings ADD COLUMN IF NOT EXISTS education VARCHAR(100);"))
            conn.execute(text("ALTER TABLE job_postings ADD COLUMN IF NOT EXISTS documents TEXT;"))
            conn.execute(text("ALTER TABLE company_profiles ALTER COLUMN logo_url TYPE TEXT;"))
            conn.execute(text("ALTER TABLE company_profiles ALTER COLUMN cover_image_url TYPE TEXT;"))
            conn.execute(text("ALTER TABLE company_profiles ALTER COLUMN about TYPE TEXT;"))
            conn.execute(text("ALTER TABLE company_profiles ADD COLUMN IF NOT EXISTS is_public BOOLEAN DEFAULT TRUE;"))
            conn.execute(text("ALTER TABLE company_profiles ADD COLUMN IF NOT EXISTS tagline VARCHAR(255);"))
    except Exception:
        pass

