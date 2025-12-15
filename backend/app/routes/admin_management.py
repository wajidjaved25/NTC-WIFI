from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from typing import List, Optional
from datetime import datetime
from passlib.context import CryptContext

from ..database import get_db
from ..models.admin import Admin
from ..utils.security import get_current_user, has_permission
from pydantic import BaseModel, Field

router = APIRouter(prefix="/admin-management", tags=["Admin Management"])

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# Pydantic models
class AdminCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=100)
    email: str
    password: str = Field(..., min_length=6)
    full_name: str
    role: str = Field(..., description="'admin' or 'ipdr_viewer'")
    can_manage_portal: bool = False
    can_manage_sessions: bool = False
    can_view_records: bool = True
    can_view_ipdr: bool = True
    can_manage_radius: bool = False


class AdminUpdate(BaseModel):
    email: Optional[str] = None
    full_name: Optional[str] = None
    can_manage_portal: Optional[bool] = None
    can_manage_sessions: Optional[bool] = None
    can_view_records: Optional[bool] = None
    can_view_ipdr: Optional[bool] = None
    can_manage_radius: Optional[bool] = None


class AdminPasswordUpdate(BaseModel):
    new_password: str = Field(..., min_length=6)


class AdminResponse(BaseModel):
    id: int
    username: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    role: str
    is_active: bool
    can_manage_portal: bool
    can_manage_sessions: bool
    can_view_records: bool
    can_view_ipdr: bool
    can_manage_radius: bool
    created_at: datetime
    last_login: Optional[datetime]
    
    class Config:
        from_attributes = True


class AdminListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    admins: List[AdminResponse]


# Middleware - Admin or Superadmin can manage admins
def require_admin_or_superadmin(current_user: Admin = Depends(get_current_user)):
    if current_user.role not in ['superadmin', 'admin']:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only superadmin or admin can manage admin accounts"
        )
    return current_user


@router.get("/admins", response_model=AdminListResponse)
async def list_admins(
    page: int = 1,
    page_size: int = 20,
    search: Optional[str] = None,
    role: Optional[str] = None,
    is_active: Optional[bool] = None,
    current_user: Admin = Depends(require_admin_or_superadmin),
    db: Session = Depends(get_db)
):
    """Get list of admin users"""
    
    query = db.query(Admin)
    
    # Apply filters
    if search:
        query = query.filter(
            or_(
                Admin.username.ilike(f"%{search}%"),
                Admin.email.ilike(f"%{search}%"),
                Admin.full_name.ilike(f"%{search}%")
            )
        )
    
    if role:
        query = query.filter(Admin.role == role)
    
    if is_active is not None:
        query = query.filter(Admin.is_active == is_active)
    
    # Count total
    total = query.count()
    
    # Apply pagination
    admins = query.order_by(Admin.created_at.desc())\
        .offset((page - 1) * page_size)\
        .limit(page_size)\
        .all()
    
    return AdminListResponse(
        total=total,
        page=page,
        page_size=page_size,
        admins=admins
    )


@router.get("/admins/{admin_id}", response_model=AdminResponse)
async def get_admin(
    admin_id: int,
    current_user: Admin = Depends(require_admin_or_superadmin),
    db: Session = Depends(get_db)
):
    """Get single admin details"""
    
    admin = db.query(Admin).filter(Admin.id == admin_id).first()
    if not admin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Admin not found"
        )
    
    return admin


@router.post("/admins", response_model=AdminResponse)
async def create_admin(
    admin_data: AdminCreate,
    current_user: Admin = Depends(require_admin_or_superadmin),
    db: Session = Depends(get_db)
):
    """Create a new admin user"""
    
    # Regular admin can only create IPDR viewers, not other admins
    if current_user.role == 'admin' and admin_data.role != 'ipdr_viewer':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin users can only create IPDR viewer accounts"
        )
    
    # Check if username already exists
    existing_admin = db.query(Admin).filter(Admin.username == admin_data.username).first()
    if existing_admin:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already exists"
        )
    
    # Check if email already exists
    existing_email = db.query(Admin).filter(Admin.email == admin_data.email).first()
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already exists"
        )
    
    # Validate role
    if admin_data.role not in ['admin', 'ipdr_viewer']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Role must be 'admin' or 'ipdr_viewer'"
        )
    
    # If creating IPDR viewer, set appropriate permissions
    if admin_data.role == 'ipdr_viewer':
        admin_data.can_manage_portal = False
        admin_data.can_manage_sessions = False
        admin_data.can_view_records = True
        admin_data.can_view_ipdr = True
        admin_data.can_manage_radius = False
    
    # Hash password
    hashed_password = pwd_context.hash(admin_data.password)
    
    # Create admin
    new_admin = Admin(
        username=admin_data.username,
        email=admin_data.email,
        password_hash=hashed_password,
        full_name=admin_data.full_name,
        role=admin_data.role,
        can_manage_portal=admin_data.can_manage_portal,
        can_manage_sessions=admin_data.can_manage_sessions,
        can_view_records=admin_data.can_view_records,
        can_view_ipdr=admin_data.can_view_ipdr,
        can_manage_radius=admin_data.can_manage_radius,
        is_active=True
    )
    
    db.add(new_admin)
    db.commit()
    db.refresh(new_admin)
    
    return new_admin


@router.put("/admins/{admin_id}", response_model=AdminResponse)
async def update_admin(
    admin_id: int,
    admin_data: AdminUpdate,
    current_user: Admin = Depends(require_admin_or_superadmin),
    db: Session = Depends(get_db)
):
    """Update admin information"""
    
    admin = db.query(Admin).filter(Admin.id == admin_id).first()
    if not admin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Admin not found"
        )
    
    # Cannot modify superadmin
    if admin.role == 'superadmin':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot modify superadmin account"
        )
    
    # Regular admin cannot modify other admin accounts, only IPDR viewers
    if current_user.role == 'admin' and admin.role != 'ipdr_viewer':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin users can only modify IPDR viewer accounts"
        )
    
    # Update fields if provided
    if admin_data.email is not None:
        # Check if new email already exists
        existing = db.query(Admin).filter(
            Admin.email == admin_data.email,
            Admin.id != admin_id
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already exists"
            )
        admin.email = admin_data.email
    
    if admin_data.full_name is not None:
        admin.full_name = admin_data.full_name
    
    if admin_data.can_manage_portal is not None:
        admin.can_manage_portal = admin_data.can_manage_portal
    
    if admin_data.can_manage_sessions is not None:
        admin.can_manage_sessions = admin_data.can_manage_sessions
    
    if admin_data.can_view_records is not None:
        admin.can_view_records = admin_data.can_view_records
    
    if admin_data.can_view_ipdr is not None:
        admin.can_view_ipdr = admin_data.can_view_ipdr
    
    if admin_data.can_manage_radius is not None:
        admin.can_manage_radius = admin_data.can_manage_radius
    
    db.commit()
    db.refresh(admin)
    
    return admin


@router.put("/admins/{admin_id}/password")
async def update_admin_password(
    admin_id: int,
    password_data: AdminPasswordUpdate,
    current_user: Admin = Depends(require_admin_or_superadmin),
    db: Session = Depends(get_db)
):
    """Update admin password"""
    
    admin = db.query(Admin).filter(Admin.id == admin_id).first()
    if not admin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Admin not found"
        )
    
    # Cannot modify superadmin password unless you are that superadmin
    if admin.role == 'superadmin' and admin.id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot modify another superadmin's password"
        )
    
    # Regular admin cannot modify other admin accounts, only IPDR viewers
    if current_user.role == 'admin' and admin.role != 'ipdr_viewer':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin users can only modify IPDR viewer accounts"
        )
    
    # Hash new password
    admin.password_hash = pwd_context.hash(password_data.new_password)
    
    db.commit()
    
    return {
        "message": "Password updated successfully",
        "admin_id": admin_id
    }


@router.post("/admins/{admin_id}/activate")
async def activate_admin(
    admin_id: int,
    current_user: Admin = Depends(require_admin_or_superadmin),
    db: Session = Depends(get_db)
):
    """Activate an admin account"""
    
    admin = db.query(Admin).filter(Admin.id == admin_id).first()
    if not admin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Admin not found"
        )
    
    if admin.role == 'superadmin':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot deactivate superadmin"
        )
    
    # Regular admin cannot modify other admin accounts, only IPDR viewers
    if current_user.role == 'admin' and admin.role != 'ipdr_viewer':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin users can only modify IPDR viewer accounts"
        )
    
    if admin.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Admin is already active"
        )
    
    admin.is_active = True
    db.commit()
    
    return {
        "message": "Admin activated successfully",
        "admin_id": admin_id
    }


@router.post("/admins/{admin_id}/deactivate")
async def deactivate_admin(
    admin_id: int,
    current_user: Admin = Depends(require_admin_or_superadmin),
    db: Session = Depends(get_db)
):
    """Deactivate an admin account"""
    
    admin = db.query(Admin).filter(Admin.id == admin_id).first()
    if not admin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Admin not found"
        )
    
    if admin.role == 'superadmin':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot deactivate superadmin"
        )
    
    # Regular admin cannot modify other admin accounts, only IPDR viewers
    if current_user.role == 'admin' and admin.role != 'ipdr_viewer':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin users can only modify IPDR viewer accounts"
        )
    
    if not admin.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Admin is already deactivated"
        )
    
    admin.is_active = False
    db.commit()
    
    return {
        "message": "Admin deactivated successfully",
        "admin_id": admin_id
    }


@router.delete("/admins/{admin_id}")
async def delete_admin(
    admin_id: int,
    current_user: Admin = Depends(require_admin_or_superadmin),
    db: Session = Depends(get_db)
):
    """Delete an admin account"""
    
    admin = db.query(Admin).filter(Admin.id == admin_id).first()
    if not admin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Admin not found"
        )
    
    # Cannot delete superadmin
    if admin.role == 'superadmin':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot delete superadmin account"
        )
    
    # Regular admin cannot delete other admin accounts, only IPDR viewers
    if current_user.role == 'admin' and admin.role != 'ipdr_viewer':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin users can only delete IPDR viewer accounts"
        )
    
    # Cannot delete self
    if admin.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account"
        )
    
    db.delete(admin)
    db.commit()
    
    return {
        "message": "Admin deleted successfully",
        "admin_id": admin_id
    }


@router.get("/roles")
async def get_roles(
    current_user: Admin = Depends(require_admin_or_superadmin)
):
    """Get available admin roles and their permissions"""
    
    # Superadmin can see all roles
    if current_user.role == 'superadmin':
        return {
            "roles": [
                {
                    "value": "admin",
                    "label": "Administrator",
                    "description": "Full system access including user management, portal settings, and IPDR",
                    "default_permissions": {
                        "can_manage_portal": True,
                        "can_manage_sessions": True,
                        "can_view_records": True,
                        "can_view_ipdr": True,
                        "can_manage_radius": True
                    }
                },
                {
                    "value": "ipdr_viewer",
                    "label": "IPDR Viewer",
                    "description": "Limited access to view IPDR reports only",
                    "default_permissions": {
                        "can_manage_portal": False,
                        "can_manage_sessions": False,
                        "can_view_records": True,
                        "can_view_ipdr": True,
                        "can_manage_radius": False
                    }
                }
            ]
        }
    
    # Regular admin can only see IPDR viewer role
    return {
        "roles": [
            {
                "value": "ipdr_viewer",
                "label": "IPDR Viewer",
                "description": "Limited access to view IPDR reports only",
                "default_permissions": {
                    "can_manage_portal": False,
                    "can_manage_sessions": False,
                    "can_view_records": True,
                    "can_view_ipdr": True,
                    "can_manage_radius": False
                }
            }
        ]
    }
