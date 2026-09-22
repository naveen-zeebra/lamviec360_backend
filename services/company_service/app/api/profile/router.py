from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from shared.database.session import get_db
from shared.models import User, CompanyProfile
from shared.schemas import CompanyProfileUpdate, APIResponse
from shared.utils import get_current_user, require_user_type, success_response

router = APIRouter(prefix="/profile", tags=["Company Profile"])

@router.get("", response_model=APIResponse[dict])
def get_company_profile(
    user: User = Depends(require_user_type("company", "super_admin")),
    db: Session = Depends(get_db),
):
    profile = db.query(CompanyProfile).filter(CompanyProfile.user_id == user.id).first()
    if not profile:
        profile = CompanyProfile(user_id=user.id, company_name=user.full_name)
        db.add(profile)
        db.commit()
        db.refresh(profile)

    return success_response(
        data={
            "id": profile.id,
            "user_id": user.id,
            "company_name": profile.company_name,
            "legal_name": profile.legal_name,
            "logo_url": profile.logo_url,
            "cover_image_url": profile.cover_image_url,
            "website": profile.website,
            "industry": profile.industry,
            "company_size": profile.company_size,
            "about": profile.about,
            "address": profile.address,
            "city": profile.city,
            "country": profile.country,
            "verification_status": profile.verification_status,
            "is_featured": profile.is_featured,
        }
    )

@router.put("", response_model=APIResponse[dict])
def update_company_profile(
    data: CompanyProfileUpdate,
    user: User = Depends(require_user_type("company", "super_admin")),
    db: Session = Depends(get_db),
):
    profile = db.query(CompanyProfile).filter(CompanyProfile.user_id == user.id).first()
    if not profile:
        profile = CompanyProfile(user_id=user.id, company_name=user.full_name)
        db.add(profile)

    for field, value in data.dict(exclude_unset=True).items():
        setattr(profile, field, value)

    db.commit()
    db.refresh(profile)

    return success_response(
        data={
            "id": profile.id,
            "company_name": profile.company_name,
            "legal_name": profile.legal_name,
            "logo_url": profile.logo_url,
            "cover_image_url": profile.cover_image_url,
            "website": profile.website,
            "industry": profile.industry,
            "company_size": profile.company_size,
            "about": profile.about,
            "address": profile.address,
            "city": profile.city,
            "country": profile.country,
            "verification_status": profile.verification_status,
        },
        message="Company profile updated successfully",
    )
