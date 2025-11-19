from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

from .config import settings
from .database import engine, Base
from .services.data_limit_enforcer import data_limit_enforcer

# Import all models (required for SQLAlchemy to create tables)
from .models import (
    Admin, User, PortalDesign, PortalSettings,
    Advertisement, AdAnalytics, Session, OmadaConfig,
    DailyUsage, SystemLog, OTP
)

# Import routes
from .routes import auth, omada, records, ads, portal, dashboard, public, radius_admin

# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    description="Admin Portal for NTC WiFi Captive Portal Management",
    version="1.0.0",
    docs_url="/api/docs" if settings.DEBUG else None,
    redoc_url="/api/redoc" if settings.DEBUG else None
)

# CORS Middleware - Allow all origins in development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Temporary: Allow all origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

print("🌐 CORS: Allowing all origins (development mode)")

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

@app.on_event("startup")
async def startup_event():
    """Initialize database and create tables"""
    Base.metadata.create_all(bind=engine)
    print(f"✅ {settings.APP_NAME} Started Successfully")
    print(f"📍 Environment: {settings.APP_ENV}")
    print(f"🔗 Database: Connected")
    print(f"📁 Media Directory: {MEDIA_BASE}")
    
    # Start data limit enforcement
    await data_limit_enforcer.start()

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    # Stop data limit enforcer
    await data_limit_enforcer.stop()
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
