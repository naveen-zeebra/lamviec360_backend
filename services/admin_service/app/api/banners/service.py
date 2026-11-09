from typing import Dict, Any, Optional, List
from datetime import datetime, timezone, timedelta
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, desc, asc

from shared.models import Banner, AdminUser
from .schemas import (
    BannerCreate,
    BannerUpdate,
    BannerStatusUpdate,
    BannerResponse,
    BannerActiveItem,
)


def list_banners(
    db: Session,
    page: int = 1,
    page_size: int = 15,
    search: Optional[str] = None,
    placement: Optional[str] = None,
    category: Optional[str] = None,
    status_filter: Optional[str] = None,
) -> Dict[str, Any]:
    """Retrieve banners with pagination, multi-criteria filtering, and performance stats."""
    seed_demo_banners_if_empty(db)

    query = db.query(Banner)
    now = datetime.utcnow()

    # Search filter
    if search and search.strip():
        term = f"%{search.strip()}%"
        query = query.filter(
            or_(
                Banner.title.ilike(term),
                Banner.headline.ilike(term),
                Banner.headline_en.ilike(term),
                Banner.badge_text.ilike(term),
                Banner.organizer.ilike(term),
            )
        )

    # Placement filter
    if placement and placement.upper() != "ALL":
        query = query.filter(Banner.placement == placement.upper())

    # Category filter
    if category and category.upper() != "ALL":
        query = query.filter(Banner.category == category.upper())

    # Lifecycle status filter
    if status_filter:
        sf = status_filter.upper()
        if sf == "ACTIVE":
            query = query.filter(
                Banner.is_active == True,
                or_(Banner.start_date == None, Banner.start_date <= now),
                or_(Banner.end_date == None, Banner.end_date >= now),
            )
        elif sf == "SCHEDULED":
            query = query.filter(
                Banner.is_active == True,
                Banner.start_date > now,
            )
        elif sf == "EXPIRED":
            query = query.filter(
                Banner.end_date != None,
                Banner.end_date < now,
            )
        elif sf == "INACTIVE":
            query = query.filter(Banner.is_active == False)

    total_items = query.count()
    offset = (page - 1) * page_size
    banners = (
        query.order_by(Banner.display_order.asc(), desc(Banner.created_at))
        .offset(offset)
        .limit(page_size)
        .all()
    )

    # Calculate overall aggregate metrics
    all_banners = db.query(Banner).all()
    total_banners = len(all_banners)
    active_now = sum(
        1
        for b in all_banners
        if b.is_active
        and (not b.start_date or b.start_date <= now)
        and (not b.end_date or b.end_date >= now)
    )
    scheduled = sum(
        1
        for b in all_banners
        if b.is_active and b.start_date and b.start_date > now
    )
    total_impressions = sum(b.impression_count or 0 for b in all_banners)
    total_clicks = sum(b.click_count or 0 for b in all_banners)
    avg_ctr = (
        round((total_clicks / total_impressions) * 100, 2)
        if total_impressions > 0
        else 0.0
    )

    items_data = []
    for b in banners:
        imp = b.impression_count or 0
        clk = b.click_count or 0
        ctr = round((clk / imp) * 100, 2) if imp > 0 else 0.0

        item = BannerResponse.from_orm(b)
        item.ctr_percent = ctr
        items_data.append(item.dict())

    return {
        "items": items_data,
        "pagination": {
            "total_items": total_items,
            "page": page,
            "page_size": page_size,
            "total_pages": max(1, (total_items + page_size - 1) // page_size),
        },
        "stats": {
            "total_banners": total_banners,
            "active_now": active_now,
            "scheduled": scheduled,
            "total_impressions": total_impressions,
            "total_clicks": total_clicks,
            "avg_ctr_percent": avg_ctr,
        },
    }


def get_banner_by_id(db: Session, banner_id: int) -> Banner:
    """Retrieve single banner by primary key."""
    banner = db.query(Banner).filter(Banner.id == banner_id).first()
    if not banner:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Banner with ID {banner_id} not found",
        )
    return banner


def create_banner(
    db: Session,
    payload: BannerCreate,
    admin_user: Optional[AdminUser] = None,
) -> Banner:
    """Create a new promotional advertisement banner."""
    if payload.start_date and payload.end_date and payload.start_date > payload.end_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Schedule start date must be before or equal to end date",
        )

    banner = Banner(
        title=payload.title.strip(),
        placement=payload.placement.upper(),
        category=payload.category.upper(),
        headline=payload.headline,
        headline_en=payload.headline_en,
        description=payload.description,
        description_en=payload.description_en,
        badge_text=payload.badge_text,
        event_date=payload.event_date,
        location_or_platform=payload.location_or_platform,
        organizer=payload.organizer,
        image_url=payload.image_url,
        bg_gradient=payload.bg_gradient,
        cta_label=payload.cta_label,
        cta_label_en=payload.cta_label_en,
        cta_url=payload.cta_url,
        open_in_new_tab=payload.open_in_new_tab,
        display_order=payload.display_order,
        start_date=payload.start_date,
        end_date=payload.end_date,
        is_active=payload.is_active,
        impression_count=0,
        click_count=0,
        created_by_admin_id=admin_user.id if admin_user else None,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(banner)
    db.commit()
    db.refresh(banner)
    return banner


def update_banner(
    db: Session,
    banner_id: int,
    payload: BannerUpdate,
) -> Banner:
    """Update existing banner attributes."""
    banner = get_banner_by_id(db, banner_id)

    update_dict = payload.dict(exclude_unset=True)

    # Validate date ordering if both are present in target state
    new_start = update_dict.get("start_date", banner.start_date)
    new_end = update_dict.get("end_date", banner.end_date)
    if new_start and new_end and new_start > new_end:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Schedule start date must be before or equal to end date",
        )

    for k, v in update_dict.items():
        if k in ["placement", "category"] and v:
            setattr(banner, k, v.upper())
        elif k == "title" and v:
            setattr(banner, k, v.strip())
        else:
            setattr(banner, k, v)

    banner.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(banner)
    return banner


def toggle_banner_status(
    db: Session,
    banner_id: int,
    payload: BannerStatusUpdate,
) -> Banner:
    """Toggle activation state of a banner."""
    banner = get_banner_by_id(db, banner_id)
    banner.is_active = payload.is_active
    banner.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(banner)
    return banner


def delete_banner(db: Session, banner_id: int) -> None:
    """Permanently delete a banner."""
    banner = get_banner_by_id(db, banner_id)
    db.delete(banner)
    db.commit()


def get_active_banners(
    db: Session,
    placement: Optional[str] = None,
) -> List[BannerActiveItem]:
    """Retrieve active scheduled banners for public portal or employer dashboard delivery."""
    seed_demo_banners_if_empty(db)

    now = datetime.utcnow()
    query = db.query(Banner).filter(
        Banner.is_active == True,
        or_(Banner.start_date == None, Banner.start_date <= now),
        or_(Banner.end_date == None, Banner.end_date >= now),
    )

    if placement and placement.upper() != "ALL":
        query = query.filter(Banner.placement == placement.upper())

    banners = (
        query.order_by(Banner.display_order.asc(), desc(Banner.created_at))
        .limit(10)
        .all()
    )

    # Increment impression counts for active delivery
    for b in banners:
        b.impression_count = (b.impression_count or 0) + 1
    db.commit()

    return [BannerActiveItem.from_orm(b) for b in banners]


def record_banner_click(db: Session, banner_id: int) -> int:
    """Track a click event for a banner."""
    banner = db.query(Banner).filter(Banner.id == banner_id).first()
    if not banner:
        return 0

    banner.click_count = (banner.click_count or 0) + 1
    db.commit()
    return banner.click_count


def seed_demo_banners_if_empty(db: Session) -> None:
    """Seed initial realistic demo banners if ad_banners table is empty."""
    if db.query(Banner).count() > 0:
        return

    now = datetime.utcnow()
    future = now + timedelta(days=60)

    demo_items = [
        Banner(
            title="Vietnam Tech Career Expo 2027",
            placement="LANDING_HERO",
            category="HIRING_EVENT",
            headline="Ngày Hội Việc Làm Công Nghệ & AI Việt Nam 2027",
            headline_en="Vietnam Tech & AI Career Fair 2027",
            description="Gặp gỡ trực tiếp 50+ tập đoàn công nghệ hàng đầu, phỏng vấn tại chỗ và nhận offer ngay trong ngày.",
            description_en="Meet 50+ leading tech enterprises, interview on the spot and receive high-impact job offers.",
            badge_text="SỰ KIỆN NỔI BẬT",
            event_date=now + timedelta(days=15),
            location_or_platform="Trung tâm Hội chợ Triển lãm SECC, TP.HCM & Hybrid Online",
            organizer="Hiệp hội Phần mềm VINASA & LàmViệc360",
            bg_gradient="linear-gradient(135deg, #1e3a8a 0%, #3b82f6 50%, #06b6d4 100%)",
            cta_label="Đăng ký tham gia miễn phí",
            cta_label_en="Register for Free",
            cta_url="/jobs?q=technology",
            open_in_new_tab=False,
            display_order=1,
            start_date=now - timedelta(days=1),
            end_date=future,
            is_active=True,
            impression_count=142,
            click_count=28,
            created_at=now,
            updated_at=now,
        ),
        Banner(
            title="CV Mastery & Technical Interview Prep",
            placement="LANDING_HERO",
            category="WEBINAR",
            headline="Masterclass: Tối Ưu CV & Chinh Phục Phỏng Vấn Senior Engineer",
            headline_en="Masterclass: CV Optimization & Senior Tech Interview Strategies",
            description="Workshop chuyên sâu cùng các Giám đốc Công nghệ & Trưởng phòng Tuyển dụng từ Shopee, VNG, FPT.",
            description_en="Exclusive technical workshop hosted by Chief Architects & Lead Recruiters across top tech firms.",
            badge_text="WORKSHOP MIỄN PHÍ",
            event_date=now + timedelta(days=7),
            location_or_platform="Trực tuyến qua LàmViệc360 Live Studio",
            organizer="LàmViệc360 Career Center",
            bg_gradient="linear-gradient(135deg, #4338ca 0%, #6366f1 50%, #8b5cf6 100%)",
            cta_label="Nhận vé tham gia ngay",
            cta_label_en="Claim Your Seat",
            cta_url="/resources",
            open_in_new_tab=False,
            display_order=2,
            start_date=now - timedelta(days=1),
            end_date=future,
            is_active=True,
            impression_count=89,
            click_count=19,
            created_at=now,
            updated_at=now,
        ),
        Banner(
            title="Mid-Page Jobseeker Promotion",
            placement="LANDING_FEATURED",
            category="PROMOTION",
            headline="Tạo Hồ Sơ LàmViệc360 — Nhận Cơ Hội Việc Làm Tự Động Gửi Đến Bạn",
            headline_en="Build Your LàmViệc360 Profile — Let Top Companies Find You",
            description="Ứng viên có hồ sơ đầy đủ nhận được tỷ lệ phản hồi cao gấp 3.5 lần từ các nhà tuyển dụng hàng đầu.",
            description_en="Candidates with complete profiles experience 3.5x higher callback rates from verified employers.",
            badge_text="GỢI Ý TỰ ĐỘNG",
            bg_gradient="linear-gradient(135deg, #047857 0%, #10b981 100%)",
            cta_label="Hoàn thiện hồ sơ ngay",
            cta_label_en="Complete Profile Now",
            cta_url="/register",
            open_in_new_tab=False,
            display_order=1,
            start_date=now - timedelta(days=2),
            end_date=future,
            is_active=True,
            impression_count=210,
            click_count=45,
            created_at=now,
            updated_at=now,
        ),
        Banner(
            title="Employer Enterprise Package Year-End Offer",
            placement="EMPLOYER_DASHBOARD",
            category="FEATURED_PACKAGE",
            headline="Ưu Đãi Tuyển Dụng Cuối Năm: Giảm 35% Gói Đăng Tin Doanh Nghiệp Không Giới Hạn",
            headline_en="Year-End Hiring Drive: 35% OFF Enterprise Unlimited Job Posting & Talent Search",
            description="Tiếp cận hơn 500,000+ ứng viên chất lượng cao, tích hợp công cụ sàng lọc AI và bài test chuyên môn tự động.",
            description_en="Gain instant access to 500,000+ vetted candidates with AI candidate matching and skill verification tests.",
            badge_text="ƯU ĐÃI ĐẶC QUYỀN",
            bg_gradient="linear-gradient(135deg, #1e293b 0%, #0f172a 50%, #2563eb 100%)",
            cta_label="Nâng cấp gói ngay",
            cta_label_en="Upgrade Plan Now",
            cta_url="/company/billing",
            open_in_new_tab=False,
            display_order=1,
            start_date=now - timedelta(days=1),
            end_date=future,
            is_active=True,
            impression_count=95,
            click_count=22,
            created_at=now,
            updated_at=now,
        ),
    ]

    db.add_all(demo_items)
    db.commit()
