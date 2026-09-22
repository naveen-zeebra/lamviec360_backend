from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.orm import relationship
from shared.database.base import Base, TimestampMixin, SoftDeleteMixin
from shared.models.role import user_roles

class User(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role_type = Column(String(50), nullable=False, index=True)  # "super_admin", "admin", "company", "jobseeker"
    
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    phone = Column(String(50), nullable=True)
    avatar_url = Column(String(500), nullable=True)

    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    last_login = Column(DateTime, nullable=True)

    # Relationships
    roles = relationship("Role", secondary=user_roles, back_populates="users")
    jobseeker_profile = relationship("JobSeekerProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    company_profile = relationship("CompanyProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")

    def __init__(self, **kwargs):
        # Support aliases
        if "full_name" in kwargs:
            fn = kwargs.pop("full_name")
            if fn:
                parts = fn.strip().split(" ", 1)
                kwargs["first_name"] = parts[0]
                kwargs["last_name"] = parts[1] if len(parts) > 1 else ""
        if "hashed_password" in kwargs:
            kwargs["password_hash"] = kwargs.pop("hashed_password")
        if "user_type" in kwargs:
            kwargs["role_type"] = kwargs.pop("user_type")
        kwargs.pop("is_superuser", None)
        super().__init__(**kwargs)

    @property
    def full_name(self) -> str:
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}".strip()
        return self.first_name or self.last_name or self.email

    @full_name.setter
    def full_name(self, value: str):
        if value:
            parts = value.strip().split(" ", 1)
            self.first_name = parts[0]
            self.last_name = parts[1] if len(parts) > 1 else ""

    @property
    def hashed_password(self) -> str:
        return self.password_hash

    @hashed_password.setter
    def hashed_password(self, value: str):
        self.password_hash = value

    @property
    def user_type(self) -> str:
        return self.role_type

    @user_type.setter
    def user_type(self, value: str):
        self.role_type = value

    @property
    def is_superuser(self) -> bool:
        return self.role_type == "super_admin"
