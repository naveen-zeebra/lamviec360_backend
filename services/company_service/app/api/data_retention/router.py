# ─────────────────────────────────────────────────────────────────────────────
# File    : services/company_service/app/api/data_retention/router.py
# Purpose : Presentation layer (FastAPI endpoints) for Company Data Retention
# ─────────────────────────────────────────────────────────────────────────────

from typing import Any
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from shared.database.session import get_db
from shared.schemas import APIResponse
from shared.utils import get_current_company_user, success_response

from .controller import purge_company_data_controller

router = APIRouter(prefix="/data-retention", tags=["Data Retention"])


@router.post("/purge", response_model=APIResponse[dict], summary="Purge Expired Candidate Data")
def purge_company_data(
    months: int = Query(6, ge=1, description="Threshold in months to purge candidate applications"),
    user: Any = Depends(get_current_company_user),
    db: Session = Depends(get_db),
):
    result = purge_company_data_controller(months, user, db)
    return success_response(
        data={"purged_count": result["purged_count"]},
        message=result["message"],
    )
