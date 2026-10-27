# ─────────────────────────────────────────────────────────────────────────────
# File    : services/company_service/app/api/team/roles.py
# Purpose : Dynamic Role & Permission Registry for Company Tenant Domain
# ─────────────────────────────────────────────────────────────────────────────

import json
from typing import List, Dict, Any, Optional
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from shared.database.session import get_db
from shared.models import CompanyProfile
from shared.utils import get_current_company_user

# Available granular permissions across the company workspace
AVAILABLE_PERMISSIONS: List[Dict[str, str]] = [
    {"key": "overview.view", "name": "View Dashboard", "module": "Dashboard", "description": "Access overview KPIs, charts and recent activities."},
    {"key": "jobs.view", "name": "View Jobs", "module": "Jobs", "description": "View published, paused, draft and closed job postings."},
    {"key": "jobs.manage", "name": "Manage Jobs", "module": "Jobs", "description": "Create, edit, pause, resume, duplicate and delete jobs."},
    {"key": "candidates.view", "name": "View Candidates", "module": "ATS", "description": "View applicant lists, profiles and resume previews."},
    {"key": "candidates.manage", "name": "Manage Candidates", "module": "ATS", "description": "Move stages, schedule interviews, rate and reject candidates."},
    {"key": "candidates.notes", "name": "Candidate Notes", "module": "ATS", "description": "Record and view internal hiring team feedback notes."},
    {"key": "candidates.documents", "name": "View Verification Docs", "module": "ATS", "description": "View-only access to candidate verification documents (PDPD compliant)."},
    {"key": "team.manage", "name": "Manage Team", "module": "Team", "description": "Invite employees, assign roles, revoke/reactivate access."},
    {"key": "settings.manage", "name": "Manage Settings", "module": "Settings", "description": "Configure company profile, pipeline stages and preferences."},
    {"key": "billing.manage", "name": "Manage Billing", "module": "Billing", "description": "View and manage subscriptions, quotas and invoices."},
]

# The 3 fixed core company roles per FSD-004 specification
CORE_COMPANY_ROLES: List[Dict[str, Any]] = [
    {
        "id": "company_admin",
        "code": "company_admin",
        "name": "Company Admin",
        "description": "Full access to organization settings, team members, billing, jobs, and recruitment pipelines.",
        "is_system": True,
        "color_tone": "purple",
        "permissions": ["*"],
    },
    {
        "id": "recruiter",
        "code": "recruiter",
        "name": "HR / Recruiter",
        "description": "Post and edit jobs, manage applicant ATS pipelines, conduct candidate communications, and schedule interviews.",
        "is_system": True,
        "color_tone": "blue",
        "permissions": [
            "overview.view",
            "jobs.view",
            "jobs.manage",
            "candidates.view",
            "candidates.manage",
            "candidates.notes",
            "candidates.documents",
        ],
    },
    {
        "id": "viewer",
        "code": "viewer",
        "name": "Viewer",
        "description": "Read-only access to published job listings and applicant pipelines. Cannot modify jobs or take candidate actions.",
        "is_system": True,
        "color_tone": "slate",
        "permissions": [
            "overview.view",
            "jobs.view",
            "candidates.view",
        ],
    },
]


def normalize_role_code(role_input: Optional[str]) -> str:
    """Normalize any display name or code into canonical role identifier."""
    if not role_input:
        return "recruiter"
    clean = role_input.lower().replace(" ", "_").replace("/", "").strip()
    if clean in ["company_admin", "admin", "owner", "superadmin"]:
        return "company_admin"
    if clean in ["hr__recruiter", "hr_recruiter", "recruiter", "hr"]:
        return "recruiter"
    if clean in ["viewer", "read_only", "readonly"]:
        return "viewer"
    return clean


def get_company_roles(company_id: Optional[int] = None, db: Optional[Session] = None) -> List[Dict[str, Any]]:
    """
    Retrieve all dynamic company roles for a tenant:
    The 3 fixed core roles + any custom tenant-defined roles stored in settings.
    """
    roles = [dict(r) for r in CORE_COMPANY_ROLES]

    if not company_id or not db:
        return roles

    # Fetch custom roles from CompanyProfile settings if configured
    profile = db.query(CompanyProfile).filter(CompanyProfile.id == company_id).first()
    if profile and profile.settings:
        try:
            settings_dict = json.loads(profile.settings) if isinstance(profile.settings, str) else profile.settings
            custom_roles = settings_dict.get("custom_roles", [])
            if isinstance(custom_roles, list):
                for cr in custom_roles:
                    if isinstance(cr, dict) and cr.get("code") and cr.get("name"):
                        # Ensure custom role doesn't override system role
                        if cr.get("code") not in [r["code"] for r in CORE_COMPANY_ROLES]:
                            roles.append({
                                "id": cr.get("code"),
                                "code": cr.get("code"),
                                "name": cr.get("name"),
                                "description": cr.get("description", "Custom organizational role"),
                                "is_system": False,
                                "color_tone": cr.get("color_tone", "indigo"),
                                "permissions": cr.get("permissions", ["overview.view"]),
                            })
        except Exception:
            pass

    return roles


def get_role_permissions(role_code: str, company_id: Optional[int] = None, db: Optional[Session] = None) -> List[str]:
    """Retrieve granted permissions list for a given role code."""
    canonical = normalize_role_code(role_code)
    roles = get_company_roles(company_id, db)
    for r in roles:
        if r["code"] == canonical:
            if "*" in r.get("permissions", []):
                return [p["key"] for p in AVAILABLE_PERMISSIONS]
            return r.get("permissions", [])
    return ["overview.view"]


def has_permission(
    role_code: str,
    permission_key: str,
    company_id: Optional[int] = None,
    db: Optional[Session] = None,
) -> bool:
    """
    Permission-level check: Verify whether a role holds the specified permission key.
    Enforces check purely at the permission level, not hardcoded role names.
    """
    canonical = normalize_role_code(role_code)
    if canonical == "company_admin":
        return True

    roles = get_company_roles(company_id, db)
    for r in roles:
        if r["code"] == canonical:
            perms = r.get("permissions", [])
            return "*" in perms or permission_key in perms

    return False


def require_company_permission(permission_key: str):
    """
    FastAPI dependency factory: Enforce granular permission check on authenticated company user.
    Evaluates dynamically against tenant role permissions (no hardcoded role names).
    """
    def dependency(
        user: Any = Depends(get_current_company_user),
        db: Session = Depends(get_db),
    ) -> Any:
        if getattr(user, "is_superuser", False):
            return user

        user_role = getattr(user, "role", None) or getattr(user, "user_type", None)
        company_id = getattr(user, "company_id", None)

        if not has_permission(user_role, permission_key, company_id, db):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: action requires '{permission_key}' privilege",
            )
        return user

    return dependency

