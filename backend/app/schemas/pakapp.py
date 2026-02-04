from pydantic import BaseModel, EmailStr, validator
from typing import Optional
from datetime import datetime
import re

class PakAppUserCreate(BaseModel):
    name: str
    cnic: str
    phone: str
    email: Optional[str] = None
    
    @validator('name')
    def validate_name(cls, v):
        if not v or len(v.strip()) < 2:
            raise ValueError('Name must be at least 2 characters')
        if len(v) > 255:
            raise ValueError('Name must be less than 255 characters')
        return v.strip()
    
    @validator('cnic')
    def validate_cnic(cls, v):
        # Remove any dashes or spaces
        cnic_clean = v.replace('-', '').replace(' ', '')
        
        # CNIC should be 13 digits
        if not re.match(r'^\d{13}$', cnic_clean):
            raise ValueError('CNIC must be 13 digits')
        
        return cnic_clean
    
    @validator('phone')
    def validate_phone(cls, v):
        # Remove any spaces, dashes, or plus signs
        phone_clean = v.replace(' ', '').replace('-', '').replace('+', '')
        
        # Accept Pakistani numbers in various formats
        # 92XXXXXXXXXX (12 digits) or 03XXXXXXXXX (11 digits)
        if re.match(r'^92\d{10}$', phone_clean):
            return phone_clean
        elif re.match(r'^03\d{9}$', phone_clean):
            # Convert 03XX to 923XX
            return '92' + phone_clean[1:]
        elif re.match(r'^3\d{9}$', phone_clean):
            # Convert 3XX to 923XX
            return '92' + phone_clean
        else:
            raise ValueError('Phone must be a valid Pakistani number (03XXXXXXXXX or 92XXXXXXXXXX)')
        
        return phone_clean
    
    @validator('email')
    def validate_email(cls, v):
        if v:
            # Basic email validation
            if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', v):
                raise ValueError('Invalid email format')
            if len(v) > 255:
                raise ValueError('Email must be less than 255 characters')
            return v.lower().strip()
        return v


class PakAppUserResponse(BaseModel):
    id: int
    name: str
    cnic: str
    phone: str
    email: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime
    source: str
    
    class Config:
        from_attributes = True


class PakAppUserUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    is_active: Optional[bool] = None
    
    @validator('name')
    def validate_name(cls, v):
        if v is not None:
            if len(v.strip()) < 2:
                raise ValueError('Name must be at least 2 characters')
            if len(v) > 255:
                raise ValueError('Name must be less than 255 characters')
            return v.strip()
        return v
    
    @validator('phone')
    def validate_phone(cls, v):
        if v is not None:
            phone_clean = v.replace(' ', '').replace('-', '').replace('+', '')
            if re.match(r'^92\d{10}$', phone_clean):
                return phone_clean
            elif re.match(r'^03\d{9}$', phone_clean):
                return '92' + phone_clean[1:]
            elif re.match(r'^3\d{9}$', phone_clean):
                return '92' + phone_clean
            else:
                raise ValueError('Phone must be a valid Pakistani number')
        return v
    
    @validator('email')
    def validate_email(cls, v):
        if v is not None and v:
            if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', v):
                raise ValueError('Invalid email format')
            return v.lower().strip()
        return v


class PakAppUserListResponse(BaseModel):
    total: int
    page: int
    per_page: int
    users: list[PakAppUserResponse]
