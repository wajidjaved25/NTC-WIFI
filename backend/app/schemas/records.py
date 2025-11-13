from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, date

# Session/Record Schemas
class SessionBase(BaseModel):
    user_id: Optional[int]
    mac_address: str
    ip_address: Optional[str]
    ap_mac: Optional[str]
    ap_name: Optional[str]
    ssid: Optional[str]
    site: Optional[str]

class SessionResponse(BaseModel):
    id: int
    user_id: Optional[int]
    user_name: Optional[str]
    user_mobile: Optional[str]
    user_cnic: Optional[str]
    user_passport: Optional[str]
    mac_address: str
    ip_address: Optional[str]
    ap_name: Optional[str]
    ssid: Optional[str]
    start_time: datetime
    end_time: Optional[datetime]
    duration: Optional[int]
    total_data: Optional[int]
    data_upload: Optional[int]
    data_download: Optional[int]
    disconnect_reason: Optional[str]
    session_status: str
    
    class Config:
        from_attributes = True

# Filters for records
class RecordFilters(BaseModel):
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    mobile: Optional[str] = None
    cnic: Optional[str] = None
    passport: Optional[str] = None
    mac_address: Optional[str] = None
    status: Optional[str] = None
    min_duration: Optional[int] = None
    max_duration: Optional[int] = None
    page: int = 1
    page_size: int = 50

# Export Request
class ExportRequest(BaseModel):
    format: str  # excel, pdf, csv
    filters: RecordFilters
    include_fields: Optional[List[str]] = None

# Dashboard Stats
class DashboardStats(BaseModel):
    total_users: int
    active_sessions: int
    today_sessions: int
    today_data_usage: int
    total_sessions: int
    average_session_duration: int
    peak_hour: Optional[str]
    top_users: List[dict]
