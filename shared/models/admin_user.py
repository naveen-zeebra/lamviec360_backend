from sqlalchemy import Column, Integer, String, Boolean, Text, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from shared.database.base import Base, TimestampMixin, SoftDeleteMixin

class AdminRole(Base, TimestampMixin):
    __tablename__ = "admin_roles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False, index=True)  # "Super Admin", "Operations Admin", etc.
    code = Column(String(50), unique=True, nullable=False, index=True)  # "super_admin", "operations_admin", etc.
    description = Column(Text, nullable=True)
    is_system = Column(Boolean, default=True, nullable=False)  # System default roles cannot be deleted

    # Relationships
    permissions = relationship("AdminRolePermission", back_populates="role", cascade="all, delete-orphan")
    admins = relationship("AdminUser", back_populates="role_rel")


class AdminRolePermission(Base, TimestampMixin):
    __tablename__ = "admin_role_permissions"

    id = Column(Integer, primary_key=True, index=True)
    role_id = Column(Integer, ForeignKey("admin_roles.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Module Key: DASHBOARD, ANALYTICS, TENANTS, USERS, COMMERCIAL, GOVERNANCE, CONFIGURATION, ADMIN_MANAGEMENT, ACCOUNT
    module_key = Column(String(50), nullable=False, index=True)
    can_view = Column(Boolean, default=False, nullable=False)
    can_create = Column(Boolean, default=False, nullable=False)
    can_edit = Column(Boolean, default=False, nullable=False)
    can_delete = Column(Boolean, default=False, nullable=False)

    role = relationship("AdminRole", back_populates="permissions")


class AdminUser(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "admin_users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    phone = Column(String(50), nullable=True)
    avatar_url = Column(String(500), nullable=True)
    
    role_id = Column(Integer, ForeignKey("admin_roles.id", ondelete="RESTRICT"), nullable=True)
    role_name = Column(String(50), default="Operations Admin", nullable=False)  # Cached title: "Super Admin", etc.
    
    is_active = Column(Boolean, default=True, nullable=False)
    last_login = Column(DateTime, nullable=True)

    # Relationships
    role_rel = relationship("AdminRole", back_populates="admins")

    @property
    def full_name(self) -> str:
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}".strip()
        return self.first_name or self.last_name or self.email

    @property
    def role(self) -> str:
        return self.role_name or (self.role_rel.name if self.role_rel else "Admin")

    @property
    def permissions_dict(self) -> dict:
        """Returns {MODULE_KEY: {can_view, can_create, can_edit, can_delete}}"""
        result = {}
        if self.role_rel:
            for p in self.role_rel.permissions:
                result[p.module_key] = {
                    "can_view": p.can_view,
                    "can_create": p.can_create,
                    "can_edit": p.can_edit,
                    "can_delete": p.can_delete,
                }
        return result
