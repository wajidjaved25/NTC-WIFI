from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.sql import func
from app.database import Base

class OTP(Base):
    __tablename__ = "otps"
    
    id = Column(Integer, primary_key=True, index=True)
    mobile = Column(String(20), nullable=False, index=True)
    otp = Column(String(6), nullable=False)
    otp_type = Column(String(20), default='user_login')  # user_login, admin_login
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=False)
    verified = Column(Boolean, default=False)
    attempts = Column(Integer, default=0)
    ip_address = Column(String(45), nullable=True)
