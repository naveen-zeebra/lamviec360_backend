from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field


class BannerBase(BaseModel):
    title: str = Field(..., min_length=2, max_length=255, description="Internal identification title")
    placement: str = Field(default="LANDING_HERO", description="LANDING_HERO, LANDING_FEATURED, EMPLOYER_DASHBOARD")
    category: str = Field(default="PROMOTION", description="PROMOTION, HIRING_EVENT, FEATURED_PACKAGE, WEBINAR, ANNOUNCEMENT")
    headline: Optional[str] = Field(default=None, max_length=255, description="Vietnamese headline")
    headline_en: Optional[str] = Field(default=None, max_length=255, description="English headline")
    description: Optional[str] = Field(default=None, description="Vietnamese description")
    description_en: Optional[str] = Field(default=None, description="English description")
    badge_text: Optional[str] = Field(default=None, max_length=100, description="Badge text, e.g. HOT, MỚI, 30% OFF")
    event_date: Optional[datetime] = Field(default=None, description="Specific event schedule date if applicable")
    location_or_platform: Optional[str] = Field(default=None, max_length=255, description="e.g. Hà Nội, TP.HCM, Zoom, Online")
    organizer: Optional[str] = Field(default=None, max_length=255, description="Event host or partner organizer")
    image_url: Optional[str] = Field(default=None, max_length=500, description="Image banner URL")
    bg_gradient: Optional[str] = Field(default=None, max_length=255, description="CSS gradient string or theme identifier")
    cta_label: Optional[str] = Field(default=None, max_length=100, description="Vietnamese button text")
    cta_label_en: Optional[str] = Field(default=None, max_length=100, description="English button text")
    cta_url: Optional[str] = Field(default=None, max_length=500, description="Target destination URL")
    open_in_new_tab: bool = Field(default=False, description="Open link in a new browser tab")
    display_order: int = Field(default=0, ge=0, description="Priority sorting order (0 is highest)")
    start_date: Optional[datetime] = Field(default=None, description="Schedule start date/time")
    end_date: Optional[datetime] = Field(default=None, description="Schedule end date/time")
    is_active: bool = Field(default=True, description="Master active state toggle")


class BannerCreate(BannerBase):
    pass


class BannerUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=2, max_length=255)
    placement: Optional[str] = None
    category: Optional[str] = None
    headline: Optional[str] = None
    headline_en: Optional[str] = None
    description: Optional[str] = None
    description_en: Optional[str] = None
    badge_text: Optional[str] = None
    event_date: Optional[datetime] = None
    location_or_platform: Optional[str] = None
    organizer: Optional[str] = None
    image_url: Optional[str] = None
    bg_gradient: Optional[str] = None
    cta_label: Optional[str] = None
    cta_label_en: Optional[str] = None
    cta_url: Optional[str] = None
    open_in_new_tab: Optional[bool] = None
    display_order: Optional[int] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    is_active: Optional[bool] = None


class BannerStatusUpdate(BaseModel):
    is_active: bool = Field(..., description="Active state toggle")


class BannerResponse(BannerBase):
    id: int
    impression_count: int = 0
    click_count: int = 0
    ctr_percent: float = 0.0
    created_by_admin_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class BannerActiveItem(BaseModel):
    id: int
    title: str
    placement: str
    category: str
    headline: Optional[str] = None
    headline_en: Optional[str] = None
    description: Optional[str] = None
    description_en: Optional[str] = None
    badge_text: Optional[str] = None
    event_date: Optional[datetime] = None
    location_or_platform: Optional[str] = None
    organizer: Optional[str] = None
    image_url: Optional[str] = None
    bg_gradient: Optional[str] = None
    cta_label: Optional[str] = None
    cta_label_en: Optional[str] = None
    cta_url: Optional[str] = None
    open_in_new_tab: bool = False
    display_order: int = 0

    class Config:
        from_attributes = True
