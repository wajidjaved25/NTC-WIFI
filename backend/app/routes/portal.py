from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List, Optional
import os
import shutil
from datetime import datetime

from ..database import get_db
from ..models.admin import Admin
from ..models.portal_design import PortalDesign
from ..models.portal_settings import PortalSettings
from ..schemas.portal import (
    PortalDesignCreate, PortalDesignUpdate, PortalDesignResponse,
    PortalSettingUpdate, PortalSettingResponse
)
from ..utils.security import get_current_user, has_permission
from ..utils.helpers import sanitize_filename, log_system_event

router = APIRouter(prefix="/portal", tags=["Portal Design & Settings"])

# Media storage path
MEDIA_DIR = "D:/Codes/NTC/NTC Public Wifi/media/portal"
os.makedirs(MEDIA_DIR, exist_ok=True)

# Middleware to check portal design permission
def require_portal_permission(current_user: Admin = Depends(get_current_user)):
    if not has_permission(current_user, "edit_portal_design"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to edit portal design"
        )
    return current_user

# ========== PORTAL DESIGN ENDPOINTS ==========

# Get all portal designs
@router.get("/designs", response_model=List[PortalDesignResponse])
async def get_portal_designs(
    current_user: Admin = Depends(require_portal_permission),
    db: Session = Depends(get_db)
):
    designs = db.query(PortalDesign).order_by(PortalDesign.created_at.desc()).all()
    return designs

# Get active portal design (alias for frontend)
@router.get("/design", response_model=PortalDesignResponse)
@router.get("/design/active", response_model=PortalDesignResponse)
async def get_active_design(db: Session = Depends(get_db)):
    """Public endpoint - used by user portal"""
    # First try to get active design
    design = db.query(PortalDesign).filter(PortalDesign.is_active == True).first()
    
    # If no active design, get the most recently updated one
    if not design:
        design = db.query(PortalDesign).order_by(PortalDesign.updated_at.desc()).first()
    
    # If still no design exists, return default
    if not design:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No portal design found"
        )
    
    return design

# Get specific portal design
@router.get("/designs/{design_id}", response_model=PortalDesignResponse)
async def get_portal_design(
    design_id: int,
    current_user: Admin = Depends(require_portal_permission),
    db: Session = Depends(get_db)
):
    design = db.query(PortalDesign).filter(PortalDesign.id == design_id).first()
    if not design:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portal design not found"
        )
    return design

# Create portal design
@router.post("/designs", response_model=PortalDesignResponse)
async def create_portal_design(
    design_data: PortalDesignCreate,
    current_user: Admin = Depends(require_portal_permission),
    db: Session = Depends(get_db)
):
    # Check if this is the first design - make it active by default
    existing_count = db.query(PortalDesign).count()
    is_first_design = existing_count == 0
    
    design = PortalDesign(
        **design_data.dict(),
        updated_by=current_user.id,
        is_active=is_first_design  # First design is active by default
    )
    
    db.add(design)
    db.commit()
    db.refresh(design)
    
    # Log the action
    await log_system_event(
        db, "INFO", "portal", "design_created",
        f"Portal design '{design_data.template_name}' created",
        {"design_id": design.id},
        current_user.id
    )
    
    return design

# Update portal design
@router.patch("/designs/{design_id}", response_model=PortalDesignResponse)
async def update_portal_design(
    design_id: int,
    design_data: PortalDesignUpdate,
    current_user: Admin = Depends(require_portal_permission),
    db: Session = Depends(get_db)
):
    design = db.query(PortalDesign).filter(PortalDesign.id == design_id).first()
    if not design:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portal design not found"
        )
    
    # Debug logging
    print(f"\n=== UPDATE PORTAL DESIGN ===")
    print(f"Received data: {design_data.dict()}")
    print(f"Exclude unset: {design_data.dict(exclude_unset=True)}")
    print(f"show_logo: {design_data.show_logo}")
    print(f"show_background: {design_data.show_background}")
    
    # Update fields - use dict() instead of dict(exclude_unset=True) to include False values
    update_data = design_data.dict(exclude_unset=True)
    
    # Special handling for boolean fields - explicitly check if they were provided
    if design_data.show_logo is not None:
        update_data['show_logo'] = design_data.show_logo
    if design_data.show_background is not None:
        update_data['show_background'] = design_data.show_background
    
    print(f"Final update_data: {update_data}")
    
    for key, value in update_data.items():
        print(f"Setting {key} = {value} (type: {type(value)})")
        setattr(design, key, value)
    
    design.updated_by = current_user.id
    design.updated_at = datetime.now()
    
    # If this design is not active and there's no active design, activate it
    if not design.is_active:
        active_design = db.query(PortalDesign).filter(PortalDesign.is_active == True).first()
        if not active_design:
            design.is_active = True
    
    db.commit()
    db.refresh(design)
    
    print(f"After save - show_logo: {design.show_logo}, show_background: {design.show_background}")
    print(f"=== END UPDATE ===")
    
    # Log the action
    await log_system_event(
        db, "INFO", "portal", "design_updated",
        f"Portal design '{design.template_name}' updated",
        {"design_id": design.id, "updated_fields": list(update_data.keys())},
        current_user.id
    )
    
    return design

# Activate portal design
@router.post("/designs/{design_id}/activate")
async def activate_design(
    design_id: int,
    current_user: Admin = Depends(require_portal_permission),
    db: Session = Depends(get_db)
):
    design = db.query(PortalDesign).filter(PortalDesign.id == design_id).first()
    if not design:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portal design not found"
        )
    
    # Deactivate all other designs
    db.query(PortalDesign).update({PortalDesign.is_active: False})
    
    # Activate this design
    design.is_active = True
    db.commit()
    
    # Log the action
    await log_system_event(
        db, "INFO", "portal", "design_activated",
        f"Portal design '{design.template_name}' activated",
        {"design_id": design.id},
        current_user.id
    )
    
    return {"success": True, "message": "Design activated"}

# Upload logo
@router.post("/designs/{design_id}/upload-logo")
async def upload_logo(
    design_id: int,
    file: UploadFile = File(...),
    current_user: Admin = Depends(require_portal_permission),
    db: Session = Depends(get_db)
):
    design = db.query(PortalDesign).filter(PortalDesign.id == design_id).first()
    if not design:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portal design not found"
        )
    
    # Validate file type
    if not file.content_type.startswith('image/'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be an image"
        )
    
    # Generate filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_ext = os.path.splitext(file.filename)[1]
    filename = f"logo_{design_id}_{timestamp}{file_ext}"
    file_path = os.path.join(MEDIA_DIR, filename)
    
    # Save file
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Delete old logo if exists
        if design.logo_path and os.path.exists(design.logo_path):
            os.remove(design.logo_path)
        
        # Update design with web-accessible path and enable logo display
        design.logo_path = f"http://localhost:8000/media/portal/{filename}"
        design.show_logo = True  # Automatically enable logo when uploaded
        db.commit()
        
        return {
            "success": True,
            "message": "Logo uploaded successfully",
            "file_path": f"http://localhost:8000/media/portal/{filename}"
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload logo: {str(e)}"
        )

# Upload background image
@router.post("/designs/{design_id}/upload-background")
async def upload_background(
    design_id: int,
    file: UploadFile = File(...),
    current_user: Admin = Depends(require_portal_permission),
    db: Session = Depends(get_db)
):
    design = db.query(PortalDesign).filter(PortalDesign.id == design_id).first()
    if not design:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portal design not found"
        )
    
    # Validate file type
    if not file.content_type.startswith('image/'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be an image"
        )
    
    # Generate filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_ext = os.path.splitext(file.filename)[1]
    filename = f"background_{design_id}_{timestamp}{file_ext}"
    file_path = os.path.join(MEDIA_DIR, filename)
    
    # Save file
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Delete old background if exists
        if design.background_image and os.path.exists(design.background_image):
            os.remove(design.background_image)
        
        # Update design with web-accessible path
        # Note: We don't automatically set show_background=True here anymore
        # because the user might have explicitly toggled it OFF
        design.background_image = f"http://localhost:8000/media/portal/{filename}"
        # Only enable show_background if it's not already explicitly set to False
        if design.show_background is None:
            design.show_background = True
        db.commit()
        
        return {
            "success": True,
            "message": "Background uploaded successfully",
            "file_path": f"http://localhost:8000/media/portal/{filename}"
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload background: {str(e)}"
        )

# Delete portal design
@router.delete("/designs/{design_id}")
async def delete_design(
    design_id: int,
    current_user: Admin = Depends(require_portal_permission),
    db: Session = Depends(get_db)
):
    design = db.query(PortalDesign).filter(PortalDesign.id == design_id).first()
    if not design:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portal design not found"
        )
    
    if design.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete active design"
        )
    
    # Delete associated files
    if design.logo_path and os.path.exists(design.logo_path):
        os.remove(design.logo_path)
    if design.background_image and os.path.exists(design.background_image):
        os.remove(design.background_image)
    
    design_name = design.template_name
    db.delete(design)
    db.commit()
    
    # Log the action
    await log_system_event(
        db, "INFO", "portal", "design_deleted",
        f"Portal design '{design_name}' deleted",
        {"design_id": design_id},
        current_user.id
    )
    
    return {"success": True, "message": "Design deleted"}

# ========== PORTAL SETTINGS ENDPOINTS ==========

# Get all portal settings
@router.get("/settings", response_model=List[PortalSettingResponse])
async def get_portal_settings(
    current_user: Admin = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    settings = db.query(PortalSettings).all()
    return settings

# Get specific setting
@router.get("/settings/{setting_key}", response_model=PortalSettingResponse)
async def get_portal_setting(
    setting_key: str,
    current_user: Admin = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    setting = db.query(PortalSettings).filter(PortalSettings.setting_key == setting_key).first()
    if not setting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Setting not found"
        )
    return setting

# Update portal setting
@router.patch("/settings/{setting_key}", response_model=PortalSettingResponse)
async def update_portal_setting(
    setting_key: str,
    setting_data: PortalSettingUpdate,
    current_user: Admin = Depends(require_portal_permission),
    db: Session = Depends(get_db)
):
    setting = db.query(PortalSettings).filter(PortalSettings.setting_key == setting_key).first()
    if not setting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Setting not found"
        )
    
    setting.setting_value = setting_data.setting_value
    setting.updated_by = current_user.id
    
    db.commit()
    db.refresh(setting)
    
    # Log the action
    await log_system_event(
        db, "INFO", "portal", "setting_updated",
        f"Portal setting '{setting_key}' updated",
        {"setting_key": setting_key, "new_value": setting_data.setting_value},
        current_user.id
    )
    
    # Special handling for domain/URL changes - restart services if needed
    if setting_key in ['portal_domain', 'portal_url']:
        # TODO: Trigger Nginx config update and reload
        pass
    
    return setting
