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
    
    # Syslog Server Database (for firewall logs)
    SYSLOG_DB_HOST: str = "localhost"  # Will be syslog server IP in production
    SYSLOG_DB_PORT: int = 5432
    SYSLOG_DB_NAME: str = "ntc_wifi_logs"
    SYSLOG_DB_USER: str = "syslog_user"
    SYSLOG_DB_PASSWORD: str = "SecureLogPassword123"
    
    @property
    def syslog_database_url(self) -> str:
        return f"postgresql://{self.SYSLOG_DB_USER}:{self.SYSLOG_DB_PASSWORD}@{self.SYSLOG_DB_HOST}:{self.SYSLOG_DB_PORT}/{self.SYSLOG_DB_NAME}"
    
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
    ENABLE_API_DOCS: bool = False  # MUST be False in production
    
    # CORS - Added localhost:3001 for public portal
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:3001,http://localhost:5173"
    
    @property
    def origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]
    
    # SMS API (SuperApp - Primary)
    SUPERAPP_API_URL: str = "https://connect.smsapp.pk/api/SendSMS"
    SUPERAPP_API_KEY: str
    SUPERAPP_CLIENT_ID: str
    SUPERAPP_SENDER_ID: str = "NTC WiFi"
    
    # SMS API 2 (Secondary Provider)
    SMS2_API_URL: str = ""
    SMS2_API_KEY: str = ""
    SMS2_SENDER_ID: str = "NTC WiFi"
    SMS2_ENABLED: bool = False  # Set to True to enable second provider
    
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
    
    # Security Validators
    @validator('SECRET_KEY')
    def validate_secret_key(cls, v):
        if len(v) < 32:
            raise ValueError('SECRET_KEY must be at least 32 characters long')
        if v == 'your-super-secret-key-change-this-in-production-min-32-chars':
            raise ValueError('SECRET_KEY must be changed from default value')
        return v
    
    @validator('ENCRYPTION_KEY')
    def validate_encryption_key(cls, v):
        if len(v) != 44:
            raise ValueError('ENCRYPTION_KEY must be exactly 44 characters (Fernet key). Generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"')
        return v
    
    @validator('DB_PASSWORD')
    def validate_db_password(cls, v):
        if v in ['your_secure_password_here', 'postgres', 'password', '123456']:
            raise ValueError('DB_PASSWORD must be changed from default/common value')
        if len(v) < 12:
            raise ValueError('DB_PASSWORD must be at least 12 characters long')
        return v
    
    # Portal Settings
    PORTAL_DOMAIN: str = "admin.local"
    PORTAL_URL: str = "http://10.2.49.27:3000"
    ENABLE_IP_MASKING: bool = True
    
    # PakApp API Security
    PAKAPP_API_KEY: str = ""  # Set a strong API key for PakApp
    PAKAPP_ENABLE_API_KEY: bool = True  # Require API key for PakApp endpoints
    PAKAPP_ALLOWED_IPS: str = ""  # Comma-separated IPs (e.g., "1.2.3.4,5.6.7.8") - empty means all IPs allowed
    PAKAPP_ENABLE_SIGNATURE: bool = False  # Enable HMAC signature verification
    PAKAPP_SIGNATURE_SECRET: str = ""  # Shared secret for HMAC signature
    
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
