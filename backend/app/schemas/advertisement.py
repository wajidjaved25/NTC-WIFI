from pydantic import BaseModel, validator
from typing import Optional
from datetime import datetime

# Advertisement Schemas
class AdvertisementBase(BaseModel):
    title: str
    description: Optional[str] = None
    ad_type: str
    display_duration: int = 10
    display_order: int = 0
    auto_skip: bool = False
    skip_after: int = 5
    is_active: bool = True
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    auto_disable: bool = False
    
    @validator('ad_type')
    def validate_ad_type(cls, v):
        allowed_types = ['video', 'image', 'download']
        if v not in allowed_types:
            raise ValueError(f'Ad type must be one of: {", ".join(allowed_types)}')
        return v
    
    @validator('display_duration')
    def validate_duration(cls, v):
        if v < 1 or v > 300:
            raise ValueError('Display duration must be between 1 and 300 seconds')
        return v

class AdvertisementCreate(AdvertisementBase):
    file_path: str
    file_name: str
    file_size: int
    mime_type: str

class AdvertisementUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    display_duration: Optional[int] = None
    display_order: Optional[int] = None
    auto_skip: Optional[bool] = None
    skip_after: Optional[int] = None
    is_active: Optional[bool] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    auto_disable: Optional[bool] = None

class AdvertisementResponse(BaseModel):
    id: int
    title: str
    description: Optional[str]
    ad_type: str
    file_path: str
    file_name: str
    file_size: int
    mime_type: str
    display_duration: int
    display_order: int
    auto_skip: bool
    skip_after: int
    is_active: bool
    start_date: Optional[datetime]
    end_date: Optional[datetime]
    auto_disable: bool
    view_count: int
    click_count: int
    skip_count: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

# Ad Analytics
class AdAnalyticsResponse(BaseModel):
    ad_id: int
    ad_title: str
    total_views: int
    total_clicks: int
    total_skips: int
    average_watch_duration: float
    click_through_rate: float
    completion_rate: float
