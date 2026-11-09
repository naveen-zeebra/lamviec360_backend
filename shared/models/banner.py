from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey
from shared.database.base import Base, TimestampMixin


class Banner(Base, TimestampMixin):
    __tablename__ = "ad_banners"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(255), nullable=False)
    placement = Column(String(50), nullable=False, default="LANDING_HERO")
    category = Column(String(50), nullable=False, default="PROMOTION")
    headline = Column(String(255), nullable=True)
    headline_en = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    description_en = Column(Text, nullable=True)
    badge_text = Column(String(100), nullable=True)
    event_date = Column(DateTime, nullable=True)
    location_or_platform = Column(String(255), nullable=True)
    organizer = Column(String(255), nullable=True)
    image_url = Column(String(500), nullable=True)
    bg_gradient = Column(String(255), nullable=True)
    cta_label = Column(String(100), nullable=True)
    cta_label_en = Column(String(100), nullable=True)
    cta_url = Column(String(500), nullable=True)
    open_in_new_tab = Column(Boolean, default=False, nullable=False)
    display_order = Column(Integer, default=0, nullable=False)
    start_date = Column(DateTime, nullable=True)
    end_date = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    impression_count = Column(Integer, default=0, nullable=False)
    click_count = Column(Integer, default=0, nullable=False)
    created_by_admin_id = Column(Integer, ForeignKey("admin_users.id"), nullable=True)
