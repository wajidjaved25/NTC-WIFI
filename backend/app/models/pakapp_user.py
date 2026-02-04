from sqlalchemy import Column, Integer, String, DateTime, Boolean
from sqlalchemy.sql import func
from app.database import Base

class PakAppUser(Base):
    __tablename__ = "pakapp_users"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    cnic = Column(String(15), nullable=False, unique=True, index=True)
    phone = Column(String(20), nullable=False, index=True)
    email = Column(String(255), nullable=True)
    
    # Tracking fields
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Optional metadata
    source = Column(String(50), default='pakapp')  # Source of registration
    ip_address = Column(String(45), nullable=True)
    
    def __repr__(self):
        return f"<PakAppUser {self.name} - {self.cnic}>"
