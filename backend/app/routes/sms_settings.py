"""
SMS Settings API Routes
Manage SMS templates and configuration (Superadmin only)
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.sms_settings import SMSSettings
from app.schemas.sms_settings import (
    SMSSettingsResponse,
    SMSSettingsUpdate,
    SMSPreview
)
from app.routes.admin_management import get_current_superadmin


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
    current_admin: dict = Depends(get_current_superadmin)
):
    """
    Get current SMS settings
    
    **Requires:** Superadmin role
    """
    settings = get_or_create_sms_settings(db)
    return settings


@router.put("/", response_model=SMSSettingsResponse)
async def update_sms_settings(
    updates: SMSSettingsUpdate,
    db: Session = Depends(get_db),
    current_admin: dict = Depends(get_current_superadmin)
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
    settings = get_or_create_sms_settings(db)
    
    # Update fields
    update_data = updates.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(settings, field, value)
    
    # Track who made the update
    settings.updated_by = current_admin.get('username', 'unknown')
    
    db.commit()
    db.refresh(settings)
    
    return settings


@router.post("/preview", response_model=SMSPreview)
async def preview_sms_template(
    template: str,
    db: Session = Depends(get_db),
    current_admin: dict = Depends(get_current_superadmin)
):
    """
    Preview how SMS will look with current settings
    
    **Requires:** Superadmin role
    """
    settings = get_or_create_sms_settings(db)
    
    preview = SMSPreview.from_template(
        template=template,
        otp="123456",  # Example OTP
        portal_url="pmfreewifi.lan",
        validity=settings.otp_validity_minutes,
        sender=settings.sender_id
    )
    
    return preview


@router.post("/reset", response_model=SMSSettingsResponse)
async def reset_to_default(
    db: Session = Depends(get_db),
    current_admin: dict = Depends(get_current_superadmin)
):
    """
    Reset SMS settings to default values
    
    **Requires:** Superadmin role
    """
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
    settings.updated_by = current_admin.get('username', 'unknown')
    
    db.commit()
    db.refresh(settings)
    
    return settings
