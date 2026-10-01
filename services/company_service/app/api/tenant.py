import json
from sqlalchemy.orm import Session
from shared.models import User, CompanyProfile

def get_tenant_profile(db: Session, user: User) -> CompanyProfile:
    """Retrieve existing profile or create verified profile.
    If the user was invited, find the company they are a member of.
    """
    profile = user.company_profile
    if profile:
        return profile
        
    # Check if this user is a team member in another company
    profiles = db.query(CompanyProfile).all()
    for p in profiles:
        settings_str = p.settings
        if settings_str and isinstance(settings_str, str):
            try:
                settings = json.loads(settings_str)
            except Exception:
                continue
            members = settings.get("team_members", [])
            for m in members:
                if m.get("email") == user.email:
                    return p
                    
    # If not found anywhere, create a new profile
    profile = CompanyProfile(
        user_id=user.id,
        company_name=user.full_name or "My Company",
        settings=json.dumps({}),
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile
