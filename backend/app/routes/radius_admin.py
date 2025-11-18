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


@router.get("/settings")
async def get_radius_settings(
    current_user: Admin = Depends(require_session_permission),
    db: Session = Depends(get_db)
):
    """Get RADIUS settings from database"""
    from ..models.radius_settings import RadiusSettings
    
    # Get or create settings
    settings = db.query(RadiusSettings).first()
    
    if not settings:
        # Create default settings
        settings = RadiusSettings(
            default_session_timeout=3600,
            max_session_timeout=86400,
            default_bandwidth_down=0,
            default_bandwidth_up=0,
            max_concurrent_sessions=1,
            idle_timeout=600,
            daily_data_limit=0,
            monthly_data_limit=0,
            allow_multiple_devices=False
        )
        db.add(settings)
        db.commit()
        db.refresh(settings)
    
    return {
        "success": True,
        "settings": {
            "default_session_timeout": settings.default_session_timeout,
            "max_session_timeout": settings.max_session_timeout,
            "default_bandwidth_down": settings.default_bandwidth_down,
            "default_bandwidth_up": settings.default_bandwidth_up,
            "max_concurrent_sessions": settings.max_concurrent_sessions,
            "idle_timeout": settings.idle_timeout,
            "daily_data_limit": settings.daily_data_limit,
            "monthly_data_limit": settings.monthly_data_limit,
            "allow_multiple_devices": settings.allow_multiple_devices,
            "timeout_options": [
                {"value": 1800, "label": "30 minutes"},
                {"value": 3600, "label": "1 hour"},
                {"value": 7200, "label": "2 hours"},
                {"value": 14400, "label": "4 hours"},
                {"value": 28800, "label": "8 hours"},
                {"value": 43200, "label": "12 hours"},
                {"value": 86400, "label": "24 hours"}
            ],
            "bandwidth_options": [
                {"value": 0, "label": "Unlimited"},
                {"value": 512, "label": "512 Kbps"},
                {"value": 1024, "label": "1 Mbps"},
                {"value": 2048, "label": "2 Mbps"},
                {"value": 5120, "label": "5 Mbps"},
                {"value": 10240, "label": "10 Mbps"}
            ]
        }
    }


@router.put("/settings")
async def update_radius_settings(
    settings_data: dict,
    current_user: Admin = Depends(require_session_permission),
    db: Session = Depends(get_db)
):
    """Update RADIUS settings"""
    from ..models.radius_settings import RadiusSettings
    from sqlalchemy import text
    
    # Only superadmin can change global settings
    if current_user.role != "superadmin":
        raise HTTPException(status_code=403, detail="Only superadmin can change global settings")
    
    # Get or create settings
    settings = db.query(RadiusSettings).first()
    
    if not settings:
        settings = RadiusSettings()
        db.add(settings)
    
    # Update fields
    if 'default_session_timeout' in settings_data:
        settings.default_session_timeout = settings_data['default_session_timeout']
    if 'max_session_timeout' in settings_data:
        settings.max_session_timeout = settings_data['max_session_timeout']
    if 'default_bandwidth_down' in settings_data:
        settings.default_bandwidth_down = settings_data['default_bandwidth_down']
    if 'default_bandwidth_up' in settings_data:
        settings.default_bandwidth_up = settings_data['default_bandwidth_up']
    if 'max_concurrent_sessions' in settings_data:
        settings.max_concurrent_sessions = settings_data['max_concurrent_sessions']
    if 'idle_timeout' in settings_data:
        settings.idle_timeout = settings_data['idle_timeout']
    if 'daily_data_limit' in settings_data:
        settings.daily_data_limit = settings_data['daily_data_limit']
    if 'monthly_data_limit' in settings_data:
        settings.monthly_data_limit = settings_data['monthly_data_limit']
    if 'allow_multiple_devices' in settings_data:
        settings.allow_multiple_devices = settings_data['allow_multiple_devices']
    
    db.commit()
    
    # Apply to all existing users if requested
    if settings_data.get('apply_to_all', False):
        db.execute(
            text("""
                UPDATE radreply 
                SET value = :timeout 
                WHERE attribute = 'Session-Timeout'
            """),
            {"timeout": str(settings.default_session_timeout)}
        )
        
        if settings.default_bandwidth_down > 0:
            db.execute(
                text("""
                    UPDATE radreply 
                    SET value = :bandwidth 
                    WHERE attribute = 'WISPr-Bandwidth-Max-Down'
                """),
                {"bandwidth": str(settings.default_bandwidth_down * 1000)}
            )
        
        db.commit()
    
    return {
        "success": True,
        "message": "RADIUS settings updated",
        "settings": {
            "default_session_timeout": settings.default_session_timeout,
            "default_bandwidth_down": settings.default_bandwidth_down,
            "default_bandwidth_up": settings.default_bandwidth_up
        }
    }


@router.patch("/users/{username}/bandwidth")
async def update_user_bandwidth(
    username: str,
    bandwidth: int,
    current_user: Admin = Depends(require_session_permission)
):
    """Update bandwidth limit for a specific user (in kbps)"""
    from ..database import SessionLocal
    from sqlalchemy import text
    
    if bandwidth < 0:
        raise HTTPException(status_code=400, detail="Bandwidth must be non-negative")
    
    db = SessionLocal()
    try:
        # Check if bandwidth attribute exists for user
        exists = db.execute(
            text("""
                SELECT id FROM radreply 
                WHERE username = :username AND attribute = 'WISPr-Bandwidth-Max-Down'
            """),
            {"username": username}
        ).fetchone()
        
        if bandwidth == 0:
            # Remove bandwidth limit (unlimited)
            db.execute(
                text("""
                    DELETE FROM radreply 
                    WHERE username = :username AND attribute = 'WISPr-Bandwidth-Max-Down'
                """),
                {"username": username}
            )
            db.execute(
                text("""
                    DELETE FROM radreply 
                    WHERE username = :username AND attribute = 'WISPr-Bandwidth-Max-Up'
                """),
                {"username": username}
            )
        elif exists:
            # Update existing
            db.execute(
                text("""
                    UPDATE radreply 
                    SET value = :bandwidth 
                    WHERE username = :username AND attribute = 'WISPr-Bandwidth-Max-Down'
                """),
                {"username": username, "bandwidth": str(bandwidth * 1000)}
            )
        else:
            # Insert new
            db.execute(
                text("""
                    INSERT INTO radreply (username, attribute, op, value)
                    VALUES (:username, 'WISPr-Bandwidth-Max-Down', ':=', :bandwidth)
                """),
                {"username": username, "bandwidth": str(bandwidth * 1000)}
            )
        
        db.commit()
        
        return {
            "success": True,
            "message": f"Bandwidth {'removed' if bandwidth == 0 else f'set to {bandwidth} kbps'} for {username}"
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()
