from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, BigInteger, CheckConstraint, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from ..database import Base

class Advertisement(Base):
    __tablename__ = "advertisements"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    
    # File Info
    ad_type = Column(String(20), nullable=False)  # video, image, download
    file_path = Column(String(255), nullable=False)
    file_name = Column(String(255), nullable=True)
    file_size = Column(BigInteger, nullable=True)
    mime_type = Column(String(100), nullable=True)
    
    # Display Settings
    display_duration = Column(Integer, default=10)  # seconds
    display_order = Column(Integer, default=0)  # sequence
    auto_skip = Column(Boolean, default=False)
    skip_after = Column(Integer, default=5)  # seconds
    
    # Scheduling
    is_active = Column(Boolean, default=True)
    start_date = Column(DateTime(timezone=True), nullable=True)
    end_date = Column(DateTime(timezone=True), nullable=True)
    auto_disable = Column(Boolean, default=False)
    
    # Target Audience
    target_audience = Column(JSON, nullable=True)
    
    # Analytics
    view_count = Column(Integer, default=0)
    click_count = Column(Integer, default=0)
    skip_count = Column(Integer, default=0)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    created_by = Column(Integer, ForeignKey('admins.id'), nullable=True)
    
    # Relationships
    analytics = relationship("AdAnalytics", back_populates="advertisement", cascade="all, delete-orphan")
    creator = relationship("Admin")
    
    __table_args__ = (
        CheckConstraint(
            "ad_type IN ('video', 'image', 'download')",
            name='check_ad_type'
        ),
    )
