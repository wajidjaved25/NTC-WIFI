from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, ARRAY, BigInteger
from sqlalchemy.sql import func
from app.database import Base

class OmadaConfig(Base):
    __tablename__ = "omada_config"
    
    id = Column(Integer, primary_key=True, index=True)
    config_name = Column(String(100), nullable=False, default='Default')
    controller_url = Column(String(255), nullable=False)
    controller_id = Column(String(100), nullable=True)
    username = Column(String(100), nullable=False)
    password_encrypted = Column(Text, nullable=False)
    site_id = Column(String(100), default='Default')
    site_name = Column(String(100), nullable=True)
    
    # Authentication Settings
    auth_type = Column(String(50), default='external')
    redirect_url = Column(String(255), nullable=True)
    
    # Session Control
    session_timeout = Column(Integer, default=3600)  # seconds
    idle_timeout = Column(Integer, default=600)  # seconds
    daily_time_limit = Column(Integer, default=7200)  # seconds
    max_daily_sessions = Column(Integer, default=3)
    
    # Bandwidth Control
    bandwidth_limit_up = Column(Integer, nullable=True)  # kbps
    bandwidth_limit_down = Column(Integer, nullable=True)  # kbps
    
    # Advanced Settings
    enable_rate_limiting = Column(Boolean, default=True)
    rate_limit_up = Column(Integer, nullable=True)  # kbps
    rate_limit_down = Column(Integer, nullable=True)  # kbps
    
    # Data Limits
    daily_data_limit = Column(BigInteger, nullable=True)  # bytes
    session_data_limit = Column(BigInteger, nullable=True)  # bytes
    
    # Access Control
    enable_mac_filtering = Column(Boolean, default=False)
    allowed_mac_addresses = Column(ARRAY(Text), nullable=True)
    blocked_mac_addresses = Column(ARRAY(Text), nullable=True)
    
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    updated_by = Column(Integer, ForeignKey('admins.id'), nullable=True)
