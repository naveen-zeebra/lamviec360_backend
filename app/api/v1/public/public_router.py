from typing import Optional, List
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.core.database import get_db
from app.models.job import Job
from app.models.company import Company
from app.models.enums import JobStatus, CompanyApprovalStatus
from app.schemas.job import JobOut

router = APIRouter(prefix="/public", tags=["Public Data & Job Board"])

DEFAULT_MASTER_DATA = {
    "industries": ["Technology", "Manufacturing", "Retail", "Finance", "Logistics", "Hospitality", "Healthcare", "Education"],
    "companySizes": ["1-10", "11-50", "51-200", "201-500", "500+"],
    "jobTypes": ["Full-time", "Part-time", "Contract", "Internship", "Remote"],
}


@router.get("/jobs", response_model=List[JobOut])
def get_public_jobs(
    q: Optional[str] = Query(None, description="Search keyword in title or description"),
    location: Optional[str] = Query(None),
    job_type: Optional[str] = Query(None),
    department: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """Public job search endpoint returning only Published jobs from Active companies."""
    query = (
        db.query(Job)
        .join(Company, Job.company_id == Company.id)
        .filter(Job.status == JobStatus.PUBLISHED, Company.approval_status == CompanyApprovalStatus.ACTIVE)
    )

    if q:
        search_pattern = f"%{q}%"
        query = query.filter(or_(Job.title.ilike(search_pattern), Job.jd.ilike(search_pattern)))
    if location:
        query = query.filter(Job.location.ilike(f"%{location}%"))
    if job_type:
        query = query.filter(Job.type.ilike(f"%{job_type}%"))
    if department:
        query = query.filter(Job.department.ilike(f"%{department}%"))

    jobs = query.order_by(Job.created_at.desc()).offset(offset).limit(limit).all()

    result = []
    for j in jobs:
        result.append(
            JobOut(
                id=j.id,
                company_id=j.company_id,
                company_name=j.company.name if j.company else "",
                company_logo=j.company.logo if j.company else "",
                title=j.title,
                department=j.department,
                type=j.type,
                location=j.location,
                salary_min=j.salary_min,
                salary_max=j.salary_max,
                negotiable=j.negotiable,
                jd=j.jd,
                skills=j.skills or [],
                experience=j.experience,
                education=j.education,
                deadline=j.deadline.strftime("%Y-%m-%d") if j.deadline else None,
                vacancies=j.vacancies,
                documents=j.documents or ["CV / Resume"],
                status=j.status.value,
                ai_generated=j.ai_generated,
                created_at=j.created_at.strftime("%Y-%m-%d"),
                applicant_count=len(j.applications) if j.applications else 0,
            )
        )
    return result


@router.get("/jobs/{id}", response_model=JobOut)
def get_public_job_detail(id: str, db: Session = Depends(get_db)):
    """Fetch details of a single public job."""
    j = db.query(Job).filter(Job.id == id).first()
    if not j or j.status != JobStatus.PUBLISHED:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found or no longer active")

    return JobOut(
        id=j.id,
        company_id=j.company_id,
        company_name=j.company.name if j.company else "",
        company_logo=j.company.logo if j.company else "",
        title=j.title,
        department=j.department,
        type=j.type,
        location=j.location,
        salary_min=j.salary_min,
        salary_max=j.salary_max,
        negotiable=j.negotiable,
        jd=j.jd,
        skills=j.skills or [],
        experience=j.experience,
        education=j.education,
        deadline=j.deadline.strftime("%Y-%m-%d") if j.deadline else None,
        vacancies=j.vacancies,
        documents=j.documents or ["CV / Resume"],
        status=j.status.value,
        ai_generated=j.ai_generated,
        created_at=j.created_at.strftime("%Y-%m-%d"),
        applicant_count=len(j.applications) if j.applications else 0,
    )


@router.get("/master-data")
def get_master_data():
    """Returns platform metadata: industries, company size ranges, job types."""
    return DEFAULT_MASTER_DATA
