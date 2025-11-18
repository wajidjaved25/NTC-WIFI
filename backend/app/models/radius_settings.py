"""
RADIUS Settings Model
Stores default configuration for RADIUS authentication
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.sql import func

from ..database import Base


class RadiusSettings(Base):
    __tablename__ = "radius_settings"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Session Settings
    default_session_timeout = Column(Integer, default=3600)  # seconds (1 hour)
    max_session_timeout = Column(Integer, default=86400)  # 24 hours max
    
    # Bandwidth Settings (in kbps, 0 = unlimited)
    default_bandwidth_down = Column(Integer, default=0)
    default_bandwidth_up = Column(Integer, default=0)
    
    # Concurrent Sessions
    max_concurrent_sessions = Column(Integer, default=1)
    
    # Idle Timeout
    idle_timeout = Column(Integer, default=600)  # 10 minutes
    
    # Data Limits (in MB, 0 = unlimited)
    daily_data_limit = Column(Integer, default=0)
    monthly_data_limit = Column(Integer, default=0)
    
    # Authentication Settings
    allow_multiple_devices = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
