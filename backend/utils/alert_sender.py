"""
Email utility for sending alerts, OTP verification codes, and enrollment tokens via SendGrid.
"""
import logging
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional, Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------
# SendGrid SMTP Configuration Hardcoded Specifics
# ---------------------------------------------------------
SENDGRID_SMTP_HOST = "smtp.sendgrid.net"
SENDGRID_SMTP_PORT = 587
SENDGRID_SMTP_USER = "apikey"

# Explicit 'From' Email Address Requirement
FROM_EMAIL = "ceo@technohavenmalaysia.com"


def get_smtp_password() -> Optional[str]:
    """
    Retrieve SMTP_PASSWORD directly from .env / environment variables.
    Does not query Firestore to prevent authentication bootstrap lockouts.
    """
    pwd = os.getenv("SMTP_PASSWORD")
    if not pwd:
        try:
            from utils.config import get_settings
            pwd = get_settings().smtp_password
        except Exception:
            pass
    if pwd and isinstance(pwd, str) and pwd.strip():
        return pwd.strip()
    return None


def get_smtp_password_from_firestore(db: Optional[Any] = None) -> Optional[str]:
    """
    Deprecated alias maintained for backwards compatibility.
    Loads SMTP_PASSWORD directly from .env instead of querying Firestore.
    """
    return get_smtp_password()


def send_otp_email(to_email: str, otp_code: str, user_name: str = "Admin") -> bool:
    """
    Send an OTP authentication email via SendGrid SMTP using SMTP_PASSWORD from .env.
    Host: smtp.sendgrid.net (port 587)
    User: apikey
    From: ceo@technohavenmalaysia.com
    """
    smtp_password = get_smtp_password()
    if not smtp_password:
        logger.error(
            "Email dispatch cancelled: SMTP_PASSWORD is not configured in .env. "
            "Please ensure SMTP_PASSWORD is set in your root .env file."
        )
        return False

    subject = "[Defendra.AI] One-Time Verification Code (OTP)"

    html_body = f"""
    <html>
        <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; line-height: 1.6; color: #1e293b; background-color: #0f172a; margin: 0; padding: 20px;">
            <div style="max-width: 520px; margin: 20px auto; background: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 10px 25px rgba(0, 0, 0, 0.25);">
                <div style="background: linear-gradient(135deg, #0284c7 0%, #06b6d4 100%); padding: 28px; text-align: center;">
                    <h1 style="color: #ffffff; margin: 0; font-size: 22px; font-weight: 700; letter-spacing: 0.5px;">Defendra.AI Platform</h1>
                    <p style="color: rgba(255, 255, 255, 0.9); margin: 6px 0 0; font-size: 13px;">Security Portal Verification</p>
                </div>
                <div style="padding: 32px 28px; color: #334155;">
                    <p style="font-size: 15px; margin: 0 0 16px;">Hello <strong>{user_name}</strong>,</p>
                    <p style="font-size: 14px; margin: 0 0 24px; color: #64748b; line-height: 1.5;">
                        Use the single-use verification code below to sign in to your Defendra.AI administrative console.
                    </p>
                    <div style="background: #0f172a; border-radius: 8px; padding: 24px; text-align: center; margin: 0 0 24px;">
                        <div style="font-size: 11px; text-transform: uppercase; letter-spacing: 1.5px; color: #06b6d4; margin-bottom: 8px; font-weight: 600;">One-Time Passcode (OTP)</div>
                        <div style="font-size: 36px; font-weight: 800; letter-spacing: 8px; color: #38bdf8; font-family: monospace;">{otp_code}</div>
                        <div style="font-size: 12px; color: #94a3b8; margin-top: 8px;">Expires in 5 minutes</div>
                    </div>
                    <p style="font-size: 13px; color: #64748b; margin: 0 0 16px; line-height: 1.5;">
                        If you did not request this login code, please verify that your credentials are secure and notify your system administrator.
                    </p>
                    <div style="border-top: 1px solid #e2e8f0; padding-top: 16px; margin-top: 24px; font-size: 12px; color: #94a3b8; text-align: center;">
                        Defendra.AI Enterprise EDR • Automated Security Dispatch
                    </div>
                </div>
            </div>
        </body>
    </html>
    """

    text_body = f"""Defendra.AI Security Verification

Hello {user_name},

Your one-time authentication code (OTP) for the Defendra.AI administrative console is:

    OTP Code: {otp_code}

This code expires in 5 minutes.
If you did not request this code, please review your security logs immediately.

---
Defendra.AI Enterprise EDR
"""

    msg = MIMEMultipart("alternative")
    msg["From"] = FROM_EMAIL
    msg["To"] = to_email
    msg["Subject"] = subject

    msg.attach(MIMEText(text_body, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    # Print the OTP out directly for local testing so we don't get locked out via dummy seeds
    logger.info(f"Preparing to send SendGrid OTP [{otp_code}] to {to_email}")
    print(f"\n[ALERT SENDER] Sending OTP code {otp_code} to {to_email}\n", flush=True)

    try:
        with smtplib.SMTP(SENDGRID_SMTP_HOST, SENDGRID_SMTP_PORT, timeout=20) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(SENDGRID_SMTP_USER, smtp_password)
            server.send_message(msg)

        logger.info(f"Successfully dispatched SendGrid OTP email to {to_email}")
        return True
    except Exception as e:
        logger.error(f"Failed to dispatch SendGrid OTP email to {to_email}: {e}")
        return False


def send_login_otp_email(to_email: str, otp_code: str, user_name: str = "Admin") -> bool:
    """Alias for send_otp_email."""
    return send_otp_email(to_email, otp_code, user_name)


def send_enrollment_token_email(to_email: str, token: str, admin_name: str = "Admin", db: Optional[Any] = None) -> bool:
    """
    Format and send a clear, professional email containing the enrollment token
    to the admin's email address using Python's built-in smtplib and email.mime.
    """
    smtp_password = get_smtp_password()
    if not smtp_password:
        logger.warning("Email dispatch cancelled: SMTP_PASSWORD is not configured in .env.")
        return False
        
    subject = "[Defendra.AI] Windows Agent Enrollment Token (OTP)"
    
    # Generate Professional HTML Email Body
    html_body = f"""
    <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; background-color: #f4f6f9; padding: 20px;">
            <div style="max-width: 600px; margin: 0 auto; background: #ffffff; padding: 30px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); border-top: 5px solid #06b6d4;">
                <h2 style="color: #0f172a; margin-top: 0;">Defendra.AI Windows Agent Deployment</h2>
                <p>Hello {admin_name},</p>
                <p>A new Windows installer (install.ps1) has been generated. Use the single-use enrollment token below to authenticate and register the Windows endpoint to your enterprise fleet.</p>
                
                <div style="background-color: #0f172a; border-radius: 6px; padding: 20px; text-align: center; margin: 25px 0;">
                    <div style="font-size: 12px; color: #94a3b8; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 8px;">Enrollment Token (OTP)</div>
                    <div style="font-size: 28px; font-family: monospace; color: #22d3ee; letter-spacing: 2px;">{token}</div>
                </div>
                
                <h4 style="margin-bottom: 5px;">Installation Instructions:</h4>
                <p style="font-size: 14px; color: #475569; margin-top: 0;">Run the installer script in an elevated PowerShell prompt on the target endpoint. Provide the token above when prompted or via parameter if applicable.</p>
                <div style="background: #f1f5f9; padding: 15px; border-radius: 4px; font-family: monospace; font-size: 13px; color: #334155; margin-bottom: 25px;">
                    .\\install.ps1 -Token "{token}"
                </div>
                
                <div style="font-size: 13px; color: #64748b; padding-top: 20px; border-top: 1px solid #e2e8f0;">
                    <strong>Security Notice:</strong> This token is strictly for single-use deployment. If you did not request this token, please immediately review your Defendra.AI audit logs.
                </div>
            </div>
            <div style="text-align: center; font-size: 12px; color: #94a3b8; margin-top: 20px;">
                Secure Email Gateway • Defendra.AI Enterprise EDR
            </div>
        </body>
    </html>
    """
    
    text_body = f"""
Defendra.AI Windows Agent Deployment

Hello {admin_name},

A new Windows installer (install.ps1) has been generated. 
Use the single-use enrollment token below to authenticate and register the Windows endpoint to your enterprise fleet.

Enrollment Token (OTP): {token}

Installation Instructions:
Run the installer script in an elevated PowerShell prompt on the target endpoint.
Provide the token above when prompted or via parameter if applicable.

    .\\install.ps1 -Token "{token}"

Security Notice: This token is strictly for single-use deployment. 
If you did not request this token, please immediately review your Defendra.AI audit logs.
    """
    
    msg = MIMEMultipart("alternative")
    msg["From"] = FROM_EMAIL
    msg["To"] = to_email
    msg["Subject"] = subject
    
    msg.attach(MIMEText(text_body, "plain"))
    msg.attach(MIMEText(html_body, "html"))
    
    try:
        with smtplib.SMTP(SENDGRID_SMTP_HOST, SENDGRID_SMTP_PORT, timeout=20) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(SENDGRID_SMTP_USER, smtp_password)
            server.send_message(msg)
            
        logger.info(f"Successfully dispatched SendGrid enrollment email to {to_email}")
        return True
    except Exception as e:
        logger.error(f"Failed to dispatch SendGrid enrollment email to {to_email}: {e}")
        return False
