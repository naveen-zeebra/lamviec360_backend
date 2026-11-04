# ─────────────────────────────────────────────────────────────────────────────
# File    : shared/notifications/templates/catalog.py
# Purpose : Master Notification Template Catalog (19 scenarios per LV360-FSD-006)
# Standard: Primary Language: Vietnamese (vi); Secondary: English (en)
# ─────────────────────────────────────────────────────────────────────────────

from typing import Dict, Any

NOTIFICATION_CATALOG: Dict[str, Dict[str, Any]] = {
    # ── Authentication & Security (SCN-AUTH) ──────────────────────────────────
    "SCN-AUTH-01": {
        "scenario_id": "SCN-AUTH-01",
        "category": "Authentication",
        "badge_vi": "Xác thực tài khoản",
        "badge_en": "Account Verification",
        "vi": {
            "subject": "{{otp_code}} là mã xác thực tài khoản LàmViệc360 của bạn",
            "headline": "Xác thực địa chỉ email",
            "body": """
<p>Xin chào <strong>{{user_name}}</strong>,</p>
<p>Cảm ơn bạn đã đăng ký tài khoản trên nền tảng tuyển dụng <strong>LàmViệc360</strong>. Vui lòng sử dụng mã xác thực OTP 6 chữ số dưới đây để kích hoạt tài khoản của bạn:</p>
<div style="text-align: center;">
  <span class="otp-code">{{otp_code}}</span>
</div>
<p style="font-size: 13px; color: #64748b;">Mã này có hiệu lực trong vòng <strong>10 phút</strong>. Vì lý do bảo mật, tuyệt đối không chia sẻ mã này cho bất kỳ ai khác.</p>
            """,
            "cta_text": "Kích hoạt tài khoản",
            "cta_url": "{{portal_url}}/verify",
        },
        "en": {
            "subject": "{{otp_code}} is your LamViec360 verification code",
            "headline": "Verify Your Email Address",
            "body": """
<p>Hello <strong>{{user_name}}</strong>,</p>
<p>Thank you for registering on <strong>LamViec360</strong>. Please use the 6-digit OTP verification code below to verify your email and activate your account:</p>
<div style="text-align: center;">
  <span class="otp-code">{{otp_code}}</span>
</div>
<p style="font-size: 13px; color: #64748b;">This code is valid for <strong>10 minutes</strong>. For your security, never share this code with anyone.</p>
            """,
            "cta_text": "Verify Account",
            "cta_url": "{{portal_url}}/verify",
        },
    },

    "SCN-AUTH-02": {
        "scenario_id": "SCN-AUTH-02",
        "category": "Authentication",
        "badge_vi": "Chào mừng thành viên",
        "badge_en": "Welcome Onboarding",
        "vi": {
            "subject": "Chào mừng bạn gia nhập cộng đồng nhân tài LàmViệc360!",
            "headline": "Chào mừng bạn đến với LàmViệc360",
            "body": """
<p>Xin chào <strong>{{user_name}}</strong>,</p>
<p>Tài khoản của bạn đã được kích hoạt thành công. LàmViệc360 là hệ sinh thái tuyển dụng thông minh giúp bạn tiếp cận hàng nghìn cơ hội nghề nghiệp uy tín và kết nối trực tiếp với các nhà tuyển dụng hàng đầu.</p>
<div class="highlight-card">
  <strong>Gợi ý bước tiếp theo:</strong>
  <ul style="margin: 8px 0 0 0; padding-left: 20px;">
    <li>Hoàn thiện hồ sơ cá nhân để tăng 300% lượt xem từ nhà tuyển dụng.</li>
    <li>Tải lên CV cập nhật mới nhất ở định dạng PDF.</li>
    <li>Bật thông báo gợi ý việc làm phù hợp theo kỹ năng và địa điểm.</li>
  </ul>
</div>
            """,
            "cta_text": "Khám phá việc làm ngay",
            "cta_url": "{{portal_url}}/jobs",
        },
        "en": {
            "subject": "Welcome to LamViec360 Smart Recruitment Platform!",
            "headline": "Welcome to LamViec360",
            "body": """
<p>Hello <strong>{{user_name}}</strong>,</p>
<p>Your account is now fully activated. LamViec360 connects exceptional talent with verified employers across Vietnam and Southeast Asia.</p>
<div class="highlight-card">
  <strong>Recommended Next Steps:</strong>
  <ul style="margin: 8px 0 0 0; padding-left: 20px;">
    <li>Complete your talent profile to increase employer discovery by 300%.</li>
    <li>Upload your latest CV in PDF format.</li>
    <li>Set up job alert preferences tailored to your domain and salary expectations.</li>
  </ul>
</div>
            """,
            "cta_text": "Explore Jobs Now",
            "cta_url": "{{portal_url}}/jobs",
        },
    },

    "SCN-AUTH-03": {
        "scenario_id": "SCN-AUTH-03",
        "category": "Authentication",
        "badge_vi": "Bảo mật tài khoản",
        "badge_en": "Account Security",
        "vi": {
            "subject": "Yêu cầu đặt lại mật khẩu tài khoản LàmViệc360",
            "headline": "Đặt lại mật khẩu của bạn",
            "body": """
<p>Xin chào <strong>{{user_name}}</strong>,</p>
<p>Chúng tôi nhận được yêu cầu đặt lại mật khẩu cho tài khoản liên kết với địa chỉ email này. Vui lòng bấm vào nút bên dưới để thiết lập mật khẩu mới an toàn:</p>
<p style="font-size: 13px; color: #64748b;">Liên kết đặt lại mật khẩu có hiệu lực trong vòng <strong>15 phút</strong>. Nếu bạn không gửi yêu cầu này, vui lòng bỏ qua email hoặc đổi mật khẩu ngay để bảo đảm an toàn.</p>
            """,
            "cta_text": "Đặt lại mật khẩu",
            "cta_url": "{{reset_link}}",
        },
        "en": {
            "subject": "Password Reset Request for your LamViec360 Account",
            "headline": "Reset Your Password",
            "body": """
<p>Hello <strong>{{user_name}}</strong>,</p>
<p>We received a request to reset the password for your account. Please click the button below to set a new password:</p>
<p style="font-size: 13px; color: #64748b;">This reset link will expire in <strong>15 minutes</strong>. If you did not make this request, you can safely disregard this email.</p>
            """,
            "cta_text": "Reset Password",
            "cta_url": "{{reset_link}}",
        },
    },

    "SCN-AUTH-04": {
        "scenario_id": "SCN-AUTH-04",
        "category": "Security",
        "badge_vi": "Cảnh báo bảo mật",
        "badge_en": "Security Alert",
        "vi": {
            "subject": "Cảnh báo đăng nhập từ thiết bị mới trên LàmViệc360",
            "headline": "Phát hiện lượt đăng nhập mới",
            "body": """
<p>Xin chào <strong>{{user_name}}</strong>,</p>
<p>Hệ thống ghi nhận tài khoản của bạn vừa đăng nhập thành công từ một thiết bị hoặc địa chỉ IP mới:</p>
<div class="highlight-card">
  <div><strong>Thời gian:</strong> {{login_time}}</div>
  <div><strong>Thiết bị:</strong> {{device_info}}</div>
  <div><strong>Vị trí ước tính:</strong> {{location_ip}}</div>
</div>
<p style="font-size: 13px; color: #64748b;">Nếu đây là bạn, bạn không cần làm gì thêm. Nếu không phải bạn, hãy đổi mật khẩu ngay lập tức để bảo vệ tài khoản.</p>
            """,
            "cta_text": "Kiểm tra bảo mật tài khoản",
            "cta_url": "{{portal_url}}/settings?tab=security",
        },
        "en": {
            "subject": "Security Alert: New Sign-in to your LamViec360 Account",
            "headline": "New Sign-in Detected",
            "body": """
<p>Hello <strong>{{user_name}}</strong>,</p>
<p>Your account was just accessed from a new device or IP address:</p>
<div class="highlight-card">
  <div><strong>Timestamp:</strong> {{login_time}}</div>
  <div><strong>Device:</strong> {{device_info}}</div>
  <div><strong>Estimated Location:</strong> {{location_ip}}</div>
</div>
<p style="font-size: 13px; color: #64748b;">If this was you, no action is needed. If you did not authorize this login, please secure your account immediately.</p>
            """,
            "cta_text": "Review Account Security",
            "cta_url": "{{portal_url}}/settings?tab=security",
        },
    },

    # ── Job Applications (SCN-APP) ───────────────────────────────────────────
    "SCN-APP-01": {
        "scenario_id": "SCN-APP-01",
        "category": "Application",
        "badge_vi": "Ứng tuyển thành công",
        "badge_en": "Application Submitted",
        "vi": {
            "subject": "Xác nhận nộp hồ sơ thành công: {{job_title}} tại {{company_name}} (#{{application_id}})",
            "headline": "Hồ sơ ứng tuyển đã được ghi nhận",
            "body": """
<p>Xin chào <strong>{{candidate_name}}</strong>,</p>
<p>Hồ sơ ứng tuyển của bạn cho vị trí <strong>{{job_title}}</strong> tại <strong>{{company_name}}</strong> đã được chuyển trực tiếp đến hệ thống tuyển dụng của doanh nghiệp.</p>
<div class="highlight-card">
  <div><strong>Mã hồ sơ:</strong> #{{application_id}}</div>
  <div><strong>Doanh nghiệp:</strong> {{company_name}}</div>
  <div><strong>Ngày nộp:</strong> {{date}}</div>
  <div style="margin-top: 8px; font-weight: 600; color: #2563eb;">Cam kết xem xét hồ sơ trong vòng 24 giờ làm việc theo quy chuẩn dịch vụ LàmViệc360.</div>
</div>
<p>Bạn có thể theo dõi tiến trình xét duyệt hồ sơ trực tiếp tại trang Quản lý Ứng tuyển.</p>
            """,
            "cta_text": "Theo dõi tiến trình hồ sơ",
            "cta_url": "{{tracker_url}}",
        },
        "en": {
            "subject": "Application Received: {{job_title}} at {{company_name}} (#{{application_id}})",
            "headline": "Your Application Has Been Received",
            "body": """
<p>Hello <strong>{{candidate_name}}</strong>,</p>
<p>Your application for <strong>{{job_title}}</strong> at <strong>{{company_name}}</strong> has been successfully delivered to the hiring team.</p>
<div class="highlight-card">
  <div><strong>Application ID:</strong> #{{application_id}}</div>
  <div><strong>Company:</strong> {{company_name}}</div>
  <div><strong>Submitted Date:</strong> {{date}}</div>
  <div style="margin-top: 8px; font-weight: 600; color: #2563eb;">24-hour review SLA commitment in progress per LamViec360 standards.</div>
</div>
<p>You can track the live evaluation status anytime in your Applications Dashboard.</p>
            """,
            "cta_text": "Track Application Status",
            "cta_url": "{{tracker_url}}",
        },
    },

    "SCN-APP-02": {
        "scenario_id": "SCN-APP-02",
        "category": "Application",
        "badge_vi": "Cập nhật hồ sơ",
        "badge_en": "Status Update",
        "vi": {
            "subject": "Cập nhật trạng thái hồ sơ ứng tuyển {{job_title}} tại {{company_name}}",
            "headline": "Trạng thái ứng tuyển mới",
            "body": """
<p>Xin chào <strong>{{candidate_name}}</strong>,</p>
<p>Nhà tuyển dụng <strong>{{company_name}}</strong> vừa cập nhật trạng thái hồ sơ của bạn cho vị trí <strong>{{job_title}}</strong> sang:</p>
<div class="highlight-card" style="text-align: center;">
  <span style="font-size: 18px; font-weight: 700; color: #2563eb;">{{new_status}}</span>
</div>
<p>Vui lòng đăng nhập để xem chi tiết thông tin phản hồi từ nhà tuyển dụng.</p>
            """,
            "cta_text": "Xem chi tiết hồ sơ",
            "cta_url": "{{tracker_url}}",
        },
        "en": {
            "subject": "Application Status Update: {{job_title}} at {{company_name}}",
            "headline": "Application Status Changed",
            "body": """
<p>Hello <strong>{{candidate_name}}</strong>,</p>
<p>The hiring team at <strong>{{company_name}}</strong> has updated your application status for <strong>{{job_title}}</strong> to:</p>
<div class="highlight-card" style="text-align: center;">
  <span style="font-size: 18px; font-weight: 700; color: #2563eb;">{{new_status}}</span>
</div>
<p>Please log in to your dashboard to review recruiter notes and next steps.</p>
            """,
            "cta_text": "View Application",
            "cta_url": "{{tracker_url}}",
        },
    },

    # ── Candidate ATS Progression (SCN-ATS) ──────────────────────────────────
    "SCN-ATS-01": {
        "scenario_id": "SCN-ATS-01",
        "category": "ATS Stage",
        "badge_vi": "Hồ sơ được chọn",
        "badge_en": "Profile Shortlisted",
        "vi": {
            "subject": "Hồ sơ của bạn đã được chọn vào danh sách xem xét: {{job_title}} tại {{company_name}}",
            "headline": "Hồ sơ của bạn đã qua vòng sơ loại",
            "body": """
<p>Xin chào <strong>{{candidate_name}}</strong>,</p>
<p>Chúng tôi vui mừng thông báo hồ sơ ứng tuyển của bạn cho vị trí <strong>{{job_title}}</strong> tại <strong>{{company_name}}</strong> đã gây ấn tượng xuất sắc với ban tuyển dụng và chính thức được đưa vào danh sách rút gọn (Shortlisted).</p>
<p>Bộ phận Tuyển dụng của doanh nghiệp sẽ sớm liên hệ với bạn để thông báo lịch trình phỏng vấn chi tiết.</p>
            """,
            "cta_text": "Xem trạng thái ứng tuyển",
            "cta_url": "{{tracker_url}}",
        },
        "en": {
            "subject": "Your Profile Has Been Shortlisted: {{job_title}} at {{company_name}}",
            "headline": "You Have Been Shortlisted",
            "body": """
<p>Hello <strong>{{candidate_name}}</strong>,</p>
<p>We are pleased to inform you that your profile for <strong>{{job_title}}</strong> at <strong>{{company_name}}</strong> has successfully passed initial screening and has been moved to the Shortlisted stage.</p>
<p>The hiring team will contact you shortly regarding the next interview schedule.</p>
            """,
            "cta_text": "Review Application",
            "cta_url": "{{tracker_url}}",
        },
    },

    "SCN-ATS-02": {
        "scenario_id": "SCN-ATS-02",
        "category": "ATS Stage",
        "badge_vi": "Bài kiểm tra năng lực",
        "badge_en": "Assessment Test",
        "vi": {
            "subject": "Thư mời làm bài kiểm tra chuyên môn: {{job_title}} tại {{company_name}}",
            "headline": "Bài kiểm tra đánh giá năng lực",
            "body": """
<p>Xin chào <strong>{{candidate_name}}</strong>,</p>
<p>Để đánh giá chuyên sâu năng lực chuyên môn cho vị trí <strong>{{job_title}}</strong>, <strong>{{company_name}}</strong> trân trọng mời bạn hoàn thành bài đánh giá trực tuyến theo thông tin dưới đây:</p>
<div class="highlight-card">
  <div><strong>Bài kiểm tra:</strong> {{test_title}}</div>
  <div><strong>Thời lượng làm bài:</strong> {{duration_minutes}} phút</div>
  <div><strong>Hạn chót hoàn thành:</strong> {{deadline}}</div>
</div>
<p style="font-size: 13px; color: #64748b;">Vui lòng chuẩn bị đường truyền internet ổn định và không gian yên tĩnh trước khi bắt đầu bài thi.</p>
            """,
            "cta_text": "Bắt đầu làm bài kiểm tra",
            "cta_url": "{{test_link}}",
        },
        "en": {
            "subject": "Technical Assessment Invitation: {{job_title}} at {{company_name}}",
            "headline": "Online Skill Assessment",
            "body": """
<p>Hello <strong>{{candidate_name}}</strong>,</p>
<p>To further assess your qualifications for <strong>{{job_title}}</strong>, <strong>{{company_name}}</strong> invites you to complete an online assessment:</p>
<div class="highlight-card">
  <div><strong>Assessment:</strong> {{test_title}}</div>
  <div><strong>Duration:</strong> {{duration_minutes}} minutes</div>
  <div><strong>Submission Deadline:</strong> {{deadline}}</div>
</div>
<p style="font-size: 13px; color: #64748b;">Please ensure a stable internet connection and quiet environment before starting.</p>
            """,
            "cta_text": "Start Assessment",
            "cta_url": "{{test_link}}",
        },
    },

    "SCN-ATS-03": {
        "scenario_id": "SCN-ATS-03",
        "category": "ATS Stage",
        "badge_vi": "Mời phỏng vấn",
        "badge_en": "Interview Invitation",
        "vi": {
            "subject": "Thư mời phỏng vấn: {{job_title}} tại {{company_name}}",
            "headline": "Thư mời tham dự phỏng vấn",
            "body": """
<p>Xin chào <strong>{{candidate_name}}</strong>,</p>
<p>Thay mặt <strong>{{company_name}}</strong>, chúng tôi trân trọng kính mời bạn tham gia buổi phỏng vấn cho vị trí <strong>{{job_title}}</strong> theo lịch trình chi tiết:</p>
<div class="highlight-card">
  <div><strong>Ngày phỏng vấn:</strong> {{interview_date}}</div>
  <div><strong>Thời gian:</strong> {{interview_time}}</div>
  <div><strong>Hình thức:</strong> {{interview_format}}</div>
  <div><strong>Đường dẫn tham gia:</strong> <a href="{{interview_link}}" style="color: #2563eb;">{{interview_link}}</a></div>
</div>
<p>Vui lòng đăng nhập để xác nhận lịch phỏng vấn hoặc đề xuất thời gian phù hợp hơn nếu có thay đổi.</p>
            """,
            "cta_text": "Xác nhận tham dự phỏng vấn",
            "cta_url": "{{tracker_url}}",
        },
        "en": {
            "subject": "Interview Invitation: {{job_title}} at {{company_name}}",
            "headline": "Interview Invitation",
            "body": """
<p>Hello <strong>{{candidate_name}}</strong>,</p>
<p>On behalf of <strong>{{company_name}}</strong>, we are pleased to invite you for an interview for the <strong>{{job_title}}</strong> position:</p>
<div class="highlight-card">
  <div><strong>Interview Date:</strong> {{interview_date}}</div>
  <div><strong>Time:</strong> {{interview_time}}</div>
  <div><strong>Format:</strong> {{interview_format}}</div>
  <div><strong>Meeting Link:</strong> <a href="{{interview_link}}" style="color: #2563eb;">{{interview_link}}</a></div>
</div>
<p>Please log in to confirm your attendance or request a reschedule if needed.</p>
            """,
            "cta_text": "Confirm Interview Attendance",
            "cta_url": "{{tracker_url}}",
        },
    },

    "SCN-ATS-04": {
        "scenario_id": "SCN-ATS-04",
        "category": "ATS Stage",
        "badge_vi": "Thay đổi lịch phỏng vấn",
        "badge_en": "Interview Rescheduled",
        "vi": {
            "subject": "Thông báo điều chỉnh lịch phỏng vấn: {{job_title}} tại {{company_name}}",
            "headline": "Điều chỉnh lịch phỏng vấn",
            "body": """
<p>Xin chào <strong>{{candidate_name}}</strong>,</p>
<p>Lịch phỏng vấn cho vị trí <strong>{{job_title}}</strong> tại <strong>{{company_name}}</strong> đã được cập nhật lại theo thời gian mới như sau:</p>
<div class="highlight-card">
  <div><strong>Thời gian mới:</strong> {{interview_time}} ngày {{interview_date}}</div>
  <div><strong>Hình thức:</strong> {{interview_format}}</div>
  <div><strong>Đường dẫn tham gia:</strong> <a href="{{interview_link}}" style="color: #2563eb;">{{interview_link}}</a></div>
</div>
<p>Rất mong bạn thông cảm vì sự thay đổi này. Vui lòng bấm xác nhận để ban tuyển dụng ghi nhận lịch mới.</p>
            """,
            "cta_text": "Xác nhận lịch mới",
            "cta_url": "{{tracker_url}}",
        },
        "en": {
            "subject": "Interview Rescheduled: {{job_title}} at {{company_name}}",
            "headline": "Interview Schedule Updated",
            "body": """
<p>Hello <strong>{{candidate_name}}</strong>,</p>
<p>Your interview schedule for <strong>{{job_title}}</strong> at <strong>{{company_name}}</strong> has been updated to the following time:</p>
<div class="highlight-card">
  <div><strong>New Time:</strong> {{interview_time}} on {{interview_date}}</div>
  <div><strong>Format:</strong> {{interview_format}}</div>
  <div><strong>Meeting Link:</strong> <a href="{{interview_link}}" style="color: #2563eb;">{{interview_link}}</a></div>
</div>
<p>We apologize for any inconvenience caused. Please confirm your availability for this new slot.</p>
            """,
            "cta_text": "Confirm New Slot",
            "cta_url": "{{tracker_url}}",
        },
    },

    "SCN-ATS-05": {
        "scenario_id": "SCN-ATS-05",
        "category": "ATS Stage",
        "badge_vi": "Thư mời nhận việc",
        "badge_en": "Job Offer Letter",
        "vi": {
            "subject": "Thư mời nhận việc (Job Offer): {{job_title}} tại {{company_name}}",
            "headline": "Chúc mừng bạn nhận được Thư mời làm việc!",
            "body": """
<p>Xin chào <strong>{{candidate_name}}</strong>,</p>
<p>Thay mặt Ban Lãnh đạo <strong>{{company_name}}</strong>, chúng tôi vô cùng vui mừng gửi tới bạn Thư mời nhận việc (Job Offer) cho vị trí <strong>{{job_title}}</strong>.</p>
<div class="highlight-card">
  <div><strong>Vị trí:</strong> {{job_title}}</div>
  <div><strong>Doanh nghiệp:</strong> {{company_name}}</div>
  <div><strong>Hạn chót phản hồi:</strong> {{expiry_date}}</div>
</div>
<p>Vui lòng xem xét các điều khoản, chế độ đãi ngộ chi tiết và xác nhận phản hồi trước ngày hết hạn quy định.</p>
            """,
            "cta_text": "Xem và phản hồi Thư mời nhận việc",
            "cta_url": "{{offer_link}}",
        },
        "en": {
            "subject": "Job Offer: {{job_title}} at {{company_name}}",
            "headline": "Congratulations on Your Job Offer!",
            "body": """
<p>Hello <strong>{{candidate_name}}</strong>,</p>
<p>On behalf of <strong>{{company_name}}</strong>, we are thrilled to extend a formal Job Offer to you for the position of <strong>{{job_title}}</strong>.</p>
<div class="highlight-card">
  <div><strong>Position:</strong> {{job_title}}</div>
  <div><strong>Company:</strong> {{company_name}}</div>
  <div><strong>Offer Expiration:</strong> {{expiry_date}}</div>
</div>
<p>Please review your offer package and compensation terms and confirm your response before the expiration deadline.</p>
            """,
            "cta_text": "Review and Accept Offer",
            "cta_url": "{{offer_link}}",
        },
    },

    # ── Candidate Rejections (SCN-REJ) ───────────────────────────────────────
    "SCN-REJ-01": {
        "scenario_id": "SCN-REJ-01",
        "category": "Rejection",
        "badge_vi": "Thông báo hồ sơ",
        "badge_en": "Application Status",
        "vi": {
            "subject": "Cập nhật về hồ sơ ứng tuyển {{job_title}} tại {{company_name}}",
            "headline": "Cảm ơn sự quan tâm của bạn dành cho chúng tôi",
            "body": """
<p>Kính gửi <strong>{{candidate_name}}</strong>,</p>
<p>Cảm ơn bạn đã dành thời gian quan tâm và nộp hồ sơ ứng tuyển cho vị trí <strong>{{job_title}}</strong> tại <strong>{{company_name}}</strong>.</p>
<p>Sau khi xem xét kỹ lưỡng hồ sơ, chúng tôi rất tiếc phải thông báo hiện tại hồ sơ của bạn chưa hoàn toàn phù hợp với các tiêu chí ưu tiên cho vị trí này.</p>
<p>Chúng tôi đánh giá cao kinh nghiệm và nhiệt huyết của bạn, và chúc bạn luôn gặt hái nhiều thành công trên con đường phát triển sự nghiệp tương lai.</p>
            """,
            "cta_text": "Tìm kiếm các cơ hội phù hợp khác",
            "cta_url": "{{portal_url}}/jobs",
        },
        "en": {
            "subject": "Update regarding your application for {{job_title}} at {{company_name}}",
            "headline": "Thank You for Your Application",
            "body": """
<p>Dear <strong>{{candidate_name}}</strong>,</p>
<p>Thank you for taking the time to apply for the <strong>{{job_title}}</strong> role at <strong>{{company_name}}</strong>.</p>
<p>After careful evaluation of your qualifications, we regret to inform you that we will not be moving forward with your candidacy at this time.</p>
<p>We truly appreciate your interest in our company and wish you continued success in your professional endeavors.</p>
            """,
            "cta_text": "Explore Other Opportunities",
            "cta_url": "{{portal_url}}/jobs",
        },
    },

    "SCN-REJ-02": {
        "scenario_id": "SCN-REJ-02",
        "category": "Rejection",
        "badge_vi": "Lưu trữ dữ liệu nhân tài",
        "badge_en": "Talent Pool Retention",
        "vi": {
            "subject": "Cập nhật hồ sơ & Lưu trữ Talent Pool: {{job_title}} tại {{company_name}}",
            "headline": "Lưu trữ hồ sơ trong Mạng lưới Nhân tài",
            "body": """
<p>Kính gửi <strong>{{candidate_name}}</strong>,</p>
<p>Cảm ơn bạn đã ứng tuyển vị trí <strong>{{job_title}}</strong> tại <strong>{{company_name}}</strong>.</p>
<p>Mặc dù hiện tại vị trí này đã được lấp đầy, hồ sơ và kinh nghiệm của bạn rất ấn tượng. Với sự cho phép của bạn theo quy định bảo mật, chúng tôi xin phép lưu trữ hồ sơ của bạn trong Hệ thống Dữ liệu Nhân tài ưu tiên (Talent Pool) của công ty và sẽ chủ động liên hệ ngay khi có cơ hội phù hợp trong tương lai.</p>
            """,
            "cta_text": "Quản lý hồ sơ nhân tài của bạn",
            "cta_url": "{{portal_url}}/profile",
        },
        "en": {
            "subject": "Application Update & Talent Network Retention: {{job_title}} at {{company_name}}",
            "headline": "Retaining Your Profile in Our Talent Pool",
            "body": """
<p>Dear <strong>{{candidate_name}}</strong>,</p>
<p>Thank you for interviewing for the <strong>{{job_title}}</strong> role at <strong>{{company_name}}</strong>.</p>
<p>Although we selected another candidate whose experience aligned more closely with current immediate needs, we were thoroughly impressed by your background. We would like to retain your profile in our preferred Talent Pool to proactively reach out when relevant openings arise.</p>
            """,
            "cta_text": "Manage Your Talent Profile",
            "cta_url": "{{portal_url}}/profile",
        },
    },

    "SCN-REJ-03": {
        "scenario_id": "SCN-REJ-03",
        "category": "Rejection",
        "badge_vi": "Phản hồi phỏng vấn",
        "badge_en": "Interview Feedback",
        "vi": {
            "subject": "Phản hồi sau buổi phỏng vấn vị trí {{job_title}} tại {{company_name}}",
            "headline": "Cảm ơn bạn đã tham gia buổi phỏng vấn",
            "body": """
<p>Kính gửi <strong>{{candidate_name}}</strong>,</p>
<p>Cảm ơn bạn đã dành thời gian tham gia buổi phỏng vấn cho vị trí <strong>{{job_title}}</strong> tại <strong>{{company_name}}</strong>.</p>
<div class="highlight-card">
  <strong>Ghi nhận từ Hội đồng Tuyển dụng:</strong>
  <p style="margin: 8px 0 0 0; font-style: italic;">{{feedback_text}}</p>
</div>
<p>Dù chưa thể đồng hành ở thời điểm hiện tại, chúng tôi tin rằng bạn sẽ sớm tìm được môi trường phát huy tối đa thế mạnh của mình.</p>
            """,
            "cta_text": "Xem việc làm gợi ý",
            "cta_url": "{{portal_url}}/jobs",
        },
        "en": {
            "subject": "Post-Interview Feedback: {{job_title}} at {{company_name}}",
            "headline": "Thank You for Interviewing With Us",
            "body": """
<p>Dear <strong>{{candidate_name}}</strong>,</p>
<p>Thank you for taking part in our interview process for <strong>{{job_title}}</strong> at <strong>{{company_name}}</strong>.</p>
<div class="highlight-card">
  <strong>Feedback from the Hiring Panel:</strong>
  <p style="margin: 8px 0 0 0; font-style: italic;">{{feedback_text}}</p>
</div>
<p>We appreciate your transparency and dedication, and wish you all the best in your career growth.</p>
            """,
            "cta_text": "View Recommended Roles",
            "cta_url": "{{portal_url}}/jobs",
        },
    },

    "SCN-REJ-04": {
        "scenario_id": "SCN-REJ-04",
        "category": "Rejection",
        "badge_vi": "Thay đổi kế hoạch tuyển dụng",
        "badge_en": "Position On Hold",
        "vi": {
            "subject": "Thông báo về vị trí tuyển dụng {{job_title}} tại {{company_name}}",
            "headline": "Thông báo tạm dừng tuyển dụng",
            "body": """
<p>Kính gửi <strong>{{candidate_name}}</strong>,</p>
<p>Chúng tôi liên hệ để thông báo do có sự điều chỉnh trong kế hoạch nhân sự và cơ cấu dự án, vị trí <strong>{{job_title}}</strong> tại <strong>{{company_name}}</strong> hiện đang tạm hoãn tuyển dụng.</p>
<p>Chúng tôi rất tiếc vì sự bất tiện này và trân trọng cảm ơn sự quan tâm bạn đã dành cho doanh nghiệp. Ngay khi vị trí được mở lại, bạn sẽ là người đầu tiên chúng tôi ưu tiên liên hệ.</p>
            """,
            "cta_text": "Khám phá việc làm khác",
            "cta_url": "{{portal_url}}/jobs",
        },
        "en": {
            "subject": "Update on Position {{job_title}} at {{company_name}}",
            "headline": "Hiring Paused for This Role",
            "body": """
<p>Dear <strong>{{candidate_name}}</strong>,</p>
<p>We are writing to inform you that due to project reprioritization and internal organizational adjustments, the hiring for <strong>{{job_title}}</strong> at <strong>{{company_name}}</strong> has been temporarily placed on hold.</p>
<p>We sincerely appreciate the time you invested with us and will keep your record active to prioritize you once headcount reopens.</p>
            """,
            "cta_text": "Browse Open Positions",
            "cta_url": "{{portal_url}}/jobs",
        },
    },

    # ── Employer & Recruiter (SCN-EMP) ───────────────────────────────────────
    "SCN-EMP-01": {
        "scenario_id": "SCN-EMP-01",
        "category": "Employer Alert",
        "badge_vi": "Ứng viên mới",
        "badge_en": "New Candidate",
        "vi": {
            "subject": "Hồ sơ ứng tuyển mới: {{candidate_name}} ứng tuyển {{job_title}}",
            "headline": "Ứng viên mới nộp hồ sơ",
            "body": """
<p>Xin chào <strong>{{recruiter_name}}</strong>,</p>
<p>Vị trí <strong>{{job_title}}</strong> của công ty bạn vừa nhận được một hồ sơ ứng tuyển mới từ ứng viên <strong>{{candidate_name}}</strong>.</p>
<div class="highlight-card">
  <div><strong>Ứng viên:</strong> {{candidate_name}}</div>
  <div><strong>Độ tương thích AI:</strong> {{match_score}}%</div>
  <div><strong>Kinh nghiệm:</strong> {{experience_years}} năm</div>
  <div><strong>Ngày nộp:</strong> {{date}}</div>
</div>
<p>Vui lòng đăng nhập vào Kanban Pipeline để xem xét và xử lý hồ sơ kịp thời.</p>
            """,
            "cta_text": "Xem hồ sơ ứng viên trên Pipeline",
            "cta_url": "{{employer_pipeline_url}}",
        },
        "en": {
            "subject": "New Applicant: {{candidate_name}} applied for {{job_title}}",
            "headline": "New Candidate Submission",
            "body": """
<p>Hello <strong>{{recruiter_name}}</strong>,</p>
<p>A new candidate, <strong>{{candidate_name}}</strong>, has applied for your job opening <strong>{{job_title}}</strong>.</p>
<div class="highlight-card">
  <div><strong>Candidate:</strong> {{candidate_name}}</div>
  <div><strong>AI Match Score:</strong> {{match_score}}%</div>
  <div><strong>Experience:</strong> {{experience_years}} years</div>
  <div><strong>Applied On:</strong> {{date}}</div>
</div>
<p>Please log in to your Kanban Pipeline to review the profile.</p>
            """,
            "cta_text": "Review Applicant in Pipeline",
            "cta_url": "{{employer_pipeline_url}}",
        },
    },

    "SCN-EMP-02": {
        "scenario_id": "SCN-EMP-02",
        "category": "Employer Alert",
        "badge_vi": "Báo cáo tuyển dụng",
        "badge_en": "Recruitment Digest",
        "vi": {
            "subject": "Báo cáo định kỳ hoạt động tuyển dụng - {{company_name}}",
            "headline": "Tổng kết hoạt động tuyển dụng",
            "body": """
<p>Xin chào <strong>{{recruiter_name}}</strong>,</p>
<p>Dưới đây là tóm tắt nhanh về tiến độ các chiến dịch tuyển dụng của <strong>{{company_name}}</strong>:</p>
<div class="highlight-card">
  {{metrics_summary_html}}
</div>
<p>Hãy truy cập trang Quản lý tuyển dụng để tiếp tục tối ưu hóa quy trình sàng lọc và phỏng vấn ứng viên.</p>
            """,
            "cta_text": "Mở Bảng điều khiển tuyển dụng",
            "cta_url": "{{employer_dashboard_url}}",
        },
        "en": {
            "subject": "Recruitment Activity Digest - {{company_name}}",
            "headline": "Recruitment Pipeline Summary",
            "body": """
<p>Hello <strong>{{recruiter_name}}</strong>,</p>
<p>Here is your regular summary of hiring pipeline metrics for <strong>{{company_name}}</strong>:</p>
<div class="highlight-card">
  {{metrics_summary_html}}
</div>
<p>Visit your Employer Dashboard to manage open requisitions and optimize candidate conversion.</p>
            """,
            "cta_text": "Open Hiring Dashboard",
            "cta_url": "{{employer_dashboard_url}}",
        },
    },

    "SCN-EMP-03": {
        "scenario_id": "SCN-EMP-03",
        "category": "Employer Alert",
        "badge_vi": "Phản hồi phỏng vấn",
        "badge_en": "Candidate RSVP",
        "vi": {
            "subject": "Phản hồi lịch phỏng vấn: Ứng viên {{candidate_name}} - {{job_title}}",
            "headline": "Ứng viên đã phản hồi lịch phỏng vấn",
            "body": """
<p>Xin chào <strong>{{recruiter_name}}</strong>,</p>
<p>Ứng viên <strong>{{candidate_name}}</strong> vừa gửi phản hồi về buổi phỏng vấn cho vị trí <strong>{{job_title}}</strong>:</p>
<div class="highlight-card">
  <div><strong>Trạng thái phản hồi:</strong> <span style="font-weight: 700; color: #2563eb;">{{response_status}}</span></div>
  <div><strong>Thời gian:</strong> {{interview_time}} ngày {{interview_date}}</div>
  {{candidate_note_html}}
</div>
            """,
            "cta_text": "Xem chi tiết lịch phỏng vấn",
            "cta_url": "{{employer_pipeline_url}}",
        },
        "en": {
            "subject": "Interview RSVP: {{candidate_name}} - {{job_title}}",
            "headline": "Candidate Responded to Interview",
            "body": """
<p>Hello <strong>{{recruiter_name}}</strong>,</p>
<p>Candidate <strong>{{candidate_name}}</strong> has submitted a response regarding the interview for <strong>{{job_title}}</strong>:</p>
<div class="highlight-card">
  <div><strong>Status:</strong> <span style="font-weight: 700; color: #2563eb;">{{response_status}}</span></div>
  <div><strong>Scheduled Slot:</strong> {{interview_time}} on {{interview_date}}</div>
  {{candidate_note_html}}
</div>
            """,
            "cta_text": "View Interview Schedule",
            "cta_url": "{{employer_pipeline_url}}",
        },
    },

    # ── System & Governance (SCN-SYS) ────────────────────────────────────────
    "SCN-SYS-01": {
        "scenario_id": "SCN-SYS-01",
        "category": "System Governance",
        "badge_vi": "Xác minh doanh nghiệp",
        "badge_en": "Company Verification",
        "vi": {
            "subject": "Chúc mừng: Doanh nghiệp {{company_name}} đã được phê duyệt xác thực trên LàmViệc360",
            "headline": "Doanh nghiệp đã được xác thực chính thức",
            "body": """
<p>Kính gửi Quản trị viên <strong>{{company_name}}</strong>,</p>
<p>Chúng tôi vui mừng thông báo hồ sơ pháp lý và đăng ký doanh nghiệp của bạn đã được Ban Quản trị LàmViệc360 phê duyệt chính thức.</p>
<div class="highlight-card">
  <strong>Quyền lợi doanh nghiệp đã kích hoạt:</strong>
  <ul style="margin: 8px 0 0 0; padding-left: 20px;">
    <li>Gắn huy hiệu Tích xanh Uy tín (Verified Employer) trên các bài đăng tuyển.</li>
    <li>Mở khóa đầy đủ các tính năng lọc AI và quản lý pipeline ứng viên không giới hạn.</li>
    <li>Đăng tin tuyển dụng hiển thị ưu tiên hàng đầu trên Cổng tìm việc.</li>
  </ul>
</div>
            """,
            "cta_text": "Truy cập Workspace doanh nghiệp",
            "cta_url": "{{employer_dashboard_url}}",
        },
        "en": {
            "subject": "Congratulations: {{company_name}} Has Been Verified on LamViec360",
            "headline": "Company Account Formally Verified",
            "body": """
<p>Dear Administrator at <strong>{{company_name}}</strong>,</p>
<p>We are delighted to notify you that your business verification documents have been formally reviewed and approved by LamViec360 Administration.</p>
<div class="highlight-card">
  <strong>Your Activated Enterprise Benefits:</strong>
  <ul style="margin: 8px 0 0 0; padding-left: 20px;">
    <li>Verified Employer Blue Badge displayed on all job postings.</li>
    <li>Unrestricted access to AI candidate screening and talent pipeline management.</li>
    <li>Priority job listing ranking across the public talent portal.</li>
  </ul>
</div>
            """,
            "cta_text": "Open Employer Workspace",
            "cta_url": "{{employer_dashboard_url}}",
        },
    },
}

