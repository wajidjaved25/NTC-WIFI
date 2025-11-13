from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime

from ..database import Base

class SystemLog(Base):
    __tablename__ = "system_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    log_level = Column(String(20), nullable=False)  # INFO, WARNING, ERROR, CRITICAL
    module = Column(String(100))  # auth, omada, session, ads, etc.
    action = Column(String(100))
    message = Column(Text, nullable=False)
    details = Column(JSON)
    user_id = Column(Integer, ForeignKey("admins.id"), nullable=True)
    ip_address = Column(String(45))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationship
    user = relationship("Admin", back_populates="logs")
