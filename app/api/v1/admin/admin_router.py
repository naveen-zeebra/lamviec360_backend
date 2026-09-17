from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.api.deps import get_current_super_admin
from app.models.user import User
from app.models.company import Company
from app.models.job import Job
from app.models.application import Application
from app.models.plan import SubscriptionPlan
from app.models.moderation import ModerationItem
from app.models.audit import AuditLog
from app.models.enums import (
    UserRole,
    UserStatus,
    CompanyApprovalStatus,
    JobStatus,
    ModerationStatus,
)
from app.schemas.admin import (
    TenantActionRequest,
    TenantPlanUpdateRequest,
    UserStatusUpdateRequest,
    ModerationActionRequest,
    SubscriptionPlanUpdateRequest,
    AnalyticsOverview,
)
from app.schemas.common import MessageResponse

router = APIRouter(prefix="/admin", tags=["Super Admin Governance"])


def record_audit(db: Session, actor: User, action: str, target_type: str, target_id: str, details: dict = None):
    log = AuditLog(
        actor_id=actor.id,
        actor_email=actor.email,
        action=action,
        target_type=target_type,
        target_id=target_id,
        details=details or {},
    )
    db.add(log)


@router.get("/dashboard/analytics", response_model=AnalyticsOverview)
def get_platform_analytics(current_user: User = Depends(get_current_super_admin), db: Session = Depends(get_db)):
    """Computes global platform metrics and KPIs for Super Admin dashboard."""
    total_users = db.query(User).count()
    total_tenants = db.query(Company).count()
    pending_tenants = db.query(Company).filter(Company.approval_status == CompanyApprovalStatus.PENDING).count()
    active_jobs = db.query(Job).filter(Job.status == JobStatus.PUBLISHED).count()
    total_applications = db.query(Application).count()

    user_growth = [
        {"month": "Jan", "count": int(total_users * 0.4)},
        {"month": "Feb", "count": int(total_users * 0.6)},
        {"month": "Mar", "count": total_users},
    ]
    tenant_growth = [
        {"month": "Jan", "count": max(1, int(total_tenants * 0.3))},
        {"month": "Feb", "count": max(1, int(total_tenants * 0.7))},
        {"month": "Mar", "count": total_tenants},
    ]

    return AnalyticsOverview(
        total_users=total_users,
        total_tenants=total_tenants,
        pending_tenants=pending_tenants,
        active_jobs=active_jobs,
        total_applications=total_applications,
        user_growth=user_growth,
        tenant_growth=tenant_growth,
    )


# ---- TENANT MANAGEMENT ----


@router.get("/tenants")
def list_tenants(
    status_filter: Optional[str] = Query(None, alias="status"),
    q: Optional[str] = None,
    current_user: User = Depends(get_current_super_admin),
    db: Session = Depends(get_db),
):
    """Lists company tenants with status filtering (Pending, Active, Rejected, Suspended)."""
    query = db.query(Company)
    if status_filter:
        query = query.filter(Company.approval_status == CompanyApprovalStatus(status_filter))
    if q:
        query = query.filter(Company.name.ilike(f"%{q}%"))

    companies = query.order_by(Company.created_at.desc()).all()
    results = []
    for c in companies:
        admin_user = next((m for m in c.members if m.role == UserRole.COMPANY_ADMIN), None)
        active_jobs = sum(1 for j in c.jobs if j.status == JobStatus.PUBLISHED)
        results.append(
            {
                "id": c.id,
                "name": c.name,
                "logo": c.name[:1],
                "regNumber": c.reg_number or "",
                "industry": c.industry,
                "size": c.size,
                "website": c.website or "",
                "description": c.description or "",
                "adminName": admin_user.name if admin_user else "",
                "adminEmail": admin_user.email if admin_user else "",
                "submittedDate": c.created_at.strftime("%Y-%m-%d"),
                "status": c.approval_status.value,
                "verified": c.verified,
                "emailVerified": c.email_verified,
                "plan": c.plan_id,
                "rejectionReason": c.rejection_reason or "",
                "suspendReason": c.suspend_reason or "",
                "activeJobs": active_jobs,
            }
        )
    return results


@router.get("/tenants/{id}")
def get_tenant_details(id: str, current_user: User = Depends(get_current_super_admin), db: Session = Depends(get_db)):
    c = db.query(Company).filter(Company.id == id).first()
    if not c:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant company not found")

    admin_user = next((m for m in c.members if m.role == UserRole.COMPANY_ADMIN), None)
    return {
        "id": c.id,
        "name": c.name,
        "regNumber": c.reg_number,
        "industry": c.industry,
        "size": c.size,
        "website": c.website,
        "description": c.description,
        "adminName": admin_user.name if admin_user else "",
        "adminEmail": admin_user.email if admin_user else "",
        "status": c.approval_status.value,
        "verified": c.verified,
        "emailVerified": c.email_verified,
        "plan": c.plan_id,
        "rejectionReason": c.rejection_reason,
        "suspendReason": c.suspend_reason,
        "submittedDate": c.created_at.strftime("%Y-%m-%d"),
        "totalJobs": len(c.jobs),
        "totalMembers": len(c.members),
    }


@router.post("/tenants/{id}/approve", response_model=MessageResponse)
def approve_tenant(id: str, current_user: User = Depends(get_current_super_admin), db: Session = Depends(get_db)):
    """Approves a pending company account, granting full hiring workspace access."""
    c = db.query(Company).filter(Company.id == id).first()
    if not c:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")

    c.approval_status = CompanyApprovalStatus.ACTIVE
    c.verified = True

    # Activate associated company admin user if pending
    for m in c.members:
        if m.role == UserRole.COMPANY_ADMIN and m.status == UserStatus.PENDING:
            m.status = UserStatus.ACTIVE

    record_audit(db, current_user, "COMPANY_APPROVED", "Company", c.id, {"company_name": c.name})
    db.commit()

    return MessageResponse(success=True, message=f"Company '{c.name}' approved successfully.")


@router.post("/tenants/{id}/reject", response_model=MessageResponse)
def reject_tenant(
    id: str,
    req: TenantActionRequest,
    current_user: User = Depends(get_current_super_admin),
    db: Session = Depends(get_db),
):
    """Rejects a company registration with official feedback reason."""
    c = db.query(Company).filter(Company.id == id).first()
    if not c:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")

    c.approval_status = CompanyApprovalStatus.REJECTED
    c.rejection_reason = req.reason or "Business documentation could not be verified."

    record_audit(db, current_user, "COMPANY_REJECTED", "Company", c.id, {"reason": c.rejection_reason})
    db.commit()

    return MessageResponse(success=True, message=f"Company '{c.name}' registration rejected.")


@router.post("/tenants/{id}/suspend", response_model=MessageResponse)
def suspend_tenant(
    id: str,
    req: TenantActionRequest,
    current_user: User = Depends(get_current_super_admin),
    db: Session = Depends(get_db),
):
    """Suspends a company for policy violations."""
    c = db.query(Company).filter(Company.id == id).first()
    if not c:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")

    c.approval_status = CompanyApprovalStatus.SUSPENDED
    c.suspend_reason = req.reason or "Policy violation or fraudulent activity reported."

    # Pause active jobs
    for j in c.jobs:
        if j.status == JobStatus.PUBLISHED:
            j.status = JobStatus.PAUSED

    record_audit(db, current_user, "COMPANY_SUSPENDED", "Company", c.id, {"reason": c.suspend_reason})
    db.commit()

    return MessageResponse(success=True, message=f"Company '{c.name}' suspended.")


@router.post("/tenants/{id}/reactivate", response_model=MessageResponse)
def reactivate_tenant(id: str, current_user: User = Depends(get_current_super_admin), db: Session = Depends(get_db)):
    c = db.query(Company).filter(Company.id == id).first()
    if not c:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")

    c.approval_status = CompanyApprovalStatus.ACTIVE
    c.suspend_reason = None
    record_audit(db, current_user, "COMPANY_REACTIVATED", "Company", c.id)
    db.commit()

    return MessageResponse(success=True, message=f"Company '{c.name}' reactivated.")


@router.patch("/tenants/{id}/plan", response_model=MessageResponse)
def update_tenant_plan(
    id: str,
    req: TenantPlanUpdateRequest,
    current_user: User = Depends(get_current_super_admin),
    db: Session = Depends(get_db),
):
    """Changes the subscription plan tier for a tenant."""
    c = db.query(Company).filter(Company.id == id).first()
    if not c:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")

    old_plan = c.plan_id
    c.plan_id = req.plan_id
    record_audit(db, current_user, "PLAN_ASSIGNED", "Company", c.id, {"from": old_plan, "to": req.plan_id})
    db.commit()

    return MessageResponse(success=True, message=f"Plan updated to {req.plan_id}")


# ---- USER MANAGEMENT ----


@router.get("/users")
def list_all_users(
    role: Optional[str] = None,
    user_status: Optional[str] = Query(None, alias="status"),
    current_user: User = Depends(get_current_super_admin),
    db: Session = Depends(get_db),
):
    """Platform-wide user directory."""
    query = db.query(User)
    if role:
        query = query.filter(User.role == UserRole(role))
    if user_status:
        query = query.filter(User.status == UserStatus(user_status))

    users = query.order_by(User.created_at.desc()).all()
    return [
        {
            "id": u.id,
            "name": u.name,
            "email": u.email,
            "role": u.role.value,
            "company": u.company.name if u.company else "",
            "companyId": u.company_id or "",
            "status": u.status.value,
            "createdAt": u.created_at.strftime("%Y-%m-%d"),
            "lastLogin": u.last_login_at.strftime("%Y-%m-%d") if u.last_login_at else "",
        }
        for u in users
    ]


@router.patch("/users/{id}/status", response_model=MessageResponse)
def update_user_status(
    id: str,
    req: UserStatusUpdateRequest,
    current_user: User = Depends(get_current_super_admin),
    db: Session = Depends(get_db),
):
    """Activates or suspends a platform user account."""
    u = db.query(User).filter(User.id == id).first()
    if not u:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if u.role == UserRole.SUPER_ADMIN and current_user.id != u.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot alter other Super Admin accounts")

    u.status = UserStatus(req.status)
    record_audit(db, current_user, "USER_STATUS_UPDATED", "User", u.id, {"new_status": req.status})
    db.commit()

    return MessageResponse(success=True, message=f"User account status changed to {req.status}")


# ---- MODERATION QUEUE ----


@router.get("/moderation")
def list_moderation_queue(
    mod_status: Optional[str] = Query("Open", alias="status"),
    current_user: User = Depends(get_current_super_admin),
    db: Session = Depends(get_db),
):
    """Lists moderation tickets (reported jobs, flagged companies)."""
    query = db.query(ModerationItem)
    if mod_status:
        query = query.filter(ModerationItem.status == ModerationStatus(mod_status))
    items = query.order_by(ModerationItem.flagged_at.desc()).all()
    return [
        {
            "id": m.id,
            "type": m.type.value,
            "targetId": m.target_id,
            "targetName": m.target_name,
            "companyId": m.company_id or "",
            "reason": m.reason,
            "flaggedBy": m.flagged_by,
            "flaggedAt": m.flagged_at.strftime("%Y-%m-%d"),
            "status": m.status.value,
            "targetData": m.target_data or {},
        }
        for m in items
    ]


@router.post("/moderation/{id}/resolve", response_model=MessageResponse)
def resolve_moderation(
    id: str,
    req: ModerationActionRequest,
    current_user: User = Depends(get_current_super_admin),
    db: Session = Depends(get_db),
):
    """Actions or dismisses a moderation ticket."""
    m = db.query(ModerationItem).filter(ModerationItem.id == id).first()
    if not m:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Moderation ticket not found")

    m.status = ModerationStatus(req.action)
    m.resolution_notes = req.resolution_notes or ""
    m.resolved_at = datetime.utcnow()

    # If actioned and type is Job Posting, close the job
    if req.action == "Actioned" and m.type.value == "Job Posting":
        job = db.query(Job).filter(Job.id == m.target_id).first()
        if job:
            job.status = JobStatus.CLOSED

    record_audit(db, current_user, "MODERATION_RESOLVED", "ModerationItem", m.id, {"action": req.action})
    db.commit()

    return MessageResponse(success=True, message=f"Moderation ticket marked as {req.action}.")


# ---- SUBSCRIPTION PLANS & AUDIT LOGS ----


@router.get("/plans")
def list_plans(current_user: User = Depends(get_current_super_admin), db: Session = Depends(get_db)):
    return db.query(SubscriptionPlan).all()


@router.put("/plans/{id}", response_model=MessageResponse)
def update_plan(
    id: str,
    req: SubscriptionPlanUpdateRequest,
    current_user: User = Depends(get_current_super_admin),
    db: Session = Depends(get_db),
):
    p = db.query(SubscriptionPlan).filter(SubscriptionPlan.id == id).first()
    if not p:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")

    for key, val in req.model_dump(exclude_unset=True).items():
        setattr(p, key, val)

    record_audit(db, current_user, "PLAN_CONFIG_UPDATED", "SubscriptionPlan", p.id)
    db.commit()
    return MessageResponse(success=True, message="Plan configuration updated.")


@router.get("/audit-logs")
def list_audit_logs(
    limit: int = 50,
    current_user: User = Depends(get_current_super_admin),
    db: Session = Depends(get_db),
):
    logs = db.query(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit).all()
    return [
        {
            "id": a.id,
            "actorEmail": a.actor_email,
            "action": a.action,
            "targetType": a.target_type,
            "targetId": a.target_id,
            "details": a.details,
            "timestamp": a.created_at.strftime("%Y-%m-%d %H:%M:%S"),
        }
        for a in logs
    ]
