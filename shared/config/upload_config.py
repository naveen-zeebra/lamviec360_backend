"""
=============================================================================
LamViec360 Centralized File Upload & Size Configuration Module
=============================================================================
Single source of truth for all file upload limits, extensions, MIME types,
storage directories, and error messages across backend microservices.

Supports environment variable overrides via .env:
- MAX_AVATAR_SIZE_MB (default: 2)
- MAX_RESUME_SIZE_MB (default: 5)
- MAX_RESUMES_PER_SEEKER (default: 5)
- MAX_CERTIFICATION_SIZE_MB (default: 5)
- MAX_DOCUMENT_SIZE_MB (default: 10)
- MAX_DOCUMENT_QUOTA_MB (default: 100)
- MAX_COMPANY_LOGO_MB (default: 5)
- MAX_COMPANY_BANNER_MB (default: 10)
=============================================================================
"""

import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Set


def _get_int_env(key: str, default: int) -> int:
    val = os.getenv(key)
    if val is not None:
        try:
            return int(str(val).strip())
        except (ValueError, TypeError):
            pass
    return default


@dataclass(frozen=True)
class AvatarConfig:
    max_size_mb: int = field(default_factory=lambda: _get_int_env("MAX_AVATAR_SIZE_MB", 2))
    allowed_extensions: Set[str] = field(default_factory=lambda: {".jpg", ".jpeg", ".png"})
    allowed_mime_types: Set[str] = field(default_factory=lambda: {"image/jpeg", "image/png", "image/jpg"})
    sub_dir: str = "avatars"

    @property
    def max_size_bytes(self) -> int:
        return self.max_size_mb * 1024 * 1024

    @property
    def max_size_error_message(self) -> str:
        return f"Profile photo must not exceed {self.max_size_mb}MB."

    @property
    def format_error_message(self) -> str:
        return "Unsupported file format. Allowed formats: JPG, JPEG, and PNG only."


@dataclass(frozen=True)
class ResumeConfig:
    max_size_mb: int = field(default_factory=lambda: _get_int_env("MAX_RESUME_SIZE_MB", 5))
    max_count: int = field(default_factory=lambda: _get_int_env("MAX_RESUMES_PER_SEEKER", 5))
    allowed_extensions: Set[str] = field(default_factory=lambda: {".pdf", ".doc", ".docx"})
    mime_by_ext: Dict[str, str] = field(
        default_factory=lambda: {
            ".pdf": "application/pdf",
            ".doc": "application/msword",
            ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        }
    )
    sub_dir: str = "resumes"

    @property
    def max_size_bytes(self) -> int:
        return self.max_size_mb * 1024 * 1024

    @property
    def max_size_error_message(self) -> str:
        return f"Resume file size must not exceed {self.max_size_mb} MB"

    @property
    def max_count_error_message(self) -> str:
        return f"You can save a maximum of {self.max_count} résumés. Remove one before uploading another."

    @property
    def format_error_message(self) -> str:
        return "Unsupported file format. Allowed formats: PDF, DOC, and DOCX only"


@dataclass(frozen=True)
class CertificationConfig:
    max_size_mb: int = field(default_factory=lambda: _get_int_env("MAX_CERTIFICATION_SIZE_MB", 5))
    allowed_extensions: Set[str] = field(default_factory=lambda: {".pdf", ".png", ".jpg", ".jpeg", ".doc", ".docx"})
    sub_dir: str = "certifications"

    @property
    def max_size_bytes(self) -> int:
        return self.max_size_mb * 1024 * 1024

    @property
    def max_size_error_message(self) -> str:
        return f"Certificate file size must not exceed {self.max_size_mb} MB."

    @property
    def format_error_message(self) -> str:
        return "Unsupported file format. Allowed formats: PDF, PNG, JPG, and DOCX only."


@dataclass(frozen=True)
class DocumentArchiveConfig:
    max_size_mb: int = field(default_factory=lambda: _get_int_env("MAX_DOCUMENT_SIZE_MB", 10))
    quota_mb: int = field(default_factory=lambda: _get_int_env("MAX_DOCUMENT_QUOTA_MB", 100))
    allowed_extensions: Set[str] = field(default_factory=lambda: {"pdf", "doc", "docx", "jpg", "jpeg", "png"})
    allowed_categories: List[str] = field(
        default_factory=lambda: ["contract", "relieving", "relieving_letter", "payslip", "certificate", "other"]
    )
    sub_dir: str = "documents"

    @property
    def max_size_bytes(self) -> int:
        return self.max_size_mb * 1024 * 1024

    @property
    def quota_bytes(self) -> int:
        return self.quota_mb * 1024 * 1024

    @property
    def allowed_extensions_list(self) -> List[str]:
        return sorted(list(self.allowed_extensions))

    @property
    def max_size_error_message(self) -> str:
        return f"File size cannot exceed {self.max_size_mb}MB (JSP-FR-012)."

    @property
    def quota_error_message(self) -> str:
        return f"Total storage quota ({self.quota_mb}MB) exceeded. Please delete old documents before uploading new ones (JSP-FR-012)."


@dataclass(frozen=True)
class CompanyMediaConfig:
    logo_max_size_mb: int = field(default_factory=lambda: _get_int_env("MAX_COMPANY_LOGO_MB", 5))
    banner_max_size_mb: int = field(default_factory=lambda: _get_int_env("MAX_COMPANY_BANNER_MB", 10))
    allowed_extensions: Set[str] = field(default_factory=lambda: {".jpg", ".jpeg", ".png", ".webp", ".svg"})

    @property
    def logo_max_bytes(self) -> int:
        return self.logo_max_size_mb * 1024 * 1024

    @property
    def banner_max_bytes(self) -> int:
        return self.banner_max_size_mb * 1024 * 1024


@dataclass(frozen=True)
class ProfileAttachmentQuotaConfig:
    max_total_mb: int = field(default_factory=lambda: _get_int_env("MAX_PROFILE_ATTACHMENT_MB", 10))
    error_message_en: str = "Total file size cannot exceed 10MB. Please reduce file sizes or remove some documents."
    error_message_vi: str = "Tổng dung lượng tệp không được vượt quá 10MB. Vui lòng giảm kích thước tệp hoặc xóa bớt tài liệu."

    @property
    def max_total_bytes(self) -> int:
        return self.max_total_mb * 1024 * 1024


@dataclass
class UploadConfig:
    avatar: AvatarConfig = field(default_factory=AvatarConfig)
    resume: ResumeConfig = field(default_factory=ResumeConfig)
    certification: CertificationConfig = field(default_factory=CertificationConfig)
    document_archive: DocumentArchiveConfig = field(default_factory=DocumentArchiveConfig)
    company: CompanyMediaConfig = field(default_factory=CompanyMediaConfig)
    profile_attachment_quota: ProfileAttachmentQuotaConfig = field(default_factory=ProfileAttachmentQuotaConfig)

    def to_frontend_dict(self) -> Dict[str, Any]:
        """Serialize configuration for frontend consumption via API."""
        return {
            "AVATAR": {
                "maxMb": self.avatar.max_size_mb,
                "maxBytes": self.avatar.max_size_bytes,
                "extensions": sorted(list(self.avatar.allowed_extensions)),
                "accept": ",".join(sorted(list(self.avatar.allowed_extensions))),
            },
            "RESUME": {
                "maxMb": self.resume.max_size_mb,
                "maxBytes": self.resume.max_size_bytes,
                "maxCount": self.resume.max_count,
                "extensions": sorted(list(self.resume.allowed_extensions)),
                "accept": ",".join(sorted(list(self.resume.allowed_extensions))),
            },
            "CERTIFICATION": {
                "maxMb": self.certification.max_size_mb,
                "maxBytes": self.certification.max_size_bytes,
                "extensions": sorted(list(self.certification.allowed_extensions)),
                "accept": ",".join(sorted(list(self.certification.allowed_extensions))),
            },
            "PORTFOLIO": {
                "maxMb": self.certification.max_size_mb,
                "maxBytes": self.certification.max_size_bytes,
                "extensions": sorted(list(self.certification.allowed_extensions)),
                "accept": ",".join(sorted(list(self.certification.allowed_extensions))),
            },
            "PROFILE_ATTACHMENT_QUOTA": {
                "maxMb": self.profile_attachment_quota.max_total_mb,
                "maxBytes": self.profile_attachment_quota.max_total_bytes,
                "errorEn": self.profile_attachment_quota.error_message_en,
                "errorVi": self.profile_attachment_quota.error_message_vi,
            },
            "DOCUMENT_ARCHIVE": {
                "maxMb": self.document_archive.max_size_mb,
                "maxBytes": self.document_archive.max_size_bytes,
                "quotaMb": self.document_archive.quota_mb,
                "quotaBytes": self.document_archive.quota_bytes,
                "extensions": [f".{ext}" if not ext.startswith(".") else ext for ext in self.document_archive.allowed_extensions_list],
                "accept": ",".join([f".{ext}" if not ext.startswith(".") else ext for ext in self.document_archive.allowed_extensions_list]),
                "categories": self.document_archive.allowed_categories,
            },
            "COMPANY": {
                "logoMaxMb": self.company.logo_max_size_mb,
                "logoMaxBytes": self.company.logo_max_bytes,
                "bannerMaxMb": self.company.banner_max_size_mb,
                "bannerMaxBytes": self.company.banner_max_bytes,
                "extensions": sorted(list(self.company.allowed_extensions)),
            },
        }


# Singleton configuration instance
UPLOAD_CONFIG = UploadConfig()
