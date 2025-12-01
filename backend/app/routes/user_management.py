from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from typing import List, Optional
from datetime import datetime

from ..database import get_db
from ..models.admin import Admin
from ..models.user import User
from ..models.session import Session as WiFiSession
from ..utils.security import get_current_user
from pydantic import BaseModel, Field

router = APIRouter(prefix="/user-management", tags=["WiFi User Management"])


# Pydantic models
class UserCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    mobile: str = Field(..., min_length=10, max_length=20)
    email: Optional[str] = None
    id_type: Optional[str] = Field(None, description="'cnic' or 'passport'")
    cnic: Optional[str] = Field(None, max_length=15)
    passport: Optional[str] = Field(None, max_length=50)


class UserUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=255)
    email: Optional[str] = None
    id_type: Optional[str] = None
    cnic: Optional[str] = None
    passport: Optional[str] = None


class UserResponse(BaseModel):
    id: int
    name: str
    mobile: str
    email: Optional[str]
    id_type: Optional[str]
    cnic: Optional[str]
    passport: Optional[str]
    is_blocked: bool
    block_reason: Optional[str]
    created_at: datetime
    last_login: Optional[datetime]
    total_sessions: int
    total_data_usage: int
    
    class Config:
        from_attributes = True


class UserListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    users: List[UserResponse]


# Middleware - Only admin and superadmin can manage WiFi users
def require_user_management_permission(current_user: Admin = Depends(get_current_user)):
    if current_user.role not in ['admin', 'superadmin']:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to manage WiFi users"
        )
    return current_user


@router.get("/users", response_model=UserListResponse)
async def list_users(
    page: int = 1,
    page_size: int = 20,
    search: Optional[str] = None,
    is_blocked: Optional[bool] = None,
    current_user: Admin = Depends(require_user_management_permission),
    db: Session = Depends(get_db)
):
    """Get list of WiFi portal users with pagination and filters"""
    
    query = db.query(User)
    
    # Apply filters
    if search:
        query = query.filter(
            or_(
                User.name.ilike(f"%{search}%"),
                User.mobile.ilike(f"%{search}%"),
                User.cnic.ilike(f"%{search}%"),
                User.passport.ilike(f"%{search}%"),
                User.email.ilike(f"%{search}%")
            )
        )
    
    if is_blocked is not None:
        query = query.filter(User.is_blocked == is_blocked)
    
    # Count total
    total = query.count()
    
    # Apply pagination
    users = query.order_by(User.created_at.desc())\
        .offset((page - 1) * page_size)\
        .limit(page_size)\
        .all()
    
    return UserListResponse(
        total=total,
        page=page,
        page_size=page_size,
        users=users
    )


@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    current_user: Admin = Depends(require_user_management_permission),
    db: Session = Depends(get_db)
):
    """Get single WiFi user details"""
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return user


@router.post("/users", response_model=UserResponse)
async def create_user(
    user_data: UserCreate,
    current_user: Admin = Depends(require_user_management_permission),
    db: Session = Depends(get_db)
):
    """Create a new WiFi portal user"""
    
    # Check if mobile already exists
    existing_user = db.query(User).filter(User.mobile == user_data.mobile).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this mobile number already exists"
        )
    
    # Validate ID type
    if user_data.id_type:
        if user_data.id_type not in ['cnic', 'passport']:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="id_type must be 'cnic' or 'passport'"
            )
        
        # Check if required ID field is provided
        if user_data.id_type == 'cnic' and not user_data.cnic:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="CNIC number is required when id_type is 'cnic'"
            )
        
        if user_data.id_type == 'passport' and not user_data.passport:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Passport number is required when id_type is 'passport'"
            )
    
    # Create user
    new_user = User(
        name=user_data.name,
        mobile=user_data.mobile,
        email=user_data.email,
        id_type=user_data.id_type,
        cnic=user_data.cnic,
        passport=user_data.passport,
        terms_accepted=True,
        terms_accepted_at=datetime.now()
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return new_user


@router.put("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user_data: UserUpdate,
    current_user: Admin = Depends(require_user_management_permission),
    db: Session = Depends(get_db)
):
    """Update WiFi user information"""
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Update fields if provided
    if user_data.name is not None:
        user.name = user_data.name
    
    if user_data.email is not None:
        user.email = user_data.email
    
    if user_data.id_type is not None:
        if user_data.id_type not in ['cnic', 'passport', None]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="id_type must be 'cnic' or 'passport'"
            )
        user.id_type = user_data.id_type
    
    if user_data.cnic is not None:
        user.cnic = user_data.cnic
    
    if user_data.passport is not None:
        user.passport = user_data.passport
    
    db.commit()
    db.refresh(user)
    
    return user


@router.post("/users/{user_id}/block")
async def block_user(
    user_id: int,
    reason: str,
    current_user: Admin = Depends(require_user_management_permission),
    db: Session = Depends(get_db)
):
    """Block a WiFi user from accessing WiFi"""
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    if user.is_blocked:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is already blocked"
        )
    
    user.is_blocked = True
    user.block_reason = reason
    
    db.commit()
    
    return {
        "message": "User blocked successfully",
        "user_id": user_id,
        "blocked_by": current_user.username
    }


@router.post("/users/{user_id}/unblock")
async def unblock_user(
    user_id: int,
    current_user: Admin = Depends(require_user_management_permission),
    db: Session = Depends(get_db)
):
    """Unblock a WiFi user"""
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    if not user.is_blocked:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not blocked"
        )
    
    user.is_blocked = False
    user.block_reason = None
    
    db.commit()
    
    return {
        "message": "User unblocked successfully",
        "user_id": user_id,
        "unblocked_by": current_user.username
    }


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    current_user: Admin = Depends(require_user_management_permission),
    db: Session = Depends(get_db)
):
    """Delete a WiFi user (only if no sessions exist)"""
    
    # Only superadmin can delete
    if current_user.role != 'superadmin':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only superadmin can delete users. Use block/unblock instead."
        )
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Check if user has sessions
    session_count = db.query(func.count(WiFiSession.id))\
        .filter(WiFiSession.user_id == user_id)\
        .scalar()
    
    if session_count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete user with {session_count} sessions. Block user instead."
        )
    
    db.delete(user)
    db.commit()
    
    return {
        "message": "User deleted successfully",
        "user_id": user_id,
        "deleted_by": current_user.username
    }


@router.get("/users/{user_id}/sessions")
async def get_user_sessions(
    user_id: int,
    page: int = 1,
    page_size: int = 20,
    current_user: Admin = Depends(require_user_management_permission),
    db: Session = Depends(get_db)
):
    """Get WiFi user's session history"""
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Get sessions with pagination
    sessions_query = db.query(WiFiSession).filter(
        WiFiSession.user_id == user_id
    ).order_by(WiFiSession.start_time.desc())
    
    total = sessions_query.count()
    sessions = sessions_query.offset((page - 1) * page_size).limit(page_size).all()
    
    return {
        "user": {
            "id": user.id,
            "name": user.name,
            "mobile": user.mobile,
            "total_sessions": user.total_sessions,
            "total_data_usage": user.total_data_usage,
            "is_blocked": user.is_blocked
        },
        "sessions": {
            "total": total,
            "page": page,
            "page_size": page_size,
            "items": [
                {
                    "id": s.id,
                    "start_time": s.start_time,
                    "end_time": s.end_time,
                    "duration": s.duration,
                    "total_data": s.total_data,
                    "ip_address": s.ip_address,
                    "mac_address": s.mac_address,
                    "ap_name": s.ap_name,
                    "status": s.session_status,
                    "disconnect_reason": s.disconnect_reason
                }
                for s in sessions
            ]
        }
    }


@router.get("/stats")
async def get_user_stats(
    current_user: Admin = Depends(require_user_management_permission),
    db: Session = Depends(get_db)
):
    """Get WiFi user statistics"""
    
    total_users = db.query(func.count(User.id)).scalar()
    blocked_users = db.query(func.count(User.id)).filter(User.is_blocked == True).scalar()
    active_users = total_users - blocked_users
    
    # Users with sessions today
    today = datetime.now().date()
    today_start = datetime.combine(today, datetime.min.time())
    users_today = db.query(func.count(func.distinct(WiFiSession.user_id))).filter(
        WiFiSession.start_time >= today_start
    ).scalar()
    
    return {
        "total_users": total_users,
        "active_users": active_users,
        "blocked_users": blocked_users,
        "users_today": users_today
    }
