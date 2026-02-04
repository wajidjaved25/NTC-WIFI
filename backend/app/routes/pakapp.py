from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from sqlalchemy import or_, desc
from typing import Optional

from ..database import get_db
from ..models.pakapp_user import PakAppUser
from ..schemas.pakapp import (
    PakAppUserCreate,
    PakAppUserResponse,
    PakAppUserUpdate,
    PakAppUserListResponse
)
from ..utils.security import get_current_user
from ..utils.pakapp_security import require_pakapp_auth
from ..models.admin import Admin
from ..limiter import limiter

router = APIRouter(prefix="/pakapp", tags=["PakApp Users"])


# Secured endpoint for PakApp to register users
@router.post("/register", response_model=PakAppUserResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")  # Rate limit to prevent abuse
async def register_pakapp_user(
    request: Request,
    user_data: PakAppUserCreate,
    db: Session = Depends(get_db),
    _auth: bool = Depends(require_pakapp_auth)  # Security check
):
    """
    Register a new user from PakApp.
    This endpoint receives user information from PakApp and saves it to the database.
    
    Security:
    - Requires X-API-Key header (if PAKAPP_ENABLE_API_KEY=true)
    - IP whitelist check (if PAKAPP_ALLOWED_IPS is set)
    - HMAC signature verification (if PAKAPP_ENABLE_SIGNATURE=true)
    - Rate limited to 10 requests per minute
    """
    # Check if user with this CNIC already exists
    existing_user = db.query(PakAppUser).filter(PakAppUser.cnic == user_data.cnic).first()
    
    if existing_user:
        # Update existing user
        existing_user.name = user_data.name
        existing_user.phone = user_data.phone
        existing_user.email = user_data.email
        existing_user.is_active = True
        existing_user.ip_address = request.client.host
        
        db.commit()
        db.refresh(existing_user)
        
        return existing_user
    
    # Create new user
    new_user = PakAppUser(
        name=user_data.name,
        cnic=user_data.cnic,
        phone=user_data.phone,
        email=user_data.email,
        source='pakapp',
        ip_address=request.client.host
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return new_user


# Get user by CNIC (Protected - admin only)
@router.get("/users/cnic/{cnic}", response_model=PakAppUserResponse)
async def get_user_by_cnic(
    cnic: str,
    current_user: Admin = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get PakApp user by CNIC"""
    # Clean CNIC
    cnic_clean = cnic.replace('-', '').replace(' ', '')
    
    user = db.query(PakAppUser).filter(PakAppUser.cnic == cnic_clean).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return user


# Get user by Phone (Protected - admin only)
@router.get("/users/phone/{phone}", response_model=PakAppUserResponse)
async def get_user_by_phone(
    phone: str,
    current_user: Admin = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get PakApp user by phone number"""
    # Clean phone
    phone_clean = phone.replace(' ', '').replace('-', '').replace('+', '')
    
    # Try to find with 92 prefix or 03 prefix
    user = db.query(PakAppUser).filter(
        or_(
            PakAppUser.phone == phone_clean,
            PakAppUser.phone == '92' + phone_clean.lstrip('0'),
            PakAppUser.phone == phone_clean.lstrip('92')
        )
    ).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return user


# List all users (Protected - admin only)
@router.get("/users", response_model=PakAppUserListResponse)
async def list_pakapp_users(
    page: int = 1,
    per_page: int = 50,
    search: Optional[str] = None,
    is_active: Optional[bool] = None,
    current_user: Admin = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List all PakApp users with pagination and optional filters.
    Admin access required.
    """
    # Base query
    query = db.query(PakAppUser)
    
    # Apply filters
    if is_active is not None:
        query = query.filter(PakAppUser.is_active == is_active)
    
    # Apply search
    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            or_(
                PakAppUser.name.ilike(search_pattern),
                PakAppUser.cnic.ilike(search_pattern),
                PakAppUser.phone.ilike(search_pattern),
                PakAppUser.email.ilike(search_pattern)
            )
        )
    
    # Get total count
    total = query.count()
    
    # Apply pagination
    offset = (page - 1) * per_page
    users = query.order_by(desc(PakAppUser.created_at)).offset(offset).limit(per_page).all()
    
    return {
        "total": total,
        "page": page,
        "per_page": per_page,
        "users": users
    }


# Update user (Protected - admin only)
@router.patch("/users/{user_id}", response_model=PakAppUserResponse)
async def update_pakapp_user(
    user_id: int,
    user_data: PakAppUserUpdate,
    current_user: Admin = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update PakApp user information. Admin access required."""
    user = db.query(PakAppUser).filter(PakAppUser.id == user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Update fields if provided
    if user_data.name is not None:
        user.name = user_data.name
    if user_data.phone is not None:
        user.phone = user_data.phone
    if user_data.email is not None:
        user.email = user_data.email
    if user_data.is_active is not None:
        user.is_active = user_data.is_active
    
    db.commit()
    db.refresh(user)
    
    return user


# Delete user (Protected - superadmin only)
@router.delete("/users/{user_id}")
async def delete_pakapp_user(
    user_id: int,
    current_user: Admin = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete PakApp user. Superadmin access required."""
    if current_user.role != "superadmin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only superadmin can delete users"
        )
    
    user = db.query(PakAppUser).filter(PakAppUser.id == user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    db.delete(user)
    db.commit()
    
    return {
        "success": True,
        "message": "User deleted successfully"
    }


# Get statistics (Protected - admin only)
@router.get("/stats")
async def get_pakapp_stats(
    current_user: Admin = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get statistics about PakApp users"""
    total_users = db.query(PakAppUser).count()
    active_users = db.query(PakAppUser).filter(PakAppUser.is_active == True).count()
    inactive_users = db.query(PakAppUser).filter(PakAppUser.is_active == False).count()
    
    # Get recent registrations (last 7 days)
    from datetime import datetime, timedelta
    seven_days_ago = datetime.now() - timedelta(days=7)
    recent_registrations = db.query(PakAppUser).filter(
        PakAppUser.created_at >= seven_days_ago
    ).count()
    
    return {
        "total_users": total_users,
        "active_users": active_users,
        "inactive_users": inactive_users,
        "recent_registrations_7days": recent_registrations
    }


# Bulk import endpoint (Protected - superadmin only)
@router.post("/bulk-import")
async def bulk_import_users(
    users: list[PakAppUserCreate],
    current_user: Admin = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Bulk import users from PakApp.
    Superadmin access required.
    """
    if current_user.role != "superadmin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only superadmin can bulk import users"
        )
    
    created_count = 0
    updated_count = 0
    errors = []
    
    for user_data in users:
        try:
            # Check if user exists
            existing_user = db.query(PakAppUser).filter(
                PakAppUser.cnic == user_data.cnic
            ).first()
            
            if existing_user:
                # Update
                existing_user.name = user_data.name
                existing_user.phone = user_data.phone
                existing_user.email = user_data.email
                existing_user.is_active = True
                updated_count += 1
            else:
                # Create
                new_user = PakAppUser(
                    name=user_data.name,
                    cnic=user_data.cnic,
                    phone=user_data.phone,
                    email=user_data.email,
                    source='pakapp'
                )
                db.add(new_user)
                created_count += 1
        
        except Exception as e:
            errors.append({
                "cnic": user_data.cnic,
                "error": str(e)
            })
    
    db.commit()
    
    return {
        "success": True,
        "created": created_count,
        "updated": updated_count,
        "errors": errors,
        "total_processed": len(users)
    }
