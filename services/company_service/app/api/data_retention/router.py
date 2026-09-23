from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from shared.database.session import get_db
from shared.models import User
from shared.schemas import APIResponse
from shared.utils import get_current_user, require_user_type, success_response

router = APIRouter(prefix="/data-retention", tags=["Data Retention"])

@router.post("/purge", response_model=APIResponse[dict])
def purge_company_data(
    months: int = Query(6, ge=1),
    user: User = Depends(require_user_type("company", "super_admin")),
    db: Session = Depends(get_db),
):
    # Mock data purge logic
    return success_response(message=f"Data older than {months} months purged successfully")
