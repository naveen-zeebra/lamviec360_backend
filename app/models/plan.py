from sqlalchemy import Column, String, Integer, Boolean, JSON
from app.core.database import Base


class SubscriptionPlan(Base):
    __tablename__ = "subscription_plans"

    id = Column(String(50), primary_key=True)  # Freemium, Professional, Enterprise
    name = Column(String(100), nullable=False)
    tier = Column(String(50), nullable=False)
    price = Column(String(100), nullable=False)
    posting_limit = Column(Integer, nullable=True)  # None = Unlimited
    retention_months = Column(Integer, default=6, nullable=False)
    ai_features = Column(Boolean, default=False, nullable=False)
    blurb = Column(String(255), nullable=True, default="")
    features = Column(JSON, nullable=True, default=list)
    active = Column(Boolean, default=True, nullable=False)
