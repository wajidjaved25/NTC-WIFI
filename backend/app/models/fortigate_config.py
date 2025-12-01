from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.sql import func
from ..database import Base


class FortiGateSyslogConfig(Base):
    __tablename__ = "fortigate_syslog_config"
    
    id = Column(Integer, primary_key=True, index=True)
    enabled = Column(Boolean, default=True)
    listen_host = Column(String(45), default="0.0.0.0")
    listen_port = Column(Integer, default=514)
    protocol = Column(String(10), default="udp")  # udp or tcp
    
    # FortiGate connection info (optional, for reference)
    fortigate_ip = Column(String(45), nullable=True)
    fortigate_name = Column(String(100), nullable=True)
    
    # Statistics
    total_logs_received = Column(Integer, default=0)
    last_log_received_at = Column(DateTime(timezone=True), nullable=True)
    
    # Configuration
    correlation_enabled = Column(Boolean, default=True)
    correlation_time_window_minutes = Column(Integer, default=5)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
