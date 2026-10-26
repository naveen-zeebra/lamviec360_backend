import smtplib
import re
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional
from shared.environment import env
from shared.utils.logger import get_logger

logger = get_logger("email_service")


def _strip_html(html: str) -> str:
    """Basic helper to convert HTML to plain text for console & fallback."""
    clean = re.sub(r"<style[\s\S]*?>[\s\S]*?</style>", "", html, flags=re.IGNORECASE)
    clean = re.sub(r"<[^>]+>", " ", clean)
    clean = re.sub(r"\s+", " ", clean).strip()
    return clean


def send_email(
    to_email: str,
    subject: str,
    html_content: str,
    text_content: Optional[str] = None,
) -> bool:
    """
    Sends an email using configured SMTP settings.
    If SMTP settings are not provided or if sending fails,
    logs the email content cleanly to the server console.
    """
    if not text_content:
        text_content = _strip_html(html_content)

    from_header = f"{env.FROM_NAME} <{env.FROM_EMAIL}>"

    # If SMTP is configured, attempt real delivery
    if env.SMTP_HOST and env.SMTP_USER:
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = from_header
            msg["To"] = to_email

            part1 = MIMEText(text_content, "plain", "utf-8")
            part2 = MIMEText(html_content, "html", "utf-8")
            msg.attach(part1)
            msg.attach(part2)

            with smtplib.SMTP(env.SMTP_HOST, env.SMTP_PORT, timeout=12) as server:
                if env.SMTP_TLS:
                    server.starttls()
                if env.SMTP_PASSWORD:
                    server.login(env.SMTP_USER, env.SMTP_PASSWORD)
                server.send_message(msg)

            logger.info(f"[SMTP] Successfully sent email to {to_email}: '{subject}'")
            return True
        except Exception as e:
            logger.warning(f"[SMTP] Failed to send email via SMTP ({e}). Falling back to dev logger.")

    # Development fallback display
    separator = "=" * 70
    logger.info(
        f"\n{separator}\n"
        f"[EMAIL SERVICE - DEV LOG]\n"
        f"To: {to_email}\n"
        f"From: {from_header}\n"
        f"Subject: {subject}\n"
        f"----------------------------------------------------------------------\n"
        f"{text_content}\n"
        f"{separator}\n"
    )
    return True


def send_verification_email(to_email: str, code: str, name: Optional[str] = None) -> bool:
    """Dispatches a 6-digit email verification OTP."""
    display_name = name or "Candidate"
    subject = f"{code} is your LamViec360 verification code"

    html_content = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f8fafc; margin: 0; padding: 24px; color: #1e293b; }}
    .container {{ max-width: 540px; margin: 0 auto; background: #ffffff; border-radius: 12px; border: 1px solid #e2e8f0; overflow: hidden; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); }}
    .header {{ background: #0f172a; padding: 28px 32px; text-align: center; }}
    .logo {{ font-size: 22px; font-weight: 800; color: #3b82f6; letter-spacing: -0.5px; text-decoration: none; }}
    .body {{ padding: 32px; }}
    .greeting {{ font-size: 18px; font-weight: 700; margin-bottom: 12px; }}
    .otp-box {{ margin: 28px 0; text-align: center; }}
    .otp-code {{ display: inline-block; font-size: 36px; font-weight: 800; letter-spacing: 8px; color: #2563eb; background: #eff6ff; border: 2px dashed #93c5fd; padding: 14px 28px; border-radius: 10px; }}
    .expiry {{ font-size: 13px; color: #64748b; margin-top: 10px; }}
    .footer {{ padding: 20px 32px; background: #f8fafc; border-top: 1px solid #e2e8f0; font-size: 12px; color: #94a3b8; text-align: center; }}
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <div class="logo">LamViec360</div>
    </div>
    <div class="body">
      <div class="greeting">Hi {display_name},</div>
      <p style="color: #475569; font-size: 15px; line-height: 1.6;">
        Welcome to LamViec360! Please use the following 6-digit verification code to verify your email address and activate your job seeker account:
      </p>
      <div class="otp-box">
        <div class="otp-code">{code}</div>
        <div class="expiry">This verification code expires in 15 minutes.</div>
      </div>
      <p style="color: #64748b; font-size: 13px; line-height: 1.5;">
        If you did not request this email, please disregard it. Your account remains secure.
      </p>
    </div>
    <div class="footer">
      &copy; LamViec360 Career Portal. All rights reserved.
    </div>
  </div>
</body>
</html>"""

    text_content = f"""Hi {display_name},

Welcome to LamViec360! Please use the following 6-digit verification code to verify your email address:

Verification Code: {code}

(This verification code expires in 15 minutes)

If you did not request this verification, please disregard this email.
"""

    return send_email(to_email=to_email, subject=subject, html_content=html_content, text_content=text_content)


def send_password_reset_email(
    to_email: str,
    reset_token: str,
    reset_url: Optional[str] = None,
    name: Optional[str] = None,
) -> bool:
    """Dispatches a password reset link and token."""
    display_name = name or "Candidate"
    subject = "Reset your LamViec360 password"

    if not reset_url:
        reset_url = f"{env.JOBSEEKER_WEB_URL}/reset-password?token={reset_token}&email={to_email}"

    html_content = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f8fafc; margin: 0; padding: 24px; color: #1e293b; }}
    .container {{ max-width: 540px; margin: 0 auto; background: #ffffff; border-radius: 12px; border: 1px solid #e2e8f0; overflow: hidden; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); }}
    .header {{ background: #0f172a; padding: 28px 32px; text-align: center; }}
    .logo {{ font-size: 22px; font-weight: 800; color: #3b82f6; letter-spacing: -0.5px; text-decoration: none; }}
    .body {{ padding: 32px; }}
    .greeting {{ font-size: 18px; font-weight: 700; margin-bottom: 12px; }}
    .btn-container {{ margin: 28px 0; text-align: center; }}
    .btn {{ display: inline-block; background-color: #2563eb; color: #ffffff !important; font-size: 15px; font-weight: 600; text-decoration: none; padding: 13px 28px; border-radius: 8px; box-shadow: 0 2px 4px rgba(37,99,235,0.2); }}
    .link-box {{ word-break: break-all; font-size: 12px; color: #64748b; background: #f1f5f9; padding: 12px; border-radius: 6px; margin-top: 20px; }}
    .token-preview {{ font-family: monospace; font-size: 12px; color: #334155; margin-top: 12px; }}
    .footer {{ padding: 20px 32px; background: #f8fafc; border-top: 1px solid #e2e8f0; font-size: 12px; color: #94a3b8; text-align: center; }}
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <div class="logo">LamViec360</div>
    </div>
    <div class="body">
      <div class="greeting">Hi {display_name},</div>
      <p style="color: #475569; font-size: 15px; line-height: 1.6;">
        We received a request to reset the password for your LamViec360 account associated with <strong>{to_email}</strong>.
      </p>
      <div class="btn-container">
        <a href="{reset_url}" class="btn" target="_blank">Reset Password</a>
      </div>
      <p style="color: #64748b; font-size: 13px; line-height: 1.5;">
        Or copy and paste this link into your browser:
      </p>
      <div class="link-box">
        <a href="{reset_url}" style="color: #2563eb; text-decoration: none;">{reset_url}</a>
      </div>
      <div class="token-preview">
        Reset Token: <code>{reset_token}</code>
      </div>
      <p style="color: #94a3b8; font-size: 12px; margin-top: 24px; line-height: 1.5;">
        This link is valid for 1 hour. If you didn't request a password reset, you can safely ignore this email; your password will not be changed.
      </p>
    </div>
    <div class="footer">
      &copy; LamViec360 Career Portal. All rights reserved.
    </div>
  </div>
</body>
</html>"""

    text_content = f"""Hi {display_name},

We received a request to reset your password for LamViec360.
Click the link below to set a new password:

{reset_url}

Reset Token: {reset_token}

This link is valid for 1 hour. If you did not request this, please ignore this email.
"""

    return send_email(to_email=to_email, subject=subject, html_content=html_content, text_content=text_content)


def send_application_confirmation_email(
    to_email: str,
    candidate_name: Optional[str] = None,
    job_title: str = "Position",
    company_name: str = "Company",
    application_id: Optional[int] = None,
    applied_at: Optional[object] = None,
    job_location: Optional[str] = None,
    resume_name: Optional[str] = None,
    tracker_url: Optional[str] = None,
) -> bool:
    """
    Dispatches a simplified application confirmation and 24-hour review notice email.
    """
    display_name = candidate_name or "Candidate"
    app_id_str = f"#{application_id}" if application_id else ""

    subject = f"Application Received: {job_title} at {company_name}"
    if app_id_str:
        subject += f" ({app_id_str})"

    if not tracker_url:
        app_path = f"/applications/{application_id}" if application_id else "/applications"
        tracker_url = f"{env.JOBSEEKER_WEB_URL}{app_path}"

    app_id_line = f"<div style='margin-bottom: 8px;'><strong>Application ID:</strong> #{application_id}</div>" if application_id else ""

    html_content = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f8fafc; margin: 0; padding: 24px; color: #1e293b; }}
    .container {{ max-width: 540px; margin: 0 auto; background: #ffffff; border-radius: 12px; border: 1px solid #e2e8f0; overflow: hidden; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); }}
    .header {{ background: #0f172a; padding: 28px 32px; text-align: center; }}
    .logo {{ font-size: 22px; font-weight: 800; color: #3b82f6; letter-spacing: -0.5px; text-decoration: none; }}
    .body {{ padding: 32px; }}
    .greeting {{ font-size: 18px; font-weight: 700; margin-bottom: 12px; color: #0f172a; }}
    .summary-card {{ background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 16px 20px; margin: 20px 0; font-size: 14px; line-height: 1.6; color: #334155; }}
    .btn-container {{ margin: 28px 0; text-align: center; }}
    .btn {{ display: inline-block; background-color: #2563eb; color: #ffffff !important; font-size: 15px; font-weight: 600; text-decoration: none; padding: 13px 28px; border-radius: 8px; box-shadow: 0 2px 4px rgba(37,99,235,0.2); }}
    .footer {{ padding: 20px 32px; background: #f8fafc; border-top: 1px solid #e2e8f0; font-size: 12px; color: #94a3b8; text-align: center; }}
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <div class="logo">LamViec360</div>
    </div>
    <div class="body">
      <div class="greeting">Hi {display_name},</div>
      <p style="color: #475569; font-size: 15px; line-height: 1.6;">
        Your application for <strong>{job_title}</strong> at <strong>{company_name}</strong> has been received successfully.
      </p>

      <div class="summary-card">
        {app_id_line}
        <div style="color: #166534; font-weight: 500;">
          &#x23F1;&#xFE0F; Your profile is under review. You can expect an update within 24 hours.
        </div>
      </div>

      <div class="btn-container">
        <a href="{tracker_url}" class="btn" target="_blank">View Application</a>
      </div>

      <p style="color: #64748b; font-size: 13px; line-height: 1.5; margin-top: 24px;">
        You can track the progress of your application anytime in your LamViec360 portal.
      </p>
    </div>
    <div class="footer">
      &copy; LamViec360 Career Portal. All rights reserved.
    </div>
  </div>
</body>
</html>"""

    text_content = f"""Hi {display_name},

Your application for {job_title} at {company_name} has been received successfully{f" (Application ID: #{application_id})" if application_id else ""}.

Your profile is under review, and you can expect an update within 24 hours.

View your application:
{tracker_url}

Best regards,
LamViec360 Team
"""

    return send_email(to_email=to_email, subject=subject, html_content=html_content, text_content=text_content)


def send_company_approval_email(
    to_email: str,
    company_name: str,
    contact_name: Optional[str] = None,
    portal_url: Optional[str] = None,
) -> bool:
    """Dispatches an official account approval notification to the company employer."""
    display_name = contact_name or "Company Representative"
    subject = f"Congratulations! Your company account has been verified - LàmViệc360"
    if not portal_url:
        portal_url = f"{env.COMPANY_WEB_URL}/employer-login"

    html_content = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f8fafc; margin: 0; padding: 24px; color: #1e293b; }}
    .container {{ max-width: 560px; margin: 0 auto; background: #ffffff; border-radius: 12px; border: 1px solid #e2e8f0; overflow: hidden; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); }}
    .header {{ background: #0f172a; padding: 28px 32px; text-align: center; }}
    .logo {{ font-size: 22px; font-weight: 800; color: #3b82f6; letter-spacing: -0.5px; text-decoration: none; }}
    .body {{ padding: 32px; }}
    .badge {{ display: inline-flex; align-items: center; gap: 6px; background: #ecfdf5; border: 1px solid #a7f3d0; color: #047857; font-size: 13px; font-weight: 700; padding: 6px 14px; border-radius: 9999px; margin-bottom: 16px; }}
    .greeting {{ font-size: 19px; font-weight: 700; margin-bottom: 12px; color: #0f172a; }}
    .features-card {{ background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 10px; padding: 18px 20px; margin: 24px 0; }}
    .feature-item {{ display: flex; align-items: center; gap: 10px; font-size: 14px; color: #334155; margin-bottom: 8px; }}
    .feature-item:last-child {{ margin-bottom: 0; }}
    .btn-container {{ margin: 28px 0; text-align: center; }}
    .btn {{ display: inline-block; background-color: #2563eb; color: #ffffff !important; font-size: 15px; font-weight: 700; text-decoration: none; padding: 14px 32px; border-radius: 8px; box-shadow: 0 2px 4px rgba(37,99,235,0.25); }}
    .link-box {{ word-break: break-all; font-size: 12px; color: #64748b; background: #f1f5f9; padding: 10px 14px; border-radius: 6px; margin-top: 16px; }}
    .footer {{ padding: 20px 32px; background: #f8fafc; border-top: 1px solid #e2e8f0; font-size: 12px; color: #94a3b8; text-align: center; }}
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <div class="logo">LàmViệc360</div>
    </div>
    <div class="body">
      <div class="badge">&#10003; Company Verified & Approved</div>
      <div class="greeting">Hi {display_name},</div>
      <p style="color: #475569; font-size: 15px; line-height: 1.6;">
        Great news! Your company profile for <strong>{company_name}</strong> has been officially reviewed, verified, and approved by the LàmViệc360 administration team.
      </p>

      <div class="features-card">
        <div style="font-weight: 700; font-size: 14px; color: #0f172a; margin-bottom: 12px;">What you can do right now:</div>
        <div class="feature-item">&#128640; <span><strong>Publish Job Openings</strong> — reach thousands of verified candidates across Vietnam.</span></div>
        <div class="feature-item">&#128101; <span><strong>Manage Applicants</strong> — pipeline screening, notes, and interview scheduling.</span></div>
        <div class="feature-item">&#9989; <span><strong>Verified Employer Badge</strong> — showcased on all your public job postings and company page.</span></div>
      </div>

      <div class="btn-container">
        <a href="{portal_url}" class="btn" target="_blank">Sign in to Employer Portal</a>
      </div>

      <p style="color: #64748b; font-size: 13px; line-height: 1.5;">
        Or access directly via browser:
      </p>
      <div class="link-box">
        <a href="{portal_url}" style="color: #2563eb; text-decoration: none;">{portal_url}</a>
      </div>
    </div>
    <div class="footer">
      &copy; LàmViệc360 Employer Solutions &bull; Support: support@lamviec360.vn
    </div>
  </div>
</body>
</html>"""

    text_content = f"""Hi {display_name},

Congratulations! Your company account for {company_name} has been verified and approved on LàmViệc360.

You can now sign in to your employer portal to publish job postings, review applicants, and build your team:
{portal_url}

Best regards,
LàmViệc360 Administration Team
"""
    return send_email(to_email=to_email, subject=subject, html_content=html_content, text_content=text_content)


def send_company_rejection_email(
    to_email: str,
    company_name: str,
    contact_name: Optional[str] = None,
    reason: Optional[str] = None,
    support_email: Optional[str] = "support@lamviec360.vn",
) -> bool:
    """Dispatches a registration rejection notice with the official reason to the company applicant."""
    display_name = contact_name or "Company Representative"
    subject = f"Update regarding your company registration on LàmViệc360: {company_name}"
    display_reason = reason or "Business registration details could not be verified against official national business records."

    html_content = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f8fafc; margin: 0; padding: 24px; color: #1e293b; }}
    .container {{ max-width: 560px; margin: 0 auto; background: #ffffff; border-radius: 12px; border: 1px solid #e2e8f0; overflow: hidden; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); }}
    .header {{ background: #0f172a; padding: 28px 32px; text-align: center; }}
    .logo {{ font-size: 22px; font-weight: 800; color: #3b82f6; letter-spacing: -0.5px; text-decoration: none; }}
    .body {{ padding: 32px; }}
    .badge {{ display: inline-flex; align-items: center; gap: 6px; background: #fff1f2; border: 1px solid #fecdd3; color: #be123c; font-size: 13px; font-weight: 700; padding: 6px 14px; border-radius: 9999px; margin-bottom: 16px; }}
    .greeting {{ font-size: 19px; font-weight: 700; margin-bottom: 12px; color: #0f172a; }}
    .reason-box {{ background: #fff1f2; border-left: 4px solid #e11d48; border-radius: 6px; padding: 14px 18px; margin: 20px 0; font-size: 14px; color: #881337; line-height: 1.6; }}
    .footer {{ padding: 20px 32px; background: #f8fafc; border-top: 1px solid #e2e8f0; font-size: 12px; color: #94a3b8; text-align: center; }}
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <div class="logo">LàmViệc360</div>
    </div>
    <div class="body">
      <div class="badge">&#9888; Registration Status Update</div>
      <div class="greeting">Hi {display_name},</div>
      <p style="color: #475569; font-size: 15px; line-height: 1.6;">
        Thank you for your interest in hiring through LàmViệc360. Our verification team has reviewed your company registration for <strong>{company_name}</strong>.
      </p>
      <p style="color: #475569; font-size: 15px; line-height: 1.6;">
        Unfortunately, we are unable to approve your company account at this time due to the following reason:
      </p>

      <div class="reason-box">
        <strong>Reason for rejection:</strong><br />
        {display_reason}
      </div>

      <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 16px; margin: 24px 0; font-size: 13px; color: #475569; line-height: 1.6;">
        <strong>Need assistance or have updated documents?</strong><br />
        If you have updated business registration certificates or believe this decision was made in error, please reply to this email or contact our support team at <a href="mailto:{support_email}" style="color: #2563eb; font-weight: 600;">{support_email}</a>.
      </div>
    </div>
    <div class="footer">
      &copy; LàmViệc360 Employer Solutions &bull; Support: {support_email}
    </div>
  </div>
</body>
</html>"""

    text_content = f"""Hi {display_name},

Thank you for your interest in LàmViệc360. Our verification team has reviewed your company registration for {company_name}.

Unfortunately, we are unable to approve your company account at this time due to the following reason:

{display_reason}

If you have updated business documentation or wish to appeal this decision, please reach out to our team at {support_email}.

Best regards,
LàmViệc360 Verification Team
"""
    return send_email(to_email=to_email, subject=subject, html_content=html_content, text_content=text_content)

