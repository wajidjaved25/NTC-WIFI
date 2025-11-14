from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from ..database import get_db
from ..models.admin import Admin
from ..models.omada_config import OmadaConfig
from ..schemas.omada import (
    OmadaConfigCreate, OmadaConfigUpdate, OmadaConfigResponse,
    OmadaTestConnection, ClientAuthorization
)
from ..services.omada_service import OmadaService
from ..utils.security import get_current_user, has_permission
from ..utils.helpers import encrypt_password, log_system_event

router = APIRouter(prefix="/omada", tags=["Omada Configuration"])

# Middleware to check omada permissions
def require_omada_permission(current_user: Admin = Depends(get_current_user)):
    if not has_permission(current_user, "edit_omada"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to manage Omada settings"
        )
    return current_user

# Get all Omada configurations
@router.get("/configs", response_model=List[OmadaConfigResponse])
async def get_omada_configs(
    current_user: Admin = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    configs = db.query(OmadaConfig).all()
    return configs

# Get active Omada configuration (alias for frontend)
@router.get("/config", response_model=OmadaConfigResponse)
@router.get("/config/active", response_model=OmadaConfigResponse)
async def get_active_config(
    current_user: Admin = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    config = db.query(OmadaConfig).filter(OmadaConfig.is_active == True).first()
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active Omada configuration found"
        )
    return config

# Get specific Omada configuration
@router.get("/configs/{config_id}", response_model=OmadaConfigResponse)
async def get_omada_config(
    config_id: int,
    current_user: Admin = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    config = db.query(OmadaConfig).filter(OmadaConfig.id == config_id).first()
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Configuration not found"
        )
    return config

# Create new Omada configuration
@router.post("/configs", response_model=OmadaConfigResponse)
async def create_omada_config(
    config_data: OmadaConfigCreate,
    current_user: Admin = Depends(require_omada_permission),
    db: Session = Depends(get_db)
):
    # Encrypt password before storing
    encrypted_password = encrypt_password(config_data.password)
    
    # Create new config
    new_config = OmadaConfig(
        config_name=config_data.config_name,
        controller_url=config_data.controller_url,
        controller_id=config_data.controller_id,
        username=config_data.username,
        password_encrypted=encrypted_password,
        site_id=config_data.site_id,
        site_name=config_data.site_name,
        auth_type=config_data.auth_type,
        redirect_url=config_data.redirect_url,
        session_timeout=config_data.session_timeout,
        idle_timeout=config_data.idle_timeout,
        daily_time_limit=config_data.daily_time_limit,
        max_daily_sessions=config_data.max_daily_sessions,
        bandwidth_limit_up=config_data.bandwidth_limit_up,
        bandwidth_limit_down=config_data.bandwidth_limit_down,
        enable_rate_limiting=config_data.enable_rate_limiting,
        rate_limit_up=config_data.rate_limit_up,
        rate_limit_down=config_data.rate_limit_down,
        daily_data_limit=config_data.daily_data_limit,
        session_data_limit=config_data.session_data_limit,
        enable_mac_filtering=config_data.enable_mac_filtering,
        allowed_mac_addresses=config_data.allowed_mac_addresses,
        blocked_mac_addresses=config_data.blocked_mac_addresses,
        updated_by=current_user.id
    )
    
    db.add(new_config)
    db.commit()
    db.refresh(new_config)
    
    # Log the action
    await log_system_event(
        db, "INFO", "omada", "config_created",
        f"Omada config '{config_data.config_name}' created",
        {"config_id": new_config.id},
        current_user.id
    )
    
    return new_config

# Update Omada configuration
@router.patch("/configs/{config_id}", response_model=OmadaConfigResponse)
async def update_omada_config(
    config_id: int,
    config_data: OmadaConfigUpdate,
    current_user: Admin = Depends(require_omada_permission),
    db: Session = Depends(get_db)
):
    config = db.query(OmadaConfig).filter(OmadaConfig.id == config_id).first()
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Configuration not found"
        )
    
    # Update fields
    update_data = config_data.dict(exclude_unset=True)
    
    # Encrypt password if provided
    if 'password' in update_data and update_data['password']:
        update_data['password_encrypted'] = encrypt_password(update_data.pop('password'))
    
    for key, value in update_data.items():
        setattr(config, key, value)
    
    config.updated_by = current_user.id
    
    db.commit()
    db.refresh(config)
    
    # Log the action
    await log_system_event(
        db, "INFO", "omada", "config_updated",
        f"Omada config '{config.config_name}' updated",
        {"config_id": config.id, "updated_fields": list(update_data.keys())},
        current_user.id
    )
    
    return config

# Set active configuration
@router.post("/configs/{config_id}/activate")
async def activate_config(
    config_id: int,
    current_user: Admin = Depends(require_omada_permission),
    db: Session = Depends(get_db)
):
    config = db.query(OmadaConfig).filter(OmadaConfig.id == config_id).first()
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Configuration not found"
        )
    
    # Deactivate all other configs
    db.query(OmadaConfig).update({OmadaConfig.is_active: False})
    
    # Activate this config
    config.is_active = True
    db.commit()
    
    # Log the action
    await log_system_event(
        db, "INFO", "omada", "config_activated",
        f"Omada config '{config.config_name}' activated",
        {"config_id": config.id},
        current_user.id
    )
    
    return {"success": True, "message": "Configuration activated"}

# Test connection to Omada controller
@router.post("/test-connection")
async def test_connection(
    test_data: OmadaTestConnection,
    current_user: Admin = Depends(require_omada_permission),
    db: Session = Depends(get_db)
):
    import logging
    logger = logging.getLogger(__name__)
    
    # If use_stored_password is True, fetch password from database
    if test_data.use_stored_password and test_data.config_id:
        config = db.query(OmadaConfig).filter(OmadaConfig.id == test_data.config_id).first()
        if not config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Configuration not found"
            )
        encrypted_password = config.password_encrypted
        logger.info(f"Using stored encrypted password for config {test_data.config_id}")
        logger.info(f"Encrypted password (first 20 chars): {encrypted_password[:20]}...")
    elif test_data.password:
        encrypted_password = encrypt_password(test_data.password)
        logger.info(f"Using provided password, encrypted (first 20 chars): {encrypted_password[:20]}...")
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password is required"
        )
    
    # Test decryption
    from ..utils.helpers import decrypt_password
    try:
        decrypted = decrypt_password(encrypted_password)
        logger.info(f"Password decrypted successfully, length: {len(decrypted)}")
    except Exception as e:
        logger.error(f"Password decryption failed: {str(e)}")
    
    omada = OmadaService(
        test_data.controller_url,
        test_data.username,
        encrypted_password,
        test_data.controller_id,
        test_data.site_id
    )
    
    result = omada.test_connection()
    return result

# Authorize client
@router.post("/authorize-client")
async def authorize_client(
    auth_data: ClientAuthorization,
    db: Session = Depends(get_db)
):
    # Get active config
    config = db.query(OmadaConfig).filter(OmadaConfig.is_active == True).first()
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active Omada configuration"
        )
    
    omada = OmadaService(
        config.controller_url,
        config.username,
        config.password_encrypted,
        config.controller_id,
        config.site_id
    )
    
    result = omada.authorize_client(
        auth_data.mac_address,
        auth_data.duration,
        auth_data.upload_limit,
        auth_data.download_limit
    )
    
    return result

# Get online clients
@router.get("/online-clients")
async def get_online_clients(
    current_user: Admin = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    config = db.query(OmadaConfig).filter(OmadaConfig.is_active == True).first()
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active Omada configuration"
        )
    
    omada = OmadaService(
        config.controller_url,
        config.username,
        config.password_encrypted,
        config.controller_id,
        config.site_id
    )
    
    result = omada.get_online_clients()
    return result

# Get available sites
@router.get("/sites")
async def get_sites(
    current_user: Admin = Depends(require_omada_permission),
    db: Session = Depends(get_db)
):
    config = db.query(OmadaConfig).filter(OmadaConfig.is_active == True).first()
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active Omada configuration"
        )
    
    omada = OmadaService(
        config.controller_url,
        config.username,
        config.password_encrypted,
        config.controller_id
    )
    
    result = omada.get_sites()
    return result

# Auto-detect controller ID
@router.post("/detect-controller-id")
async def detect_controller_id(
    test_data: OmadaTestConnection,
    current_user: Admin = Depends(require_omada_permission)
):
    encrypted_password = encrypt_password(test_data.password)
    omada = OmadaService(
        test_data.controller_url,
        test_data.username,
        encrypted_password,
        None,
        "Default"
    )
    
    result = omada.get_controller_id()
    return result

# Delete configuration
@router.delete("/configs/{config_id}")
async def delete_config(
    config_id: int,
    current_user: Admin = Depends(require_omada_permission),
    db: Session = Depends(get_db)
):
    config = db.query(OmadaConfig).filter(OmadaConfig.id == config_id).first()
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Configuration not found"
        )
    
    if config.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete active configuration"
        )
    
    config_name = config.config_name
    db.delete(config)
    db.commit()
    
    # Log the action
    await log_system_event(
        db, "INFO", "omada", "config_deleted",
        f"Omada config '{config_name}' deleted",
        {"config_id": config_id},
        current_user.id
    )
    
    return {"success": True, "message": "Configuration deleted"}
