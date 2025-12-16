"""
Site Management Routes - UPDATED
Separate Controller and Site Management
One Controller → Many Sites
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime

from ..database import get_db
from ..models.site_updated import Site, NASClient, OmadaController
from ..models.admin import Admin
from ..utils.security import get_current_user
from ..services.coa_service import coa_service


router = APIRouter(tags=["Site Management"])


# ==================== PYDANTIC MODELS ====================

# Controller Models
class ControllerCreate(BaseModel):
    controller_name: str
    controller_type: str = 'cloud'  # 'cloud' or 'on-premise'
    controller_url: str
    controller_port: int = 8043
    username: Optional[str] = None
    password: Optional[str] = None
    controller_id: Optional[str] = None  # For cloud


class ControllerUpdate(BaseModel):
    controller_name: Optional[str] = None
    controller_url: Optional[str] = None
    controller_port: Optional[int] = None
    username: Optional[str] = None
    password: Optional[str] = None
    is_active: Optional[bool] = None


class ControllerResponse(BaseModel):
    id: int
    controller_name: str
    controller_type: str
    controller_url: str
    controller_port: int
    is_active: bool
    connection_status: str
    last_connected: Optional[datetime]
    created_at: datetime
    
    class Config:
        from_attributes = True


# Site Models
class SiteCreate(BaseModel):
    site_name: str = Field(..., min_length=3, max_length=100)
    site_code: str = Field(..., min_length=2, max_length=20)
    location: Optional[str] = None
    
    # Controller Reference
    controller_id: int = Field(..., description="ID of the Omada controller managing this site")
    omada_site_id: str = 'Default'
    
    # RADIUS Configuration
    radius_nas_ip: str
    radius_secret: str
    radius_coa_port: int = Field(..., ge=1024, le=65535)
    
    # Network
    network_subnet: Optional[str] = None
    gateway_ip: Optional[str] = None
    
    # Portal
    portal_url: Optional[str] = None


class SiteUpdate(BaseModel):
    site_name: Optional[str] = None
    location: Optional[str] = None
    omada_site_id: Optional[str] = None
    radius_nas_ip: Optional[str] = None
    radius_secret: Optional[str] = None
    radius_coa_port: Optional[int] = None
    network_subnet: Optional[str] = None
    gateway_ip: Optional[str] = None
    portal_url: Optional[str] = None
    is_active: Optional[bool] = None


class SiteResponse(BaseModel):
    id: int
    site_name: str
    site_code: str
    location: Optional[str]
    controller_id: int
    controller_name: Optional[str] = None  # Joined from controller
    omada_site_id: str
    radius_nas_ip: str
    radius_coa_port: int
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


class DisconnectRequest(BaseModel):
    username: Optional[str] = None
    mac_address: Optional[str] = None
    session_id: Optional[str] = None


# Middleware
def require_admin(current_user: Admin = Depends(get_current_user)):
    if current_user.role not in ['superadmin', 'admin']:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admin or superadmin can manage sites"
        )
    return current_user


# ==================== CONTROLLER ROUTES ====================

@router.get("/controllers", response_model=List[ControllerResponse])
async def list_controllers(
    active_only: bool = False,
    current_user: Admin = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get list of all Omada controllers"""
    
    query = db.query(OmadaController)
    
    if active_only:
        query = query.filter(OmadaController.is_active == True)
    
    controllers = query.order_by(OmadaController.controller_name).all()
    return controllers


@router.post("/controllers", response_model=ControllerResponse)
async def create_controller(
    controller_data: ControllerCreate,
    current_user: Admin = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Create a new Omada controller"""
    
    # Check if controller name exists
    existing = db.query(OmadaController).filter(
        OmadaController.controller_name == controller_data.controller_name
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Controller name already exists"
        )
    
    new_controller = OmadaController(
        controller_name=controller_data.controller_name,
        controller_type=controller_data.controller_type,
        controller_url=controller_data.controller_url,
        controller_port=controller_data.controller_port,
        username=controller_data.username,
        controller_id=controller_data.controller_id,
        is_active=True,
        created_by=current_user.id
    )
    
    # Encrypt password if provided
    if controller_data.password:
        # TODO: Implement password encryption
        new_controller.password_encrypted = controller_data.password
    
    db.add(new_controller)
    db.commit()
    db.refresh(new_controller)
    
    return new_controller


@router.put("/controllers/{controller_id}", response_model=ControllerResponse)
async def update_controller(
    controller_id: int,
    controller_data: ControllerUpdate,
    current_user: Admin = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Update controller information"""
    
    controller = db.query(OmadaController).filter(OmadaController.id == controller_id).first()
    if not controller:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Controller not found"
        )
    
    # Update fields
    update_data = controller_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        if field == 'password' and value:
            # TODO: Encrypt password
            setattr(controller, 'password_encrypted', value)
        else:
            setattr(controller, field, value)
    
    db.commit()
    db.refresh(controller)
    return controller


@router.delete("/controllers/{controller_id}")
async def delete_controller(
    controller_id: int,
    current_user: Admin = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Delete a controller - only if no sites are using it"""
    
    controller = db.query(OmadaController).filter(OmadaController.id == controller_id).first()
    if not controller:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Controller not found"
        )
    
    # Check if any sites are using this controller
    site_count = db.query(Site).filter(Site.controller_id == controller_id).count()
    if site_count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete controller. {site_count} site(s) are still using it."
        )
    
    db.delete(controller)
    db.commit()
    
    return {
        "message": f"Controller '{controller.controller_name}' deleted successfully"
    }


# ==================== SITE ROUTES ====================

@router.get("/sites", response_model=List[SiteResponse])
async def list_sites(
    active_only: bool = False,
    controller_id: Optional[int] = None,
    current_user: Admin = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get list of all sites, optionally filtered by controller"""
    
    query = db.query(Site, OmadaController.controller_name).join(
        OmadaController, Site.controller_id == OmadaController.id
    )
    
    if active_only:
        query = query.filter(Site.is_active == True)
    
    if controller_id:
        query = query.filter(Site.controller_id == controller_id)
    
    results = query.order_by(Site.site_name).all()
    
    # Combine site and controller name
    sites = []
    for site, controller_name in results:
        site_dict = {
            "id": site.id,
            "site_name": site.site_name,
            "site_code": site.site_code,
            "location": site.location,
            "controller_id": site.controller_id,
            "controller_name": controller_name,
            "omada_site_id": site.omada_site_id,
            "radius_nas_ip": site.radius_nas_ip,
            "radius_coa_port": site.radius_coa_port,
            "is_active": site.is_active,
            "created_at": site.created_at
        }
        sites.append(SiteResponse(**site_dict))
    
    return sites


@router.post("/sites", response_model=SiteResponse)
async def create_site(
    site_data: SiteCreate,
    current_user: Admin = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Create a new site"""
    
    # Verify controller exists
    controller = db.query(OmadaController).filter(
        OmadaController.id == site_data.controller_id
    ).first()
    
    if not controller:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Controller with ID {site_data.controller_id} not found"
        )
    
    # Check if site code/name exists
    existing = db.query(Site).filter(
        (Site.site_code == site_data.site_code) |
        (Site.site_name == site_data.site_name)
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Site code or name already exists"
        )
    
    # Check CoA port uniqueness
    existing_port = db.query(Site).filter(
        Site.radius_coa_port == site_data.radius_coa_port
    ).first()
    
    if existing_port:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"CoA port {site_data.radius_coa_port} already in use by {existing_port.site_name}"
        )
    
    # Create site
    new_site = Site(
        site_name=site_data.site_name,
        site_code=site_data.site_code,
        location=site_data.location,
        controller_id=site_data.controller_id,
        omada_site_id=site_data.omada_site_id,
        radius_nas_ip=site_data.radius_nas_ip,
        radius_secret=site_data.radius_secret,
        radius_coa_port=site_data.radius_coa_port,
        network_subnet=site_data.network_subnet,
        gateway_ip=site_data.gateway_ip,
        portal_url=site_data.portal_url,
        is_active=True,
        created_by=current_user.id
    )
    
    db.add(new_site)
    db.commit()
    db.refresh(new_site)
    
    # Create NAS client entry
    nas_client = NASClient(
        site_id=new_site.id,
        nasname=site_data.radius_nas_ip,
        shortname=site_data.site_code.lower(),
        secret=site_data.radius_secret,
        coa_port=site_data.radius_coa_port,
        description=f"NAS for {site_data.site_name}"
    )
    
    db.add(nas_client)
    db.commit()
    
    # Reload CoA service
    coa_service.load_sites_config(db)
    
    # Add controller_name for response
    response_data = {
        **new_site.__dict__,
        "controller_name": controller.controller_name
    }
    
    return SiteResponse(**response_data)


@router.put("/sites/{site_id}", response_model=SiteResponse)
async def update_site(
    site_id: int,
    site_data: SiteUpdate,
    current_user: Admin = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Update site information"""
    
    site = db.query(Site).filter(Site.id == site_id).first()
    if not site:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Site not found"
        )
    
    # Check CoA port conflict if changing
    if site_data.radius_coa_port and site_data.radius_coa_port != site.radius_coa_port:
        existing = db.query(Site).filter(
            Site.radius_coa_port == site_data.radius_coa_port,
            Site.id != site_id
        ).first()
        
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"CoA port {site_data.radius_coa_port} already in use"
            )
    
    # Update fields
    update_data = site_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(site, field, value)
    
    db.commit()
    db.refresh(site)
    
    # Update NAS client if RADIUS config changed
    if any(k in update_data for k in ['radius_nas_ip', 'radius_secret', 'radius_coa_port']):
        nas_client = db.query(NASClient).filter(NASClient.site_id == site_id).first()
        if nas_client:
            if site_data.radius_nas_ip:
                nas_client.nasname = site_data.radius_nas_ip
            if site_data.radius_secret:
                nas_client.secret = site_data.radius_secret
            if site_data.radius_coa_port:
                nas_client.coa_port = site_data.radius_coa_port
            db.commit()
    
    # Reload CoA service
    coa_service.load_sites_config(db)
    
    # Get controller name
    controller = db.query(OmadaController).filter(
        OmadaController.id == site.controller_id
    ).first()
    
    response_data = {
        **site.__dict__,
        "controller_name": controller.controller_name if controller else None
    }
    
    return SiteResponse(**response_data)


@router.delete("/sites/{site_id}")
async def delete_site(
    site_id: int,
    current_user: Admin = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Delete a site"""
    
    site = db.query(Site).filter(Site.id == site_id).first()
    if not site:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Site not found"
        )
    
    # Check for active sessions
    result = db.execute(text("""
        SELECT COUNT(*) 
        FROM sessions 
        WHERE site_id = :site_id 
        AND session_status = 'active'
    """), {"site_id": site_id})
    
    active_sessions = result.scalar()
    if active_sessions > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete site with {active_sessions} active sessions"
        )
    
    db.delete(site)
    db.commit()
    
    # Reload CoA service
    coa_service.load_sites_config(db)
    
    return {
        "message": f"Site '{site.site_name}' deleted successfully"
    }


# ... (rest of the routes remain same: disconnect, stats, sessions)
# Keep all the existing disconnect/stats/sessions routes from previous implementation
