from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from shared.database.session import get_db
from shared.models import User, JobSeekerProfile, SavedJob, JobPosting
from shared.schemas import (
    JobSeekerProfileUpdate,
    JobSeekerProfileOut,
    APIResponse,
)
from shared.utils import get_current_user, require_user_type, success_response

router = APIRouter(prefix="/profile", tags=["Job Seeker Profile"])

@router.get("", response_model=APIResponse[dict])
def get_jobseeker_profile(
    user: User = Depends(require_user_type("jobseeker", "super_admin")),
    db: Session = Depends(get_db),
):
    profile = db.query(JobSeekerProfile).filter(JobSeekerProfile.user_id == user.id).first()
    if not profile:
        profile = JobSeekerProfile(user_id=user.id)
        db.add(profile)
        db.commit()
        db.refresh(profile)

    return success_response(
        data={
            "id": profile.id,
            "user_id": user.id,
            "full_name": user.full_name,
            "email": user.email,
            "phone": user.phone,
            "avatar_url": user.avatar_url,
            "headline": profile.headline,
            "bio": profile.bio,
            "resume_url": profile.resume_url,
            "skills": profile.skills,
            "experience_years": float(profile.experience_years or 0),
            "expected_salary": float(profile.expected_salary) if profile.expected_salary else None,
            "city": profile.city,
            "country": profile.country,
            "github_url": profile.github_url,
            "linkedin_url": profile.linkedin_url,
        }
    )

@router.put("", response_model=APIResponse[dict])
def update_jobseeker_profile(
    data: JobSeekerProfileUpdate,
    user: User = Depends(require_user_type("jobseeker", "super_admin")),
    db: Session = Depends(get_db),
):
    profile = db.query(JobSeekerProfile).filter(JobSeekerProfile.user_id == user.id).first()
    if not profile:
        profile = JobSeekerProfile(user_id=user.id)
        db.add(profile)

    # Update User attributes
    if data.full_name is not None:
        user.full_name = data.full_name
    if data.phone is not None:
        user.phone = data.phone
    if data.avatar_url is not None:
        user.avatar_url = data.avatar_url

    # Update Profile attributes
    profile_fields = [
        "headline", "bio", "resume_url", "skills",
        "experience_years", "expected_salary", "city",
        "country", "github_url", "linkedin_url"
    ]
    for field in profile_fields:
        if hasattr(data, field):
            val = getattr(data, field)
            if val is not None:
                setattr(profile, field, val)

    db.commit()
    db.refresh(profile)
    db.refresh(user)

    return success_response(
        data={
            "id": profile.id,
            "user_id": user.id,
            "full_name": user.full_name,
            "phone": user.phone,
            "avatar_url": user.avatar_url,
            "email": user.email,
            "headline": profile.headline,
            "bio": profile.bio,
            "resume_url": profile.resume_url,
            "skills": profile.skills,
            "experience_years": float(profile.experience_years or 0),
            "expected_salary": float(profile.expected_salary) if profile.expected_salary else None,
            "city": profile.city,
            "country": profile.country,
            "github_url": profile.github_url,
            "linkedin_url": profile.linkedin_url,
        },
        message="Profile updated successfully",
    )

@router.get("/saved-jobs", response_model=APIResponse[list])
def get_saved_jobs(
    user: User = Depends(require_user_type("jobseeker", "super_admin")),
    db: Session = Depends(get_db),
):
    profile = db.query(JobSeekerProfile).filter(JobSeekerProfile.user_id == user.id).first()
    if not profile:
        return success_response(data=[])

    saved = db.query(SavedJob).filter(SavedJob.jobseeker_id == profile.id).all()
    results = []
    for s in saved:
        if s.job and not s.job.is_deleted:
            results.append({
                "saved_id": s.id,
                "saved_at": s.created_at,
                "job": {
                    "id": s.job.id,
                    "title": s.job.title,
                    "job_type": s.job.job_type,
                    "city": s.job.city,
                    "country": s.job.country,
                    "location": f"{s.job.city}, {s.job.country}" if s.job.city and s.job.country else (s.job.city or s.job.country or "Remote"),
                    "salary_min": float(s.job.salary_min) if s.job.salary_min else None,
                    "salary_max": float(s.job.salary_max) if s.job.salary_max else None,
                    "salary_currency": getattr(s.job, "salary_currency", "VND") or "VND",
                    "workplace_type": getattr(s.job, "workplace_type", "On-site") or "On-site",
                    "company_name": s.job.company.company_name if s.job.company else "Unknown",
                    "company_logo": s.job.company.logo_url if s.job.company else None,
                }
            })
    return success_response(data=results)

@router.post("/saved-jobs/{job_id}", response_model=APIResponse[dict])
def save_job(
    job_id: int,
    user: User = Depends(require_user_type("jobseeker", "super_admin")),
    db: Session = Depends(get_db),
):
    profile = db.query(JobSeekerProfile).filter(JobSeekerProfile.user_id == user.id).first()
    if not profile:
        profile = JobSeekerProfile(user_id=user.id)
        db.add(profile)
        db.flush()

    job = db.query(JobPosting).filter(JobPosting.id == job_id, JobPosting.is_deleted == False).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    existing = db.query(SavedJob).filter(SavedJob.jobseeker_id == profile.id, SavedJob.job_id == job_id).first()
    if existing:
        return success_response(message="Job already saved")

    new_saved = SavedJob(jobseeker_id=profile.id, job_id=job_id)
    db.add(new_saved)
    db.commit()
    return success_response(message="Job saved successfully")

@router.delete("/saved-jobs/{job_id}", response_model=APIResponse[None])
def unsave_job(
    job_id: int,
    user: User = Depends(require_user_type("jobseeker", "super_admin")),
    db: Session = Depends(get_db),
):
    profile = db.query(JobSeekerProfile).filter(JobSeekerProfile.user_id == user.id).first()
    if not profile:
        return success_response(message="Job unsaved")

    db.query(SavedJob).filter(SavedJob.jobseeker_id == profile.id, SavedJob.job_id == job_id).delete()
    db.commit()
    return success_response(message="Job removed from saved list")
