# ─────────────────────────────────────────────────────────────────────────────
# File    : services/admin_service/app/api/master_data/controller.py
# Purpose : Controller layer for Platform Master Data & Taxonomy (BR-010)
# ─────────────────────────────────────────────────────────────────────────────

from typing import Dict, List, Optional
from fastapi import HTTPException, status, Request

from shared.models import User
from shared.utils import log_audit_event
from shared.utils.logger import get_logger
from .service import (
    get_all_master_data,
    get_category_items,
    add_master_item,
    remove_master_item,
    update_category_items,
    edit_master_item,
)

logger = get_logger("admin_master_data_controller")


def list_master_data_controller() -> Dict[str, List[str]]:
    """Retrieve all master data taxonomy lists."""
    return get_all_master_data()


def get_category_controller(category: str) -> List[str]:
    """Retrieve items for a specific master data category."""
    items = get_category_items(category)
    if items is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Master data category '{category}' not found",
        )
    return items


def add_item_controller(
    category: str,
    value: str,
    current_admin: Optional[User] = None,
    request: Optional[Request] = None,
) -> List[str]:
    """Add a new item to the category."""
    updated = add_master_item(category, value)
    if updated is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to add '{value}' to category '{category}'",
        )

    if current_admin:
        try:
            from shared.database.session import SessionLocal
            with SessionLocal() as db:
                log_audit_event(
                    db=db,
                    action="CREATE",
                    module="MASTER_DATA",
                    description=f"Added '{value}' to master data category '{category}'",
                    user_id=current_admin.id,
                    user_email=current_admin.email,
                    user_type="super_admin",
                    details={"category": category, "added_item": value},
                    request=request,
                )
        except Exception as e:
            logger.warning("Audit log error on master data add: %s", e)

    return updated


def remove_item_controller(
    category: str,
    value: str,
    current_admin: Optional[User] = None,
    request: Optional[Request] = None,
) -> List[str]:
    """Remove an item from the category."""
    updated = remove_master_item(category, value)
    if updated is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to remove '{value}' from category '{category}'",
        )

    if current_admin:
        try:
            from shared.database.session import SessionLocal
            with SessionLocal() as db:
                log_audit_event(
                    db=db,
                    action="DELETE",
                    module="MASTER_DATA",
                    description=f"Removed '{value}' from master data category '{category}'",
                    user_id=current_admin.id,
                    user_email=current_admin.email,
                    user_type="super_admin",
                    details={"category": category, "removed_item": value},
                    request=request,
                )
        except Exception as e:
            logger.warning("Audit log error on master data remove: %s", e)

    return updated


def update_category_controller(
    category: str,
    items: List[str],
    current_admin: Optional[User] = None,
    request: Optional[Request] = None,
) -> List[str]:
    """Update all items in a category."""
    updated = update_category_items(category, items)
    if updated is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to update category '{category}'",
        )

    if current_admin:
        try:
            from shared.database.session import SessionLocal
            with SessionLocal() as db:
                log_audit_event(
                    db=db,
                    action="UPDATE",
                    module="MASTER_DATA",
                    description=f"Updated items in master data category '{category}'",
                    user_id=current_admin.id,
                    user_email=current_admin.email,
                    user_type="super_admin",
                    details={"category": category, "count": len(items)},
                    request=request,
                )
        except Exception as e:
            logger.warning("Audit log error on master data update: %s", e)

    return updated


def edit_item_controller(
    category: str,
    old_value: str,
    new_value: str,
    current_admin: Optional[User] = None,
    request: Optional[Request] = None,
) -> List[str]:
    """Edit / rename an existing item in the category."""
    updated = edit_master_item(category, old_value, new_value)
    if updated is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to edit item '{old_value}' in category '{category}'",
        )

    if current_admin:
        try:
            from shared.database.session import SessionLocal
            with SessionLocal() as db:
                log_audit_event(
                    db=db,
                    action="UPDATE",
                    module="MASTER_DATA",
                    description=f"Renamed '{old_value}' to '{new_value}' in master data category '{category}'",
                    user_id=current_admin.id,
                    user_email=current_admin.email,
                    user_type="super_admin",
                    details={"category": category, "old_value": old_value, "new_value": new_value},
                    request=request,
                )
        except Exception as e:
            logger.warning("Audit log error on master data edit: %s", e)

    return updated


