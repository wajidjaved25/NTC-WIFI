"""
RADIUS Management Routes
For admin portal - session management, user disconnect, statistics
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict

from ..database import get_db
from ..services.radius_service import RadiusService
from ..dependencies import verify_token, verify_admin_or_superadmin

router = APIRouter(prefix="/radius", tags=["RADIUS Management"])


@router.get("/sessions/active", dependencies=[Depends(verify_token)])
async def get_active_sessions(db: Session = Depends(get_db)):
    """Get all currently active RADIUS sessions"""
    
    radius_service = RadiusService(db)
    sessions = radius_service.get_active_sessions()
    
    return {
        "success": True,
        "count": len(sessions),
        "sessions": sessions
    }


@router.get("/sessions/user/{username}", dependencies=[Depends(verify_token)])
async def get_user_sessions(username: str, db: Session = Depends(get_db)):
    """Get session history for a specific user"""
    
    radius_service = RadiusService(db)
    sessions = radius_service.get_user_sessions(username)
    
    return {
        "success": True,
        "username": username,
        "count": len(sessions),
        "sessions": sessions
    }


@router.post("/sessions/disconnect/{username}", dependencies=[Depends(verify_admin_or_superadmin)])
async def disconnect_user(username: str, db: Session = Depends(get_db)):
    """Disconnect a user from WiFi"""
    
    radius_service = RadiusService(db)
    
    success = radius_service.disconnect_user(username)
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to disconnect user")
    
    return {
        "success": True,
        "message": f"User {username} has been disconnected",
        "note": "Session marked as closed in accounting. User will be disconnected on next RADIUS check."
    }


@router.patch("/users/{username}/timeout", dependencies=[Depends(verify_admin_or_superadmin)])
async def update_session_timeout(
    username: str,
    timeout: int,
    db: Session = Depends(get_db)
):
    """Update session timeout for a user"""
    
    if timeout < 60 or timeout > 86400:
        raise HTTPException(
            status_code=400,
            detail="Timeout must be between 60 seconds (1 min) and 86400 seconds (24 hours)"
        )
    
    radius_service = RadiusService(db)
    
    success = radius_service.update_session_timeout(username, timeout)
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to update session timeout")
    
    return {
        "success": True,
        "message": f"Session timeout updated to {timeout} seconds for {username}"
    }


@router.delete("/users/{username}", dependencies=[Depends(verify_admin_or_superadmin)])
async def delete_radius_user(username: str, db: Session = Depends(get_db)):
    """Delete RADIUS user account"""
    
    radius_service = RadiusService(db)
    
    success = radius_service.delete_radius_user(username)
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete RADIUS user")
    
    return {
        "success": True,
        "message": f"RADIUS user {username} has been deleted"
    }
