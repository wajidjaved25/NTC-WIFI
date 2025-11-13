from sqlalchemy import Column, Integer, String, DateTime, BigInteger, ForeignKey, Text
from sqlalchemy.sql import func
from app.database import Base

class Session(Base):
    __tablename__ = "sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    mac_address = Column(String(17), nullable=False, index=True)
    ip_address = Column(String(45), nullable=True)
    ap_mac = Column(String(17), nullable=True)
    ap_name = Column(String(100), nullable=True)
    ssid = Column(String(100), nullable=True)
    site = Column(String(100), nullable=True)
    
    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=True)
    duration = Column(Integer, nullable=True)  # seconds
    
    data_upload = Column(BigInteger, default=0)
    data_download = Column(BigInteger, default=0)
    total_data = Column(BigInteger, default=0)
    
    disconnect_reason = Column(String(100), nullable=True)
    session_status = Column(String(50), default='active')
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
