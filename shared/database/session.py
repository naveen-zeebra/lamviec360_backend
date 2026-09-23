from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from shared.environment import env
from shared.database.base import Base

is_sqlite = "sqlite" in env.DATABASE_URL
connect_args = {"check_same_thread": False} if is_sqlite else {}
engine_kwargs = {
    "connect_args": connect_args,
    "pool_pre_ping": True,
    "echo": False,
}
if not is_sqlite:
    engine_kwargs.update({
        "pool_size": 10,
        "max_overflow": 20,
        "pool_recycle": 1800,
    })

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
    from shared.models import user, role, jobseeker, company, job, application, audit_log, admin_user  # noqa: F401
    Base.metadata.create_all(bind=engine)
