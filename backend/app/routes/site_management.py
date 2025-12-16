"""
Site/Location Management Routes
Manage multiple Omada sites with their own RADIUS configuration
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime

from ..database import get_db
from ..models.site import Site, NASClient
from ..models.admin import Admin
from ..utils.security import get_current_user
from ..services.coa_service import coa_service


router = APIRouter(prefix="/sites", tags=["Site Management"])


# Pydantic Models
class SiteCreate(BaseModel):
    site_name: str = Field(..., min_length=3, max_length=100)
    site_code: str = Field(..., min_length=2, max_length=20)
    location: Optional[str] = None
    
    # Omada Controller
    omada_controller_ip: str
    omada_controller_port: int = 8043
    omada_site_id: str = 'Default'
    omada_username: Optional[str] = None
    omada_password: Optional[str] = None
    
    # RADIUS Configuration
    radius_nas_ip: str
    radius_secret: str
    radius_coa_port: int = Field(..., ge=1024, le=65535, description="Must be unique per site")
    
    # Portal
    portal_url: Optional[str] = None


class SiteUpdate(BaseModel):
    site_name: Optional[str] = None
    location: Optional[str] = None
    omada_controller_ip: Optional[str] = None
    omada_controller_port: Optional[int] = None
    omada_username: Optional[str] = None
    omada_password: Optional[str] = None
    radius_secret: Optional[str] = None
    radius_coa_port: Optional[int] = None
    portal_url: Optional[str] = None
    is_active: Optional[bool] = None


class SiteResponse(BaseModel):
    id: int
    site_name: str
    site_code: str
    location: Optional[str]
    omada_controller_ip: str
    omada_controller_port: int
    omada_site_id: str
    radius_nas_ip: str
    radius_coa_port: int
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


class SiteListResponse(BaseModel):
    total: int
    sites: List[SiteResponse]


class DisconnectRequest(BaseModel):
    username: Optional[str] = None
    mac_address: Optional[str] = None
    session_id: Optional[str] = None
    site_id: Optional[int] = None


# Middleware
def require_admin(current_user: Admin = Depends(get_current_user)):
    if current_user.role not in ['superadmin', 'admin']:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admin or superadmin can manage sites"
        )
    return current_user


@router.get("/", response_model=SiteListResponse)
async def list_sites(
    active_only: bool = False,
    current_user: Admin = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get list of all sites"""
    
    query = db.query(Site)
    
    if active_only:
        query = query.filter(Site.is_active == True)
    
    sites = query.order_by(Site.site_name).all()
    
    return SiteListResponse(
        total=len(sites),
        sites=sites
    )


@router.get("/{site_id}", response_model=SiteResponse)
async def get_site(
    site_id: int,
    current_user: Admin = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get single site details"""
    
    site = db.query(Site).filter(Site.id == site_id).first()
    if not site:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Site not found"
        )
    
    return site


@router.post("/", response_model=SiteResponse)
async def create_site(
    site_data: SiteCreate,
    current_user: Admin = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Create a new site"""
    
    # Check if site code or name already exists
    existing = db.query(Site).filter(
        (Site.site_code == site_data.site_code) |
        (Site.site_name == site_data.site_name)
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Site code or name already exists"
        )
    
    # Check if CoA port already in use
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
        omada_controller_ip=site_data.omada_controller_ip,
        omada_controller_port=site_data.omada_controller_port,
        omada_site_id=site_data.omada_site_id,
        omada_username=site_data.omada_username,
        radius_nas_ip=site_data.radius_nas_ip,
        radius_secret=site_data.radius_secret,
        radius_coa_port=site_data.radius_coa_port,
        portal_url=site_data.portal_url,
        is_active=True,
        created_by=current_user.id
    )
    
    # Encrypt password if provided
    if site_data.omada_password:
        # TODO: Implement password encryption
        new_site.omada_password_encrypted = site_data.omada_password
    
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
    
    # Reload CoA service configuration
    coa_service.load_sites_config(db)
    
    return new_site


@router.put("/{site_id}", response_model=SiteResponse)
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
    
    return site


@router.delete("/{site_id}")
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
    
    # Check if site has active sessions
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
        "message": f"Site '{site.site_name}' deleted successfully",
        "site_id": site_id
    }


@router.post("/{site_id}/disconnect")
async def disconnect_user_from_site(
    site_id: int,
    disconnect_data: DisconnectRequest,
    current_user: Admin = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Disconnect a user from specific site"""
    
    if not any([disconnect_data.username, disconnect_data.mac_address, disconnect_data.session_id]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Must provide username, mac_address, or session_id"
        )
    
    # Verify site exists
    site = db.query(Site).filter(Site.id == site_id).first()
    if not site:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Site not found"
        )
    
    # Disconnect based on what's provided
    if disconnect_data.session_id:
        result = await coa_service.disconnect_by_session_id(disconnect_data.session_id, db)
    elif disconnect_data.mac_address:
        result = await coa_service.disconnect_by_mac(disconnect_data.mac_address, site_id, db)
    else:  # username
        result = await coa_service.disconnect_user(disconnect_data.username, site_id)
    
    if not result['success']:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result['message']
        )
    
    return result


@router.get("/{site_id}/sessions/active")
async def get_site_active_sessions(
    site_id: int,
    current_user: Admin = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get active sessions for a specific site"""
    
    result = db.execute(text("""
        SELECT 
            r.username,
            r.callingstationid as mac_address,
            r.framedipaddress as ip_address,
            r.acctstarttime as start_time,
            r.acctsessiontime as duration,
            r.acctinputoctets + r.acctoutputoctets as total_bytes,
            r.acctsessionid as session_id
        FROM radacct r
        JOIN sites s ON r.nasipaddress = s.radius_nas_ip
        WHERE s.id = :site_id
        AND r.acctstoptime IS NULL
        ORDER BY r.acctstarttime DESC
    """), {"site_id": site_id})
    
    sessions = []
    for row in result:
        sessions.append({
            "username": row[0],
            "mac_address": row[1],
            "ip_address": row[2],
            "start_time": row[3],
            "duration": row[4],
            "total_bytes": row[5],
            "session_id": row[6]
        })
    
    return {
        "site_id": site_id,
        "active_sessions": len(sessions),
        "sessions": sessions
    }


@router.get("/{site_id}/stats")
async def get_site_statistics(
    site_id: int,
    current_user: Admin = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get statistics for a specific site"""
    
    # Total users registered at this site
    total_users = db.execute(text("""
        SELECT COUNT(*) FROM users WHERE registered_site_id = :site_id
    """), {"site_id": site_id}).scalar() or 0
    
    # Active sessions
    active_sessions = db.execute(text("""
        SELECT COUNT(*) 
        FROM radacct r
        JOIN sites s ON r.nasipaddress = s.radius_nas_ip
        WHERE s.id = :site_id AND r.acctstoptime IS NULL
    """), {"site_id": site_id}).scalar() or 0
    
    # Total sessions today
    today_sessions = db.execute(text("""
        SELECT COUNT(*) 
        FROM radacct r
        JOIN sites s ON r.nasipaddress = s.radius_nas_ip
        WHERE s.id = :site_id 
        AND DATE(r.acctstarttime) = CURRENT_DATE
    """), {"site_id": site_id}).scalar() or 0
    
    # Total data usage today (MB)
    today_data = db.execute(text("""
        SELECT COALESCE(SUM(r.acctinputoctets + r.acctoutputoctets), 0) / 1048576.0
        FROM radacct r
        JOIN sites s ON r.nasipaddress = s.radius_nas_ip
        WHERE s.id = :site_id 
        AND DATE(r.acctstarttime) = CURRENT_DATE
    """), {"site_id": site_id}).scalar() or 0
    
    return {
        "site_id": site_id,
        "total_users": total_users,
        "active_sessions": active_sessions,
        "today_sessions": today_sessions,
        "today_data_mb": round(today_data, 2)
    }
