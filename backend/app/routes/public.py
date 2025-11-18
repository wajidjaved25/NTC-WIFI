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
from ..services.radius_service import RadiusService
from ..services.radius_auth_client import RadiusAuthClient
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
    
    try:
        mobile = data.mobile.strip()
        
        if not mobile.startswith('03') or len(mobile) != 11:
            raise HTTPException(status_code=400, detail="Invalid mobile number format")
        
        otp_code = generate_otp()
        
        db.query(OTP).filter(OTP.mobile == mobile).delete()
        
        new_otp = OTP(
            mobile=mobile,
            otp=otp_code,
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=5)
        )
        db.add(new_otp)
        db.commit()
        
        try:
            await send_otp_sms(mobile, otp_code)
        except Exception as e:
            print(f"SMS failed: {e}")
        
        return {"success": True, "message": "OTP sent successfully"}
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/verify-otp")
async def verify_otp(data: OTPVerify, db: Session = Depends(get_db)):
    """Verify OTP code"""
    
    mobile = data.mobile.strip()
    otp_code = data.otp.strip()
    
    otp_record = db.query(OTP).filter(
        OTP.mobile == mobile,
        OTP.otp == otp_code,
        OTP.verified == False,
        OTP.expires_at > datetime.now(timezone.utc)
    ).first()
    
    if not otp_record:
        raise HTTPException(status_code=400, detail="Invalid or expired OTP")
    
    otp_record.verified = True
    db.commit()
    
    return {"success": True, "message": "OTP verified successfully"}


@router.post("/register")
async def register_user(data: UserRegister, db: Session = Depends(get_db)):
    """Register user and create RADIUS account"""
    
    mobile = data.mobile.strip()
    
    user = db.query(User).filter(User.mobile == mobile).first()
    
    if user:
        user.name = data.name
        user.id_type = data.id_type
        user.cnic = data.cnic if data.id_type == 'cnic' else None
        user.passport = data.passport if data.id_type == 'passport' else None
        user.terms_accepted = data.terms_accepted
        user.terms_accepted_at = datetime.now(timezone.utc)
        user.last_login = datetime.now(timezone.utc)
    else:
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
    
    # Create RADIUS user with settings from database
    radius_password = data.cnic if data.id_type == 'cnic' else data.passport
    radius_service = RadiusService(db)
    
    try:
        # Get RADIUS settings
        from ..models.radius_settings import RadiusSettings
        radius_settings = db.query(RadiusSettings).first()
        
        session_timeout = 3600  # Default 1 hour
        bandwidth_down = None
        bandwidth_up = None
        
        if radius_settings:
            session_timeout = radius_settings.default_session_timeout
            if radius_settings.default_bandwidth_down > 0:
                bandwidth_down = radius_settings.default_bandwidth_down * 1000  # Convert to bps
            if radius_settings.default_bandwidth_up > 0:
                bandwidth_up = radius_settings.default_bandwidth_up * 1000
        
        radius_created = radius_service.create_radius_user(
            username=mobile,
            password=radius_password,
            session_timeout=session_timeout,
            bandwidth_down=bandwidth_down,
            bandwidth_up=bandwidth_up
        )
        
        if radius_created:
            print(f"✓ RADIUS user created: {mobile} (timeout: {session_timeout}s)")
        else:
            print(f"✗ RADIUS user creation failed: {mobile}")
    except Exception as e:
        print(f"✗ RADIUS error: {e}")
    
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
    """
    Authorize WiFi via RADIUS authentication
    
    When Omada uses RADIUS auth, Access-Accept grants network access automatically
    """
    
    print(f"\n{'='*60}")
    print(f"=== WIFI AUTHORIZATION ===")
    print(f"Mobile: {data.mobile}")
    print(f"{'='*60}\n")
    
    user = None
    if data.user_id:
        user = db.query(User).filter(User.id == data.user_id).first()
    elif data.mobile:
        user = db.query(User).filter(User.mobile == data.mobile).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user.is_blocked:
        raise HTTPException(status_code=403, detail="User is blocked")
    
    omada_config = db.query(OmadaConfig).filter(OmadaConfig.is_active == True).first()
    if not omada_config:
        raise HTTPException(status_code=500, detail="No Omada configuration")
    
    user_password = user.cnic if user.id_type == 'cnic' else user.passport
    
    session = WiFiSession(
        user_id=user.id,
        mac_address=data.mac_address or "pending",
        ap_mac=data.ap_mac,
        ssid=data.ssid,
        start_time=datetime.now(timezone.utc),
        session_status='authenticating'
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    
    try:
        # RADIUS Server Authentication Flow:
        # 1. RADIUS user already created during registration
        # 2. Authenticate via RADIUS to validate credentials
        # 3. For RADIUS Server type portal, we just need to confirm auth succeeded
        #    The client will be authorized by Omada when it receives RADIUS Access-Accept
        
        print("[Step 1: RADIUS Authentication]")
        radius_client = RadiusAuthClient(
            radius_server="127.0.0.1",
            radius_secret="testing123"
        )
        
        radius_result = radius_client.authenticate(
            username=user.mobile,
            password=user_password,
            nas_ip="192.168.3.254"
        )
        
        if not radius_result.get('success'):
            session.session_status = 'failed'
            session.end_time = datetime.now(timezone.utc)
            db.commit()
            raise HTTPException(
                status_code=401,
                detail=f"RADIUS authentication failed: {radius_result.get('message')}"
            )
        
        print(f"✓ RADIUS authentication successful")
        
        # For RADIUS Server + External Portal configuration:
        # We need to call Omada's External Portal API to authorize the client
        # This tells Omada to grant access, and Omada will record it in its session
        
        print("[Step 2: Submit to Omada RADIUS Auth Endpoint]")
        
        # For RADIUS Server + External Web Portal:
        # We need to POST credentials to Omada's /portal/radius/browserauth endpoint
        # Omada will then verify with RADIUS server and authorize the client
        
        # Build the Omada RADIUS auth URL
        # Default portal port is 8843 for HTTPS
        import re
        controller_match = re.search(r'https?://([^:/]+)', omada_config.controller_url)
        controller_ip = controller_match.group(1) if controller_match else '192.168.0.1'
        
        # For browserauth, we need to redirect the client with a form POST
        # The frontend will handle this redirect
        
        # Normalize MAC addresses (Omada expects uppercase with hyphens)
        def normalize_mac(mac):
            if not mac:
                return mac
            mac_clean = mac.replace(':', '').replace('-', '').replace('.', '').upper()
            return '-'.join(mac_clean[i:i+2] for i in range(0, 12, 2))
        
        client_mac = normalize_mac(data.mac_address)
        ap_mac_normalized = normalize_mac(data.ap_mac) if data.ap_mac else ''
        
        # Build the browserauth URL and form data
        # Port 8088 is HTTP portal, 8843 is HTTPS portal
        # Using HTTP to avoid SSL certificate issues with self-signed certs
        browserauth_url = f"http://{controller_ip}:8088/portal/radius/browserauth"
        
        # Prepare form data for browserauth
        auth_form_data = {
            "clientMac": client_mac,
            "apMac": ap_mac_normalized,
            "ssidName": data.ssid or '',
            "radioId": 0,  # 0 for 2.4GHz, 1 for 5GHz
            "authType": 2,  # 2 for External RADIUS
            "originUrl": omada_config.redirect_url or "http://www.google.com",
            "username": user.mobile,
            "password": user_password
        }
        
        print(f"Browserauth URL: {browserauth_url}")
        print(f"Form data: {auth_form_data}")
        
        # Update session status
        session.session_status = 'pending_browserauth'
        user.total_sessions += 1
        user.last_login = datetime.now(timezone.utc)
        db.commit()
        
        print(f"\n{'='*60}")
        print(f"✓✓✓ RADIUS AUTHENTICATION READY ✓✓✓")
        print(f"User: {user.mobile}")
        print(f"MAC: {client_mac}")
        print(f"Duration: {radius_result.get('session_timeout', 3600)}s")
        print(f"Redirect to: {browserauth_url}")
        print(f"{'='*60}\n")
        
        return {
            "success": True,
            "message": "RADIUS ready. Submitting to Omada...",
            "session_id": session.id,
            "duration": radius_result.get('session_timeout', 3600),
            "auth_method": "radius_browserauth",
            "radius_authenticated": True,
            "browserauth_url": browserauth_url,
            "form_data": auth_form_data,
            "redirect_url": omada_config.redirect_url or "http://www.google.com"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        session.session_status = 'failed'
        session.end_time = datetime.now(timezone.utc)
        db.commit()
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# ========== ADVERTISEMENTS ==========

@router.get("/ads/active")
async def get_active_ads(db: Session = Depends(get_db)):
    """Get active ads"""
    
    now = datetime.now(timezone.utc)
    
    ads = db.query(Advertisement).filter(
        Advertisement.is_active == True,
        func.coalesce(Advertisement.start_date, now) <= now,
        func.coalesce(Advertisement.end_date, now + timedelta(days=365)) >= now
    ).order_by(Advertisement.display_order).all()
    
    import os
    
    return {
        "success": True,
        "ads": [{
            "id": ad.id,
            "title": ad.title,
            "description": ad.description,
            "ad_type": ad.ad_type,
            "file_path": f"/media/ads/{os.path.basename(ad.file_path)}",
            "link_url": getattr(ad, 'link_url', None),
            "display_duration": ad.display_duration,
            "enable_skip": getattr(ad, 'auto_skip', False),
            "skip_after_seconds": getattr(ad, 'skip_after', 5)
        } for ad in ads]
    }


@router.post("/ads/track")
async def track_ad(data: AdTrack, request: Request, db: Session = Depends(get_db)):
    """Track ad event"""
    
    analytics = AdAnalytics(
        ad_id=data.ad_id,
        event_type=data.event_type,
        user_id=data.user_id,
        mac_address=data.mac_address,
        watch_duration=data.watch_duration,
        ip_address=request.client.host,
        user_agent=request.headers.get("user-agent"),
        event_timestamp=datetime.now(timezone.utc)
    )
    db.add(analytics)
    
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


@router.get("/health")
async def health_check():
    return {"status": "ok", "service": "ntc-wifi-portal"}
