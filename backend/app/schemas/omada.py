from pydantic import BaseModel, validator
from typing import Optional, List
from datetime import datetime

# Omada Config Schemas
class OmadaConfigBase(BaseModel):
    config_name: str
    controller_url: str
    controller_id: Optional[str] = None
    username: str
    password: str  # Will be encrypted before storage
    site_id: str = "Default"
    site_name: Optional[str] = None
    
    # Authentication Settings
    auth_type: str = "external"
    redirect_url: Optional[str] = None
    
    # Session Control
    session_timeout: int = 3600
    idle_timeout: int = 600
    daily_time_limit: int = 7200
    max_daily_sessions: int = 3
    
    # Bandwidth Control
    bandwidth_limit_up: Optional[int] = None
    bandwidth_limit_down: Optional[int] = None
    
    # Rate Limiting
    enable_rate_limiting: bool = True
    rate_limit_up: Optional[int] = None
    rate_limit_down: Optional[int] = None
    
    # Data Limits
    daily_data_limit: Optional[int] = None
    session_data_limit: Optional[int] = None
    
    # Access Control
    enable_mac_filtering: bool = False
    allowed_mac_addresses: Optional[List[str]] = []
    blocked_mac_addresses: Optional[List[str]] = []

class OmadaConfigCreate(OmadaConfigBase):
    pass

class OmadaConfigUpdate(BaseModel):
    config_name: Optional[str] = None
    controller_url: Optional[str] = None
    controller_id: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    site_id: Optional[str] = None
    site_name: Optional[str] = None
    auth_type: Optional[str] = None
    redirect_url: Optional[str] = None
    session_timeout: Optional[int] = None
    idle_timeout: Optional[int] = None
    daily_time_limit: Optional[int] = None
    max_daily_sessions: Optional[int] = None
    bandwidth_limit_up: Optional[int] = None
    bandwidth_limit_down: Optional[int] = None
    enable_rate_limiting: Optional[bool] = None
    rate_limit_up: Optional[int] = None
    rate_limit_down: Optional[int] = None
    daily_data_limit: Optional[int] = None
    session_data_limit: Optional[int] = None
    enable_mac_filtering: Optional[bool] = None
    allowed_mac_addresses: Optional[List[str]] = None
    blocked_mac_addresses: Optional[List[str]] = None
    is_active: Optional[bool] = None

class OmadaConfigResponse(BaseModel):
    id: int
    config_name: str
    controller_url: str
    controller_id: Optional[str]
    username: str
    site_id: str
    site_name: Optional[str]
    auth_type: str
    session_timeout: int
    idle_timeout: int
    daily_time_limit: int
    max_daily_sessions: int
    bandwidth_limit_up: Optional[int]
    bandwidth_limit_down: Optional[int]
    enable_rate_limiting: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

# Test Connection
class OmadaTestConnection(BaseModel):
    controller_url: str
    username: str
    password: Optional[str] = None
    controller_id: Optional[str] = None
    site_id: Optional[str] = "Default"
    use_stored_password: Optional[bool] = False
    config_id: Optional[int] = None

# Client Authorization
class ClientAuthorization(BaseModel):
    mac_address: str
    duration: int  # seconds
    upload_limit: Optional[int] = None
    download_limit: Optional[int] = None
