from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, CheckConstraint
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from ..database import Base

class Admin(Base):
    __tablename__ = "admins"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=True)  # NULL for OTP-only users
    role = Column(String(50), nullable=False)
    mobile = Column(String(20), index=True)
    full_name = Column(String(255))
    email = Column(String(255))
    is_active = Column(Boolean, default=True)
    requires_otp = Column(Boolean, default=False)
    created_by = Column(Integer, ForeignKey('admins.id'), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_login = Column(DateTime(timezone=True), nullable=True)
    login_attempts = Column(Integer, default=0)
    locked_until = Column(DateTime(timezone=True), nullable=True)
    
    # Permission columns
    can_manage_portal = Column(Boolean, default=False)
    can_manage_sessions = Column(Boolean, default=False)
    can_view_records = Column(Boolean, default=True)
    can_view_ipdr = Column(Boolean, default=True)
    can_manage_radius = Column(Boolean, default=False)
    
    # Relationships
    logs = relationship("SystemLog", back_populates="user")
    
    __table_args__ = (
        CheckConstraint(
            "role IN ('superadmin', 'admin', 'reports_user', 'ads_user', 'ipdr_viewer')",
            name='check_admin_role'
        ),
        CheckConstraint(
            "(requires_otp = TRUE AND mobile IS NOT NULL) OR requires_otp = FALSE",
            name='check_mobile_for_otp'
        ),
    )
