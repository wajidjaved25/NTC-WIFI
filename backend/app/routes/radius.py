"""
RADIUS Management Routes
For admin portal - session management, user disconnect, statistics
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict

from ..database import get_db
from ..services.radius_service import RadiusService
from ..utils.security import get_current_user
from ..models.admin import Admin

router = APIRouter(prefix="/radius", tags=["RADIUS Management"])


@router.get("/sessions/active")
async def get_active_sessions(
    current_user: Admin = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all currently active RADIUS sessions"""
    
    radius_service = RadiusService(db)
    sessions = radius_service.get_active_sessions()
    
    return {
        "success": True,
        "count": len(sessions),
        "sessions": sessions
    }


@router.get("/sessions/user/{username}")
async def get_user_sessions(
    username: str,
    current_user: Admin = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get session history for a specific user"""
    
    radius_service = RadiusService(db)
    sessions = radius_service.get_user_sessions(username)
    
    return {
        "success": True,
        "username": username,
        "count": len(sessions),
        "sessions": sessions
    }


@router.post("/sessions/disconnect/{username}")
async def disconnect_user(
    username: str,
    current_user: Admin = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Disconnect a user from WiFi (admin and superadmin only)"""
    
    # Check if user has admin privileges
    if current_user.role not in ["admin", "superadmin"]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    radius_service = RadiusService(db)
    
    success = radius_service.disconnect_user(username)
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to disconnect user")
    
    return {
        "success": True,
        "message": f"User {username} has been disconnected",
        "note": "Session marked as closed in accounting. User will be disconnected on next RADIUS check."
    }


@router.patch("/users/{username}/timeout")
async def update_session_timeout(
    username: str,
    timeout: int,
    current_user: Admin = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update session timeout for a user (admin and superadmin only)"""
    
    # Check if user has admin privileges
    if current_user.role not in ["admin", "superadmin"]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
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


@router.delete("/users/{username}")
async def delete_radius_user(
    username: str,
    current_user: Admin = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete RADIUS user account (admin and superadmin only)"""
    
    # Check if user has admin privileges
    if current_user.role not in ["admin", "superadmin"]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    radius_service = RadiusService(db)
    
    success = radius_service.delete_radius_user(username)
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete RADIUS user")
    
    return {
        "success": True,
        "message": f"RADIUS user {username} has been deleted"
    }
