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
