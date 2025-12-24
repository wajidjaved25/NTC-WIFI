from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
import os

from .config import settings
from .database import engine, Base
from .services.data_limit_enforcer import data_limit_enforcer
from .services.fortigate_syslog_receiver import syslog_receiver
from .services.coa_service import coa_service

# Import all models (required for SQLAlchemy to create tables)
from .models import (
    Admin, User, PortalDesign, PortalSettings,
    Advertisement, AdAnalytics, Session, OmadaConfig,
    DailyUsage, SystemLog, OTP, FirewallLog, FirewallImportJob, IPDRSearchHistory,
    Site, NASClient
)

# Import routes
from .routes import auth, omada, records, ads, portal, dashboard, public, radius_admin, ipdr, user_management, admin_management, site_management

# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    description="Admin Portal for NTC WiFi Captive Portal Management",
    version="1.0.0",
    docs_url="/api/docs" if settings.ENABLE_API_DOCS else None,
    redoc_url="/api/redoc" if settings.ENABLE_API_DOCS else None
)

if settings.ENABLE_API_DOCS:
    print("📚 API Documentation: ENABLED (ensure this is disabled in production!)")
else:
    print("📚 API Documentation: DISABLED (production mode)")

# Initialize Rate Limiter with Redis backend
from .limiter import limiter

limiter.storage_uri = settings.REDIS_URL  # Set Redis storage
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
print("⏱️ Rate limiting: Enabled (Redis backend)")

# CORS Middleware - Production Safe Configuration
# Define allowed origins based on environment
ALLOWED_ORIGINS = []

if settings.APP_ENV == "development":
    ALLOWED_ORIGINS = [
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:5173",
    ]
    print("🌐 CORS: Development mode - localhost allowed")
else:
    # Production origins - Configure these in .env file
    ALLOWED_ORIGINS = settings.origins_list
    print(f"🌐 CORS: Production mode - {len(ALLOWED_ORIGINS)} origins allowed")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    allow_headers=["*"],
    max_age=3600,
)

# Security Headers Middleware
from .middleware.security import SecurityHeadersMiddleware
app.add_middleware(SecurityHeadersMiddleware)
print("🔒 Security headers middleware enabled")

# Mount static files directory for media
MEDIA_BASE = "D:/Codes/NTC/NTC Public Wifi/media"
os.makedirs(os.path.join(MEDIA_BASE, "ads"), exist_ok=True)
os.makedirs(os.path.join(MEDIA_BASE, "portal"), exist_ok=True)

app.mount("/media", StaticFiles(directory=MEDIA_BASE), name="media")

# Include routers
app.include_router(auth.router, prefix="/api")
app.include_router(dashboard.router, prefix="/api")
app.include_router(omada.router, prefix="/api")
app.include_router(records.router, prefix="/api")
app.include_router(ads.router, prefix="/api")
app.include_router(portal.router, prefix="/api")
app.include_router(public.router, prefix="/api")  # Public API for portal
app.include_router(radius_admin.router, prefix="/api")  # RADIUS admin routes
app.include_router(ipdr.router, prefix="/api")  # IPDR reports
app.include_router(user_management.router, prefix="/api")  # WiFi user management
app.include_router(admin_management.router, prefix="/api")  # Admin user management
app.include_router(site_management.router, prefix="/api")  # Site management

@app.on_event("startup")
async def startup_event():
    """Initialize database and create tables"""
    Base.metadata.create_all(bind=engine)
    print(f"✅ {settings.APP_NAME} Started Successfully")
    print(f"📍 Environment: {settings.APP_ENV}")
    print(f"🔗 Database: Connected")
    print(f"📁 Media Directory: {MEDIA_BASE}")
    
    # Initialize CoA service with site configurations
    from .database import SessionLocal
    db = SessionLocal()
    try:
        coa_service.load_sites_config(db)
        print(f"📡 CoA Service: Initialized with {len(coa_service.sites_config)} sites")
    except Exception as e:
        print(f"⚠️  CoA Service: Failed to initialize - {e}")
    finally:
        db.close()
    
    # Start data limit enforcement
    await data_limit_enforcer.start()
    
    # Start FortiGate syslog receiver
    try:
        syslog_receiver.start()
        print(f"🔥 FortiGate Syslog Receiver: Started on port {syslog_receiver.port}")
    except Exception as e:
        print(f"⚠️  FortiGate Syslog Receiver: Failed to start - {e}")
        print(f"    Note: Port 514 requires root/admin privileges")
        print(f"    Consider using port 5140 instead")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    # Stop data limit enforcer
    await data_limit_enforcer.stop()
    
    # Stop syslog receiver
    syslog_receiver.stop()
    
    print(f"🛑 {settings.APP_NAME} Shutting Down...")

@app.get("/")
async def root():
    return {
        "message": f"Welcome to {settings.APP_NAME}",
        "version": "1.0.0",
        "status": "running",
        "docs": "/api/docs" if settings.DEBUG else "disabled"
    }

@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "environment": settings.APP_ENV,
        "database": "connected"
    }
