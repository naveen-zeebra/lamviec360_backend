import json
from typing import Any
from sqlalchemy.orm import Session
from shared.models import CompanyProfile
from shared.models.company_user import CompanyUser

def get_tenant_profile(db: Session, user: Any) -> CompanyProfile:
    """
    Retrieve existing company profile for an authenticated company user or admin.
    Executes in O(1) time using direct foreign-key resolution.
    """
    # 1. Direct CompanyUser relationship or company_id
    if hasattr(user, "company") and user.company:
        return user.company
    if hasattr(user, "company_id") and user.company_id:
        profile = db.query(CompanyProfile).filter(CompanyProfile.id == user.company_id).first()
        if profile:
            return profile

    # 2. Direct CompanyProfile relationship on User
    if hasattr(user, "company_profile") and user.company_profile:
        return user.company_profile

    # 3. Lookup CompanyUser by email or id
    user_email = getattr(user, "email", None)
    if user_email:
        cu = db.query(CompanyUser).filter(CompanyUser.email == user_email.lower()).first()
        if cu and cu.company:
            return cu.company

    # 4. Lookup CompanyProfile by user_id
    user_id = getattr(user, "id", None)
    if user_id:
        profile = db.query(CompanyProfile).filter(CompanyProfile.user_id == user_id).first()
        if profile:
            return profile

    # 5. Fallback auto-provision if none exists
    full_name = getattr(user, "full_name", None) or "My Company"
    profile = CompanyProfile(
        user_id=user_id,
        company_name=full_name,
        settings=json.dumps({}),
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile
