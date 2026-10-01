# ─────────────────────────────────────────────────────────────────────────────
# File    : services/company_service/app/api/data_retention/service.py
# Purpose : Domain & data lifecycle logic for Company Data Retention
# ─────────────────────────────────────────────────────────────────────────────

from datetime import datetime, timedelta, timezone
from typing import Optional
from sqlalchemy.orm import Session

from shared.models import User, CompanyProfile, JobPosting, JobApplication
from shared.utils.error_handler import service_error_handler
from shared.utils.logger import get_logger

logger = get_logger("company_data_retention_service")


@service_error_handler
def get_company_tenant(user: User) -> Optional[CompanyProfile]:
    from ..tenant import get_tenant_profile
    from shared.database.session import SessionLocal
    with SessionLocal() as db:
        return get_tenant_profile(db, user)


@service_error_handler
def purge_expired_company_applications(db: Session, company_id: int, months: int) -> int:
    """Purge candidate applications older than the retention threshold for company."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=months * 30)

    matching_apps = (
        db.query(JobApplication.id)
        .join(JobPosting, JobApplication.job_id == JobPosting.id)
        .filter(
            JobPosting.company_id == company_id,
            JobApplication.created_at < cutoff,
            JobApplication.status.in_(["rejected", "withdrawn"]),
        )
        .all()
    )
    ids_to_purge = [r[0] for r in matching_apps]

    deleted_count = 0
    if ids_to_purge:
        deleted_count = (
            db.query(JobApplication)
            .filter(JobApplication.id.in_(ids_to_purge))
            .delete(synchronize_session=False)
        )
        db.commit()

    logger.info(f"Purged {deleted_count} candidate applications for company_id={company_id}")
    return deleted_count
