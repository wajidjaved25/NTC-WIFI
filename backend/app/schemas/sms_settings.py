"""
SMS Settings Schemas
Pydantic models for SMS configuration
"""

from pydantic import BaseModel, Field, validator
from datetime import datetime
from typing import Optional


class SMSSettingsBase(BaseModel):
    """Base SMS settings schema"""
    otp_template: str = Field(
        ...,
        min_length=10,
        max_length=500,
        description="OTP SMS template. Use {otp}, {validity}, {portal_url}, {sender} as placeholders"
    )
    sender_id: str = Field(..., min_length=3, max_length=20, description="SMS Sender ID")
    otp_validity_minutes: int = Field(default=5, ge=1, le=60, description="OTP validity in minutes")
    otp_length: int = Field(default=6, ge=4, le=8, description="OTP code length")
    max_otp_per_number_per_hour: int = Field(default=3, ge=1, le=20)
    max_otp_per_number_per_day: int = Field(default=10, ge=1, le=50)
    enable_primary_sms: bool = True
    enable_secondary_sms: bool = True
    
    @validator('otp_template')
    def validate_template(cls, v):
        """Ensure template contains {otp} placeholder"""
        if '{otp}' not in v:
            raise ValueError('Template must contain {otp} placeholder')
        
        # Check for valid placeholders
        valid_placeholders = ['{otp}', '{validity}', '{portal_url}', '{sender}']
        import re
        placeholders = re.findall(r'\{([^}]+)\}', v)
        
        for placeholder in placeholders:
            if f'{{{placeholder}}}' not in valid_placeholders:
                raise ValueError(f'Invalid placeholder: {{{placeholder}}}. Valid: {", ".join(valid_placeholders)}')
        
        return v
    
    @validator('sender_id')
    def validate_sender_id(cls, v):
        """Validate sender ID format"""
        if not v.replace('-', '').replace(' ', '').isalnum():
            raise ValueError('Sender ID must be alphanumeric')
        return v


class SMSSettingsUpdate(BaseModel):
    """Schema for updating SMS settings (all fields optional)"""
    otp_template: Optional[str] = None
    sender_id: Optional[str] = None
    otp_validity_minutes: Optional[int] = None
    otp_length: Optional[int] = None
    max_otp_per_number_per_hour: Optional[int] = None
    max_otp_per_number_per_day: Optional[int] = None
    enable_primary_sms: Optional[bool] = None
    enable_secondary_sms: Optional[bool] = None
    
    @validator('otp_template')
    def validate_template(cls, v):
        """Ensure template contains {otp} placeholder"""
        if v and '{otp}' not in v:
            raise ValueError('Template must contain {otp} placeholder')
        return v


class SMSSettingsResponse(SMSSettingsBase):
    """Schema for SMS settings response"""
    id: int
    created_at: datetime
    updated_at: datetime
    updated_by: Optional[str]
    
    class Config:
        from_attributes = True


class SMSPreview(BaseModel):
    """Preview of formatted SMS message"""
    template: str
    formatted_message: str
    character_count: int
    sms_parts: int  # Number of SMS parts (1 part = 160 chars)
    estimated_cost: str
    
    @classmethod
    def from_template(cls, template: str, otp: str = "123456", portal_url: str = "192.168.3.252", validity: int = 5, sender: str = "NTC"):
        """Create preview from template"""
        formatted = template.format(
            otp=otp,
            validity=validity,
            portal_url=portal_url,
            sender=sender
        )
        
        char_count = len(formatted)
        # SMS is 160 chars per part (or 70 for unicode)
        has_unicode = any(ord(char) > 127 for char in formatted)
        char_limit = 70 if has_unicode else 160
        sms_parts = (char_count // char_limit) + (1 if char_count % char_limit else 0)
        
        return cls(
            template=template,
            formatted_message=formatted,
            character_count=char_count,
            sms_parts=sms_parts,
            estimated_cost=f"~{sms_parts} credit(s)"
        )
