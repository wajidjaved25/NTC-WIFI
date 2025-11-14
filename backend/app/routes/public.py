"""
Public API Routes
For public portal - user registration, OTP, WiFi authorization, ads
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional
from datetime import datetime, timedelta, timezone
from pydantic import BaseModel

from ..database import get_db
from ..models.portal_design import PortalDesign
from ..models.user import User
from ..models.otp import OTP
from ..models.session import Session as WiFiSession
from ..models.advertisement import Advertisement
from ..models.ad_analytics import AdAnalytics
from ..services.ad_service import AdDisplayService
from ..services.omada_service import OmadaService
from ..models.omada_config import OmadaConfig
from ..utils.helpers import send_otp_sms, generate_otp

router = APIRouter(prefix="/public", tags=["Public API"])


# Schemas
class OTPRequest(BaseModel):
    mobile: str

class OTPVerify(BaseModel):
    mobile: str
    otp: str

class UserRegister(BaseModel):
    name: str
    mobile: str
    id_type: str
    cnic: Optional[str] = None
    passport: Optional[str] = None
    terms_accepted: bool

class WiFiAuth(BaseModel):
    user_id: Optional[int] = None
    mobile: Optional[str] = None
    mac_address: Optional[str] = None
    ap_mac: Optional[str] = None
    ssid: Optional[str] = None

class AdTrack(BaseModel):
    ad_id: int
    event_type: str  # view, click, skip, complete
    user_id: Optional[int] = None
    mobile: Optional[str] = None
    mac_address: Optional[str] = None
    watch_duration: Optional[int] = None

class AdViewTrack(BaseModel):
    ad_id: int
    user_id: Optional[int] = None
    mac_address: Optional[str] = None

class AdClickTrack(BaseModel):
    ad_id: int
    user_id: Optional[int] = None
    mac_address: Optional[str] = None

class AdSkipTrack(BaseModel):
    ad_id: int
    watch_duration: int
    user_id: Optional[int] = None
    mac_address: Optional[str] = None

class AdCompleteTrack(BaseModel):
    ad_id: int
    watch_duration: int
    user_id: Optional[int] = None
    mac_address: Optional[str] = None


# ========== PORTAL DESIGN ==========

@router.get("/portal-design")
async def get_portal_design(db: Session = Depends(get_db)):
    """Get active portal design for public WiFi page"""
    
    design = db.query(PortalDesign).filter(
        PortalDesign.is_active == True
    ).order_by(PortalDesign.updated_at.desc()).first()
    
    if not design:
        # Return default design if none active
        return {
            "template_name": "Default",
            "welcome_title": "Welcome to Free WiFi",
            "welcome_text": "Please register to connect",
            "terms_text": "<p>By using this service, you agree to our terms and conditions.</p>",
            "terms_checkbox_text": "I accept the terms and conditions",
            "footer_text": "© 2025 NTC Public WiFi",
            "primary_color": "#1890ff",
            "secondary_color": "#ffffff",
            "accent_color": "#52c41a",
            "text_color": "#000000",
            "background_color": "#f0f2f5"
        }
    
    return {
        "id": design.id,
        "template_name": design.template_name,
        "logo_path": design.logo_path,
        "background_image": design.background_image,
        "primary_color": design.primary_color,
        "secondary_color": design.secondary_color,
        "accent_color": design.accent_color,
        "text_color": design.text_color,
        "background_color": design.background_color,
        "welcome_title": design.welcome_title,
        "welcome_text": design.welcome_text,
        "terms_text": design.terms_text,
        "terms_checkbox_text": design.terms_checkbox_text,
        "footer_text": design.footer_text,
        "custom_css": design.custom_css,
        "custom_js": design.custom_js,
        "layout_type": design.layout_type
    }


# ========== OTP & AUTHENTICATION ==========

@router.post("/send-otp")
async def send_otp(data: OTPRequest, db: Session = Depends(get_db)):
    """Send OTP to mobile number"""
    
    print(f"\n=== SEND OTP REQUEST ===")
    print(f"Mobile: {data.mobile}")
    
    try:
        # Validate mobile format
        mobile = data.mobile.strip()
        print(f"Stripped mobile: {mobile}")
        
        if not mobile.startswith('03') or len(mobile) != 11:
            print(f"Invalid mobile format: {mobile}")
            raise HTTPException(status_code=400, detail="Invalid mobile number format (use 03XXXXXXXXX)")
        
        # Generate OTP
        otp_code = generate_otp()
        print(f"Generated OTP: {otp_code}")
        
        # Delete old OTPs for this mobile
        db.query(OTP).filter(OTP.mobile == mobile).delete()
        print(f"Deleted old OTPs")
        
        # Create new OTP
        new_otp = OTP(
            mobile=mobile,
            otp_code=otp_code,
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=5)
        )
        db.add(new_otp)
        db.commit()
        print(f"OTP saved to database")
        
        # Send SMS
        try:
            print(f"Attempting to send SMS...")
            result = await send_otp_sms(mobile, otp_code)
            print(f"SMS result: {result}")
        except Exception as e:
            # Log error but don't fail - OTP is still valid
            print(f"SMS sending failed: {e}")
            import traceback
            traceback.print_exc()
        
        print(f"Returning success response")
        return {"success": True, "message": "OTP sent successfully"}
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"\nERROR in send_otp: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/verify-otp")
async def verify_otp(data: OTPVerify, db: Session = Depends(get_db)):
    """Verify OTP code"""
    
    mobile = data.mobile.strip()
    otp_code = data.otp.strip()
    
    # Find OTP
    otp_record = db.query(OTP).filter(
        OTP.mobile == mobile,
        OTP.otp_code == otp_code,
        OTP.is_used == False,
        OTP.expires_at > datetime.now(timezone.utc)
    ).first()
    
    if not otp_record:
        raise HTTPException(status_code=400, detail="Invalid or expired OTP")
    
    # Mark as used
    otp_record.is_used = True
    otp_record.verified_at = datetime.now(timezone.utc)
    db.commit()
    
    return {"success": True, "message": "OTP verified successfully"}


@router.post("/register")
async def register_user(data: UserRegister, db: Session = Depends(get_db)):
    """Register or update user"""
    
    mobile = data.mobile.strip()
    
    # Check if user exists
    user = db.query(User).filter(User.mobile == mobile).first()
    
    if user:
        # Update existing user
        user.name = data.name
        user.id_type = data.id_type
        user.cnic = data.cnic if data.id_type == 'cnic' else None
        user.passport = data.passport if data.id_type == 'passport' else None
        user.terms_accepted = data.terms_accepted
        user.terms_accepted_at = datetime.now(timezone.utc)
        user.last_login = datetime.now(timezone.utc)
    else:
        # Create new user
        user = User(
            name=data.name,
            mobile=mobile,
            id_type=data.id_type,
            cnic=data.cnic if data.id_type == 'cnic' else None,
            passport=data.passport if data.id_type == 'passport' else None,
            terms_accepted=data.terms_accepted,
            terms_accepted_at=datetime.now(timezone.utc),
            last_login=datetime.now(timezone.utc)
        )
        db.add(user)
    
    db.commit()
    db.refresh(user)
    
    return {
        "success": True,
        "user": {
            "id": user.id,
            "name": user.name,
            "mobile": user.mobile
        }
    }


@router.post("/authorize")
async def authorize_wifi(data: WiFiAuth, db: Session = Depends(get_db)):
    """Authorize WiFi access"""
    
    # Get user
    user = None
    if data.user_id:
        user = db.query(User).filter(User.id == data.user_id).first()
    elif data.mobile:
        user = db.query(User).filter(User.mobile == data.mobile).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Check if user is blocked
    if user.is_blocked:
        raise HTTPException(status_code=403, detail="User is blocked")
    
    # Validate MAC address
    if not data.mac_address:
        raise HTTPException(status_code=400, detail="MAC address is required")
    
    # Get active Omada configuration
    omada_config = db.query(OmadaConfig).filter(OmadaConfig.is_active == True).first()
    if not omada_config:
        raise HTTPException(status_code=500, detail="No active Omada configuration found")
    
    # Create session record
    session = WiFiSession(
        user_id=user.id,
        mac_address=data.mac_address,
        ap_mac=data.ap_mac,
        ssid=data.ssid,
        start_time=datetime.now(timezone.utc),
        session_status='active'
    )
    db.add(session)
    
    # Update user stats
    user.total_sessions += 1
    user.last_login = datetime.now(timezone.utc)
    
    db.commit()
    db.refresh(session)
    
    # Call Omada API to authorize client
    try:
        omada = OmadaService(
            controller_url=omada_config.controller_url,
            username=omada_config.username,
            encrypted_password=omada_config.password_encrypted,
            controller_id=omada_config.controller_id,
            site_id=omada_config.site_id
        )
        
        # Authorize the client on Omada controller
        result = omada.authorize_client(
            mac_address=data.mac_address,
            duration=omada_config.session_timeout,
            upload_limit=omada_config.bandwidth_limit_up,
            download_limit=omada_config.bandwidth_limit_down
        )
        
        if not result.get('success'):
            # Rollback session if Omada authorization failed
            session.session_status = 'failed'
            session.disconnect_time = datetime.now(timezone.utc)
            db.commit()
            
            raise HTTPException(
                status_code=500, 
                detail=f"Failed to authorize on WiFi controller: {result.get('message', 'Unknown error')}"
            )
        
        # Update session with Omada response data
        session.session_status = 'active'
        db.commit()
        
        return {
            "success": True,
            "message": "WiFi access authorized successfully",
            "session_id": session.id,
            "duration": omada_config.session_timeout,
            "redirect_url": omada_config.redirect_url
        }
        
    except Exception as e:
        # Rollback session if any error
        session.session_status = 'failed'
        session.disconnect_time = datetime.now(timezone.utc)
        db.commit()
        
        raise HTTPException(
            status_code=500,
            detail=f"Authorization error: {str(e)}"
        )


# ========== ADVERTISEMENTS ==========

@router.get("/ads/active")
async def get_active_ads(db: Session = Depends(get_db)):
    """Get active advertisements for display"""
    
    now = datetime.now(timezone.utc)
    
    ads = db.query(Advertisement).filter(
        Advertisement.is_active == True,
        func.coalesce(Advertisement.start_date, now) <= now,
        func.coalesce(Advertisement.end_date, now + timedelta(days=365)) >= now
    ).order_by(Advertisement.display_order).all()
    
    import os
    
    # Return wrapped in object to match frontend expectations
    return {
        "success": True,
        "ads": [{
            "id": ad.id,
            "title": ad.title,
            "description": ad.description,
            "ad_type": ad.ad_type,
            "file_path": f"http://localhost:8000/media/ads/{os.path.basename(ad.file_path)}",
            "link_url": getattr(ad, 'link_url', None),
            "display_duration": ad.display_duration,
            "enable_skip": getattr(ad, 'auto_skip', False),
            "skip_after_seconds": getattr(ad, 'skip_after', 5)
        } for ad in ads]
    }


@router.post("/ads/track")
async def track_ad(
    data: AdTrack,
    request: Request,
    db: Session = Depends(get_db)
):
    """Track ad event (view, click, skip, complete)"""
    
    # Get client info
    ip_address = request.client.host
    user_agent = request.headers.get("user-agent")
    
    # Create analytics record
    analytics = AdAnalytics(
        ad_id=data.ad_id,
        event_type=data.event_type,
        user_id=data.user_id,
        mac_address=data.mac_address,
        watch_duration=data.watch_duration,
        ip_address=ip_address,
        user_agent=user_agent,
        event_timestamp=datetime.now(timezone.utc)
    )
    db.add(analytics)
    
    # Update ad counters
    ad = db.query(Advertisement).filter(Advertisement.id == data.ad_id).first()
    if ad:
        if data.event_type == 'view':
            ad.view_count += 1
        elif data.event_type == 'click':
            ad.click_count += 1
        elif data.event_type == 'skip':
            ad.skip_count += 1
    
    db.commit()
    
    return {"success": True}


# ========== LEGACY ENDPOINTS (for PHP portal) ==========

@router.get("/ads")
async def get_ads(
    user_id: Optional[int] = None,
    mac_address: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get active advertisements (legacy endpoint)"""
    
    now = datetime.now(timezone.utc)
    
    ads = db.query(Advertisement).filter(
        Advertisement.is_active == True,
        func.coalesce(Advertisement.start_date, now) <= now,
        func.coalesce(Advertisement.end_date, now + timedelta(days=365)) >= now
    ).order_by(Advertisement.display_order).all()
    
    import os
    
    return {
        "success": True,
        "count": len(ads),
        "ads": [{
            "id": ad.id,
            "title": ad.title,
            "description": ad.description,
            "ad_type": ad.ad_type,
            "file_path": f"http://localhost:8000/media/ads/{os.path.basename(ad.file_path)}",
            "link_url": getattr(ad, 'link_url', None),
            "display_duration": ad.display_duration
        } for ad in ads]
    }


@router.post("/ads/track/view")
async def track_ad_view(
    data: AdViewTrack,
    request: Request,
    db: Session = Depends(get_db)
):
    """Track when an ad is viewed"""
    
    ad_service = AdDisplayService(db)
    
    ip_address = request.client.host
    user_agent = request.headers.get("user-agent")
    
    success = await ad_service.track_ad_view(
        ad_id=data.ad_id,
        user_id=data.user_id,
        mac_address=data.mac_address,
        ip_address=ip_address,
        user_agent=user_agent
    )
    
    return {"success": success}


@router.post("/ads/track/click")
async def track_ad_click(
    data: AdClickTrack,
    request: Request,
    db: Session = Depends(get_db)
):
    """Track when an ad is clicked"""
    
    ad_service = AdDisplayService(db)
    
    ip_address = request.client.host
    user_agent = request.headers.get("user-agent")
    
    success = await ad_service.track_ad_click(
        ad_id=data.ad_id,
        user_id=data.user_id,
        mac_address=data.mac_address,
        ip_address=ip_address,
        user_agent=user_agent
    )
    
    return {"success": success}


@router.post("/ads/track/skip")
async def track_ad_skip(
    data: AdSkipTrack,
    request: Request,
    db: Session = Depends(get_db)
):
    """Track when an ad is skipped"""
    
    ad_service = AdDisplayService(db)
    
    ip_address = request.client.host
    user_agent = request.headers.get("user-agent")
    
    success = await ad_service.track_ad_skip(
        ad_id=data.ad_id,
        watch_duration=data.watch_duration,
        user_id=data.user_id,
        mac_address=data.mac_address,
        ip_address=ip_address,
        user_agent=user_agent
    )
    
    return {"success": success}


@router.post("/ads/track/complete")
async def track_ad_complete(
    data: AdCompleteTrack,
    request: Request,
    db: Session = Depends(get_db)
):
    """Track when an ad is watched completely"""
    
    ad_service = AdDisplayService(db)
    
    ip_address = request.client.host
    user_agent = request.headers.get("user-agent")
    
    success = await ad_service.track_ad_complete(
        ad_id=data.ad_id,
        watch_duration=data.watch_duration,
        user_id=data.user_id,
        mac_address=data.mac_address,
        ip_address=ip_address,
        user_agent=user_agent
    )
    
    return {"success": success}


# Health check
@router.get("/health")
async def health_check():
    """Simple health check endpoint"""
    return {"status": "ok", "service": "ntc-wifi-portal"}
