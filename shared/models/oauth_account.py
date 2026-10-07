from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from shared.database.base import Base, TimestampMixin


class OAuthAccount(Base, TimestampMixin):
    """Stores third-party OAuth provider connections linked to users (Google, Zalo, LinkedIn, Facebook)."""
    __tablename__ = "oauth_accounts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    provider = Column(String(50), nullable=False, index=True)  # "google", "zalo", "linkedin", "facebook"
    provider_user_id = Column(String(255), nullable=False, index=True)
    provider_email = Column(String(255), nullable=True)
    access_token = Column(Text, nullable=True)
    refresh_token = Column(Text, nullable=True)
    expires_at = Column(DateTime, nullable=True)

    __table_args__ = (
        UniqueConstraint("provider", "provider_user_id", name="uq_oauth_provider_user_id"),
    )

    # Relationships
    user = relationship("User", back_populates="oauth_accounts")
