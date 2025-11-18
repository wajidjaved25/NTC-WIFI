"""
Models package - Import all SQLAlchemy models here
"""

from .admin import Admin
from .user import User
from .portal_design import PortalDesign
from .portal_settings import PortalSettings
from .advertisement import Advertisement
from .ad_analytics import AdAnalytics
from .session import Session
from .omada_config import OmadaConfig
from .daily_usage import DailyUsage
from .system_log import SystemLog
from .otp import OTP
from .radius_settings import RadiusSettings

__all__ = [
    "Admin",
    "User",
    "PortalDesign",
    "PortalSettings",
    "Advertisement",
    "AdAnalytics",
    "Session",
    "OmadaConfig",
    "DailyUsage",
    "SystemLog",
    "OTP",
    "RadiusSettings"
]
