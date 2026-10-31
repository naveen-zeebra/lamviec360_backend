#!/usr/bin/env python3
"""
─────────────────────────────────────────────────────────────────────────────
File    : scripts/export_email_scenarios.py
Purpose : Automated generator and maintainer for LàmViệc360 Email Sending
          Scenarios & Content Catalog (Excel .xlsx and CSV formats).
Run     : python scripts/export_email_scenarios.py
─────────────────────────────────────────────────────────────────────────────
"""

import os
import csv
from datetime import datetime
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

# Output Paths
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DOCS_DIR = os.path.join(BASE_DIR, "docs")
EXCEL_PATH = os.path.join(DOCS_DIR, "email_scenarios_catalog.xlsx")
CSV_PATH = os.path.join(DOCS_DIR, "email_scenarios_catalog.csv")

# ─────────────────────────────────────────────────────────────────────────────
# 1. SCENARIOS MASTER DATA
# ─────────────────────────────────────────────────────────────────────────────
SCENARIOS = [
    {
        "id": "SCN-AUTH-01",
        "domain": "Jobseeker Authentication",
        "name": "Candidate Email Verification (Registration / Resend)",
        "audience": "Jobseeker Candidate",
        "category": "Security OTP",
        "trigger": "Candidate submits registration or clicks 'Resend Verification Code'",
        "endpoint": "POST /api/v1/jobseeker/auth/register, POST /api/v1/jobseeker/auth/send-verification-email",
        "dispatcher": "send_verification_email(..., account_type='jobseeker')",
        "file_ref": "shared/utils/email.py:76",
        "sender": "LàmViệc360 <notifications@lamviec360.vn>",
        "recipient": "user.email",
        "subject_en": "{{code}} is your LamViec360 verification code",
        "subject_vi": "{{code}} là mã xác thực tài khoản LàmViệc360 của bạn",
        "placeholders": "{{code}}, {{display_name}}",
        "expiration": "15 minutes",
        "delivery": "Direct SMTP / Transactional API",
        "audit_action": "REGISTER_OTP_SENT",
        "status": "Active / Live",
        "body_en": """Hi {{display_name}},

Welcome to LamViec360! Please use the following 6-digit verification code to verify your email address and activate your job seeker account:

Verification Code: {{code}}

(This verification code expires in 15 minutes)

If you did not request this verification, please disregard this email. Your account remains secure.

Best regards,
LamViec360 Career Portal Team""",
        "body_vi": """Xin chào {{display_name}},

Chào mừng bạn đến với LàmViệc360! Vui lòng sử dụng mã xác thực 6 chữ số dưới đây để xác nhận địa chỉ email và kích hoạt tài khoản ứng viên của bạn:

Mã xác thực (OTP): {{code}}

(Mã xác thực có hiệu lực trong vòng 15 phút)

Nếu bạn không thực hiện yêu cầu này, vui lòng bỏ qua email. Tài khoản của bạn vẫn được bảo mật an toàn.

Trân trọng,
Đội ngũ Cổng Việc làm LàmViệc360""",
        "html_notes": "Navy header (#0F172A), prominent blue dashed OTP box (#EFF6FF, 36px font, letter-spacing 8px), security reminder box.",
        "cta_label": "N/A (Copy/Input 6-digit OTP code directly in browser)",
        "cta_url": "{{JOBSEEKER_WEB_URL}}/verify-email",
        "compliance": "PDPD Decree 13/2023/ND-CP compliant. Automated security notification."
    },
    {
        "id": "SCN-AUTH-02",
        "domain": "Jobseeker Authentication",
        "name": "Candidate Password Reset Request",
        "audience": "Jobseeker Candidate",
        "category": "Account Security",
        "trigger": "Candidate clicks 'Forgot Password' and enters their registered email",
        "endpoint": "POST /api/v1/jobseeker/auth/forgot-password",
        "dispatcher": "send_password_reset_email(...)",
        "file_ref": "shared/utils/email.py:234",
        "sender": "LàmViệc360 Security <security@lamviec360.vn>",
        "recipient": "user.email",
        "subject_en": "{{otp_code}} is your LamViec360 password reset code",
        "subject_vi": "{{otp_code}} là mã đặt lại mật khẩu LàmViệc360 của bạn",
        "placeholders": "{{display_name}}, {{to_email}}, {{otp_code}}, {{reset_url}}, {{reset_token}}",
        "expiration": "15 minutes",
        "delivery": "Direct SMTP / Transactional API",
        "audit_action": "PASSWORD_RESET_REQUESTED",
        "status": "Active / Live",
        "body_en": """Hi {{display_name}},

We received a request to reset the password for your LamViec360 account associated with {{to_email}}.

Your 6-Digit Verification Code: {{otp_code}}
(Valid for 15 minutes)

You can also click the secure link below to set a new password:
{{reset_url}}

If you did not request a password reset, you can safely ignore this email; your password will not be changed.

Best regards,
LamViec360 Security Team""",
        "body_vi": """Xin chào {{display_name}},

Hệ thống đã nhận được yêu cầu đặt lại mật khẩu cho tài khoản LàmViệc360 gắn với địa chỉ {{to_email}}.

Mã xác thực đặt lại mật khẩu: {{otp_code}}
(Có hiệu lực trong vòng 15 phút)

Bạn cũng có thể nhấp trực tiếp vào đường dẫn bảo mật sau để tạo mật khẩu mới:
{{reset_url}}

Nếu bạn không yêu cầu đặt lại mật khẩu, vui lòng bỏ qua email này; mật khẩu hiện tại của bạn vẫn được giữ nguyên an toàn.

Trân trọng,
Bộ phận An toàn & Bảo mật LàmViệc360""",
        "html_notes": "Centered Reset Password button (#2563EB, rounded-8px, padding 13px 28px), fallback direct link box, 15-min warning.",
        "cta_label": "Reset Password / Đặt lại mật khẩu",
        "cta_url": "{{reset_url}}",
        "compliance": "One-time cryptographically hashed token. Revoked immediately upon password change."
    },
    {
        "id": "SCN-AUTH-03",
        "domain": "Employer Authentication",
        "name": "Employer Registration Work Email Verification",
        "audience": "Company Admin / Employer",
        "category": "Security OTP",
        "trigger": "Employer submits company registration form with business tax code and work email",
        "endpoint": "POST /api/v1/company/auth/register, POST /api/v1/company/auth/send-verification-email",
        "dispatcher": "send_verification_email(..., account_type='company')",
        "file_ref": "shared/utils/email.py:76",
        "sender": "LàmViệc360 Employer Solutions <employer-support@lamviec360.vn>",
        "recipient": "user.email",
        "subject_en": "{{code}} is your LamViec360 Employer verification code",
        "subject_vi": "{{code}} là mã xác thực tài khoản Nhà tuyển dụng LàmViệc360",
        "placeholders": "{{code}}, {{display_name}}",
        "expiration": "15 minutes",
        "delivery": "Direct SMTP / Transactional API",
        "audit_action": "COMPANY_REGISTER_OTP_SENT",
        "status": "Active / Live",
        "body_en": """Hi {{display_name}},

Welcome to the LamViec360 Employer Portal! Please use the following 6-digit verification code to verify your company administrator work email and complete your organization registration:

Verification Code: {{code}}

(This verification code expires in 15 minutes)

If you did not request this email, please disregard it.

Best regards,
LamViec360 Employer Solutions Team""",
        "body_vi": """Kính gửi {{display_name}},

Chào mừng Quý doanh nghiệp đến với Cổng Nhà tuyển dụng LàmViệc360! Vui lòng sử dụng mã xác thực 6 chữ số dưới đây để xác thực email quản trị viên và hoàn tất đăng ký doanh nghiệp:

Mã xác thực doanh nghiệp: {{code}}

(Mã xác thực có hiệu lực trong vòng 15 phút)

Nếu Quý vị không thực hiện đăng ký này, xin vui lòng bỏ qua email.

Trân trọng,
Ban Hỗ trợ Doanh nghiệp LàmViệc360""",
        "html_notes": "Employer Portal purple/blue branded badge, prominent OTP dashed card, enterprise security note.",
        "cta_label": "Verify Work Email / Xác thực Email doanh nghiệp",
        "cta_url": "{{COMPANY_WEB_URL}}/company-register",
        "compliance": "Vietnamese National Business Registry tax ID validation integrated."
    },
    {
        "id": "SCN-AUTH-04",
        "domain": "Employer Security",
        "name": "Company Admin Two-Factor Authentication (2FA OTP)",
        "audience": "Company Admin",
        "category": "Security 2FA",
        "trigger": "Company Admin enters valid email and password on employer login portal",
        "endpoint": "POST /api/v1/company/auth/login/initiate, POST /api/v1/company/auth/login/resend-otp",
        "dispatcher": "send_company_2fa_email(...)",
        "file_ref": "shared/utils/email.py:159",
        "sender": "LàmViệc360 Security <security@lamviec360.vn>",
        "recipient": "user.email",
        "subject_en": "{{code}} is your LamViec360 Company Admin 2FA verification code",
        "subject_vi": "{{code}} là mã bảo mật 2FA đăng nhập Quản trị viên LàmViệc360",
        "placeholders": "{{code}}, {{display_name}}, {{company_name}}",
        "expiration": "15 minutes",
        "delivery": "Direct SMTP / Transactional API",
        "audit_action": "COMPANY_2FA_DISPATCHED",
        "status": "Active / Live",
        "body_en": """Hi {{display_name}},

A sign-in request was detected for your Company Administrator account for {{company_name}}.

Please enter the Two-Factor Authentication (2FA) verification code below to complete your login:

2FA Login Security Code: {{code}}

(This 2FA security code expires in 15 minutes)

Security Notice: Never share this code with anyone. If you did not initiate this login request, please change your password immediately.

LamViec360 Employer Portal""",
        "body_vi": """Kính gửi {{display_name}},

Hệ thống phát hiện một yêu cầu đăng nhập vào tài khoản Quản trị viên doanh nghiệp của Quý vị tại {{company_name}}.

Vui lòng nhập mã xác thực 2 lớp (2FA) bên dưới để hoàn tất đăng nhập:

Mã xác thực 2FA: {{code}}

(Mã xác thực bảo mật có hiệu lực trong vòng 15 phút)

Lưu ý an toàn: Tuyệt đối không chia sẻ mã này cho bất kỳ ai. Nếu Quý vị không thực hiện đăng nhập, vui lòng đổi mật khẩu ngay lập tức.

Cổng Nhà tuyển dụng LàmViệc360""",
        "html_notes": "Red alert box warning against sharing code, dark header with 'Employer Security - 2FA' pill badge.",
        "cta_label": "Enter Code on Login Screen",
        "cta_url": "{{COMPANY_WEB_URL}}/employer-login",
        "compliance": "Mandatory 2FA strictly enforced for Company Admin role per security guidelines."
    },
    {
        "id": "SCN-AUTH-05",
        "domain": "Employer Authentication",
        "name": "Employer Password Reset Request",
        "audience": "Company User / Recruiter",
        "category": "Account Security",
        "trigger": "Company User clicks 'Forgot Password' on employer portal",
        "endpoint": "POST /api/v1/company/auth/forgot-password",
        "dispatcher": "send_password_reset_email(..., reset_url=...)",
        "file_ref": "shared/utils/email.py:234",
        "sender": "LàmViệc360 Security <security@lamviec360.vn>",
        "recipient": "user.email",
        "subject_en": "{{otp_code}} is your LamViec360 employer password reset code",
        "subject_vi": "{{otp_code}} là mã đặt lại mật khẩu Nhà tuyển dụng LàmViệc360",
        "placeholders": "{{display_name}}, {{to_email}}, {{otp_code}}, {{reset_url}}, {{reset_token}}",
        "expiration": "15 minutes",
        "delivery": "Direct SMTP / Transactional API",
        "audit_action": "COMPANY_PASSWORD_RESET_REQ",
        "status": "Active / Live",
        "body_en": """Hi {{display_name}},

We received a request to reset the password for your employer account at {{to_email}}.

Your 6-Digit Password Reset Code: {{otp_code}}
(Valid for 15 minutes)

Or click the link below to set a new password:
{{reset_url}}

If you did not request this, please disregard this email.

Best regards,
LamViec360 Security Team""",
        "body_vi": """Kính gửi {{display_name}},

Chúng tôi đã nhận được yêu cầu đặt lại mật khẩu cho tài khoản tuyển dụng gắn với email {{to_email}}.

Mã xác thực đặt lại mật khẩu: {{otp_code}}
(Có hiệu lực trong vòng 15 phút)

Hoặc nhấp vào đường dẫn bên dưới để thiết lập mật khẩu mới:
{{reset_url}}

Nếu Quý vị không yêu cầu thao tác này, xin vui lòng bỏ qua email.

Trân trọng,
Bộ phận An toàn & Bảo mật LàmViệc360""",
        "html_notes": "Employer portal themed reset layout with button, OTP fallback, and security advisory.",
        "cta_label": "Set New Password / Đặt mật khẩu mới",
        "cta_url": "{{reset_url}}",
        "compliance": "Single-use token with 15-min auto-invalidation."
    },
    {
        "id": "SCN-ADMIN-01",
        "domain": "Super Admin Moderation",
        "name": "Company Account Verified & Approved Notice",
        "audience": "Company Admin",
        "category": "Moderation Decision",
        "trigger": "Super Admin reviews tax code, business documents, and clicks 'Verify & Approve'",
        "endpoint": "PATCH /api/v1/admin/companies/{id}/verification",
        "dispatcher": "send_company_approval_email(...)",
        "file_ref": "shared/utils/email.py:416",
        "sender": "LàmViệc360 Administration <admin@lamviec360.vn>",
        "recipient": "company.contact_email / admin.email",
        "subject_en": "Congratulations! Your company account has been verified - LàmViệc360",
        "subject_vi": "Chúc mừng! Doanh nghiệp của bạn đã được xác thực thành công trên LàmViệc360",
        "placeholders": "{{contact_name}}, {{company_name}}, {{portal_url}}",
        "expiration": "Permanent approval",
        "delivery": "Direct SMTP / Transactional API",
        "audit_action": "COMPANY_APPROVED",
        "status": "Active / Live",
        "body_en": """Hi {{contact_name}},

Great news! Your company profile for {{company_name}} has been officially reviewed, verified, and approved by the LàmViệc360 administration team.

What you can do right now:
- Publish Job Openings: reach thousands of verified candidates across Vietnam.
- Manage Applicants: pipeline screening, team evaluation notes, and interview scheduling.
- Verified Employer Badge: proudly showcased on all your public job postings.

Sign in to your Employer Portal:
{{portal_url}}

Best regards,
LàmViệc360 Administration Team""",
        "body_vi": """Kính gửi {{contact_name}},

Tin vui! Hồ sơ doanh nghiệp của Quý vị cho {{company_name}} đã được Ban Quản trị LàmViệc360 chính thức thẩm định, đối chiếu pháp lý và phê duyệt xác thực.

Các quyền lợi doanh nghiệp có thể sử dụng ngay:
- Đăng tin tuyển dụng không giới hạn: tiếp cận hàng ngàn ứng viên tiềm năng trên toàn quốc.
- Quy trình tuyển dụng ATS: sàng lọc hồ sơ, ghi chú đánh giá và lên lịch phỏng vấn thông minh.
- Huy hiệu Doanh nghiệp đã xác thực (Verified Employer): nổi bật trên mọi tin tuyển dụng và trang công ty.

Đăng nhập vào Cổng Nhà tuyển dụng:
{{portal_url}}

Trân trọng,
Ban Quản trị Hệ sinh thái Tuyển dụng LàmViệc360""",
        "html_notes": "Green verified badge with checkmark, feature highlight list with icons, direct login CTA button.",
        "cta_label": "Sign in to Employer Portal / Đăng nhập Cổng Doanh nghiệp",
        "cta_url": "{{portal_url}}",
        "compliance": "Confirms official verified employer status under Vietnamese business registration compliance."
    },
    {
        "id": "SCN-ADMIN-02",
        "domain": "Super Admin Moderation",
        "name": "Company Account Registration Rejection Notice",
        "audience": "Company Applicant",
        "category": "Moderation Decision",
        "trigger": "Super Admin rejects company registration with specific audit reason notes",
        "endpoint": "PATCH /api/v1/admin/companies/{id}/verification",
        "dispatcher": "send_company_rejection_email(...)",
        "file_ref": "shared/utils/email.py:499",
        "sender": "LàmViệc360 Moderation <moderation@lamviec360.vn>",
        "recipient": "company.contact_email / admin.email",
        "subject_en": "Update regarding your company registration on LàmViệc360: {{company_name}}",
        "subject_vi": "Thông báo về việc xét duyệt đăng ký doanh nghiệp trên LàmViệc360: {{company_name}}",
        "placeholders": "{{contact_name}}, {{company_name}}, {{reason}}, {{support_email}}",
        "expiration": "Immediate notification",
        "delivery": "Direct SMTP / Transactional API",
        "audit_action": "COMPANY_REJECTED",
        "status": "Active / Live",
        "body_en": """Hi {{contact_name}},

Thank you for your interest in hiring through LàmViệc360. Our verification team has reviewed your company registration for {{company_name}}.

Unfortunately, we are unable to approve your company account at this time due to the following reason:
{{reason}}

Need assistance or have updated documents?
If you have updated business registration certificates or believe this decision was made in error, please reply to this email or contact our support team at {{support_email}}.

Best regards,
LàmViệc360 Verification Team""",
        "body_vi": """Kính gửi {{contact_name}},

Cảm ơn Quý doanh nghiệp đã quan tâm và đăng ký tài khoản tuyển dụng trên LàmViệc360. Bộ phận thẩm định đã kiểm tra hồ sơ đăng ký của {{company_name}}.

Rất tiếc, hiện tại chúng tôi chưa thể phê duyệt tài khoản doanh nghiệp của Quý vị vì lý do sau:
{{reason}}

Hướng dẫn cập nhật giấy tờ hoặc hỗ trợ khiếu nại:
Nếu Quý vị có giấy phép kinh doanh cập nhật hoặc cần giải đáp thêm, vui lòng phản hồi email này hoặc liên hệ bộ phận hỗ trợ tại {{support_email}}.

Trân trọng,
Hội đồng Thẩm định Doanh nghiệp LàmViệc360""",
        "html_notes": "Red border status alert, clear rejection reason container, support email mailto link.",
        "cta_label": "Contact Support / Liên hệ Hỗ trợ",
        "cta_url": "mailto:{{support_email}}",
        "compliance": "Mandatory administrative explanation to protect platform candidate trust."
    },
    {
        "id": "SCN-TEAM-01",
        "domain": "Team Collaboration",
        "name": "Workspace Team Member Invitation",
        "audience": "Invited Team Member (HR / Recruiter / Viewer)",
        "category": "Team Invitation",
        "trigger": "Company Admin invites a new colleague via /company/team with assigned role",
        "endpoint": "POST /api/v1/company/team/invitations",
        "dispatcher": "send_team_invitation_email(...)",
        "file_ref": "shared/utils/email.py:576",
        "sender": "LàmViệc360 Team <invitations@lamviec360.vn>",
        "recipient": "invitation.email",
        "subject_en": "You're invited to join {{company_name}} on LàmViệc360 as {{role_name}}",
        "subject_vi": "Lời mời tham gia không gian làm việc của {{company_name}} trên LàmViệc360 với vai trò {{role_name}}",
        "placeholders": "{{inviter_name}}, {{company_name}}, {{role_name}}, {{activation_url}}, {{expiry_date_str}}, {{company_logo_url}}, {{custom_message}}, {{support_email}}",
        "expiration": "72 hours strict security expiry",
        "delivery": "Direct SMTP / Transactional API",
        "audit_action": "TEAM_INVITATION_SENT",
        "status": "Active / Live",
        "body_en": """Hello,

{{inviter_name}} has invited you to collaborate in the {{company_name}} employer workspace on LàmViệc360 as {{role_name}}.

{{custom_message_block}}

To accept this invitation and activate your account, click the link below:
{{activation_url}}

Notice: This invitation is strictly valid for 72 hours and will expire on {{expiry_date_str}}.

Quick instructions:
1. Open the activation link above.
2. Set up your secure password and profile.
3. Access your {{company_name}} hiring dashboard.

Best regards,
LàmViệc360 Team""",
        "body_vi": """Xin chào,

{{inviter_name}} đã gửi lời mời bạn tham gia cộng tác trong không gian tuyển dụng của {{company_name}} trên nền tảng LàmViệc360 với vai trò {{role_name}}.

{{custom_message_block}}

Để chấp nhận lời mời và kích hoạt tài khoản của bạn, vui lòng truy cập đường dẫn sau:
{{activation_url}}

Lưu ý bảo mật: Lời mời này có hiệu lực trong vòng 72 giờ và sẽ hết hạn vào ngày {{expiry_date_str}}.

Các bước kích hoạt nhanh chóng:
1. Nhấp vào đường dẫn kích hoạt ở trên.
2. Thiết lập mật khẩu bảo mật và xác nhận thông tin cá nhân.
3. Bắt đầu làm việc trên trang quản trị tuyển dụng của {{company_name}}.

Trân trọng,
Đội ngũ LàmViệc360""",
        "html_notes": "Company logo header, blue invitation badge, 3-step numbered guidance, 72h yellow warning card.",
        "cta_label": "Accept Invitation & Join Team / Chấp nhận lời mời & Tham gia",
        "cta_url": "{{activation_url}}",
        "compliance": "Role-based access pre-assigned. Activation requires self-service password establishment."
    },
    {
        "id": "SCN-TEAM-02",
        "domain": "Team Collaboration",
        "name": "Resend Team Member Workspace Invitation",
        "audience": "Invited Team Member",
        "category": "Team Invitation",
        "trigger": "Company Admin clicks 'Resend' on an unactivated pending team invitation",
        "endpoint": "POST /api/v1/company/team/invitations/{id}/resend",
        "dispatcher": "send_team_invitation_email(...)",
        "file_ref": "shared/utils/email.py:576, services/company_service/app/api/team/service.py:219",
        "sender": "LàmViệc360 Team <invitations@lamviec360.vn>",
        "recipient": "invitation.email",
        "subject_en": "Reminder: You're invited to join {{company_name}} on LàmViệc360 as {{role_name}}",
        "subject_vi": "Nhắc nhở: Lời mời tham gia {{company_name}} trên LàmViệc360 với vai trò {{role_name}}",
        "placeholders": "{{inviter_name}}, {{company_name}}, {{role_name}}, {{activation_url}}, {{expiry_date_str}}",
        "expiration": "72 hours (refreshed)",
        "delivery": "Direct SMTP / Transactional API",
        "audit_action": "TEAM_INVITATION_RESENT",
        "status": "Active / Live",
        "body_en": """Hello,

This is a reminder that {{inviter_name}} has invited you to join the {{company_name}} team workspace on LàmViệc360 as {{role_name}}.

Your refreshed activation link (valid for 72 hours until {{expiry_date_str}}):
{{activation_url}}

Click the link above to set up your password and access the workspace.

Best regards,
LàmViệc360 Team""",
        "body_vi": """Xin chào,

Đây là thông báo nhắc nhở về lời mời từ {{inviter_name}} mời bạn tham gia không gian làm việc của {{company_name}} trên LàmViệc360 với vai trò {{role_name}}.

Đường dẫn kích hoạt mới (có hiệu lực trong 72 giờ tới ngày {{expiry_date_str}}):
{{activation_url}}

Nhấp vào đường dẫn trên để tạo mật khẩu và bắt đầu sử dụng không gian tuyển dụng.

Trân trọng,
Đội ngũ LàmViệc360""",
        "html_notes": "Reminder header badge, updated token with extended 72h window, direct activation button.",
        "cta_label": "Accept Invitation & Join Team / Kích hoạt tài khoản ngay",
        "cta_url": "{{activation_url}}",
        "compliance": "Previous invitation token invalidated, new cryptographically signed token issued."
    },
    {
        "id": "SCN-APP-01",
        "domain": "Candidate Applications",
        "name": "Application Submission Confirmation (24-Hour Review SLA)",
        "audience": "Jobseeker Candidate",
        "category": "Application Receipt",
        "trigger": "Candidate submits a job application via the public jobseeker portal",
        "endpoint": "POST /api/v1/jobseeker/jobs/{id}/apply, POST /api/v1/jobseeker/applications",
        "dispatcher": "send_application_confirmation_email(...)",
        "file_ref": "shared/utils/email.py:323",
        "sender": "LàmViệc360 <applications@lamviec360.vn>",
        "recipient": "candidate.email",
        "subject_en": "Application Received: {{job_title}} at {{company_name}} (#{{application_id}})",
        "subject_vi": "Xác nhận nộp hồ sơ thành công: {{job_title}} tại {{company_name}} (#{{application_id}})",
        "placeholders": "{{candidate_name}}, {{job_title}}, {{company_name}}, {{application_id}}, {{tracker_url}}",
        "expiration": "24-hour employer initial review SLA target",
        "delivery": "Direct SMTP / Transactional API",
        "audit_action": "JOB_APPLICATION_SUBMITTED",
        "status": "Active / Live",
        "body_en": """Hi {{candidate_name}},

Your application for {{job_title}} at {{company_name}} has been received successfully (Application ID: #{{application_id}}).

Your profile is under review, and you can expect an update within 24 hours.

View and track your application status anytime:
{{tracker_url}}

Best regards,
LamViec360 Team""",
        "body_vi": """Chào bạn {{candidate_name}},

Hồ sơ ứng tuyển của bạn cho vị trí {{job_title}} tại {{company_name}} đã được hệ thống ghi nhận thành công (Mã hồ sơ: #{{application_id}}).

Hồ sơ của bạn đang được phòng nhân sự thẩm định. Bạn sẽ nhận được phản hồi cập nhật trong vòng 24 giờ tới.

Theo dõi tiến độ xử lý hồ sơ bất kỳ lúc nào tại:
{{tracker_url}}

Trân trọng,
Đội ngũ LàmViệc360""",
        "html_notes": "Green review status card with clock icon, clear application ID display, Track Application button.",
        "cta_label": "View Application / Xem hồ sơ ứng tuyển",
        "cta_url": "{{tracker_url}}",
        "compliance": "Includes candidate application tracker URL and 24-hour review SLA commitment."
    },
    {
        "id": "SCN-ATS-01",
        "domain": "ATS Recruitment Pipeline",
        "name": "Application Acknowledgment & Initial Review Notice",
        "audience": "Jobseeker Candidate",
        "category": "ATS Pipeline Notification",
        "trigger": "Recruiter moves candidate to 'Screening' stage or manually sends acknowledgment",
        "endpoint": "POST /api/v1/company/applicants/{id}/email",
        "dispatcher": "ATS Template GT-1 (Pipeline Email Dispatcher)",
        "file_ref": "lamviec360_company_web/lib/companyStore.js:374",
        "sender": "Phòng Tuyển dụng {{company_name}} <recruiting@{{company_domain}}>",
        "recipient": "candidate.email",
        "subject_en": "Application Acknowledgment: {{job_title}} at {{company_name}}",
        "subject_vi": "Xác nhận đã nhận hồ sơ ứng tuyển {{job_title}} - {{company_name}}",
        "placeholders": "{{candidate_name}}, {{job_title}}, {{company_name}}",
        "expiration": "3 - 5 business days screening notice",
        "delivery": "Company ATS Mailer / SMTP",
        "audit_action": "APPLICANT_EMAIL_SENT",
        "status": "Active / Live Template",
        "body_en": """Dear {{candidate_name}},

{{company_name}} acknowledges receipt of your application for the {{job_title}} position.

Our hiring committee is currently reviewing your qualifications and portfolio. We will notify you of screening outcomes and next steps within 3 to 5 business days.

Thank you for your interest in joining {{company_name}}.

Sincerely,
Recruiting Team, {{company_name}}""",
        "body_vi": """Kính gửi {{candidate_name}},

{{company_name}} xin xác nhận đã nhận được hồ sơ ứng tuyển của bạn cho vị trí {{job_title}}.

Hội đồng tuyển dụng đang tiến hành đánh giá chi tiết hồ sơ của bạn. Chúng tôi sẽ thông báo kết quả sàng lọc và các bước tiếp theo trong vòng 3 - 5 ngày làm việc.

Cảm ơn sự quan tâm và tình cảm bạn dành cho {{company_name}}.

Trân trọng,
Phòng Tuyển dụng {{company_name}}""",
        "html_notes": "Clean corporate typography, company signature, professional acknowledgment tone.",
        "cta_label": "N/A",
        "cta_url": "",
        "compliance": "Company branded communication per hiring pipeline standards."
    },
    {
        "id": "SCN-ATS-02",
        "domain": "ATS Recruitment Pipeline",
        "name": "Candidate Document Verification Request (PDPD Compliant)",
        "audience": "Jobseeker Candidate",
        "category": "Verification Request",
        "trigger": "Recruiter requests verification documents (payslips, previous contract, degree)",
        "endpoint": "POST /api/v1/company/applicants/{id}/email",
        "dispatcher": "ATS Template GT-2 (Pipeline Email Dispatcher)",
        "file_ref": "lamviec360_company_web/lib/companyStore.js:391",
        "sender": "Phòng Nhân sự {{company_name}} <hr@{{company_domain}}>",
        "recipient": "candidate.email",
        "subject_en": "Document Verification Request: {{job_title}} - {{company_name}}",
        "subject_vi": "Yêu cầu bổ sung tài liệu xác minh: {{job_title}} - {{company_name}}",
        "placeholders": "{{candidate_name}}, {{job_title}}, {{company_name}}",
        "expiration": "5 business days upload target",
        "delivery": "Company ATS Mailer / SMTP",
        "audit_action": "APPLICANT_DOC_REQUEST_SENT",
        "status": "Active / Live Template",
        "body_en": """Dear {{candidate_name}},

To finalize your evaluation for {{job_title}}, {{company_name}} requests that you upload proof of past experience (most recent 3 months payslips, resignation decision, or previous contract) via your secure candidate portal on LàmViệc360.

All documents are encrypted with AES-256 and strictly protected in full compliance with Decree 13/2023/ND-CP (Personal Data Protection Decree - PDPD). They are used exclusively for internal recruitment verification.

Sincerely,
Human Resources, {{company_name}}""",
        "body_vi": """Kính gửi {{candidate_name}},

Để hoàn thiện thủ tục đánh giá ứng viên vào vị trí {{job_title}}, {{company_name}} kính đề nghị bạn tải lên các tài liệu xác thực kinh nghiệm (bảng lương 3 tháng gần nhất, quyết định thôi việc hoặc hợp đồng lao động trước đây) qua cổng ứng viên LàmViệc360.

Toàn bộ tài liệu được mã hóa chuẩn AES-256 và bảo mật nghiêm ngặt theo Nghị định 13/2023/NĐ-CP (PDPD), chỉ phục vụ mục đích thẩm định tuyển dụng nội bộ.

Trân trọng,
Phòng Nhân sự {{company_name}}""",
        "html_notes": "Security encryption icon, Decree 13/2023/ND-CP privacy seal, direct upload portal button.",
        "cta_label": "Upload Verification Documents / Tải lên tài liệu",
        "cta_url": "{{JOBSEEKER_WEB_URL}}/applications",
        "compliance": "Mandatory Vietnam PDPD Decree 13/2023/ND-CP explicit consent and encryption notice."
    },
    {
        "id": "SCN-ATS-03",
        "domain": "ATS Recruitment Pipeline",
        "name": "Technical Interview Invitation (Online / In-Person)",
        "audience": "Jobseeker Candidate",
        "category": "Interview Scheduling",
        "trigger": "Recruiter schedules a Technical Interview round in the ATS pipeline",
        "endpoint": "POST /api/v1/company/applicants/{id}/schedule-interview",
        "dispatcher": "ATS Template IT-1 (Pipeline Email Dispatcher)",
        "file_ref": "lamviec360_company_web/lib/companyStore.js:309",
        "sender": "Đội ngũ Tuyển dụng {{company_name}} <recruiting@{{company_domain}}>",
        "recipient": "candidate.email",
        "subject_en": "Technical Interview Invitation: {{job_title}} at {{company_name}}",
        "subject_vi": "Thư mời phỏng vấn kỹ thuật: {{job_title}} tại {{company_name}}",
        "placeholders": "{{candidate_name}}, {{job_title}}, {{company_name}}, {{interview_date}}, {{interview_time}}, {{interview_link}}",
        "expiration": "Confirmation requested within 24h",
        "delivery": "Company ATS Mailer / SMTP",
        "audit_action": "INTERVIEW_SCHEDULED",
        "status": "Active / Live Template",
        "body_en": """Dear {{candidate_name}},

We were impressed by your background and are pleased to invite you to a Technical Interview for the {{job_title}} position at {{company_name}}.

Interview Details:
- Date: {{interview_date}} at {{interview_time}}
- Format: Online via Google Meet
- Meeting Link: {{interview_link}}
- Estimated Duration: 45 - 60 minutes

Please reply to this email to confirm if this time works for you, or suggest an alternative slot.

Best of luck with your interview!

Sincerely,
Hiring Team, {{company_name}}""",
        "body_vi": """Kính gửi {{candidate_name}},

Chúng tôi rất ấn tượng với hồ sơ của bạn và trân trọng kính mời bạn tham gia vòng Phỏng vấn Kỹ thuật cho vị trí {{job_title}} tại {{company_name}}.

Thông tin chi tiết buổi phỏng vấn:
- Thời gian: {{interview_date}} lúc {{interview_time}}
- Hình thức: Phỏng vấn trực tuyến qua Google Meet
- Đường dẫn tham gia: {{interview_link}}
- Thời lượng dự kiến: 45 - 60 phút

Vui lòng phản hồi email này để xác nhận thời gian có phù hợp với bạn không, hoặc đề xuất khung giờ thuận tiện khác.

Chúc bạn có một buổi phỏng vấn thật tự tin và thành công!

Trân trọng,
Đội ngũ Tuyển dụng {{company_name}}""",
        "html_notes": "Google Meet icon, structured date/time/link card, Join Meeting button.",
        "cta_label": "Join Video Meeting / Tham gia phỏng vấn",
        "cta_url": "{{interview_link}}",
        "compliance": "Calendar invite compatible, timezone explicitly confirmed (ICT / UTC+7)."
    },
    {
        "id": "SCN-ATS-04",
        "domain": "ATS Recruitment Pipeline",
        "name": "HR Screening Round Interview Invitation",
        "audience": "Jobseeker Candidate",
        "category": "Interview Scheduling",
        "trigger": "Recruiter schedules a 20-30 minute preliminary HR conversation",
        "endpoint": "POST /api/v1/company/applicants/{id}/schedule-interview",
        "dispatcher": "ATS Template IT-2 (Pipeline Email Dispatcher)",
        "file_ref": "lamviec360_company_web/lib/companyStore.js:332",
        "sender": "{{sender_name}} <{{sender_email}}>",
        "recipient": "candidate.email",
        "subject_en": "HR Screening Invitation: {{job_title}} - {{company_name}}",
        "subject_vi": "Thư mời trao đổi sơ bộ (HR Screening): {{job_title}} - {{company_name}}",
        "placeholders": "{{candidate_name}}, {{job_title}}, {{company_name}}, {{interview_date}}, {{interview_time}}, {{interview_location}}, {{sender_name}}",
        "expiration": "Confirmation requested",
        "delivery": "Company ATS Mailer / SMTP",
        "audit_action": "INTERVIEW_SCHEDULED",
        "status": "Active / Live Template",
        "body_en": """Dear {{candidate_name}},

Thank you for applying for the {{job_title}} role at {{company_name}}.

Our HR team would like to invite you to a short conversation (20 - 30 minutes) to introduce our projects, workplace culture, and discuss your career aspirations.

- Date & Time: {{interview_date}} at {{interview_time}}
- Location / Link: {{interview_location}}

Please confirm via email if this schedule fits your calendar. Looking forward to our chat!

Sincerely,
{{sender_name}}
Human Resources, {{company_name}}""",
        "body_vi": """Kính gửi {{candidate_name}},

Cảm ơn bạn đã ứng tuyển vào vị trí {{job_title}} tại {{company_name}}.

Bộ phận Tuyển dụng muốn mời bạn tham gia một buổi trao đổi ngắn (khoảng 20 - 30 phút) để giới thiệu tổng quan về dự án, môi trường làm việc cũng như trao đổi về định hướng và mong muốn của bạn.

- Thời gian: {{interview_date}} lúc {{interview_time}}
- Địa điểm / Đường dẫn: {{interview_location}}

Vui lòng xác nhận qua email nếu khung giờ trên phù hợp với bạn. Hẹn gặp lại bạn trong buổi trao đổi!

Trân trọng,
{{sender_name}}
Phòng Nhân sự {{company_name}}""",
        "html_notes": "Friendly introduction styling, location / video link slot, direct reply invitation.",
        "cta_label": "Confirm Schedule / Xác nhận lịch hẹn",
        "cta_url": "{{interview_location}}",
        "compliance": "Human-to-human candidate experience optimization."
    },
    {
        "id": "SCN-ATS-05",
        "domain": "ATS Recruitment Pipeline",
        "name": "Formal Job Offer Letter & Compensation Package",
        "audience": "Selected Candidate",
        "category": "Job Offer",
        "trigger": "Company moves candidate to 'Offered' stage and extends formal offer letter",
        "endpoint": "POST /api/v1/company/applicants/{id}/offer",
        "dispatcher": "ATS Template OT-1 (Pipeline Email Dispatcher)",
        "file_ref": "lamviec360_company_web/lib/companyStore.js:353",
        "sender": "Ban Giám đốc {{company_name}} <careers@{{company_domain}}>",
        "recipient": "candidate.email",
        "subject_en": "Formal Job Offer: {{job_title}} - {{company_name}}",
        "subject_vi": "Thư mời nhận việc (Job Offer): {{job_title}} - {{company_name}}",
        "placeholders": "{{candidate_name}}, {{job_title}}, {{company_name}}, {{date}}",
        "expiration": "Response required by specified deadline date",
        "delivery": "Company ATS Mailer / SMTP",
        "audit_action": "JOB_OFFER_EXTENDED",
        "status": "Active / Live Template",
        "body_en": """Dear {{candidate_name}},

On behalf of the leadership at {{company_name}}, we are thrilled to extend a formal Job Offer for the position of {{job_title}}!

We were thoroughly impressed by your skills, experience, and energy throughout our recruitment process. We are confident you will make an outstanding impact on our team and mission.

Details regarding salary, benefits, probation period, and start date are attached.

Please review and confirm your acceptance before {{date}}. Feel free to reach out with any questions.

Welcome to the {{company_name}} family!

Warm regards,
Board of Directors, {{company_name}}""",
        "body_vi": """Kính gửi {{candidate_name}},

Thay mặt Ban Lãnh đạo {{company_name}}, chúng tôi vô cùng vui mừng gửi tới bạn Thư mời nhận việc (Job Offer) cho vị trí {{job_title}}!

Chúng tôi đánh giá rất cao năng lực và tinh thần làm việc của bạn trong suốt các vòng tuyển dụng vừa qua, và tin tưởng rằng bạn sẽ là một mảnh ghép xuất sắc đóng góp vào sự phát triển của công ty.

Chi tiết về mức lương, chế độ đãi ngộ, thời gian thử việc và ngày bắt đầu công việc đã được đính kèm chi tiết.

Vui lòng xem xét và gửi phản hồi xác nhận trước ngày {{date}}. Nếu bạn có bất kỳ câu hỏi nào, xin đừng ngần ngại liên hệ trực tiếp với chúng tôi.

Chào mừng bạn gia nhập đại gia đình {{company_name}}!

Trân trọng,
Ban Giám đốc {{company_name}}""",
        "html_notes": "Celebratory gold/blue header, attached PDF offer overview card, Review Offer button.",
        "cta_label": "Review & Accept Offer / Xem & Xác nhận Thư nhận việc",
        "cta_url": "{{JOBSEEKER_WEB_URL}}/applications",
        "compliance": "Legally binding offer framework under Vietnam Labor Code 2019."
    },
    {
        "id": "SCN-REJ-01",
        "domain": "ATS Candidate Rejection",
        "name": "Rejection — Profile Does Not Match Requirements (Default)",
        "audience": "Jobseeker Candidate",
        "category": "Candidate Rejection",
        "trigger": "Recruiter moves candidate to 'Rejected' (Default Reason RT-1)",
        "endpoint": "POST /api/v1/company/applicants/{id}/reject",
        "dispatcher": "ATS Template RT-1 (Rejection Mailer)",
        "file_ref": "lamviec360_company_web/lib/companyStore.js:237",
        "sender": "Đội ngũ Tuyển dụng {{company_name}} <recruiting@{{company_domain}}>",
        "recipient": "candidate.email",
        "subject_en": "Update regarding your application for {{job_title}} at {{company_name}}",
        "subject_vi": "Cập nhật về hồ sơ ứng tuyển {{job_title}} tại {{company_name}}",
        "placeholders": "{{candidate_name}}, {{job_title}}, {{company_name}}",
        "expiration": "Optional 24h/48h delay buffer",
        "delivery": "Company ATS Mailer / SMTP",
        "audit_action": "APPLICANT_REJECTED",
        "status": "Active / Live Template",
        "body_en": """Dear {{candidate_name}},

Thank you for your interest and for applying for the {{job_title}} role at {{company_name}}.

After careful review of your qualifications against our current requirements, we regret to inform you that we will not be moving forward with your candidacy for this opening.

Your profile has been safely saved in our talent pool so we can proactively reach out for future opportunities that align with your background.

We wish you every success in your career journey!

Sincerely,
Recruiting Team, {{company_name}}""",
        "body_vi": """Kính gửi {{candidate_name}},

Cảm ơn bạn đã quan tâm và ứng tuyển vào vị trí {{job_title}} tại {{company_name}}.

Sau khi cân nhắc kỹ lưỡng hồ sơ và đối chiếu các yêu cầu hiện tại của vị trí, chúng tôi rất tiếc phải thông báo hiện tại công ty chưa thể chọn bạn đi tiếp trong quy trình tuyển dụng lần này.

Hồ sơ của bạn đã được lưu trữ an toàn trong hệ thống dữ liệu nhân tài của chúng tôi để ưu tiên liên hệ cho các cơ hội phù hợp hơn trong tương lai.

Chúc bạn luôn gặt hái nhiều thành công và may mắn trên con đường sự nghiệp!

Trân trọng,
Đội ngũ Tuyển dụng {{company_name}}""",
        "html_notes": "Polite empathetic layout, talent pool retention notice, support for automated delay.",
        "cta_label": "Explore Other Jobs on LàmViệc360",
        "cta_url": "{{SEEKER_URL}}/jobs",
        "compliance": "Maintains employer brand integrity and positive candidate NPS."
    },
    {
        "id": "SCN-REJ-02",
        "domain": "ATS Candidate Rejection",
        "name": "Rejection — Role Filled Internally",
        "audience": "Jobseeker Candidate",
        "category": "Candidate Rejection",
        "trigger": "Recruiter selects reason 'Role filled internally' (RT-2)",
        "endpoint": "POST /api/v1/company/applicants/{id}/reject",
        "dispatcher": "ATS Template RT-2 (Rejection Mailer)",
        "file_ref": "lamviec360_company_web/lib/companyStore.js:256",
        "sender": "Phòng Nhân sự {{company_name}} <hr@{{company_domain}}>",
        "recipient": "candidate.email",
        "subject_en": "Notice regarding the {{job_title}} position at {{company_name}}",
        "subject_vi": "Thông báo về vị trí {{job_title}} tại {{company_name}}",
        "placeholders": "{{candidate_name}}, {{job_title}}, {{company_name}}",
        "expiration": "Optional delay buffer",
        "delivery": "Company ATS Mailer / SMTP",
        "audit_action": "APPLICANT_REJECTED",
        "status": "Active / Live Template",
        "body_en": """Dear {{candidate_name}},

Thank you for dedicating your time to apply for the {{job_title}} position at {{company_name}}.

We would like to inform you that this vacancy has been filled through an internal appointment within our company.

We were very impressed by your qualifications and expertise. Our HR department will keep your details on file and reach out as soon as new positions matching your strengths open up.

Wishing you great success!

Sincerely,
Human Resources, {{company_name}}""",
        "body_vi": """Kính gửi {{candidate_name}},

Cảm ơn bạn đã dành thời gian quý báu ứng tuyển vào vị trí {{job_title}} tại {{company_name}}.

Chúng tôi xin thông báo rằng vị trí tuyển dụng này đã được bổ nhiệm từ nguồn lực nội bộ của công ty.

Chúng tôi rất ấn tượng với năng lực chuyên môn cùng kinh nghiệm của bạn. Bộ phận Nhân sự sẽ chủ động kết nối lại với bạn ngay khi có các vị trí mới phù hợp với thế mạnh của bạn.

Chúc bạn nhiều thành công!

Trân trọng,
Phòng Nhân sự {{company_name}}""",
        "html_notes": "Polite explanation of internal succession, talent network retention encouragement.",
        "cta_label": "N/A",
        "cta_url": "",
        "compliance": "Transparent candidate relationship management."
    },
    {
        "id": "SCN-REJ-03",
        "domain": "ATS Candidate Rejection",
        "name": "Rejection — More Experienced Candidate Selected",
        "audience": "Jobseeker Candidate",
        "category": "Candidate Rejection",
        "trigger": "Recruiter selects reason 'More experienced candidate selected' (RT-3)",
        "endpoint": "POST /api/v1/company/applicants/{id}/reject",
        "dispatcher": "ATS Template RT-3 (Rejection Mailer)",
        "file_ref": "lamviec360_company_web/lib/companyStore.js:275",
        "sender": "Hội đồng Tuyển dụng {{company_name}} <recruiting@{{company_domain}}>",
        "recipient": "candidate.email",
        "subject_en": "Recruitment Result: {{job_title}} - {{company_name}}",
        "subject_vi": "Kết quả tuyển dụng vị trí {{job_title}} - {{company_name}}",
        "placeholders": "{{candidate_name}}, {{job_title}}, {{company_name}}",
        "expiration": "Optional delay buffer",
        "delivery": "Company ATS Mailer / SMTP",
        "audit_action": "APPLICANT_REJECTED",
        "status": "Active / Live Template",
        "body_en": """Dear {{candidate_name}},

Thank you for interviewing and discussing the {{job_title}} opportunity with {{company_name}}.

We received many outstanding applications, and after thorough evaluations, our hiring committee has decided to select a candidate with more specialized experience in the specific domain of this project.

We deeply appreciate your time and thorough preparation. We hope to have the opportunity to collaborate with you on upcoming projects.

Sincerely,
Hiring Committee, {{company_name}}""",
        "body_vi": """Kính gửi {{candidate_name}},

Cảm ơn bạn đã tham gia ứng tuyển và trao đổi về vị trí {{job_title}} tại {{company_name}}.

Chúng tôi đã nhận được nhiều hồ sơ chất lượng cao và sau các vòng đánh giá, hội đồng tuyển dụng đã quyết định lựa chọn ứng viên có kinh nghiệm chuyên sâu hơn trong lĩnh vực cụ thể của dự án lần này.

Chúng tôi rất trân trọng thời gian và sự chuẩn bị chu đáo của bạn. Rất mong sẽ có cơ hội hợp tác cùng bạn trong các dự án sắp tới.

Trân trọng,
Hội đồng Tuyển dụng {{company_name}}""",
        "html_notes": "Post-interview respectful feedback tone, appreciation for candidate preparation.",
        "cta_label": "N/A",
        "cta_url": "",
        "compliance": "Professional post-interview feedback."
    },
    {
        "id": "SCN-REJ-04",
        "domain": "ATS Candidate Rejection",
        "name": "Rejection — Position Put On Hold / Cancelled",
        "audience": "Jobseeker Candidate",
        "category": "Candidate Rejection",
        "trigger": "Recruiter selects reason 'Position put on hold' (RT-4)",
        "endpoint": "POST /api/v1/company/applicants/{id}/reject",
        "dispatcher": "ATS Template RT-4 (Rejection Mailer)",
        "file_ref": "lamviec360_company_web/lib/companyStore.js:292",
        "sender": "Đội ngũ Nhân sự {{company_name}} <hr@{{company_domain}}>",
        "recipient": "candidate.email",
        "subject_en": "Recruitment Pause: {{job_title}} at {{company_name}}",
        "subject_vi": "Tạm dừng tuyển dụng vị trí {{job_title}} tại {{company_name}}",
        "placeholders": "{{candidate_name}}, {{job_title}}, {{company_name}}",
        "expiration": "Optional delay buffer",
        "delivery": "Company ATS Mailer / SMTP",
        "audit_action": "APPLICANT_REJECTED",
        "status": "Active / Live Template",
        "body_en": """Dear {{candidate_name}},

Thank you for your interest and for submitting your application for {{job_title}} at {{company_name}}.

Due to strategic adjustments in our business plan and project scope, we have temporarily paused hiring for this position at this time.

Your profile remains carefully saved, and we will reactivate our conversation as soon as project hiring resumes. Thank you for your patience and understanding.

Sincerely,
Human Resources Team, {{company_name}}""",
        "body_vi": """Kính gửi {{candidate_name}},

Cảm ơn bạn đã quan tâm và nộp hồ sơ ứng tuyển vị trí {{job_title}} tại {{company_name}}.

Do có sự điều chỉnh trong kế hoạch kinh doanh và cơ cấu dự án, công ty chúng tôi tạm thời dừng kế hoạch tuyển dụng cho vị trí này trong giai đoạn hiện tại.

Hồ sơ của bạn vẫn được lưu giữ cẩn thận và chúng tôi sẽ kích hoạt lại liên hệ ngay khi dự án mở lại đợt tuyển mới. Cảm ơn sự thông cảm và đồng hành của bạn.

Trân trọng,
Đội ngũ Nhân sự {{company_name}}""",
        "html_notes": "Headcount freeze advisory, talent preservation promise.",
        "cta_label": "N/A",
        "cta_url": "",
        "compliance": "Clear reason attribution preventing candidate confusion."
    }
]

# ─────────────────────────────────────────────────────────────────────────────
# 2. PLACEHOLDERS DICTIONARY DATA
# ─────────────────────────────────────────────────────────────────────────────
PLACEHOLDERS = [
    {
        "tag": "{{code}}",
        "source": "VerificationCode.code (6-digit alphanumeric)",
        "sample": "849201",
        "scenarios": "SCN-AUTH-01, SCN-AUTH-03, SCN-AUTH-04",
        "description": "6-digit temporary verification OTP code generated for email confirmation or 2FA login."
    },
    {
        "tag": "{{otp_code}}",
        "source": "PasswordReset.otp_code (6-digit numeric)",
        "sample": "512849",
        "scenarios": "SCN-AUTH-02, SCN-AUTH-05",
        "description": "6-digit OTP code displayed for password reset screens."
    },
    {
        "tag": "{{display_name}}",
        "source": "User.full_name / CompanyUser.first_name / fallback",
        "sample": "Nguyễn Văn Tuấn",
        "scenarios": "SCN-AUTH-01, SCN-AUTH-02, SCN-AUTH-03, SCN-AUTH-04, SCN-AUTH-05",
        "description": "Recipient full name or formatted salutation."
    },
    {
        "tag": "{{candidate_name}}",
        "source": "JobSeekerProfile.full_name / JobApplication.applicant_name",
        "sample": "Trần Thị Mai Anh",
        "scenarios": "SCN-APP-01, SCN-ATS-01 to SCN-ATS-05, SCN-REJ-01 to SCN-REJ-04",
        "description": "Applicant full legal or preferred name."
    },
    {
        "tag": "{{company_name}}",
        "source": "CompanyProfile.company_name",
        "sample": "Applogiq Vietnam Co., Ltd",
        "scenarios": "All Company, Admin & ATS Scenarios",
        "description": "Public verified enterprise employer name."
    },
    {
        "tag": "{{job_title}}",
        "source": "JobPosting.title",
        "sample": "Senior Full-Stack AI Engineer",
        "scenarios": "SCN-APP-01, SCN-ATS-01 to SCN-ATS-05, SCN-REJ-01 to SCN-REJ-04",
        "description": "Official job listing title."
    },
    {
        "tag": "{{application_id}}",
        "source": "JobApplication.id (Integer)",
        "sample": "10482",
        "scenarios": "SCN-APP-01",
        "description": "Unique numeric tracking ID assigned to application upon submission."
    },
    {
        "tag": "{{tracker_url}}",
        "source": "Config: {JOBSEEKER_WEB_URL}/applications/{id}",
        "sample": "https://lamviec360.vn/applications/10482",
        "scenarios": "SCN-APP-01",
        "description": "Direct authenticated URL where candidate can view live pipeline stage."
    },
    {
        "tag": "{{activation_url}}",
        "source": "Config: {COMPANY_WEB_URL}/employee-activation?token={token}",
        "sample": "https://company.lamviec360.vn/employee-activation?token=inv_98f82a17b...",
        "scenarios": "SCN-TEAM-01, SCN-TEAM-02",
        "description": "Cryptographically signed activation URL valid for 72 hours."
    },
    {
        "tag": "{{expiry_date_str}}",
        "source": "CompanyInvitation.expires_at (Formatted string)",
        "sample": "2026-11-03 17:00 (72 hours)",
        "scenarios": "SCN-TEAM-01, SCN-TEAM-02",
        "description": "Human-readable date/time marking when the invitation expires."
    },
    {
        "tag": "{{role_name}}",
        "source": "CompanyUser.role / CompanyInvitation.role (Human Display)",
        "sample": "HR / Recruiter",
        "scenarios": "SCN-TEAM-01, SCN-TEAM-02",
        "description": "Display name of workspace role (Company Admin, HR / Recruiter, Viewer)."
    },
    {
        "tag": "{{inviter_name}}",
        "source": "CompanyUser.full_name (Inviting Admin)",
        "sample": "Lê Hoàng Long (CEO)",
        "scenarios": "SCN-TEAM-01, SCN-TEAM-02",
        "description": "Name of the company administrator extending the workspace invite."
    },
    {
        "tag": "{{interview_date}}",
        "source": "InterviewSchedule.scheduled_date (DD/MM/YYYY)",
        "sample": "05/11/2026",
        "scenarios": "SCN-ATS-03, SCN-ATS-04",
        "description": "Scheduled interview date."
    },
    {
        "tag": "{{interview_time}}",
        "source": "InterviewSchedule.scheduled_time (HH:MM GMT+7)",
        "sample": "14:30 (GMT+7)",
        "scenarios": "SCN-ATS-03, SCN-ATS-04",
        "description": "Scheduled interview time."
    },
    {
        "tag": "{{interview_link}}",
        "source": "InterviewSchedule.meeting_url",
        "sample": "https://meet.google.com/xyz-qwer-tyu",
        "scenarios": "SCN-ATS-03",
        "description": "Video conference URL (Google Meet, Teams, or Zoom)."
    },
    {
        "tag": "{{interview_location}}",
        "source": "InterviewSchedule.location",
        "sample": "Tầng 12, Tòa nhà Bitexco, Q.1, TP.HCM / Online",
        "scenarios": "SCN-ATS-04",
        "description": "Physical office address or online conference instructions."
    },
    {
        "tag": "{{reason}}",
        "source": "CompanyProfile.verification_notes",
        "sample": "Mã số thuế không trùng khớp với dữ liệu Đăng ký kinh doanh Quốc gia.",
        "scenarios": "SCN-ADMIN-02",
        "description": "Official admin rejection reason explaining missing or invalid documents."
    },
    {
        "tag": "{{portal_url}}",
        "source": "Config: {COMPANY_WEB_URL}/employer-login",
        "sample": "https://company.lamviec360.vn/employer-login",
        "scenarios": "SCN-ADMIN-01",
        "description": "Direct URL to employer login portal."
    },
    {
        "tag": "{{support_email}}",
        "source": "Environment Config: support@lamviec360.vn",
        "sample": "support@lamviec360.vn",
        "scenarios": "SCN-ADMIN-02, SCN-TEAM-01",
        "description": "Official support email address."
    }
]

# ─────────────────────────────────────────────────────────────────────────────
# 3. BUILD EXCEL WORKBOOK WITH PROFESSIONAL STYLING
# ─────────────────────────────────────────────────────────────────────────────
def build_excel_catalog():
    wb = openpyxl.Workbook()
    # Remove default sheet
    wb.remove(wb.active)

    # Styles
    navy_header_fill = PatternFill(start_color="0F172A", end_color="0F172A", fill_type="solid")
    header_font = Font(name="Segoe UI", size=11, bold=True, color="FFFFFF")
    zebra_fill = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")
    white_fill = PatternFill(start_color="FFFFFF", end_color="FFFFFF", fill_type="solid")
    
    badge_active_fill = PatternFill(start_color="ECFDF5", end_color="ECFDF5", fill_type="solid")
    badge_active_font = Font(name="Segoe UI", size=10, bold=True, color="047857")
    
    thin_border_side = Side(style="thin", color="CBD5E1")
    grid_border = Border(
        left=thin_border_side,
        right=thin_border_side,
        top=thin_border_side,
        bottom=thin_border_side
    )
    
    cell_font = Font(name="Segoe UI", size=10, color="1E293B")
    bold_cell_font = Font(name="Segoe UI", size=10, bold=True, color="0F172A")
    code_font = Font(name="Consolas", size=9, color="2563EB")

    # ─────────────────────────────────────────────────────────────────────────
    # SHEET 1: Email Scenarios Overview
    # ─────────────────────────────────────────────────────────────────────────
    ws1 = wb.create_sheet(title="Email Scenarios Overview")
    ws1.views.sheetView[0].showGridLines = True

    headers_1 = [
        "Scenario ID",
        "Domain / Module",
        "Scenario Name",
        "Target Audience",
        "Category",
        "Trigger Event",
        "Subject (EN)",
        "Subject (VI)",
        "Validity / SLA",
        "Delivery Mechanism",
        "Dispatcher Function",
        "Audit Log Action",
        "Status"
    ]
    ws1.append(headers_1)

    for i, s in enumerate(SCENARIOS, start=2):
        row = [
            s["id"],
            s["domain"],
            s["name"],
            s["audience"],
            s["category"],
            s["trigger"],
            s["subject_en"],
            s["subject_vi"],
            s["expiration"],
            s["delivery"],
            s["dispatcher"],
            s["audit_action"],
            s["status"],
        ]
        ws1.append(row)

    # Style Sheet 1
    for col_idx in range(1, len(headers_1) + 1):
        cell = ws1.cell(row=1, column=col_idx)
        cell.fill = navy_header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    ws1.row_dimensions[1].height = 28

    for row_idx in range(2, len(SCENARIOS) + 2):
        ws1.row_dimensions[row_idx].height = 24
        fill = zebra_fill if row_idx % 2 == 0 else white_fill
        for col_idx in range(1, len(headers_1) + 1):
            c = ws1.cell(row=row_idx, column=col_idx)
            c.fill = fill
            c.border = grid_border
            c.font = cell_font
            c.alignment = Alignment(vertical="center")
            if col_idx == 1:
                c.font = bold_cell_font
                c.alignment = Alignment(horizontal="center", vertical="center")
            elif col_idx in [5, 9, 10]:
                c.alignment = Alignment(horizontal="center", vertical="center")
            elif col_idx == 11:
                c.font = code_font
            elif col_idx == 13:
                c.fill = badge_active_fill
                c.font = badge_active_font
                c.alignment = Alignment(horizontal="center", vertical="center")

    # ─────────────────────────────────────────────────────────────────────────
    # SHEET 2: Email Content & Templates
    # ─────────────────────────────────────────────────────────────────────────
    ws2 = wb.create_sheet(title="Email Content & Templates")
    ws2.views.sheetView[0].showGridLines = True

    headers_2 = [
        "Scenario ID",
        "Scenario Name",
        "Placeholders / Variables",
        "Subject (English)",
        "Subject (Vietnamese)",
        "Plain Text Body (English)",
        "Plain Text Body (Vietnamese)",
        "HTML Design Highlights",
        "CTA Button Label",
        "CTA Target URL",
        "Compliance & Privacy Notice"
    ]
    ws2.append(headers_2)

    for s in SCENARIOS:
        row = [
            s["id"],
            s["name"],
            s["placeholders"],
            s["subject_en"],
            s["subject_vi"],
            s["body_en"],
            s["body_vi"],
            s["html_notes"],
            s["cta_label"],
            s["cta_url"],
            s["compliance"]
        ]
        ws2.append(row)

    # Style Sheet 2
    for col_idx in range(1, len(headers_2) + 1):
        cell = ws2.cell(row=1, column=col_idx)
        cell.fill = navy_header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    ws2.row_dimensions[1].height = 28

    for row_idx in range(2, len(SCENARIOS) + 2):
        ws2.row_dimensions[row_idx].height = 110  # Tall row for multi-line email bodies
        fill = zebra_fill if row_idx % 2 == 0 else white_fill
        for col_idx in range(1, len(headers_2) + 1):
            c = ws2.cell(row=row_idx, column=col_idx)
            c.fill = fill
            c.border = grid_border
            c.font = cell_font
            c.alignment = Alignment(vertical="top", wrap_text=True)
            if col_idx == 1:
                c.font = bold_cell_font
                c.alignment = Alignment(horizontal="center", vertical="top")
            elif col_idx == 3:
                c.font = code_font

    # ─────────────────────────────────────────────────────────────────────────
    # SHEET 3: Placeholders Dictionary
    # ─────────────────────────────────────────────────────────────────────────
    ws3 = wb.create_sheet(title="Placeholders Dictionary")
    ws3.views.sheetView[0].showGridLines = True

    headers_3 = [
        "Placeholder Tag",
        "Backend Database Source",
        "Sample Preview Value",
        "Used In Scenarios",
        "Tag Description & Formatting Rules"
    ]
    ws3.append(headers_3)

    for p in PLACEHOLDERS:
        row = [
            p["tag"],
            p["source"],
            p["sample"],
            p["scenarios"],
            p["description"]
        ]
        ws3.append(row)

    for col_idx in range(1, len(headers_3) + 1):
        cell = ws3.cell(row=1, column=col_idx)
        cell.fill = navy_header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    ws3.row_dimensions[1].height = 28

    for row_idx in range(2, len(PLACEHOLDERS) + 2):
        ws3.row_dimensions[row_idx].height = 26
        fill = zebra_fill if row_idx % 2 == 0 else white_fill
        for col_idx in range(1, len(headers_3) + 1):
            c = ws3.cell(row=row_idx, column=col_idx)
            c.fill = fill
            c.border = grid_border
            c.font = cell_font
            c.alignment = Alignment(vertical="center", wrap_text=True)
            if col_idx == 1:
                c.font = code_font
                c.alignment = Alignment(horizontal="center", vertical="center")

    # ─────────────────────────────────────────────────────────────────────────
    # SHEET 4: Backend Code References
    # ─────────────────────────────────────────────────────────────────────────
    ws4 = wb.create_sheet(title="Backend Code References")
    ws4.views.sheetView[0].showGridLines = True

    headers_4 = [
        "Scenario ID",
        "Scenario Name",
        "Dispatcher Function",
        "Source File Reference",
        "Triggering API Endpoint",
        "Audit Log Action Recorded"
    ]
    ws4.append(headers_4)

    for s in SCENARIOS:
        row = [
            s["id"],
            s["name"],
            s["dispatcher"],
            s["file_ref"],
            s["endpoint"],
            s["audit_action"]
        ]
        ws4.append(row)

    for col_idx in range(1, len(headers_4) + 1):
        cell = ws4.cell(row=1, column=col_idx)
        cell.fill = navy_header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    ws4.row_dimensions[1].height = 28

    for row_idx in range(2, len(SCENARIOS) + 2):
        ws4.row_dimensions[row_idx].height = 24
        fill = zebra_fill if row_idx % 2 == 0 else white_fill
        for col_idx in range(1, len(headers_4) + 1):
            c = ws4.cell(row=row_idx, column=col_idx)
            c.fill = fill
            c.border = grid_border
            c.font = cell_font
            c.alignment = Alignment(vertical="center")
            if col_idx == 1:
                c.font = bold_cell_font
                c.alignment = Alignment(horizontal="center", vertical="center")
            elif col_idx in [3, 4, 5, 6]:
                c.font = code_font

    # ─────────────────────────────────────────────────────────────────────────
    # AUTO-ADJUST COLUMN WIDTHS FOR ALL SHEETS
    # ─────────────────────────────────────────────────────────────────────────
    sheet_max_widths = {
        "Email Scenarios Overview": {1: 15, 2: 24, 3: 36, 4: 22, 5: 18, 6: 42, 7: 42, 8: 42, 9: 18, 10: 22, 11: 34, 12: 26, 13: 16},
        "Email Content & Templates": {1: 15, 2: 30, 3: 32, 4: 38, 5: 38, 6: 52, 7: 52, 8: 38, 9: 30, 10: 36, 11: 34},
        "Placeholders Dictionary": {1: 24, 2: 38, 3: 32, 4: 36, 5: 50},
        "Backend Code References": {1: 15, 2: 36, 3: 36, 4: 32, 5: 48, 6: 28}
    }

    for ws in wb.worksheets:
        widths_dict = sheet_max_widths.get(ws.title, {})
        for col_idx in range(1, ws.max_column + 1):
            col_letter = get_column_letter(col_idx)
            width = widths_dict.get(col_idx, 20)
            ws.column_dimensions[col_letter].width = width

    os.makedirs(DOCS_DIR, exist_ok=True)
    wb.save(EXCEL_PATH)
    print(f"[EXCEL] Successfully generated master catalog: {EXCEL_PATH}")


# ─────────────────────────────────────────────────────────────────────────────
# 4. EXPORT CSV CATALOG (FOR GIT VERSION CONTROL DIFFING)
# ─────────────────────────────────────────────────────────────────────────────
def build_csv_catalog():
    os.makedirs(DOCS_DIR, exist_ok=True)
    csv_headers = [
        "Scenario ID",
        "Domain",
        "Scenario Name",
        "Target Audience",
        "Category",
        "Trigger Event",
        "Subject (EN)",
        "Subject (VI)",
        "Placeholders",
        "Validity / SLA",
        "Dispatcher Function",
        "File Reference",
        "Trigger Endpoint",
        "Audit Action",
        "Status"
    ]

    with open(CSV_PATH, mode="w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(csv_headers)
        for s in SCENARIOS:
            writer.writerow([
                s["id"],
                s["domain"],
                s["name"],
                s["audience"],
                s["category"],
                s["trigger"],
                s["subject_en"],
                s["subject_vi"],
                s["placeholders"],
                s["expiration"],
                s["dispatcher"],
                s["file_ref"],
                s["endpoint"],
                s["audit_action"],
                s["status"]
            ])

    print(f"[CSV] Successfully generated CSV catalog: {CSV_PATH}")


if __name__ == "__main__":
    print(f"Generating Email Scenarios & Content Catalog (Total: {len(SCENARIOS)} scenarios)...")
    build_excel_catalog()
    build_csv_catalog()
    print("Catalog generation completed successfully!")
