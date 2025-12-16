"""
Site/Location Management Model
Tracks multiple Omada sites with their own RADIUS configuration
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from ..database import Base


class Site(Base):
    __tablename__ = "sites"
    
    id = Column(Integer, primary_key=True, index=True)
    site_name = Column(String(100), unique=True, nullable=False)
    site_code = Column(String(20), unique=True, nullable=False)
    location = Column(String(255))
    
    # Omada Controller Details
    omada_controller_ip = Column(String(45), nullable=False)
    omada_controller_port = Column(Integer, default=8043)
    omada_site_id = Column(String(100), default='Default')
    omada_username = Column(String(100))
    omada_password_encrypted = Column(Text)
    
    # RADIUS Configuration
    radius_nas_ip = Column(String(45), nullable=False)
    radius_secret = Column(String(100), nullable=False)
    radius_coa_port = Column(Integer, nullable=False, unique=True)  # Must be unique!
    
    # Portal Settings
    portal_url = Column(String(255))
    custom_branding = Column(Text)  # JSON string
    
    # Status
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    created_by = Column(Integer, ForeignKey('admins.id'))
    
    # Relationships
    nas_clients = relationship("NASClient", back_populates="site", cascade="all, delete-orphan")


class NASClient(Base):
    __tablename__ = "nas_clients"
    
    id = Column(Integer, primary_key=True, index=True)
    site_id = Column(Integer, ForeignKey('sites.id', ondelete='CASCADE'), nullable=False)
    nasname = Column(String(128), nullable=False)  # IP address
    shortname = Column(String(32))
    type = Column(String(30), default='other')
    secret = Column(String(60), nullable=False)
    coa_port = Column(Integer, nullable=False)
    description = Column(String(200))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    site = relationship("Site", back_populates="nas_clients")
