from sqlalchemy import Column, Integer, String, BigInteger, Date, Time, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..database import Base


class FirewallLog(Base):
    __tablename__ = "firewall_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Timestamp Information
    log_date = Column(Date, nullable=False, index=True)
    log_time = Column(Time, nullable=False)
    log_timestamp = Column(DateTime, nullable=False, index=True)
    
    # User Session Correlation
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    
    # Network Information
    source_ip = Column(String(45), nullable=False, index=True)
    source_port = Column(Integer, nullable=False)
    source_mac = Column(String(17))
    source_interface = Column(String(100))
    
    translated_ip = Column(String(45))
    translated_port = Column(Integer)
    
    destination_ip = Column(String(45), nullable=False, index=True)
    destination_port = Column(Integer, nullable=False)
    destination_country = Column(String(100))
    
    # Protocol & Application
    protocol = Column(Integer)
    protocol_name = Column(String(20))
    service = Column(String(100))
    app_name = Column(String(100))
    app_category = Column(String(100))
    
    # Traffic Data
    sent_bytes = Column(BigInteger, default=0)
    received_bytes = Column(BigInteger, default=0)
    sent_packets = Column(Integer, default=0)
    received_packets = Column(Integer, default=0)
    duration = Column(Integer)
    
    # Action & Policy
    action = Column(String(50))
    policy_id = Column(Integer)
    policy_name = Column(String(100))
    
    # Additional Metadata
    url = Column(Text)
    domain_name = Column(String(255))
    device_type = Column(String(100))
    os_name = Column(String(100))
    
    # Import Information
    imported_at = Column(DateTime, server_default=func.now())
    csv_filename = Column(String(255))
    raw_log_data = Column(JSONB)
    
    # Relationships
    session = relationship("Session", back_populates="firewall_logs")
    user = relationship("User", back_populates="firewall_logs")


class FirewallImportJob(Base):
    __tablename__ = "firewall_import_jobs"
    
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), nullable=False)
    file_size = Column(BigInteger)
    total_rows = Column(Integer)
    processed_rows = Column(Integer, default=0)
    imported_rows = Column(Integer, default=0)
    failed_rows = Column(Integer, default=0)
    status = Column(String(50), nullable=False, index=True)
    error_message = Column(Text)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    imported_by = Column(Integer, ForeignKey("admins.id"))
    created_at = Column(DateTime, server_default=func.now())


class IPDRSearchHistory(Base):
    __tablename__ = "ipdr_search_history"
    
    id = Column(Integer, primary_key=True, index=True)
    admin_id = Column(Integer, ForeignKey("admins.id"), index=True)
    search_type = Column(String(50))
    search_params = Column(JSONB)
    results_count = Column(Integer)
    exported = Column(Boolean, default=False)
    search_timestamp = Column(DateTime, server_default=func.now(), index=True)
    ip_address = Column(String(45))
