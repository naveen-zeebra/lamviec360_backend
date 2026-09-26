from sqlalchemy import Column, Integer, String, Boolean, Text, ForeignKey, Table
from sqlalchemy.orm import relationship
from shared.database.base import Base, TimestampMixin

# Association table for User <-> Role multi-assignment
user_roles = Table(
    "user_roles",
    Base.metadata,
    Column("user_id", Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("role_id", Integer, ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
    extend_existing=True,
)

class Role(Base, TimestampMixin):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    code = Column(String(50), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    is_system = Column(Boolean, default=False, nullable=False)  # Super Admin cannot be deleted

    # Relationships
    permissions = relationship("RolePermission", back_populates="role", cascade="all, delete-orphan")
    users = relationship("User", secondary=user_roles, back_populates="roles")


class RolePermission(Base, TimestampMixin):
    __tablename__ = "role_permissions"

    id = Column(Integer, primary_key=True, index=True)
    role_id = Column(Integer, ForeignKey("roles.id", ondelete="CASCADE"), nullable=False)
    module_key = Column(String(50), nullable=False)  # DASHBOARD, USERS, ROLES, COMPANIES, JOBSEEKERS, JOBS
    can_view = Column(Boolean, default=False, nullable=False)
    can_create = Column(Boolean, default=False, nullable=False)
    can_edit = Column(Boolean, default=False, nullable=False)
    can_delete = Column(Boolean, default=False, nullable=False)

    role = relationship("Role", back_populates="permissions")

    @property
    def module(self) -> str:
        return self.module_key.lower()

    @property
    def description(self) -> str:
        return f"{self.module_key} permissions"

    @property
    def action(self) -> str:
        actions = []
        if self.can_view: actions.append("view")
        if self.can_create: actions.append("create")
        if self.can_edit: actions.append("edit")
        if self.can_delete: actions.append("delete")
        return ",".join(actions)

    def to_dict(self):
        return {
            "id": self.id,
            "role_id": self.role_id,
            "module_key": self.module_key,
            "module": self.module,
            "can_view": self.can_view,
            "can_create": self.can_create,
            "can_edit": self.can_edit,
            "can_delete": self.can_delete,
        }

