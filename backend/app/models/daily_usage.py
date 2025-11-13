from sqlalchemy import Column, Integer, BigInteger, Date, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.database import Base

class DailyUsage(Base):
    __tablename__ = "daily_usage"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    usage_date = Column(Date, nullable=False, index=True)
    total_duration = Column(Integer, default=0)  # seconds
    session_count = Column(Integer, default=0)
    data_upload = Column(BigInteger, default=0)  # bytes
    data_download = Column(BigInteger, default=0)  # bytes
    total_data = Column(BigInteger, default=0)  # bytes
    last_session_at = Column(DateTime(timezone=True), nullable=True)
