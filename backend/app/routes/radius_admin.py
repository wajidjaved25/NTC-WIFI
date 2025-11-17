"""
Admin Routes for RADIUS Session Management
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from ..database import get_db
from ..models.admin import Admin
from ..utils.security import get_current_user, has_permission
from ..utils.radius import (
    get_active_radius_sessions,
    get_user_session_history,
    disconnect_user_session,
    get_radius_statistics,
    update_user_session_timeout,
    delete_radius_user
)

router = APIRouter(prefix="/radius", tags=["RADIUS Management"])


# Middleware to check session management permission
def require_session_permission(current_user: Admin = Depends(get_current_user)):
    if not has_permission(current_user, "manage_sessions"):
        raise HTTPException(
            status_code=403,
            detail="You don't have permission to manage sessions"
        )
    return current_user


@router.get("/sessions/active")
async def get_active_sessions(
    current_user: Admin = Depends(require_session_permission)
):
    """Get all active RADIUS sessions"""
    try:
        sessions = get_active_radius_sessions()
        return {
            "success": True,
            "count": len(sessions),
            "sessions": sessions
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions/user/{username}")
async def get_user_sessions(
    username: str,
    limit: int = 10,
    current_user: Admin = Depends(require_session_permission)
):
    """Get session history for a specific user"""
    try:
        history = get_user_session_history(username, limit)
        return {
            "success": True,
            "username": username,
            "count": len(history),
            "sessions": history
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sessions/disconnect/{username}")
async def disconnect_user(
    username: str,
    current_user: Admin = Depends(require_session_permission)
):
    """Disconnect a user's active session"""
    try:
        success = disconnect_user_session(username)
        if success:
            return {
                "success": True,
                "message": f"Disconnect request sent for user {username}"
            }
        else:
            return {
                "success": False,
                "message": "Failed to send disconnect request"
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/statistics")
async def get_statistics(
    current_user: Admin = Depends(require_session_permission)
):
    """Get RADIUS statistics"""
    try:
        stats = get_radius_statistics()
        return {
            "success": True,
            "statistics": stats
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/users/{username}/timeout")
async def update_user_timeout(
    username: str,
    timeout: int,
    current_user: Admin = Depends(require_session_permission)
):
    """Update session timeout for a user"""
    try:
        if timeout < 60 or timeout > 86400:  # 1 minute to 24 hours
            raise HTTPException(
                status_code=400,
                detail="Timeout must be between 60 and 86400 seconds"
            )
        
        success = update_user_session_timeout(username, timeout)
        if success:
            return {
                "success": True,
                "message": f"Session timeout updated to {timeout} seconds"
            }
        else:
            return {
                "success": False,
                "message": "Failed to update timeout"
            }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/users/{username}")
async def delete_user(
    username: str,
    current_user: Admin = Depends(require_session_permission)
):
    """Delete a RADIUS user"""
    try:
        success = delete_radius_user(username)
        if success:
            return {
                "success": True,
                "message": f"RADIUS user {username} deleted"
            }
        else:
            return {
                "success": False,
                "message": "Failed to delete user"
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
