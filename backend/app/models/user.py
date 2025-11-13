from sqlalchemy import Column, Integer, String, Boolean, DateTime, BigInteger, Text
from sqlalchemy.sql import func
from app.database import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    mobile = Column(String(20), unique=True, nullable=False, index=True)
    email = Column(String(255), nullable=True)
    id_type = Column(String(20), nullable=True)  # 'cnic' or 'passport'
    cnic = Column(String(15), nullable=True, index=True)
    passport = Column(String(50), nullable=True, index=True)
    terms_accepted = Column(Boolean, default=False)
    terms_accepted_at = Column(DateTime(timezone=True), nullable=True)
    is_blocked = Column(Boolean, default=False)
    block_reason = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_login = Column(DateTime(timezone=True), nullable=True)
    total_sessions = Column(Integer, default=0)
    total_data_usage = Column(BigInteger, default=0)
