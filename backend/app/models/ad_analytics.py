from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime

from ..database import Base

class AdAnalytics(Base):
    __tablename__ = "ad_analytics"
    
    id = Column(Integer, primary_key=True, index=True)
    ad_id = Column(Integer, ForeignKey("advertisements.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    mac_address = Column(String(17))
    
    event_type = Column(String(50))  # view, click, skip, complete
    event_timestamp = Column(DateTime, default=datetime.utcnow)
    watch_duration = Column(Integer)  # seconds watched
    
    ip_address = Column(String(45))
    user_agent = Column(Text)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    advertisement = relationship("Advertisement", back_populates="analytics")
    user = relationship("User")
