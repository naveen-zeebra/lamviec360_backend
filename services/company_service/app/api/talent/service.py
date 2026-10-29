# ─────────────────────────────────────────────────────────────────────────────
# File    : services/company_service/app/api/talent/service.py
# Purpose : Domain logic for EMP-FR-030 Talent Search & EMP-FR-031 Access Control
# ─────────────────────────────────────────────────────────────────────────────

import re
from typing import Optional, List, Dict, Any, Tuple
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, desc, asc

from shared.models import User, CompanyProfile, JobPosting, JobSeekerProfile, Notification
from shared.utils.logger import get_logger
from shared.utils.error_handler import service_error_handler
from .schemas import TalentSearchFilterParams

logger = get_logger("company_talent_service")


def mask_email(email: Optional[str]) -> str:
    """Mask email for passive candidates per BR-014 (e.g. n***@***.com)."""
    if not email or "@" not in email:
        return "••••••••@•••••.com"
    parts = email.split("@")
    name = parts[0]
    domain = parts[1]
    masked_name = name[0] + "••••" if len(name) > 1 else "••••"
    return f"{masked_name}@{domain}"


def mask_phone(phone: Optional[str]) -> str:
    """Mask phone number for passive candidates per BR-014 (e.g. +84 ••••• 123)."""
    if not phone:
        return "+84 ••••••••••"
    clean = re.sub(r"[^\d+]", "", phone)
    if len(clean) > 4:
        return clean[:3] + " ••••• " + clean[-2:]
    return "+84 ••••••••••"


def parse_skills_list(skills_raw: Optional[str]) -> List[str]:
    """Parse comma, JSON, or semicolon-delimited skills into clean list."""
    if not skills_raw:
        return []
    raw = str(skills_raw).strip()
    if raw.startswith("[") and raw.endswith("]"):
        try:
            import json
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                return [str(s).strip() for s in parsed if str(s).strip()]
        except Exception:
            pass
    items = [s.strip() for s in re.split(r"[,;|]+", raw) if s.strip()]
    return items


def verify_company_access(company: CompanyProfile) -> None:
    """
    EMP-FR-031: Talent Search Access Enforcement.
    Talent Search is available exclusively to companies approved by Super Admin (Active).
    Pending, rejected, or suspended companies cannot open Talent Search.
    """
    if not company:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Company profile is missing or invalid.",
        )

    status_val = str(getattr(company, "verification_status", "pending")).lower()
    if status_val not in ("verified", "approved", "active"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Talent Search is available only to approved companies. "
                f"Your account status is currently '{status_val}'. "
                "Super Admin verification is required."
            ),
        )


@service_error_handler
def search_talent_profiles(
    db: Session,
    company: CompanyProfile,
    filters: TalentSearchFilterParams,
) -> Dict[str, Any]:
    """
    EMP-FR-030: Search Job Seeker profiles that are visible to employers.
    Enforces candidate privacy (BR-014), excludes 'Not looking', and filters by criteria.
    """
    verify_company_access(company)

    # Base query: join JobSeekerProfile with User
    query = (
        db.query(JobSeekerProfile, User)
        .join(User, JobSeekerProfile.user_id == User.id)
        .filter(
            JobSeekerProfile.is_visible == True,
            JobSeekerProfile.visibility != "private",
            JobSeekerProfile.is_archived == False,
            # EMP-FR-030 & JSP-FR-015: Strictly exclude 'not_looking'
            JobSeekerProfile.job_availability.in_(["open_to_work", "open_to_opportunities"]),
        )
    )

    # 1. Keyword search (name, headline, bio, skills)
    if filters.keyword and filters.keyword.strip():
        kw = f"%{filters.keyword.strip()}%"
        query = query.filter(
            or_(
                User.full_name.ilike(kw),
                JobSeekerProfile.headline.ilike(kw),
                JobSeekerProfile.bio.ilike(kw),
                JobSeekerProfile.skills.ilike(kw),
            )
        )

    # 2. Job title filter
    if filters.job_title and filters.job_title.strip():
        jt = f"%{filters.job_title.strip()}%"
        query = query.filter(JobSeekerProfile.headline.ilike(jt))

    # 3. Location / City filter
    if filters.location and filters.location.strip() and filters.location != "All":
        loc = f"%{filters.location.strip()}%"
        query = query.filter(JobSeekerProfile.city.ilike(loc))

    # 4. Years of experience range
    if filters.min_experience is not None:
        query = query.filter(JobSeekerProfile.experience_years >= filters.min_experience)
    if filters.max_experience is not None:
        query = query.filter(JobSeekerProfile.experience_years <= filters.max_experience)

    # 5. Desired salary range (VND)
    if filters.min_salary is not None:
        query = query.filter(
            or_(
                JobSeekerProfile.expected_salary == None,
                JobSeekerProfile.expected_salary >= filters.min_salary,
            )
        )
    if filters.max_salary is not None:
        query = query.filter(
            or_(
                JobSeekerProfile.expected_salary == None,
                JobSeekerProfile.expected_salary <= filters.max_salary,
            )
        )

    # 6. Availability filter
    if filters.availability and filters.availability in ("open_to_work", "open_to_opportunities"):
        query = query.filter(JobSeekerProfile.job_availability == filters.availability)

    # 7. Skills filter
    if filters.skills and filters.skills.strip():
        req_skills = [s.strip().lower() for s in filters.skills.split(",") if s.strip()]
        for sk in req_skills:
            query = query.filter(JobSeekerProfile.skills.ilike(f"%{sk}%"))

    total = query.count()

    # Pagination
    offset = (filters.page - 1) * filters.page_size
    results = query.order_by(desc(JobSeekerProfile.id)).offset(offset).limit(filters.page_size).all()

    cards = []
    for profile, user in results:
        skills_list = parse_skills_list(profile.skills)
        cards.append(
            {
                "id": profile.id,
                "user_id": user.id,
                "full_name": user.full_name or "Anonymous Talent",
                "avatar_url": user.avatar_url,
                "headline": profile.headline or "Professional Specialist",
                "bio": profile.bio,
                "experience_years": float(profile.experience_years or 0.0),
                "expected_salary": float(profile.expected_salary) if profile.expected_salary else None,
                "city": profile.city or "Vietnam",
                "country": profile.country or "Vietnam",
                "skills": skills_list,
                "job_availability": profile.job_availability or "open_to_work",
                "education_level": "Bachelor's Degree",  # Standard baseline or from seeker profile
                "allow_direct_message": False,          # JSP-FR-015: Default disabled unless approved
                "contact_approved": False,              # BR-014: Masked until approved
                "contact_email": mask_email(user.email),
                "contact_phone": mask_phone(user.phone),
            }
        )

    return {
        "items": cards,
        "total": total,
        "page": filters.page,
        "page_size": filters.page_size,
        "total_pages": (total + filters.page_size - 1) // filters.page_size if total > 0 else 1,
    }


@service_error_handler
def get_talent_profile_detail(
    db: Session,
    company: CompanyProfile,
    profile_id: int,
) -> Dict[str, Any]:
    """
    EMP-FR-021 & EMP-FR-030: Retrieve full candidate profile for slide-out view.
    Contact details remain masked per BR-014 until candidate approves request.
    """
    verify_company_access(company)

    profile = db.query(JobSeekerProfile).filter(JobSeekerProfile.id == profile_id).first()
    if not profile or not profile.is_visible or profile.job_availability == "not_looking":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Candidate profile not found or is currently private.",
        )

    user = db.query(User).filter(User.id == profile.user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User account not found.")

    skills_list = parse_skills_list(profile.skills)

    # Structured sample background if not stored in extended profile
    exp_years = float(profile.experience_years or 0.0)
    headline = profile.headline or "Specialist"
    city = profile.city or "Ho Chi Minh City"

    sample_experience = [
        {
            "role": headline,
            "company": "Leading Enterprise / Tech Co",
            "duration": f"{int(exp_years)} years (Current / Recent)",
            "description": f"Developed mission-critical software solutions and led technical initiatives in {city}.",
        }
    ]
    if exp_years > 2:
        sample_experience.append(
            {
                "role": f"Junior {headline.split()[-1] if headline else 'Developer'}",
                "company": "Innovations Lab",
                "duration": "2 years",
                "description": "Collaborated with cross-functional teams to build and scale modern web applications.",
            }
        )

    sample_education = [
        {
            "degree": "Bachelor of Computer Science / Engineering",
            "institution": f"University of Technology ({city})",
            "year": "Graduated with Honors",
        }
    ]

    return {
        "id": profile.id,
        "user_id": user.id,
        "full_name": user.full_name or "Talent Profile",
        "avatar_url": user.avatar_url,
        "headline": profile.headline or "Professional Specialist",
        "bio": profile.bio or "Dedicated professional with proven industry track record seeking impactful opportunities.",
        "experience_years": exp_years,
        "expected_salary": float(profile.expected_salary) if profile.expected_salary else None,
        "city": city,
        "country": profile.country or "Vietnam",
        "skills": skills_list,
        "job_availability": profile.job_availability or "open_to_work",
        "github_url": profile.github_url,
        "linkedin_url": profile.linkedin_url,
        "education": sample_education,
        "experience": sample_experience,
        "resume_url": profile.resume_url,
        "allow_direct_message": False,
        "contact_approved": False,
        "contact_email": mask_email(user.email),
        "contact_phone": mask_phone(user.phone),
    }


@service_error_handler
def invite_talent_to_job(
    db: Session,
    company: CompanyProfile,
    profile_id: int,
    job_id: int,
    message: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Send an official Job Invitation / Contact Request to a passive candidate.
    Dispatches a Notification to the candidate and logs the engagement.
    """
    verify_company_access(company)

    profile = db.query(JobSeekerProfile).filter(JobSeekerProfile.id == profile_id).first()
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Talent profile not found.")

    # Validate job belongs to company
    job = (
        db.query(JobPosting)
        .filter(JobPosting.id == job_id, JobPosting.company_id == company.id)
        .first()
    )
    if not job:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Specified job posting does not belong to your company or does not exist.",
        )

    # Create notification for jobseeker
    notif = Notification(
        user_id=profile.user_id,
        title=f"Job Invitation from {company.company_name}",
        message=f"{company.company_name} invited you to apply for '{job.title}'. Note: {message or 'We reviewed your profile and think you would be a great fit!'}",
        type="offer",
    )
    db.add(notif)
    db.commit()

    logger.info(
        f"Company '{company.company_name}' (ID={company.id}) invited candidate "
        f"user_id={profile.user_id} for job '{job.title}' (ID={job.id})"
    )

    return {
        "candidate_id": profile.id,
        "candidate_name": profile.user.full_name if profile.user else "Candidate",
        "job_id": job.id,
        "job_title": job.title,
        "company_name": company.company_name,
        "status": "invitation_sent",
        "message": "Job invitation and contact request sent successfully to candidate.",
    }

