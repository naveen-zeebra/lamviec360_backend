import sys
from app.core.database import SessionLocal
from app.models.seeker import SavedJob
from sqlalchemy.exc import IntegrityError

db = SessionLocal()
user_id = "test-user-id"
job_id = "11"

try:
    saved = SavedJob(user_id=user_id, job_id=job_id)
    db.add(saved)
    db.commit()
    print("Success")
except Exception as e:
    db.rollback()
    print("Error:", type(e).__name__, str(e))
