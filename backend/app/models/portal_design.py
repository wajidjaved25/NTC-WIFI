from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.sql import func
from app.database import Base

class PortalDesign(Base):
    __tablename__ = "portal_design"
    
    id = Column(Integer, primary_key=True, index=True)
    template_name = Column(String(100), nullable=False)
    
    # Branding
    logo_path = Column(String(255), nullable=True)
    favicon_path = Column(String(255), nullable=True)
    background_image = Column(String(255), nullable=True)
    background_type = Column(String(20), default='image')  # image, color, gradient
    show_logo = Column(Boolean, default=True)  # Show/hide logo
    show_background = Column(Boolean, default=False)  # Show/hide background image
    
    # Colors
    primary_color = Column(String(7), default='#1890ff')
    secondary_color = Column(String(7), default='#ffffff')
    accent_color = Column(String(7), default='#52c41a')
    text_color = Column(String(7), default='#000000')
    background_color = Column(String(7), default='#f0f2f5')
    
    # Content
    welcome_title = Column(String(255), default='Welcome to Free WiFi')
    welcome_text = Column(Text, default='Please register to connect to our WiFi network')
    terms_text = Column(Text, nullable=True)
    terms_checkbox_text = Column(Text, default='I accept the terms and conditions')
    footer_text = Column(String(255), nullable=True)
    
    # Layout
    custom_css = Column(Text, nullable=True)
    custom_js = Column(Text, nullable=True)
    layout_type = Column(String(50), default='centered')  # centered, split, fullscreen
    
    # Status
    is_active = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    updated_by = Column(Integer, ForeignKey('admins.id'), nullable=True)
