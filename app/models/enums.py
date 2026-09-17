import enum


class UserRole(str, enum.Enum):
    SUPER_ADMIN = "Super Admin"
    COMPANY_ADMIN = "Company Admin"
    COMPANY_HR = "HR / Recruiter"
    COMPANY_VIEWER = "Viewer"
    JOB_SEEKER = "Job Seeker"


class UserStatus(str, enum.Enum):
    ACTIVE = "Active"
    PENDING = "Pending"
    SUSPENDED = "Suspended"


class CompanyApprovalStatus(str, enum.Enum):
    PENDING = "Pending"
    ACTIVE = "Active"
    REJECTED = "Rejected"
    SUSPENDED = "Suspended"


class JobStatus(str, enum.Enum):
    DRAFT = "Draft"
    PUBLISHED = "Published"
    PAUSED = "Paused"
    CLOSED = "Closed"


class ApplicationStage(str, enum.Enum):
    APPLIED = "Applied"
    SCREENING = "Screening"
    SHORTLISTED = "Shortlisted"
    INTERVIEW_SCHEDULED = "Interview Scheduled"
    OFFER_SENT = "Offer Sent"
    HIRED = "Hired"
    REJECTED = "Rejected"
    WITHDRAWN = "Withdrawn"


class InterviewMode(str, enum.Enum):
    VIDEO = "video"
    IN_PERSON = "in-person"
    PHONE = "phone"


class InterviewStatus(str, enum.Enum):
    INVITED = "invited"
    CONFIRMED = "confirmed"
    DECLINED = "declined"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class ModerationType(str, enum.Enum):
    JOB_POSTING = "Job Posting"
    COMPANY_REGISTRATION = "Company Registration"


class ModerationStatus(str, enum.Enum):
    OPEN = "Open"
    ACTIONED = "Actioned"
    DISMISSED = "Dismissed"


class NotificationType(str, enum.Enum):
    APPLICATION = "application"
    INTERVIEW = "interview"
    STATUS = "status"
    OFFER = "offer"
    QUOTA = "quota"
    SYSTEM = "system"
