# ─────────────────────────────────────────────────────────────────────────────
# File    : services/company_service/app/api/templates/service.py
# Purpose : Business logic for Company Rejection Templates (EMP-FR-025b / e13)
# ─────────────────────────────────────────────────────────────────────────────

from typing import List, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException
from shared.models.rejection_template import CompanyRejectionTemplate
from services.company_service.app.api.templates.schemas import (
    CreateRejectionTemplateRequest,
    UpdateRejectionTemplateRequest,
)

DEFAULT_SEEDS = [
    {
        "title": "Chưa phù hợp tiêu chí kinh nghiệm",
        "reason_code": "qualifications",
        "subject": "Cập nhật về hồ sơ ứng tuyển {{job_title}} tại {{company_name}}",
        "body_text": "Kính gửi {{candidate_name}},\n\nCảm ơn bạn đã ứng tuyển cho vị trí {{job_title}} tại {{company_name}}.\nSau khi xem xét kỹ lưỡng hồ sơ, chúng tôi rất tiếc phải thông báo hiện tại hồ sơ của bạn chưa hoàn toàn phù hợp với các tiêu chí ưu tiên cho vị trí này.\n\nChúc bạn luôn thành công trên con đường phát triển sự nghiệp.\n\nTrân trọng,\nĐội ngũ Tuyển dụng {{company_name}}",
        "language": "vi",
        "is_default": True,
    },
    {
        "title": "Vị trí đã tuyển đủ nhân sự nội bộ",
        "reason_code": "role_filled",
        "subject": "Thông báo hoàn thành đợt tuyển dụng {{job_title}} - {{company_name}}",
        "body_text": "Kính gửi {{candidate_name}},\n\nCảm ơn bạn đã quan tâm và nộp hồ sơ ứng tuyển vị trí {{job_title}} tại {{company_name}}.\nHiện tại vị trí này đã được lấp đầy. Chúng tôi xin phép lưu hồ sơ của bạn trong hệ thống Talent Pool để ưu tiên liên hệ khi có cơ hội mới.\n\nTrân trọng,\nPhòng Tuyển dụng {{company_name}}",
        "language": "vi",
        "is_default": False,
    },
    {
        "title": "Lưu trữ hồ sơ Talent Pool dài hạn",
        "reason_code": "timing",
        "subject": "Lưu trữ hồ sơ trong Mạng lưới Nhân tài: {{job_title}} tại {{company_name}}",
        "body_text": "Kính gửi {{candidate_name}},\n\nChúng tôi đánh giá rất cao năng lực và hồ sơ chuyên môn của bạn. Mặc dù đợt tuyển dụng hiện tại đã khép lại, chúng tôi mong muốn lưu trữ thông tin của bạn trong mạng lưới nhân tài ưu tiên và sẽ liên hệ ngay khi có dự án mới.\n\nTrân trọng,\nBan Nhân sự {{company_name}}",
        "language": "vi",
        "is_default": False,
    },
]


def list_company_templates(db: Session, company_id: int) -> List[CompanyRejectionTemplate]:
    """Retrieve all rejection templates for the company, seeding defaults if empty."""
    items = (
        db.query(CompanyRejectionTemplate)
        .filter(CompanyRejectionTemplate.company_id == company_id)
        .order_by(CompanyRejectionTemplate.is_default.desc(), CompanyRejectionTemplate.id.asc())
        .all()
    )
    if not items:
        # Seed initial library
        for seed in DEFAULT_SEEDS:
            tpl = CompanyRejectionTemplate(company_id=company_id, **seed)
            db.add(tpl)
        db.commit()
        items = (
            db.query(CompanyRejectionTemplate)
            .filter(CompanyRejectionTemplate.company_id == company_id)
            .order_by(CompanyRejectionTemplate.is_default.desc(), CompanyRejectionTemplate.id.asc())
            .all()
        )
    return items


def create_company_template(
    db: Session, company_id: int, payload: CreateRejectionTemplateRequest
) -> CompanyRejectionTemplate:
    """Create a new custom rejection reason template."""
    if payload.is_default:
        # Reset previous default
        db.query(CompanyRejectionTemplate).filter(
            CompanyRejectionTemplate.company_id == company_id
        ).update({"is_default": False})

    tpl = CompanyRejectionTemplate(
        company_id=company_id,
        title=payload.title,
        reason_code=payload.reason_code or "qualifications",
        subject=payload.subject,
        body_text=payload.body_text,
        language=payload.language or "vi",
        is_default=bool(payload.is_default),
    )
    db.add(tpl)
    db.commit()
    db.refresh(tpl)
    return tpl


def update_company_template(
    db: Session, company_id: int, template_id: int, payload: UpdateRejectionTemplateRequest
) -> CompanyRejectionTemplate:
    """Update an existing template."""
    tpl = (
        db.query(CompanyRejectionTemplate)
        .filter(
            CompanyRejectionTemplate.id == template_id,
            CompanyRejectionTemplate.company_id == company_id,
        )
        .first()
    )
    if not tpl:
        raise HTTPException(status_code=404, detail="Rejection template not found.")

    if payload.is_default:
        db.query(CompanyRejectionTemplate).filter(
            CompanyRejectionTemplate.company_id == company_id
        ).update({"is_default": False})

    if payload.title is not None:
        tpl.title = payload.title
    if payload.reason_code is not None:
        tpl.reason_code = payload.reason_code
    if payload.subject is not None:
        tpl.subject = payload.subject
    if payload.body_text is not None:
        tpl.body_text = payload.body_text
    if payload.language is not None:
        tpl.language = payload.language
    if payload.is_default is not None:
        tpl.is_default = payload.is_default

    db.commit()
    db.refresh(tpl)
    return tpl


def delete_company_template(db: Session, company_id: int, template_id: int) -> bool:
    """Delete a custom template."""
    tpl = (
        db.query(CompanyRejectionTemplate)
        .filter(
            CompanyRejectionTemplate.id == template_id,
            CompanyRejectionTemplate.company_id == company_id,
        )
        .first()
    )
    if not tpl:
        raise HTTPException(status_code=404, detail="Rejection template not found.")

    count = (
        db.query(CompanyRejectionTemplate)
        .filter(CompanyRejectionTemplate.company_id == company_id)
        .count()
    )
    if count <= 1:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete the only rejection template for this organization.",
        )

    db.delete(tpl)
    db.commit()
    return True

