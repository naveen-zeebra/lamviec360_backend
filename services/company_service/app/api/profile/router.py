import json
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from shared.database.session import get_db
from shared.models import User, CompanyProfile
from shared.schemas import CompanyProfileUpdate, APIResponse
from shared.utils import get_current_user, require_user_type, success_response

router = APIRouter(prefix="/profile", tags=["Company Profile"])

def _get_or_create_company_tenant(user: User, db: Session) -> CompanyProfile:
    profile = db.query(CompanyProfile).filter(CompanyProfile.user_id == user.id).first()
    if not profile:
        profile = CompanyProfile(
            user_id=user.id,
            company_name=user.full_name or "My Company",
            verification_status="verified",
        )
        db.add(profile)
        db.commit()
        db.refresh(profile)
    return profile

def _parse_settings(raw_settings):
    if not raw_settings:
        return {}
    if isinstance(raw_settings, dict):
        return raw_settings
    try:
        return json.loads(raw_settings)
    except Exception:
        return {}

@router.get("", response_model=APIResponse[dict])
def get_company_profile(
    user: User = Depends(require_user_type("company", "super_admin")),
    db: Session = Depends(get_db),
):
    profile = _get_or_create_company_tenant(user, db)

    parsed_settings = _parse_settings(profile.settings)

    return success_response(
        data={
            "id": profile.id,
            "user_id": user.id,
            "company_name": profile.company_name,
            "name": profile.company_name,
            "legal_name": profile.legal_name,
            "tax_code": profile.tax_code,
            "reg_number": profile.tax_code or profile.legal_name or "",
            "regNumber": profile.tax_code or profile.legal_name or "",
            "contact_email": profile.contact_email or user.email,
            "email": profile.contact_email or user.email,
            "contact_phone": profile.contact_phone or user.phone or "",
            "phone": profile.contact_phone or user.phone or "",
            "contact_person": profile.contact_person or user.full_name or "",
            "founded_year": profile.founded_year,
            "linkedin_url": profile.linkedin_url or "",
            "facebook_url": profile.facebook_url or "",
            "benefits": profile.benefits or "",
            "logo_url": profile.logo_url,
            "logo": profile.logo_url,
            "cover_image_url": profile.cover_image_url,
            "website": profile.website,
            "industry": profile.industry,
            "company_size": profile.company_size,
            "size": profile.company_size,
            "about": profile.about,
            "description": profile.about,
            "address": profile.address,
            "city": profile.city,
            "country": profile.country,
            "verification_status": profile.verification_status,
            "verified": profile.verification_status == "verified",
            "approval_status": profile.verification_status or "verified",
            "is_featured": profile.is_featured,
            "plan": (profile.subscription_tier or "Freemium").title(),
            "subscription_tier": profile.subscription_tier or "Freemium",
            "settings": parsed_settings,
        }
    )

@router.put("", response_model=APIResponse[dict])
def update_company_profile(
    data: CompanyProfileUpdate,
    user: User = Depends(require_user_type("company", "super_admin")),
    db: Session = Depends(get_db),
):
    profile = _get_or_create_company_tenant(user, db)

    data_dict = data.dict(exclude_unset=True)

    # Normalize aliases to model attributes
    company_name = data_dict.get("company_name") or data_dict.get("name")
    if company_name is not None:
        profile.company_name = company_name

    logo_url = data_dict.get("logo_url") or data_dict.get("logo")
    if logo_url is not None:
        profile.logo_url = logo_url

    company_size = data_dict.get("company_size") or data_dict.get("size")
    if company_size is not None:
        profile.company_size = company_size

    about = data_dict.get("about") or data_dict.get("description")
    if about is not None:
        profile.about = about

    tax_code = data_dict.get("tax_code") or data_dict.get("reg_number") or data_dict.get("regNumber")
    if tax_code is not None:
        profile.tax_code = tax_code

    contact_phone = data_dict.get("contact_phone") or data_dict.get("phone")
    if contact_phone is not None:
        profile.contact_phone = contact_phone

    contact_email = data_dict.get("contact_email") or data_dict.get("email")
    if contact_email is not None:
        profile.contact_email = contact_email

    if "contact_person" in data_dict:
        profile.contact_person = data_dict["contact_person"]
    if "founded_year" in data_dict:
        try:
            profile.founded_year = int(data_dict["founded_year"]) if data_dict["founded_year"] else None
        except (ValueError, TypeError):
            pass
    if "linkedin_url" in data_dict:
        profile.linkedin_url = data_dict["linkedin_url"]
    if "facebook_url" in data_dict:
        profile.facebook_url = data_dict["facebook_url"]
    if "benefits" in data_dict:
        profile.benefits = data_dict["benefits"]

    plan = data_dict.get("subscription_tier") or data_dict.get("plan")
    if plan is not None:
        profile.subscription_tier = plan

    if "settings" in data_dict:
        s = data_dict["settings"]
        if isinstance(s, dict):
            # merge with existing settings
            existing = _parse_settings(profile.settings)
            existing.update(s)
            profile.settings = json.dumps(existing)
        elif isinstance(s, str):
            profile.settings = s

    if "legal_name" in data_dict:
        profile.legal_name = data_dict["legal_name"]
    if "cover_image_url" in data_dict:
        profile.cover_image_url = data_dict["cover_image_url"]
    if "website" in data_dict:
        profile.website = data_dict["website"]
    if "industry" in data_dict:
        profile.industry = data_dict["industry"]
    if "address" in data_dict:
        profile.address = data_dict["address"]
    if "city" in data_dict:
        profile.city = data_dict["city"]
    if "country" in data_dict:
        profile.country = data_dict["country"]

    db.commit()
    db.refresh(profile)

    parsed_settings = _parse_settings(profile.settings)

    return success_response(
        data={
            "id": profile.id,
            "company_name": profile.company_name,
            "name": profile.company_name,
            "legal_name": profile.legal_name,
            "tax_code": profile.tax_code,
            "reg_number": profile.tax_code or profile.legal_name or "",
            "regNumber": profile.tax_code or profile.legal_name or "",
            "contact_email": profile.contact_email or user.email,
            "email": profile.contact_email or user.email,
            "contact_phone": profile.contact_phone or user.phone or "",
            "phone": profile.contact_phone or user.phone or "",
            "contact_person": profile.contact_person or user.full_name or "",
            "founded_year": profile.founded_year,
            "linkedin_url": profile.linkedin_url or "",
            "facebook_url": profile.facebook_url or "",
            "benefits": profile.benefits or "",
            "logo_url": profile.logo_url,
            "logo": profile.logo_url,
            "cover_image_url": profile.cover_image_url,
            "website": profile.website,
            "industry": profile.industry,
            "company_size": profile.company_size,
            "size": profile.company_size,
            "about": profile.about,
            "description": profile.about,
            "address": profile.address,
            "city": profile.city,
            "country": profile.country,
            "verification_status": profile.verification_status,
            "verified": profile.verification_status == "verified",
            "plan": (profile.subscription_tier or "Freemium").title(),
            "settings": parsed_settings,
        },
        message="Company profile updated successfully",
    )
