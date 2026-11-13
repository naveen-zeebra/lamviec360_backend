# ─────────────────────────────────────────────────────────────────────────────
# File    : services/admin_service/app/api/master_data/schemas.py
# Purpose : Pydantic schemas for platform master data / configurable lists (BR-010)
# ─────────────────────────────────────────────────────────────────────────────

from typing import List, Dict
from pydantic import BaseModel, Field


class MasterDataItemCreate(BaseModel):
    value: str = Field(..., min_length=1, description="New master data item value to add")


class MasterDataItemEdit(BaseModel):
    old_value: str = Field(..., min_length=1, description="Existing master data item value to replace")
    new_value: str = Field(..., min_length=1, description="New replacement value")


class MasterDataCategoryUpdate(BaseModel):
    items: List[str] = Field(..., description="Complete replacement list for the category")


class MasterDataResponse(BaseModel):
    jobTypes: List[str]
    companySizes: List[str]
    industries: List[str]
    locations: List[str]
    departments: List[str] = Field(default_factory=list)

