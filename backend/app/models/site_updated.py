"""
Site/Location Management Model - UPDATED
One Controller manages Multiple Sites
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from ..database import Base


class OmadaController(Base):
    """Omada Controller - One controller can manage many sites"""
    __tablename__ = "omada_controllers"
    
    id = Column(Integer, primary_key=True, index=True)
    controller_name = Column(String(100), unique=True, nullable=False)
    controller_type = Column(String(20), default='cloud')  # 'cloud' or 'on-premise'
    
    # Controller Access
    controller_url = Column(String(255), nullable=False)
    controller_port = Column(Integer, default=8043)
    username = Column(String(100))
    password_encrypted = Column(Text)
    
    # Controller Info
    controller_id = Column(String(100))  # For cloud controllers
    api_key = Column(Text)
    
    # Status
    is_active = Column(Boolean, default=True)
    last_connected = Column(DateTime(timezone=True))
    connection_status = Column(String(20), default='unknown')
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    created_by = Column(Integer, ForeignKey('admins.id'))
    
    # Relationships
    sites = relationship("Site", back_populates="controller")


class Site(Base):
    """Site/Location - Many sites can use one controller"""
    __tablename__ = "sites"
    
    id = Column(Integer, primary_key=True, index=True)
    site_name = Column(String(100), unique=True, nullable=False)
    site_code = Column(String(20), unique=True, nullable=False)
    location = Column(String(255))
    
    # Controller Reference (Foreign Key)
    controller_id = Column(Integer, ForeignKey('omada_controllers.id', ondelete='RESTRICT'), nullable=False)
    omada_site_id = Column(String(100), default='Default')  # Site ID within Omada
    
    # RADIUS Configuration (Unique per site)
    radius_nas_ip = Column(String(45), nullable=False)
    radius_secret = Column(String(100), nullable=False)
    radius_coa_port = Column(Integer, nullable=False, unique=True)  # Must be unique!
    
    # Portal Settings
    portal_url = Column(String(255))
    custom_branding = Column(Text)  # JSON string
    
    # Network Info
    network_subnet = Column(String(50))
    gateway_ip = Column(String(45))
    
    # Status
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    created_by = Column(Integer, ForeignKey('admins.id'))
    
    # Relationships
    controller = relationship("OmadaController", back_populates="sites")
    sessions = relationship("Session", back_populates="site")
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
