"""
Email notification service for Defendra.AI
Handles sending email notifications for user registrations, alerts, etc.
"""

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

from utils.config import get_settings

logger = logging.getLogger(__name__)


class EmailService:
    """Service for sending email notifications via SMTP."""

    def __init__(self):
        self.settings = get_settings()

    def send_user_registration_notification(
        self,
        admin_email: str,
        user_name: str,
        user_email: str,
        approval_url: Optional[str] = None,
    ) -> bool:
        """
        Send email notification to admin when a new user registers.
        
        Args:
            admin_email: Email address of the admin to notify
            user_name: Full name of the user who registered
            user_email: Email address of the user who registered
            approval_url: Optional URL to approve the user directly
            
        Returns:
            True if email was sent successfully, False otherwise
        """
        subject = f"[Defendra.AI] New User Registration - {user_name}"
        
        html_body = self._create_registration_email_html(user_name, user_email, approval_url)
        text_body = self._create_registration_email_text(user_name, user_email, approval_url)
        
        return self._send_email(
            to_email=admin_email,
            subject=subject,
            html_body=html_body,
            text_body=text_body,
        )

    def _create_registration_email_html(self, user_name: str, user_email: str, approval_url: Optional[str]) -> str:
        """Create HTML email body for user registration notification."""
        approval_button = f'<a href="{approval_url}" style="display: inline-block; background: #667eea; color: white; padding: 12px 30px; text-decoration: none; border-radius: 6px; font-weight: bold;">Approve User</a>' if approval_url else ''
        
        return f"""
        <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; border-radius: 10px 10px 0 0;">
                        <h1 style="color: white; margin: 0; font-size: 24px;">🔔 New User Registration</h1>
                    </div>
                    
                    <div style="background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; border: 1px solid #e0e0e0; border-top: none;">
                        <p style="font-size: 16px; margin-bottom: 20px;">
                            A new user has registered and is waiting for approval:
                        </p>
                        
                        <div style="background: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; border-left: 4px solid #667eea;">
                            <p style="margin: 5px 0;"><strong>Name:</strong> {user_name}</p>
                            <p style="margin: 5px 0;"><strong>Email:</strong> {user_email}</p>
                            <p style="margin: 5px 0;"><strong>Status:</strong> <span style="color: #f59e0b; font-weight: bold;">Pending Approval</span></p>
                        </div>
                        
                        <p style="font-size: 14px; color: #666; margin-bottom: 20px;">
                            To approve this user, log in to your Defendra.AI dashboard and navigate to the Settings page.
                        </p>
                        
                        {approval_button}
                        
                        <hr style="border: none; border-top: 1px solid #e0e0e0; margin: 30px 0;">
                        
                        <p style="font-size: 12px; color: #999; margin: 0;">
                            This is an automated notification from Defendra.AI. Please do not reply to this email.
                        </p>
                    </div>
                </div>
            </body>
        </html>
        """

    def _create_registration_email_text(self, user_name: str, user_email: str, approval_url: Optional[str]) -> str:
        """Create plain text email body for user registration notification."""
        approval_text = f'\nApproval URL: {approval_url}' if approval_url else ''
        
        return f"""
New User Registration - Defendra.AI

A new user has registered and is waiting for approval:

Name: {user_name}
Email: {user_email}
Status: Pending Approval

To approve this user, log in to your Defendra.AI dashboard and navigate to the Settings page.
{approval_text}

---
This is an automated notification from Defendra.AI.
"""

    def _send_email(
        self,
        to_email: str,
        subject: str,
        html_body: str,
        text_body: str,
    ) -> bool:
        """
        Internal method to send email via SMTP.
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            html_body: HTML version of email body
            text_body: Plain text version of email body
            
        Returns:
            True if email was sent successfully, False otherwise
        """
        # Check if SMTP is configured
        if not self.settings.smtp_host or not self.settings.smtp_user:
            logger.warning(
                "SMTP not configured - email notification skipped. "
                "Set SMTP_HOST, SMTP_USER, and SMTP_PASSWORD in backend/.env to enable email notifications."
            )
            return False

        try:
            # Create message
            msg = MIMEMultipart("alternative")
            msg["From"] = self.settings.notification_from_email or self.settings.smtp_user
            msg["To"] = to_email
            msg["Subject"] = subject

            # Attach both plain text and HTML versions
            part1 = MIMEText(text_body, "plain")
            part2 = MIMEText(html_body, "html")
            msg.attach(part1)
            msg.attach(part2)

            # Connect to SMTP server and send
            with smtplib.SMTP(self.settings.smtp_host, self.settings.smtp_port) as server:
                server.starttls()  # Enable TLS encryption
                server.login(self.settings.smtp_user, self.settings.smtp_password)
                server.send_message(msg)

            logger.info(f"Email notification sent successfully to {to_email}")
            return True

        except smtplib.SMTPAuthenticationError:
            logger.error("SMTP authentication failed - check SMTP_USER and SMTP_PASSWORD")
            return False
        except smtplib.SMTPException as e:
            logger.error(f"SMTP error while sending email: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error while sending email: {e}")
            return False


# Singleton instance
_email_service: Optional[EmailService] = None


def get_email_service() -> EmailService:
    """Get the email service singleton instance."""
    global _email_service
    if _email_service is None:
        _email_service = EmailService()
    return _email_service

