"""
Convenience shim re-exporting UPLOAD_CONFIG from shared.config.upload_config
"""
from shared.config.upload_config import (
    UPLOAD_CONFIG,
    AvatarConfig,
    CertificationConfig,
    CompanyMediaConfig,
    DocumentArchiveConfig,
    ResumeConfig,
    UploadConfig,
)

__all__ = [
    "UPLOAD_CONFIG",
    "AvatarConfig",
    "ResumeConfig",
    "CertificationConfig",
    "DocumentArchiveConfig",
    "CompanyMediaConfig",
    "UploadConfig",
]
