from sqlalchemy import Column, Integer, String, Text, DateTime
from datetime import datetime
from shared.database.base import Base

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=True, index=True)
    user_email = Column(String(255), nullable=True)
    user_type = Column(String(50), nullable=True)  # admin, company, jobseeker
    
    action = Column(String(100), nullable=False, index=True)   # CREATE, UPDATE, DELETE, LOGIN, APPROVE, REJECT
    module = Column(String(100), nullable=False, index=True)   # USERS, ROLES, JOBS, COMPANIES, APPLICATIONS
    description = Column(Text, nullable=True)
    
    ip_address = Column(String(50), nullable=True)
    user_agent = Column(String(500), nullable=True)
    details = Column(Text, nullable=True)  # JSON formatted extra detail
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
