from typing import Optional, List
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from shared.database.session import get_db
from shared.schemas import APIResponse
from shared.utils import require_roles, success_response, paginated_response
from .schemas import (
    BannerCreate,
    BannerUpdate,
    BannerStatusUpdate,
    BannerResponse,
    BannerActiveItem,
)
from .service import (
    get_banner_by_id,
    get_active_banners,
    record_banner_click,
)
from .controller import (
    list_banners_controller,
    create_banner_controller,
    update_banner_controller,
    toggle_banner_status_controller,
    delete_banner_controller,
)

router = APIRouter(prefix="/banners", tags=["Advertisement Banner Management"])


@router.get("", summary="List Advertisement Banners (Admin)")
def list_banners_endpoint(
    page: int = Query(1, ge=1),
    page_size: int = Query(15, ge=1, le=100),
    search: Optional[str] = Query(None),
    placement: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    admin=Depends(require_roles("super_admin", "admin", "operations_admin")),
):
    """Admin endpoint to list banners with KPI stats, placement & lifecycle status filters."""
    res = list_banners_controller(
        db,
        page=page,
        page_size=page_size,
        search=search,
        placement=placement,
        category=category,
        status_filter=status,
    )
    response = paginated_response(
        items=res["items"],
        total_items=res["pagination"]["total_items"],
        page=res["pagination"]["page"],
        page_size=res["pagination"]["page_size"],
        message="Banners retrieved successfully",
    )
    response["stats"] = res["stats"]
    return response


@router.get("/active", summary="Get Active Scheduled Banners (Public / Portal)")
def get_active_banners_endpoint(
    placement: Optional[str] = Query(None, description="LANDING_HERO, LANDING_FEATURED, EMPLOYER_DASHBOARD"),
    db: Session = Depends(get_db),
):
    """Public / portal endpoint delivering active scheduled banners for landing page or employer dashboard."""
    active_items = get_active_banners(db, placement=placement)
    data = [item.dict() for item in active_items]
    return success_response(data=data, message="Active banners retrieved successfully")


@router.post("/{banner_id}/click", summary="Track Banner Click (Public / Portal)")
def track_banner_click_endpoint(
    banner_id: int,
    db: Session = Depends(get_db),
):
    """Records a consumer click on a promotional banner."""
    new_clicks = record_banner_click(db, banner_id)
    return success_response(
        data={"banner_id": banner_id, "click_count": new_clicks},
        message="Banner click recorded",
    )


@router.get("/{banner_id}", summary="Get Banner Detail (Admin)")
def get_banner_detail_endpoint(
    banner_id: int,
    db: Session = Depends(get_db),
    admin=Depends(require_roles("super_admin", "admin", "operations_admin")),
):
    """Retrieve full banner detail for administrative review or edit."""
    banner = get_banner_by_id(db, banner_id)
    imp = banner.impression_count or 0
    clk = banner.click_count or 0
    ctr = round((clk / imp) * 100, 2) if imp > 0 else 0.0

    resp = BannerResponse.from_orm(banner)
    resp.ctr_percent = ctr
    return success_response(data=resp.dict(), message="Banner detail retrieved")


@router.post("", summary="Create Advertisement Banner (Admin)")
def create_banner_endpoint(
    payload: BannerCreate,
    request: Request,
    db: Session = Depends(get_db),
    admin=Depends(require_roles("super_admin", "admin", "operations_admin")),
):
    """Create a new promotional advertisement banner with targeting, schedule, and styling."""
    banner = create_banner_controller(db, payload, admin_user=admin, request=request)
    resp = BannerResponse.from_orm(banner)
    resp.ctr_percent = 0.0
    return success_response(data=resp.dict(), message="Advertisement banner created successfully")


@router.put("/{banner_id}", summary="Update Advertisement Banner (Admin)")
def update_banner_endpoint(
    banner_id: int,
    payload: BannerUpdate,
    request: Request,
    db: Session = Depends(get_db),
    admin=Depends(require_roles("super_admin", "admin", "operations_admin")),
):
    """Update targeting, schedule dates, visual styling, or content of an existing banner."""
    banner = update_banner_controller(db, banner_id, payload, admin_user=admin, request=request)
    imp = banner.impression_count or 0
    clk = banner.click_count or 0
    ctr = round((clk / imp) * 100, 2) if imp > 0 else 0.0

    resp = BannerResponse.from_orm(banner)
    resp.ctr_percent = ctr
    return success_response(data=resp.dict(), message="Banner updated successfully")


@router.patch("/{banner_id}/status", summary="Toggle Banner Active State (Admin)")
def toggle_banner_status_endpoint(
    banner_id: int,
    payload: BannerStatusUpdate,
    request: Request,
    db: Session = Depends(get_db),
    admin=Depends(require_roles("super_admin", "admin", "operations_admin")),
):
    """Instantly activate or deactivate an advertisement banner."""
    banner = toggle_banner_status_controller(db, banner_id, payload, admin_user=admin, request=request)
    return success_response(
        data={"id": banner.id, "is_active": banner.is_active},
        message=f"Banner {'activated' if banner.is_active else 'deactivated'} successfully",
    )


@router.delete("/{banner_id}", summary="Delete Advertisement Banner (Admin)")
def delete_banner_endpoint(
    banner_id: int,
    request: Request,
    db: Session = Depends(get_db),
    admin=Depends(require_roles("super_admin", "admin", "operations_admin")),
):
    """Permanently delete an advertisement banner."""
    delete_banner_controller(db, banner_id, admin_user=admin, request=request)
    return success_response(data={"id": banner_id}, message="Banner deleted successfully")
