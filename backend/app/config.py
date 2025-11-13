from pydantic_settings import BaseSettings
from pydantic import validator
from typing import List
import os

class Settings(BaseSettings):
    # Application
    APP_NAME: str = "NTC WiFi Admin Portal"
    APP_ENV: str = "development"
    DEBUG: bool = True
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # Database
    DATABASE_URL: str
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_NAME: str = "ntc_wifi_admin"
    DB_USER: str = "postgres"
    DB_PASSWORD: str
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    
    # Security
    SECRET_KEY: str
    ENCRYPTION_KEY: str  # For encrypting Omada passwords
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480  # 8 hours
    
    # CORS - Added localhost:3001 for public portal
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:3001,http://localhost:5173"
    
    @property
    def origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]
    
    # SMS API (SuperApp)
    SUPERAPP_API_URL: str = "https://connect.smsapp.pk/api/SendSMS"
    SUPERAPP_API_KEY: str
    SUPERAPP_CLIENT_ID: str
    SUPERAPP_SENDER_ID: str = "NTC WiFi"
    
    # Omada Controller (Default - can be changed in admin panel)
    OMADA_CONTROLLER_URL: str = "https://10.2.49.26:8043"
    OMADA_USERNAME: str = "admin"
    OMADA_PASSWORD: str
    OMADA_SITE_ID: str = "Default"
    
    # File Upload
    UPLOAD_DIR: str = "D:/Codes/NTC/NTC Public Wifi/media"
    MAX_UPLOAD_SIZE: int = 52428800  # 50MB
    ALLOWED_EXTENSIONS: str = ".jpg,.jpeg,.png,.gif,.webp,.mp4,.webm,.ogg,.pdf,.doc,.docx"
    
    @property
    def extensions_list(self) -> List[str]:
        return [ext.strip() for ext in self.ALLOWED_EXTENSIONS.split(",")]
    
    # Portal Settings
    PORTAL_DOMAIN: str = "admin.local"
    PORTAL_URL: str = "http://10.2.49.27:3000"
    ENABLE_IP_MASKING: bool = True
    
    # Backup Settings
    BACKUP_DIR: str = "D:/Backups/NTC_WiFi"
    AUTO_BACKUP_ENABLED: bool = True
    BACKUP_SCHEDULE: str = "0 2 * * *"  # Daily at 2 AM
    BACKUP_RETENTION_DAYS: int = 30
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "logs/app.log"
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "allow"

# Create settings instance
settings = Settings()

# Ensure directories exist
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
os.makedirs(os.path.join(settings.UPLOAD_DIR, "ads"), exist_ok=True)
os.makedirs(os.path.join(settings.UPLOAD_DIR, "portal"), exist_ok=True)
os.makedirs(settings.BACKUP_DIR, exist_ok=True)
os.makedirs(os.path.dirname(settings.LOG_FILE), exist_ok=True)
