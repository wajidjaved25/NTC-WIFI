from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
from typing import Optional
import random
import requests

from ..database import get_db
from ..models.admin import Admin
from ..models.otp import OTP
from ..schemas.auth import TokenResponse, OTPRequest, OTPVerify, AdminCreate
from ..utils.security import verify_password, get_password_hash, create_access_token, get_current_user
from ..utils.helpers import send_otp_sms

router = APIRouter(prefix="/auth", tags=["Authentication"])

# Admin Login with Password (for superadmin and admin roles)
@router.post("/login", response_model=TokenResponse)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    # Find admin by username
    admin = db.query(Admin).filter(Admin.username == form_data.username).first()
    
    if not admin:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password"
        )
    
    # Check if account is locked
    if admin.locked_until and admin.locked_until > datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail=f"Account locked until {admin.locked_until}"
        )
    
    # Check if account is active
    if not admin.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated"
        )
    
    # Check if user requires OTP (shouldn't use this endpoint)
    if admin.requires_otp:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please use OTP login endpoint"
        )
    
    # Verify password
    if not verify_password(form_data.password, admin.password_hash):
        # Increment login attempts
        admin.login_attempts += 1
        if admin.login_attempts >= 5:
            admin.locked_until = datetime.now(timezone.utc) + timedelta(minutes=30)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password"
        )
    
    # Reset login attempts on successful login
    admin.login_attempts = 0
    admin.last_login = datetime.now(timezone.utc)
    admin.locked_until = None
    db.commit()
    
    # Create access token
    access_token = create_access_token(data={"sub": admin.username, "role": admin.role})
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "role": admin.role,
        "username": admin.username,
        "full_name": admin.full_name
    }


# Request OTP for reports_user or ads_user
@router.post("/request-otp")
async def request_otp(request: OTPRequest, db: Session = Depends(get_db)):
    # Find admin by mobile
    admin = db.query(Admin).filter(Admin.mobile == request.mobile).first()
    
    if not admin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mobile number not registered"
        )
    
    if not admin.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated"
        )
    
    if not admin.requires_otp:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This account uses password authentication"
        )
    
    # Generate 6-digit OTP
    otp_code = str(random.randint(100000, 999999))
    
    # Save OTP to database
    otp_entry = OTP(
        mobile=request.mobile,
        otp=otp_code,
        otp_type="admin_login",
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
        ip_address=request.ip_address
    )
    db.add(otp_entry)
    db.commit()
    
    # Send OTP via SMS
    try:
        sms_result = await send_otp_sms(request.mobile, otp_code)
        return {
            "success": True,
            "message": "OTP sent successfully",
            "expires_in": 300  # 5 minutes
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send OTP: {str(e)}"
        )


# Verify OTP and Login
@router.post("/verify-otp", response_model=TokenResponse)
async def verify_otp(request: OTPVerify, db: Session = Depends(get_db)):
    # Find valid OTP
    otp_entry = db.query(OTP).filter(
        OTP.mobile == request.mobile,
        OTP.otp == request.otp,
        OTP.otp_type == "admin_login",
        OTP.verified == False,
        OTP.expires_at > datetime.now(timezone.utc)
    ).first()
    
    if not otp_entry:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired OTP"
        )
    
    # Check attempts
    if otp_entry.attempts >= 3:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many attempts. Please request a new OTP"
        )
    
    # Mark OTP as verified
    otp_entry.verified = True
    
    # Find admin
    admin = db.query(Admin).filter(Admin.mobile == request.mobile).first()
    admin.last_login = datetime.now(timezone.utc)
    
    db.commit()
    
    # Create access token
    access_token = create_access_token(data={"sub": admin.username, "role": admin.role})
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "role": admin.role,
        "username": admin.username,
        "full_name": admin.full_name
    }


# Create Admin (superadmin only)
@router.post("/create-admin")
async def create_admin(
    admin_data: AdminCreate,
    current_user: Admin = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Only superadmin can create admins
    if current_user.role != "superadmin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only superadmin can create admins"
        )
    
    # Check if username already exists
    if db.query(Admin).filter(Admin.username == admin_data.username).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already exists"
        )
    
    # Check if mobile already exists (if provided)
    if admin_data.mobile and db.query(Admin).filter(Admin.mobile == admin_data.mobile).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mobile number already registered"
        )
    
    # Validate role-specific requirements
    if admin_data.role in ["reports_user", "ads_user"]:
        if not admin_data.mobile:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Mobile number required for OTP-based roles"
            )
        requires_otp = True
        password_hash = None
    else:
        if not admin_data.password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password required for admin roles"
            )
        requires_otp = False
        password_hash = get_password_hash(admin_data.password)
    
    # Create new admin
    new_admin = Admin(
        username=admin_data.username,
        password_hash=password_hash,
        role=admin_data.role,
        mobile=admin_data.mobile,
        full_name=admin_data.full_name,
        email=admin_data.email,
        requires_otp=requires_otp,
        created_by=current_user.id
    )
    
    db.add(new_admin)
    db.commit()
    db.refresh(new_admin)
    
    return {
        "success": True,
        "message": "Admin created successfully",
        "admin": {
            "id": new_admin.id,
            "username": new_admin.username,
            "role": new_admin.role,
            "full_name": new_admin.full_name
        }
    }


# Get current user info
@router.get("/me")
async def get_me(current_user: Admin = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "username": current_user.username,
        "role": current_user.role,
        "full_name": current_user.full_name,
        "email": current_user.email,
        "mobile": current_user.mobile,
        "requires_otp": current_user.requires_otp,
        "last_login": current_user.last_login
    }


# List all admins (superadmin only)
@router.get("/admins")
async def list_admins(
    current_user: Admin = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role != "superadmin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only superadmin can view all admins"
        )
    
    admins = db.query(Admin).filter(Admin.role != "superadmin").all()
    
    return {
        "admins": [
            {
                "id": admin.id,
                "username": admin.username,
                "role": admin.role,
                "full_name": admin.full_name,
                "email": admin.email,
                "mobile": admin.mobile,
                "is_active": admin.is_active,
                "last_login": admin.last_login,
                "created_at": admin.created_at
            }
            for admin in admins
        ]
    }


# Deactivate admin (superadmin only)
@router.patch("/admins/{admin_id}/deactivate")
async def deactivate_admin(
    admin_id: int,
    current_user: Admin = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role != "superadmin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only superadmin can deactivate admins"
        )
    
    admin = db.query(Admin).filter(Admin.id == admin_id).first()
    if not admin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Admin not found"
        )
    
    if admin.role == "superadmin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot deactivate superadmin"
        )
    
    admin.is_active = False
    db.commit()
    
    return {"success": True, "message": "Admin deactivated successfully"}


# Activate admin (superadmin only)
@router.patch("/admins/{admin_id}/activate")
async def activate_admin(
    admin_id: int,
    current_user: Admin = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role != "superadmin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only superadmin can activate admins"
        )
    
    admin = db.query(Admin).filter(Admin.id == admin_id).first()
    if not admin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Admin not found"
        )
    
    if admin.role == "superadmin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot modify superadmin status"
        )
    
    admin.is_active = True
    db.commit()
    
    return {"success": True, "message": "Admin activated successfully"}
