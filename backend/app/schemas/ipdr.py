from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, date, time


class FirewallLogBase(BaseModel):
    log_date: date
    log_time: time
    source_ip: str
    source_port: int
    destination_ip: str
    destination_port: int
    protocol: Optional[int] = None
    protocol_name: Optional[str] = None


class FirewallLogCreate(FirewallLogBase):
    log_timestamp: datetime
    source_mac: Optional[str] = None
    translated_ip: Optional[str] = None
    translated_port: Optional[int] = None
    destination_country: Optional[str] = None
    service: Optional[str] = None
    app_name: Optional[str] = None
    sent_bytes: Optional[int] = 0
    received_bytes: Optional[int] = 0
    url: Optional[str] = None
    raw_log_data: Optional[Dict[str, Any]] = None


class FirewallLogResponse(FirewallLogBase):
    id: int
    log_timestamp: datetime
    user_id: Optional[int] = None
    session_id: Optional[int] = None
    source_mac: Optional[str] = None
    translated_ip: Optional[str] = None
    translated_port: Optional[int] = None
    destination_country: Optional[str] = None
    service: Optional[str] = None
    app_name: Optional[str] = None
    app_category: Optional[str] = None
    sent_bytes: int
    received_bytes: int
    url: Optional[str] = None
    domain_name: Optional[str] = None
    imported_at: datetime
    
    class Config:
        from_attributes = True


class IPDRSearchRequest(BaseModel):
    # Date range
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    
    # User information
    user_name: Optional[str] = None
    cnic: Optional[str] = None
    passport: Optional[str] = None
    mobile: Optional[str] = None
    
    # Network identifiers
    mac_address: Optional[str] = None
    source_ip: Optional[str] = None
    destination_ip: Optional[str] = None
    translated_ip: Optional[str] = None
    
    # Port numbers
    source_port: Optional[int] = None
    destination_port: Optional[int] = None
    
    # Protocol and Application
    protocol: Optional[str] = None
    service: Optional[str] = None
    app_name: Optional[str] = None
    
    # Data usage range (in bytes)
    min_data: Optional[int] = None
    max_data: Optional[int] = None
    
    # URL search
    url: Optional[str] = None
    
    # Pagination
    page: int = 1
    page_size: int = 50


class IPDRRecord(BaseModel):
    # User Information
    full_name: Optional[str] = None
    cnic: Optional[str] = None
    passport: Optional[str] = None
    mobile: Optional[str] = None
    
    # Session Information
    login_time: Optional[datetime] = None
    logout_time: Optional[datetime] = None
    session_duration: Optional[int] = None
    
    # Network Information
    mac_address: Optional[str] = None
    source_ip: str
    source_port: int
    translated_ip: Optional[str] = None
    translated_port: Optional[int] = None
    destination_ip: str
    destination_port: int
    
    # Traffic Information
    data_consumption: int  # bytes
    url: Optional[str] = None
    protocol: Optional[str] = None
    service: Optional[str] = None
    app_name: Optional[str] = None
    
    # Timestamp
    log_timestamp: datetime


class IPDRSearchResponse(BaseModel):
    total_records: int
    page: int
    page_size: int
    total_pages: int
    records: List[IPDRRecord]


class CSVImportRequest(BaseModel):
    csv_content: str
    filename: str


class ImportJobResponse(BaseModel):
    id: int
    filename: str
    status: str
    total_rows: Optional[int] = None
    processed_rows: int
    imported_rows: int
    failed_rows: int
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    
    class Config:
        from_attributes = True


class IPDRExportRequest(BaseModel):
    search_params: IPDRSearchRequest
    format: str = "csv"  # csv or pdf
