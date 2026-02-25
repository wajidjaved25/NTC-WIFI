"""
SMS Settings API Routes
Manage SMS templates and configuration (Superadmin only)
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.sms_settings import SMSSettings
from app.models.admin import Admin
from app.schemas.sms_settings import (
    SMSSettingsResponse,
    SMSSettingsUpdate,
    SMSPreview
)
from pydantic import BaseModel


class PreviewRequest(BaseModel):
    """Request schema for template preview"""
    template: str
from app.utils.security import get_current_user


router = APIRouter(prefix="/sms-settings", tags=["SMS Settings"])


def get_or_create_sms_settings(db: Session) -> SMSSettings:
    """Get existing settings or create default ones"""
    settings = db.query(SMSSettings).first()
    if not settings:
        settings = SMSSettings(
            otp_template="Your NTC WiFi OTP: {otp}\nValid for {validity} minutes. Do not share.\n\n@{portal_url} #{otp}",
            sender_id="NTC",
            otp_validity_minutes=5,
            otp_length=6,
            max_otp_per_number_per_hour=3,
            max_otp_per_number_per_day=10,
            enable_primary_sms=True,
            enable_secondary_sms=True
        )
        db.add(settings)
        db.commit()
        db.refresh(settings)
    return settings


@router.get("/", response_model=SMSSettingsResponse)
async def get_sms_settings(
    db: Session = Depends(get_db),
    current_user: Admin = Depends(get_current_user)
):
    """
    Get current SMS settings
    
    **Requires:** Superadmin role
    """
    # Check if user is superadmin
    if current_user.role != "superadmin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only superadmin can access SMS settings"
        )
    
    settings = get_or_create_sms_settings(db)
    return settings


@router.put("/", response_model=SMSSettingsResponse)
async def update_sms_settings(
    updates: SMSSettingsUpdate,
    db: Session = Depends(get_db),
    current_user: Admin = Depends(get_current_user)
):
    """
    Update SMS settings
    
    **Requires:** Superadmin role
    
    **Available template placeholders:**
    - {otp}: The OTP code
    - {validity}: Validity period in minutes
    - {portal_url}: Portal URL/domain
    - {sender}: Sender ID
    """
    # Check if user is superadmin
    if current_user.role != "superadmin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only superadmin can update SMS settings"
        )
    
    settings = get_or_create_sms_settings(db)
    
    # Update fields
    update_data = updates.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(settings, field, value)
    
    # Track who made the update
    settings.updated_by = current_user.username
    
    db.commit()
    db.refresh(settings)
    
    return settings


@router.post("/preview", response_model=SMSPreview)
async def preview_sms_template(
    request: PreviewRequest,
    db: Session = Depends(get_db),
    current_user: Admin = Depends(get_current_user)
):
    """
    Preview how SMS will look with current settings
    
    **Requires:** Superadmin role
    """
    # Check if user is superadmin
    if current_user.role != "superadmin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only superadmin can preview SMS templates"
        )
    
    settings = get_or_create_sms_settings(db)
    
    preview = SMSPreview.from_template(
        template=request.template,
        otp="123456",  # Example OTP
        portal_url="pmfreewifi.lan",
        validity=settings.otp_validity_minutes,
        sender=settings.sender_id
    )
    
    return preview


@router.post("/reset", response_model=SMSSettingsResponse)
async def reset_to_default(
    db: Session = Depends(get_db),
    current_user: Admin = Depends(get_current_user)
):
    """
    Reset SMS settings to default values
    
    **Requires:** Superadmin role
    """
    # Check if user is superadmin
    if current_user.role != "superadmin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only superadmin can reset SMS settings"
        )
    
    settings = get_or_create_sms_settings(db)
    
    # Reset to defaults
    settings.otp_template = "Your NTC WiFi OTP: {otp}\nValid for {validity} minutes. Do not share.\n\n@{portal_url} #{otp}"
    settings.sender_id = "NTC"
    settings.otp_validity_minutes = 5
    settings.otp_length = 6
    settings.max_otp_per_number_per_hour = 3
    settings.max_otp_per_number_per_day = 10
    settings.enable_primary_sms = True
    settings.enable_secondary_sms = True
    settings.updated_by = current_user.username
    
    db.commit()
    db.refresh(settings)
    
    return settings
