from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Boolean, Text, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from shared.database.base import Base, TimestampMixin, SoftDeleteMixin

class CompanyUser(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "company_users"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("company_profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    email = Column(String(255), nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    phone = Column(String(50), nullable=True)
    avatar_url = Column(String(500), nullable=True)
    
    # Predefined company roles: "company_admin", "recruiter", "hiring_manager", "interviewer"
    role = Column(String(50), default="recruiter", nullable=False, index=True)
    
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=True, nullable=False)
    last_login = Column(DateTime, nullable=True)
    invited_by_id = Column(Integer, ForeignKey("company_users.id", ondelete="SET NULL"), nullable=True)

    # Relationships
    company = relationship("CompanyProfile", back_populates="team_members")
    invited_by = relationship("CompanyUser", remote_side=[id])

    @property
    def full_name(self) -> str:
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}".strip()
        return self.first_name or self.last_name or self.email

    @property
    def user_type(self) -> str:
        return "company"

    @property
    def role_type(self) -> str:
        return "company"

    @property
    def is_company_admin(self) -> bool:
        return self.role == "company_admin"

    @property
    def is_superuser(self) -> bool:
        return False

    @property
    def roles(self) -> list:
        class RoleAdapter:
            def __init__(self, code, name):
                self.code = code
                self.name = name
        code = self.role or "recruiter"
        name = code.replace("_", " ").title()
        return [RoleAdapter(code, name)]

    @property
    def company_profile(self):
        return self.company


class CompanyInvitation(Base, TimestampMixin):
    __tablename__ = "company_invitations"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("company_profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    email = Column(String(255), nullable=False, index=True)
    role = Column(String(50), default="recruiter", nullable=False)
    invite_token = Column(String(100), unique=True, nullable=False, index=True)
    message = Column(Text, nullable=True)
    status = Column(String(50), default="pending", nullable=False)  # pending, accepted, expired, revoked
    invited_by_id = Column(Integer, ForeignKey("company_users.id", ondelete="SET NULL"), nullable=True)
    expires_at = Column(DateTime, nullable=False)

    # Relationships
    company = relationship("CompanyProfile", back_populates="invitations")
    invited_by = relationship("CompanyUser")
