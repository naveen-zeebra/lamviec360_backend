# ─────────────────────────────────────────────────────────────────────────────
# File    : services/company_service/app/api/jobs/service.py
# Purpose : Domain & persistence logic for Company Job Postings
# ─────────────────────────────────────────────────────────────────────────────

import json
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import desc

from shared.models import User, CompanyProfile, JobPosting
from shared.utils.error_handler import service_error_handler
from shared.utils.logger import get_logger

logger = get_logger("company_jobs_service")


from ..tenant import get_tenant_profile

@service_error_handler
def get_company_tenant(user: User) -> Optional[CompanyProfile]:
    """Return the associated company profile for a user."""
    from shared.database.session import SessionLocal
    with SessionLocal() as db:
        return get_tenant_profile(db, user)

@service_error_handler
def get_or_create_company_tenant(db: Session, user: User) -> CompanyProfile:
    """Ensure company profile exists before creating jobs."""
    return get_tenant_profile(db, user)


from datetime import datetime


def parse_deadline(val: Any) -> Optional[datetime]:
    if not val:
        return None
    if isinstance(val, datetime):
        return val
    if isinstance(val, str):
        val_str = val.strip()
        for fmt in (
            "%Y-%m-%d",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%dT%H:%M:%S.%f",
            "%Y-%m-%d %H:%M:%S.%f",
        ):
            try:
                return datetime.strptime(val_str[:19], fmt[:19])
            except ValueError:
                continue
    return None


def serialize_job(j: JobPosting) -> Dict[str, Any]:
    """Serialize JobPosting entity to dictionary with frontend compatibility fields."""
    docs = []
    if getattr(j, "documents", None):
        try:
            parsed = json.loads(j.documents)
            docs = parsed if isinstance(parsed, list) else [str(parsed)]
        except Exception:
            docs = [d.strip() for d in str(j.documents).split(",") if d.strip()]
    if not docs:
        docs = ["CV / Resume"]

    sal_min = float(j.salary_min) if j.salary_min is not None else None
    sal_max = float(j.salary_max) if j.salary_max is not None else None
    deadline_iso = j.expires_at.isoformat() if j.expires_at else None
    deadline_str = j.expires_at.strftime("%Y-%m-%d") if j.expires_at else ""

    skills_list = [s.strip() for s in (j.required_skills or "").split(",") if s.strip()]

    return {
        "id": j.id,
        "title": j.title,
        "department": getattr(j, "department", None) or "",
        "job_type": j.job_type,
        "type": j.job_type,
        "workplace_type": j.workplace_type,
        "experience_level": j.experience_level,
        "experience": j.experience_level or "",
        "city": j.city or "",
        "location": j.city or "",
        "country": j.country or "Vietnam",
        "salary_min": sal_min,
        "salary_max": sal_max,
        "salaryMin": sal_min,
        "salaryMax": sal_max,
        "salary_currency": j.salary_currency or "VND",
        "is_negotiable": bool(j.is_negotiable),
        "negotiable": bool(j.is_negotiable),
        "vacancies": getattr(j, "vacancies", None) if getattr(j, "vacancies", None) is not None else 1,
        "education": getattr(j, "education", None) or "Bachelor's Degree",
        "documents": docs,
        "status": j.status,
        "moderation_status": j.moderation_status,
        "views_count": j.views_count,
        "applications_count": j.applications_count,
        "applicant_count": j.applications_count,
        "deadline": deadline_str or deadline_iso or "",
        "expires_at": deadline_iso,
        "created_at": j.created_at.isoformat() if j.created_at else None,
        "skills": skills_list,
        "required_skills": j.required_skills or ", ".join(skills_list),
        "description": j.description,
        "jd": j.description,
        "requirements": j.requirements,
        "benefits": j.benefits,
    }


@service_error_handler
def list_company_jobs(
    db: Session,
    company_id: int,
    status_filter: Optional[str] = None,
    page: int = 1,
    page_size: int = 10,
) -> Tuple[List[Dict[str, Any]], int]:
    """Fetch paginated jobs for a specific company."""
    query = db.query(JobPosting).filter(
        JobPosting.company_id == company_id,
        JobPosting.is_deleted == False,
    )
    if status_filter:
        query = query.filter(JobPosting.status == status_filter)

    total_items = query.count()
    offset = (page - 1) * page_size
    jobs = query.order_by(desc(JobPosting.created_at)).offset(offset).limit(page_size).all()

    items = [serialize_job(j) for j in jobs]
    return items, total_items


@service_error_handler
def create_job_posting(db: Session, company_id: int, data: Any) -> JobPosting:
    """Create a new job posting for the company."""
    if hasattr(data, "model_dump"):
        data = data.model_dump()
    elif hasattr(data, "dict"):
        data = data.dict()

    raw_status = (data.get("status") or "published").lower()
    init_status = "published" if raw_status in ("active", "published") else raw_status

    # City / Location resolution
    city_val = data.get("city") or data.get("location")

    # Job type resolution
    job_type_val = data.get("job_type") or data.get("type") or "Full-time"

    # Negotiable resolution
    is_neg = False
    if data.get("is_negotiable") is not None:
        is_neg = bool(data.get("is_negotiable"))
    elif data.get("negotiable") is not None:
        is_neg = bool(data.get("negotiable"))

    # Skills resolution
    skills_raw = data.get("required_skills") if data.get("required_skills") is not None else data.get("skills")
    if isinstance(skills_raw, list):
        required_skills_val = ", ".join(str(s).strip() for s in skills_raw if str(s).strip())
    elif isinstance(skills_raw, str):
        required_skills_val = skills_raw.strip()
    else:
        required_skills_val = None

    # Documents resolution
    docs_raw = data.get("documents")
    if isinstance(docs_raw, list):
        documents_val = json.dumps(docs_raw)
    elif isinstance(docs_raw, str):
        documents_val = docs_raw
    else:
        documents_val = json.dumps(["CV / Resume"])

    # Deadline / expires_at resolution
    expires_at_val = parse_deadline(data.get("expires_at") or data.get("deadline"))

    # Salaries
    sal_min = data.get("salary_min") if data.get("salary_min") is not None else data.get("salaryMin")
    sal_max = data.get("salary_max") if data.get("salary_max") is not None else data.get("salaryMax")

    # Experience
    exp_val = data.get("experience_level") or data.get("experience") or "Mid-level"

    # Vacancies
    vac_raw = data.get("vacancies")
    try:
        vac_val = int(vac_raw) if vac_raw is not None else 1
    except (ValueError, TypeError):
        vac_val = 1

    job = JobPosting(
        company_id=company_id,
        title=data["title"],
        description=data["description"],
        department=data.get("department"),
        requirements=data.get("requirements"),
        benefits=data.get("benefits"),
        job_type=job_type_val,
        workplace_type=data.get("workplace_type", "On-site"),
        experience_level=exp_val,
        city=city_val,
        country=data.get("country", "Vietnam"),
        salary_min=sal_min,
        salary_max=sal_max,
        salary_currency=data.get("salary_currency", "VND"),
        is_negotiable=is_neg,
        required_skills=required_skills_val,
        education=data.get("education", "Bachelor's Degree"),
        vacancies=vac_val,
        documents=documents_val,
        expires_at=expires_at_val,
        status=init_status,
        moderation_status="approved",
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    logger.info(f"Created job posting id={job.id} for company_id={company_id}")
    return job


@service_error_handler
def get_job_by_id(db: Session, company_id: int, job_id: int) -> Optional[JobPosting]:
    """Find a non-deleted job belonging to this company."""
    return db.query(JobPosting).filter(
        JobPosting.id == job_id,
        JobPosting.company_id == company_id,
        JobPosting.is_deleted == False,
    ).first()


@service_error_handler
def update_job_posting(db: Session, job: JobPosting, data: Any) -> JobPosting:
    """Update fields on a job posting."""
    if hasattr(data, "model_dump"):
        data = data.model_dump(exclude_unset=True)
    elif hasattr(data, "dict"):
        data = data.dict(exclude_unset=True)

    if "title" in data and data["title"] is not None:
        job.title = data["title"]
    if "description" in data and data["description"] is not None:
        job.description = data["description"]
    if "department" in data:
        job.department = data["department"]
    if "requirements" in data:
        job.requirements = data["requirements"]
    if "benefits" in data:
        job.benefits = data["benefits"]

    if "job_type" in data and data["job_type"] is not None:
        job.job_type = data["job_type"]
    elif "type" in data and data["type"] is not None:
        job.job_type = data["type"]

    if "workplace_type" in data and data["workplace_type"] is not None:
        job.workplace_type = data["workplace_type"]

    if "experience_level" in data and data["experience_level"] is not None:
        job.experience_level = data["experience_level"]
    elif "experience" in data and data["experience"] is not None:
        job.experience_level = data["experience"]

    if "city" in data and data["city"] is not None:
        job.city = data["city"]
    elif "location" in data and data["location"] is not None:
        job.city = data["location"]

    if "country" in data and data["country"] is not None:
        job.country = data["country"]

    sal_min = data.get("salary_min") if data.get("salary_min") is not None else data.get("salaryMin")
    if sal_min is not None:
        job.salary_min = sal_min

    sal_max = data.get("salary_max") if data.get("salary_max") is not None else data.get("salaryMax")
    if sal_max is not None:
        job.salary_max = sal_max

    if "salary_currency" in data and data["salary_currency"] is not None:
        job.salary_currency = data["salary_currency"]

    if "is_negotiable" in data and data["is_negotiable"] is not None:
        job.is_negotiable = bool(data["is_negotiable"])
    elif "negotiable" in data and data["negotiable"] is not None:
        job.is_negotiable = bool(data["negotiable"])

    skills_raw = data.get("required_skills") if data.get("required_skills") is not None else data.get("skills")
    if skills_raw is not None:
        if isinstance(skills_raw, list):
            job.required_skills = ", ".join(str(s).strip() for s in skills_raw if str(s).strip())
        else:
            job.required_skills = str(skills_raw).strip()

    if "education" in data:
        job.education = data["education"]

    if "vacancies" in data and data["vacancies"] is not None:
        try:
            job.vacancies = int(data["vacancies"])
        except (ValueError, TypeError):
            pass

    if "documents" in data and data["documents"] is not None:
        if isinstance(data["documents"], list):
            job.documents = json.dumps(data["documents"])
        else:
            job.documents = str(data["documents"])

    if "expires_at" in data or "deadline" in data:
        raw_deadline = data.get("expires_at") or data.get("deadline")
        job.expires_at = parse_deadline(raw_deadline)

    if "status" in data and data["status"] is not None:
        raw_status = data["status"].lower()
        job.status = "published" if raw_status in ("active", "published") else raw_status

    db.commit()
    db.refresh(job)
    logger.info(f"Updated job posting id={job.id}")
    return job


@service_error_handler
def toggle_job_status(db: Session, job: JobPosting, new_status: str) -> str:
    """Toggle job publication/lifecycle status."""
    norm = new_status.lower()
    if norm == "active":
        norm = "published"
    job.status = norm
    db.commit()
    logger.info(f"Job id={job.id} status changed to {norm}")
    return norm


@service_error_handler
def duplicate_job(db: Session, company_id: int, source_job: JobPosting) -> JobPosting:
    """Duplicate an existing job as a draft."""
    new_job = JobPosting(
        company_id=company_id,
        title=f"{source_job.title} (Copy)",
        description=source_job.description,
        department=source_job.department,
        requirements=source_job.requirements,
        benefits=source_job.benefits,
        job_type=source_job.job_type,
        workplace_type=source_job.workplace_type,
        experience_level=source_job.experience_level,
        city=source_job.city,
        country=source_job.country,
        salary_min=source_job.salary_min,
        salary_max=source_job.salary_max,
        salary_currency=source_job.salary_currency,
        is_negotiable=source_job.is_negotiable,
        required_skills=source_job.required_skills,
        vacancies=source_job.vacancies,
        education=source_job.education,
        documents=source_job.documents,
        expires_at=source_job.expires_at,
        status="draft",
        moderation_status="approved",
    )
    db.add(new_job)
    db.commit()
    db.refresh(new_job)
    logger.info(f"Duplicated job id={source_job.id} -> new job id={new_job.id}")
    return new_job


@service_error_handler
def delete_job(db: Session, job: JobPosting) -> None:
    """Soft delete a job posting."""
    job.is_deleted = True
    db.commit()
    logger.info(f"Soft-deleted job id={job.id}")
