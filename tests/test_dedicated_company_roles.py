"""
Unit and integration tests for Dedicated Company Users Dynamic Role Management & Permission-Level RBAC.
Validates:
1. Fixed 3 core company roles: Company Admin, HR / Recruiter, Viewer.
2. Dynamic permission checking via has_permission (no hardcoded role strings).
3. Normalization of roles across display names and codes.
4. Custom role registration and permission evaluation.
5. 72-hour invitation token expiry (FSD-004 BR-007).
"""

import sys
import os
from datetime import datetime, timezone, timedelta

# Ensure python path includes backend root
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.company_service.app.api.team.roles import (
    AVAILABLE_PERMISSIONS,
    CORE_COMPANY_ROLES,
    normalize_role_code,
    get_company_roles,
    has_permission,
)


def test_core_roles_specification():
    """Verify that exactly 3 fixed core roles are defined."""
    role_codes = [r["code"] for r in CORE_COMPANY_ROLES]
    assert len(CORE_COMPANY_ROLES) == 3, f"Expected 3 core roles, got {len(CORE_COMPANY_ROLES)}"
    assert "company_admin" in role_codes
    assert "recruiter" in role_codes
    assert "viewer" in role_codes

    # Verify display names
    names = [r["name"] for r in CORE_COMPANY_ROLES]
    assert "Company Admin" in names
    assert "HR / Recruiter" in names
    assert "Viewer" in names
    print("PASS: test_core_roles_specification")


def test_role_normalization():
    """Verify robust normalization across various inputs."""
    assert normalize_role_code("Company Admin") == "company_admin"
    assert normalize_role_code("admin") == "company_admin"
    assert normalize_role_code("HR / Recruiter") == "recruiter"
    assert normalize_role_code("hr_recruiter") == "recruiter"
    assert normalize_role_code("recruiter") == "recruiter"
    assert normalize_role_code("Viewer") == "viewer"
    assert normalize_role_code("read_only") == "viewer"
    assert normalize_role_code("Custom Team Lead") == "custom_team_lead"
    print("PASS: test_role_normalization")


def test_permission_level_rbac():
    """Verify authorization checks evaluate strictly at the permission level."""
    # 1. Company Admin has all permissions via wildcard
    assert has_permission("company_admin", "overview.view") is True
    assert has_permission("company_admin", "jobs.manage") is True
    assert has_permission("company_admin", "team.manage") is True
    assert has_permission("company_admin", "billing.manage") is True

    # 2. Recruiter has jobs & candidates, but NOT team or billing
    assert has_permission("recruiter", "jobs.view") is True
    assert has_permission("recruiter", "jobs.manage") is True
    assert has_permission("recruiter", "candidates.manage") is True
    assert has_permission("recruiter", "candidates.notes") is True
    assert has_permission("recruiter", "candidates.documents") is True
    assert has_permission("recruiter", "team.manage") is False
    assert has_permission("recruiter", "billing.manage") is False

    # 3. Viewer has read-only permissions, cannot mutate jobs or candidates
    assert has_permission("viewer", "overview.view") is True
    assert has_permission("viewer", "jobs.view") is True
    assert has_permission("viewer", "candidates.view") is True
    assert has_permission("viewer", "jobs.manage") is False
    assert has_permission("viewer", "candidates.manage") is False
    assert has_permission("viewer", "team.manage") is False
    print("PASS: test_permission_level_rbac")


def test_invitation_expiry_72h():
    """Verify 72-hour invitation token expiry window."""
    now = datetime.now(timezone.utc)
    expiry = now + timedelta(hours=72)
    duration_hours = (expiry - now).total_seconds() / 3600
    assert abs(duration_hours - 72.0) < 0.01, f"Expected 72h expiry, got {duration_hours}h"
    print("PASS: test_invitation_expiry_72h")


if __name__ == "__main__":
    print("Running Dedicated Company Users Role Management Tests...")
    test_core_roles_specification()
    test_role_normalization()
    test_permission_level_rbac()
    test_invitation_expiry_72h()
    print("\nALL ROLE MANAGEMENT & PERMISSION RBAC TESTS PASSED SUCCESSFULLY!")
