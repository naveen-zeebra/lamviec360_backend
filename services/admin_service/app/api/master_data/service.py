# ─────────────────────────────────────────────────────────────────────────────
# File    : services/admin_service/app/api/master_data/service.py
# Purpose : Domain and storage logic for Master Data / Configurable Lists (BR-010)
# ─────────────────────────────────────────────────────────────────────────────

import os
import json
import threading
from typing import Dict, List, Optional
from shared.utils.error_handler import service_error_handler
from shared.utils.logger import get_logger

logger = get_logger("admin_master_data_service")

# Data directory and storage file
DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../../shared/data"))
STORAGE_FILE = os.path.join(DATA_DIR, "master_data.json")

_lock = threading.Lock()

DEFAULT_MASTER_DATA: Dict[str, List[str]] = {
    "jobTypes": [
        "Full-time",
        "Part-time",
        "Contract",
        "Internship",
        "Remote",
        "Temporary",
    ],
    "companySizes": [
        "1–10",
        "11–50",
        "51–200",
        "201–500",
        "500+",
    ],
    "industries": [
        "Technology",
        "Software & IT",
        "Finance & Banking",
        "Manufacturing",
        "Retail & Commerce",
        "Logistics",
        "Hospitality",
        "Healthcare",
        "Education",
        "Other",
    ],
    "locations": [
        "Ho Chi Minh City",
        "Hanoi",
        "Da Nang",
        "Can Tho",
        "Hai Phong",
        "Binh Duong",
        "Dong Nai",
        "Remote",
    ],
    "departments": [
        "Engineering & Technology",
        "Product & Design",
        "Marketing & Communications",
        "Sales & Business Development",
        "Human Resources & Talent",
        "Finance & Accounting",
        "Customer Success & Operations",
        "Legal & Compliance",
        "Administration",
    ],
}

CATEGORY_MAP = {
    "jobtypes": "jobTypes",
    "job_types": "jobTypes",
    "companysizes": "companySizes",
    "company_sizes": "companySizes",
    "industries": "industries",
    "industry": "industries",
    "locations": "locations",
    "location": "locations",
    "departments": "departments",
    "department": "departments",
}


def _normalize_category(cat: str) -> Optional[str]:
    k = cat.lower().replace("-", "_")
    return CATEGORY_MAP.get(k, cat if cat in DEFAULT_MASTER_DATA else None)


def _ensure_storage_exists() -> None:
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR, exist_ok=True)
    if not os.path.exists(STORAGE_FILE):
        with open(STORAGE_FILE, "w", encoding="utf-8") as f:
            json.dump(DEFAULT_MASTER_DATA, f, ensure_ascii=False, indent=2)


@service_error_handler
def get_all_master_data() -> Dict[str, List[str]]:
    """Retrieve full master data taxonomy dictionary."""
    with _lock:
        _ensure_storage_exists()
        try:
            with open(STORAGE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            # Ensure all expected keys exist
            for k, default_vals in DEFAULT_MASTER_DATA.items():
                if k not in data or not isinstance(data[k], list):
                    data[k] = default_vals
            return data
        except Exception as err:
            logger.error("Failed to read master data storage: %s", err)
            return DEFAULT_MASTER_DATA.copy()


@service_error_handler
def get_category_items(category: str) -> Optional[List[str]]:
    """Get item list for a specific category."""
    canonical = _normalize_category(category)
    if not canonical:
        return None
    data = get_all_master_data()
    return data.get(canonical, [])


@service_error_handler
def add_master_item(category: str, value: str) -> Optional[List[str]]:
    """Add a new item to a master data category."""
    canonical = _normalize_category(category)
    if not canonical or not value or not value.strip():
        return None

    clean_val = value.strip()
    with _lock:
        data = get_all_master_data()
        items = data.get(canonical, [])
        if clean_val not in items:
            items.append(clean_val)
            data[canonical] = items
            with open(STORAGE_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        return items


@service_error_handler
def remove_master_item(category: str, value: str) -> Optional[List[str]]:
    """Remove an item from a master data category."""
    canonical = _normalize_category(category)
    if not canonical:
        return None

    clean_val = value.strip()
    with _lock:
        data = get_all_master_data()
        items = data.get(canonical, [])
        if clean_val in items:
            items = [x for x in items if x != clean_val]
            data[canonical] = items
            with open(STORAGE_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        return items


@service_error_handler
def update_category_items(category: str, new_items: List[str]) -> Optional[List[str]]:
    """Replace and reorder items for a category."""
    canonical = _normalize_category(category)
    if not canonical or not isinstance(new_items, list):
        return None

    clean_items = [str(x).strip() for x in new_items if str(x).strip()]
    with _lock:
        data = get_all_master_data()
        data[canonical] = clean_items
        with open(STORAGE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return clean_items

