from app.core.database import SessionLocal
from sqlalchemy import text

db = SessionLocal()
res = db.execute(text("SELECT id FROM jobs")).fetchall()
print("Jobs in DB:", [r[0] for r in res])
