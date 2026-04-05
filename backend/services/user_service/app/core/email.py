"""
Email utility for the User Service.

Uses Python's built-in smtplib to send emails through Mailpit (dev) or
any standard SMTP server (production).
"""

import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from app.core.config import settings

logger = logging.getLogger("user_service.email")


def send_reset_email(to_email: str, username: str, reset_token: str) -> bool:
    """
    Send a password-reset email with a clickable link.

    Returns True on success, False on failure (caller decides how to handle).
    """
    reset_link = f"{settings.frontend_url}/reset-password?token={reset_token}"

    msg = MIMEMultipart("alternative")
    msg["Subject"] = "ThreadHub – Password Reset"
    msg["From"] = "noreply@threadhub.dev"
    msg["To"] = to_email

    # Plain-text fallback
    text = (
        f"Hi {username},\n\n"
        f"We received a request to reset your password.\n\n"
        f"Click the link below (valid for 15 minutes):\n"
        f"{reset_link}\n\n"
        f"If you didn't request this, you can safely ignore this email.\n\n"
        f"— ThreadHub"
    )

    # HTML version
    html = f"""\
    <div style="font-family:Arial,sans-serif;max-width:480px;margin:0 auto;padding:24px;">
        <div style="background:#7C4DFF;padding:24px;text-align:center;border-radius:8px 8px 0 0;">
            <h1 style="color:#fff;margin:0;font-size:24px;">ThreadHub</h1>
        </div>
        <div style="background:#fff;padding:24px;border:1px solid #eee;border-radius:0 0 8px 8px;">
            <p>Hi <strong>{username}</strong>,</p>
            <p>We received a request to reset your password.</p>
            <p style="text-align:center;margin:24px 0;">
                <a href="{reset_link}"
                   style="background:#7C4DFF;color:#fff;padding:12px 32px;border-radius:24px;
                          text-decoration:none;font-weight:600;display:inline-block;">
                    Reset Password
                </a>
            </p>
            <p style="font-size:13px;color:#888;">
                This link expires in 15 minutes. If you didn't request this, ignore this email.
            </p>
        </div>
    </div>
    """

    msg.attach(MIMEText(text, "plain"))
    msg.attach(MIMEText(html, "html"))

    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
            server.sendmail(msg["From"], [to_email], msg.as_string())
        logger.info("Reset email sent to %s", to_email)
        return True
    except Exception as exc:
        logger.error("Failed to send reset email to %s: %s", to_email, exc)
        return False
