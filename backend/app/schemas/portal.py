from pydantic import BaseModel
from typing import Optional
from datetime import datetime

# Portal Design Schemas
class PortalDesignBase(BaseModel):
    template_name: str
    logo_path: Optional[str] = None
    favicon_path: Optional[str] = None
    background_image: Optional[str] = None
    background_type: str = "image"
    show_logo: bool = True
    show_background: bool = False
    primary_color: str = "#1890ff"
    secondary_color: str = "#ffffff"
    accent_color: str = "#52c41a"
    text_color: str = "#000000"
    background_color: str = "#f0f2f5"
    welcome_title: str = "Welcome to Free WiFi"
    welcome_text: str = "Please register to connect"
    terms_text: Optional[str] = None
    terms_checkbox_text: str = "I accept the terms and conditions"
    footer_text: Optional[str] = None
    custom_css: Optional[str] = None
    custom_js: Optional[str] = None
    layout_type: str = "centered"

class PortalDesignCreate(PortalDesignBase):
    pass

class PortalDesignUpdate(BaseModel):
    template_name: Optional[str] = None
    logo_path: Optional[str] = None
    favicon_path: Optional[str] = None
    background_image: Optional[str] = None
    background_type: Optional[str] = None
    show_logo: Optional[bool] = None
    show_background: Optional[bool] = None
    primary_color: Optional[str] = None
    secondary_color: Optional[str] = None
    accent_color: Optional[str] = None
    text_color: Optional[str] = None
    background_color: Optional[str] = None
    welcome_title: Optional[str] = None
    welcome_text: Optional[str] = None
    terms_text: Optional[str] = None
    terms_checkbox_text: Optional[str] = None
    footer_text: Optional[str] = None
    custom_css: Optional[str] = None
    custom_js: Optional[str] = None
    layout_type: Optional[str] = None
    is_active: Optional[bool] = None

class PortalDesignResponse(BaseModel):
    id: int
    template_name: str
    logo_path: Optional[str]
    favicon_path: Optional[str]
    background_image: Optional[str]
    background_type: str
    show_logo: bool
    show_background: bool
    primary_color: str
    secondary_color: str
    accent_color: str
    text_color: str
    background_color: str
    welcome_title: str
    welcome_text: str
    terms_text: Optional[str]
    terms_checkbox_text: str
    footer_text: Optional[str]
    custom_css: Optional[str]
    custom_js: Optional[str]
    layout_type: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

# Portal Settings
class PortalSettingUpdate(BaseModel):
    setting_value: str

class PortalSettingResponse(BaseModel):
    id: int
    setting_key: str
    setting_value: str
    setting_type: str
    description: Optional[str]
    updated_at: datetime
    
    class Config:
        from_attributes = True
