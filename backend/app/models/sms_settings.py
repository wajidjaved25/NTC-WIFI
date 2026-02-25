"""
SMS Settings Model
Stores customizable SMS templates for OTP and other messages
"""

from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime
from sqlalchemy.sql import func
from app.database import Base


class SMSSettings(Base):
    """SMS configuration and templates"""
    __tablename__ = "sms_settings"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # OTP SMS Template
    otp_template = Column(
        Text, 
        nullable=False, 
        default="Your NTC WiFi OTP: {otp}\nValid for {validity} minutes. Do not share.\n\n@{portal_url} #{otp}"
    )
    
    # Sender ID
    sender_id = Column(String(20), default="NTC")
    
    # OTP Settings
    otp_validity_minutes = Column(Integer, default=5)
    otp_length = Column(Integer, default=6)
    
    # Rate Limiting
    max_otp_per_number_per_hour = Column(Integer, default=3)
    max_otp_per_number_per_day = Column(Integer, default=10)
    
    # Enable/Disable Features
    enable_primary_sms = Column(Boolean, default=True)
    enable_secondary_sms = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    updated_by = Column(String(100), nullable=True)  # Admin username who made the change
    
    def format_otp_message(self, otp: str, portal_url: str = "pmfreewifi.lan") -> str:
        """
        Format OTP message using template
        
        Available variables:
        - {otp}: The OTP code
        - {validity}: Validity period in minutes
        - {portal_url}: Portal URL/domain
        - {sender}: Sender ID
        """
        return self.otp_template.format(
            otp=otp,
            validity=self.otp_validity_minutes,
            portal_url=portal_url,
            sender=self.sender_id
        )
