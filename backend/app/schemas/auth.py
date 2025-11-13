from pydantic import BaseModel, EmailStr, validator
from typing import Optional
from datetime import datetime

# Token Response
class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    role: str
    username: str
    full_name: Optional[str]

# OTP Request
class OTPRequest(BaseModel):
    mobile: str
    ip_address: Optional[str] = None
    
    @validator('mobile')
    def validate_mobile(cls, v):
        # Basic mobile validation
        if not v or len(v) < 10:
            raise ValueError('Invalid mobile number')
        return v

# OTP Verify
class OTPVerify(BaseModel):
    mobile: str
    otp: str

# Admin Create
class AdminCreate(BaseModel):
    username: str
    password: Optional[str] = None
    role: str
    mobile: Optional[str] = None
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    
    @validator('role')
    def validate_role(cls, v):
        allowed_roles = ['admin', 'reports_user', 'ads_user']
        if v not in allowed_roles:
            raise ValueError(f'Role must be one of: {", ".join(allowed_roles)}')
        return v

# Admin Response
class AdminResponse(BaseModel):
    id: int
    username: str
    role: str
    full_name: Optional[str]
    email: Optional[str]
    mobile: Optional[str]
    is_active: bool
    requires_otp: bool
    last_login: Optional[datetime]
    created_at: datetime
    
    class Config:
        from_attributes = True
