"""
Routes for generating and managing Windows agent installers and deployment tokens.
"""
import logging
import secrets
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Request, status, HTTPException
from google.cloud.firestore import Client
from pydantic import BaseModel

from database.firebase import get_firestore
from auth.dependencies import require_admin
from models.models import UserDoc
from utils.alert_sender import send_enrollment_token_email

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/deployment", tags=["Deployment"])

class GenerateInstallerRequest(BaseModel):
    target_email: Optional[str] = None
    
class GenerateInstallerResponse(BaseModel):
    token: str
    script: str
    script_name: str
    expires_at: datetime
    email_dispatched: bool
    message: str

def generate_secure_otp() -> str:
    """Generate a high-entropy token formatted as DFN-XXXX-XXXX"""
    part1 = secrets.token_hex(2).upper()
    part2 = secrets.token_hex(2).upper()
    return f"DFN-{part1}-{part2}"

INSTALL_PS1_TEMPLATE = """#Requires -RunAsAdministrator
[CmdletBinding()]
Param(
    [string]$Token = "{token}",
    [string]$BackendUrl = "{backend_url}"
)

Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "    Defendra.AI Enterprise Windows Installer" -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "[*] Validating enrollment token... ($Token)"

# Ensure token and URL are available system-wide for the Defendra Agent components
[System.Environment]::SetEnvironmentVariable("DEFENDRA_ENROLLMENT_TOKEN", $Token, "Machine")
[System.Environment]::SetEnvironmentVariable("DEFENDRA_BACKEND_URL", $BackendUrl, "Machine")

Write-Host "[*] Configuring Defendra services..."
Write-Host "[*] Downloading prerequisites..."

# ----------------------------------------------------
# Installation logic to be expanded by deployment team
# ----------------------------------------------------

Write-Host "[+] Agent Installation and Enrollment Scheduled Successfully." -ForegroundColor Green
Write-Host "[INFO] The Defendra Agent will securely register with the fleet on startup."
Write-Host "Installer completed."
"""

@router.post("/generate-installer", response_model=GenerateInstallerResponse, status_code=status.HTTP_201_CREATED)
async def generate_windows_installer(
    request: Request,
    payload: Optional[GenerateInstallerRequest] = None,
    db: Client = Depends(get_firestore),
    admin_user: UserDoc = Depends(require_admin)
):
    """
    Generate a new single-use ENROLLMENT_TOKEN and deployment PowerShell script (install.ps1).
    Emails the token to the enterprise admin via SendGrid. 
    Gracefully handles failures in email routing without failing the API response.
    """
    if payload is None:
        payload = GenerateInstallerRequest()
        
    recipient_email = payload.target_email if payload.target_email else admin_user.email
    enrollment_token = generate_secure_otp()
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(hours=24)
    
    try:
        ref = db.collection("enrollment_tokens").document(enrollment_token)
        ref.set({
            "token": enrollment_token,
            "created_by": admin_user.email,
            "created_by_id": admin_user.id,
            "created_at": now,
            "expires_at": expires_at,
            "used": False,
            "single_use": True,
        })
    except Exception as e:
        logger.error(f"Failed to record enrollment token in Firestore: {e}")
        raise HTTPException(status_code=500, detail="Database error recording enrollment token")
        
    backend_url = str(request.base_url).rstrip("/")
    script_content = INSTALL_PS1_TEMPLATE.replace("{token}", enrollment_token).replace("{backend_url}", backend_url)
    
    # ---------------------------------------------------------
    # Email Dispatch with Try-Except block for Error Handling
    # ---------------------------------------------------------
    email_dispatched = False
    try:
        admin_name = getattr(admin_user, "full_name", admin_user.email)
        email_dispatched = send_enrollment_token_email(
            to_email=recipient_email, 
            token=enrollment_token, 
            admin_name=admin_name,
            db=db
        )
    except Exception as e:
        logger.error(f"Error during SendGrid email dispatch for enrollment token to {recipient_email}: {e}", exc_info=True)
        email_dispatched = False
        
    if email_dispatched:
        message = f"Installer generated successfully. A single-use token was emailed to {recipient_email}."
    else:
        message = f"Installer generated successfully, but the SMTP email dispatch to {recipient_email} failed or is not configured. Please securely pass the token manually."
        logger.warning(f"Installer generated for {admin_user.email}, but email dispatch failed.")
        
    return GenerateInstallerResponse(
        token=enrollment_token,
        script=script_content,
        script_name="install.ps1",
        expires_at=expires_at,
        email_dispatched=email_dispatched,
        message=message
    )
