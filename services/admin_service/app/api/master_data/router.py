# ─────────────────────────────────────────────────────────────────────────────
# File    : services/admin_service/app/api/master_data/router.py
# Purpose : HTTP Endpoints for Platform Master Data & Configurable Lists (BR-010)
# ─────────────────────────────────────────────────────────────────────────────

from typing import Dict, List, Optional
from fastapi import APIRouter, Depends, Request

from shared.models import User
from shared.schemas import APIResponse
from shared.utils import require_roles, success_response
from .schemas import (
    MasterDataResponse,
    MasterDataItemCreate,
    MasterDataCategoryUpdate,
)
from .controller import (
    list_master_data_controller,
    get_category_controller,
    add_item_controller,
    remove_item_controller,
    update_category_controller,
)

router = APIRouter(prefix="/master-data", tags=["Platform Master Data"])


@router.get("", response_model=APIResponse[dict])
def get_all_master_data():
    """Retrieve all configurable master data lists (publicly readable for all portals)."""
    data = list_master_data_controller()
    return success_response(data=data, message="Master data retrieved successfully")


@router.get("/{category}", response_model=APIResponse[list])
def get_master_data_category(category: str):
    """Retrieve values for a single master data category."""
    items = get_category_controller(category)
    return success_response(data=items, message=f"Category '{category}' retrieved")


@router.post("/{category}", response_model=APIResponse[list])
def add_master_data_item(
    category: str,
    payload: MasterDataItemCreate,
    request: Request,
    current_admin: User = Depends(require_roles("super_admin", "admin")),
):
    """Add a new option to a master data category (Super Admin / Admin only)."""
    updated = add_item_controller(
        category=category,
        value=payload.value,
        current_admin=current_admin,
        request=request,
    )
    return success_response(
        data=updated,
        message=f"Added '{payload.value}' to '{category}'",
    )


@router.delete("/{category}/{value}", response_model=APIResponse[list])
def remove_master_data_item(
    category: str,
    value: str,
    request: Request,
    current_admin: User = Depends(require_roles("super_admin")),
):
    """Remove an option from a master data category (Super Admin only)."""
    updated = remove_item_controller(
        category=category,
        value=value,
        current_admin=current_admin,
        request=request,
    )
    return success_response(
        data=updated,
        message=f"Removed '{value}' from '{category}'",
    )


@router.put("/{category}", response_model=APIResponse[list])
def update_master_data_category(
    category: str,
    payload: MasterDataCategoryUpdate,
    request: Request,
    current_admin: User = Depends(require_roles("super_admin")),
):
    """Replace all items in a master data category (Super Admin only)."""
    updated = update_category_controller(
        category=category,
        items=payload.items,
        current_admin=current_admin,
        request=request,
    )
    return success_response(
        data=updated,
        message=f"Category '{category}' updated successfully",
    )

