from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from datetime import datetime
import os
import shutil

from ..database import get_db
from ..models.admin import Admin
from ..models.advertisement import Advertisement
from ..schemas.advertisement import (
    AdvertisementCreate, AdvertisementUpdate, AdvertisementResponse, AdAnalyticsResponse
)
from ..utils.security import get_current_user, has_permission
from ..utils.helpers import sanitize_filename, is_within_schedule, log_system_event

router = APIRouter(prefix="/ads", tags=["Advertisements"])

# Media storage path
MEDIA_DIR = "D:/Codes/NTC/NTC Public Wifi/media/ads"
os.makedirs(MEDIA_DIR, exist_ok=True)

# Middleware to check ads permission
def require_ads_permission(current_user: Admin = Depends(get_current_user)):
    if not has_permission(current_user, "manage_ads"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to manage advertisements"
        )
    return current_user

# Get all advertisements
@router.get("/", response_model=List[AdvertisementResponse])
async def get_advertisements(
    current_user: Admin = Depends(require_ads_permission),
    db: Session = Depends(get_db),
    active_only: bool = False
):
    query = db.query(Advertisement)
    
    if active_only:
        query = query.filter(Advertisement.is_active == True)
    
    ads = query.order_by(Advertisement.display_order, Advertisement.created_at.desc()).all()
    
    # Transform file paths to HTTP URLs
    result = []
    for ad in ads:
        ad_dict = {
            "id": ad.id,
            "title": ad.title,
            "description": ad.description,
            "ad_type": ad.ad_type,
            "file_path": f"/media/ads/{os.path.basename(ad.file_path)}",
            "file_name": ad.file_name,
            "file_size": ad.file_size,
            "mime_type": ad.mime_type,
            "display_duration": ad.display_duration,
            "display_order": ad.display_order,
            "auto_skip": ad.auto_skip,
            "skip_after": ad.skip_after,
            "is_active": ad.is_active,
            "start_date": ad.start_date,
            "end_date": ad.end_date,
            "auto_disable": ad.auto_disable,
            "view_count": ad.view_count,
            "click_count": ad.click_count,
            "skip_count": ad.skip_count,
            "created_at": ad.created_at,
            "updated_at": ad.updated_at
        }
        result.append(ad_dict)
    
    return result

# Get active advertisements for user portal
@router.get("/active")
async def get_active_ads(db: Session = Depends(get_db)):
    """Get currently active ads for display on user portal"""
    now = datetime.now()
    
    ads = db.query(Advertisement).filter(
        Advertisement.is_active == True
    ).order_by(Advertisement.display_order).all()
    
    # Filter by schedule
    active_ads = []
    for ad in ads:
        if is_within_schedule(ad.start_date, ad.end_date):
            active_ads.append({
                "id": ad.id,
                "title": ad.title,
                "ad_type": ad.ad_type,
                "file_path": f"/media/ads/{os.path.basename(ad.file_path)}",
                "display_duration": ad.display_duration,
                "auto_skip": ad.auto_skip,
                "skip_after": ad.skip_after
            })
    
    return {"ads": active_ads}

# Get single advertisement
@router.get("/{ad_id}", response_model=AdvertisementResponse)
async def get_advertisement(
    ad_id: int,
    current_user: Admin = Depends(require_ads_permission),
    db: Session = Depends(get_db)
):
    ad = db.query(Advertisement).filter(Advertisement.id == ad_id).first()
    if not ad:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Advertisement not found"
        )
    
    # Transform file path to HTTP URL
    return {
        "id": ad.id,
        "title": ad.title,
        "description": ad.description,
        "ad_type": ad.ad_type,
        "file_path": f"/media/ads/{os.path.basename(ad.file_path)}",
        "file_name": ad.file_name,
        "file_size": ad.file_size,
        "mime_type": ad.mime_type,
        "display_duration": ad.display_duration,
        "display_order": ad.display_order,
        "auto_skip": ad.auto_skip,
        "skip_after": ad.skip_after,
        "is_active": ad.is_active,
        "start_date": ad.start_date,
        "end_date": ad.end_date,
        "auto_disable": ad.auto_disable,
        "view_count": ad.view_count,
        "click_count": ad.click_count,
        "skip_count": ad.skip_count,
        "created_at": ad.created_at,
        "updated_at": ad.updated_at
    }

# Upload advertisement
@router.post("/", response_model=AdvertisementResponse)
async def create_advertisement(
    file: UploadFile = File(...),
    title: str = Form(...),
    description: Optional[str] = Form(None),
    ad_type: str = Form(...),
    display_duration: int = Form(10),
    display_order: int = Form(0),
    auto_skip: bool = Form(False),
    skip_after: int = Form(5),
    is_active: bool = Form(True),
    start_date: Optional[str] = Form(None),
    end_date: Optional[str] = Form(None),
    auto_disable: bool = Form(False),
    current_user: Admin = Depends(require_ads_permission),
    db: Session = Depends(get_db)
):
    # Validate ad type
    if ad_type not in ['video', 'image', 'download']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid ad type"
        )
    
    # Validate file type
    allowed_extensions = {
        'video': ['.mp4', '.webm', '.ogg', '.mov'],
        'image': ['.jpg', '.jpeg', '.png', '.gif', '.webp'],
        'download': ['.pdf', '.doc', '.docx', '.zip']
    }
    
    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in allowed_extensions[ad_type]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type for {ad_type}. Allowed: {', '.join(allowed_extensions[ad_type])}"
        )
    
    # Generate unique filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_filename = sanitize_filename(file.filename)
    filename = f"{timestamp}_{safe_filename}"
    file_path = os.path.join(MEDIA_DIR, filename)
    
    # Save file
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        file_size = os.path.getsize(file_path)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save file: {str(e)}"
        )
    
    # Parse dates
    start_date_obj = datetime.fromisoformat(start_date) if start_date else None
    end_date_obj = datetime.fromisoformat(end_date) if end_date else None
    
    # Create advertisement record
    ad = Advertisement(
        title=title,
        description=description,
        ad_type=ad_type,
        file_path=file_path,
        file_name=filename,
        file_size=file_size,
        mime_type=file.content_type,
        display_duration=display_duration,
        display_order=display_order,
        auto_skip=auto_skip,
        skip_after=skip_after,
        is_active=is_active,
        start_date=start_date_obj,
        end_date=end_date_obj,
        auto_disable=auto_disable,
        created_by=current_user.id
    )
    
    db.add(ad)
    db.commit()
    db.refresh(ad)
    
    # Log the action
    await log_system_event(
        db, "INFO", "ads", "ad_created",
        f"Advertisement '{title}' created",
        {"ad_id": ad.id, "ad_type": ad_type},
        current_user.id
    )
    
    # Return with HTTP URL instead of file path
    return {
        "id": ad.id,
        "title": ad.title,
        "description": ad.description,
        "ad_type": ad.ad_type,
        "file_path": f"/media/ads/{os.path.basename(ad.file_path)}",
        "file_name": ad.file_name,
        "file_size": ad.file_size,
        "mime_type": ad.mime_type,
        "display_duration": ad.display_duration,
        "display_order": ad.display_order,
        "auto_skip": ad.auto_skip,
        "skip_after": ad.skip_after,
        "is_active": ad.is_active,
        "start_date": ad.start_date,
        "end_date": ad.end_date,
        "auto_disable": ad.auto_disable,
        "view_count": ad.view_count,
        "click_count": ad.click_count,
        "skip_count": ad.skip_count,
        "created_at": ad.created_at,
        "updated_at": ad.updated_at
    }

# Update advertisement
@router.patch("/{ad_id}", response_model=AdvertisementResponse)
async def update_advertisement(
    ad_id: int,
    title: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    display_duration: Optional[int] = Form(None),
    display_order: Optional[int] = Form(None),
    auto_skip: Optional[bool] = Form(None),
    skip_after: Optional[int] = Form(None),
    is_active: Optional[bool] = Form(None),
    start_date: Optional[str] = Form(None),
    end_date: Optional[str] = Form(None),
    auto_disable: Optional[bool] = Form(None),
    current_user: Admin = Depends(require_ads_permission),
    db: Session = Depends(get_db)
):
    ad = db.query(Advertisement).filter(Advertisement.id == ad_id).first()
    if not ad:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Advertisement not found"
        )
    
    # Update fields only if provided
    updated_fields = []
    if title is not None:
        ad.title = title
        updated_fields.append('title')
    if description is not None:
        ad.description = description
        updated_fields.append('description')
    if display_duration is not None:
        ad.display_duration = display_duration
        updated_fields.append('display_duration')
    if display_order is not None:
        ad.display_order = display_order
        updated_fields.append('display_order')
    if auto_skip is not None:
        ad.auto_skip = auto_skip
        updated_fields.append('auto_skip')
    if skip_after is not None:
        ad.skip_after = skip_after
        updated_fields.append('skip_after')
    if is_active is not None:
        ad.is_active = is_active
        updated_fields.append('is_active')
    if start_date is not None:
        ad.start_date = datetime.fromisoformat(start_date) if start_date else None
        updated_fields.append('start_date')
    if end_date is not None:
        ad.end_date = datetime.fromisoformat(end_date) if end_date else None
        updated_fields.append('end_date')
    if auto_disable is not None:
        ad.auto_disable = auto_disable
        updated_fields.append('auto_disable')
    
    db.commit()
    db.refresh(ad)
    
    # Log the action
    await log_system_event(
        db, "INFO", "ads", "ad_updated",
        f"Advertisement '{ad.title}' updated",
        {"ad_id": ad.id, "updated_fields": updated_fields},
        current_user.id
    )
    
    # Return with HTTP URL
    return {
        "id": ad.id,
        "title": ad.title,
        "description": ad.description,
        "ad_type": ad.ad_type,
        "file_path": f"/media/ads/{os.path.basename(ad.file_path)}",
        "file_name": ad.file_name,
        "file_size": ad.file_size,
        "mime_type": ad.mime_type,
        "display_duration": ad.display_duration,
        "display_order": ad.display_order,
        "auto_skip": ad.auto_skip,
        "skip_after": ad.skip_after,
        "is_active": ad.is_active,
        "start_date": ad.start_date,
        "end_date": ad.end_date,
        "auto_disable": ad.auto_disable,
        "view_count": ad.view_count,
        "click_count": ad.click_count,
        "skip_count": ad.skip_count,
        "created_at": ad.created_at,
        "updated_at": ad.updated_at
    }

# Delete advertisement
@router.delete("/{ad_id}")
async def delete_advertisement(
    ad_id: int,
    current_user: Admin = Depends(require_ads_permission),
    db: Session = Depends(get_db)
):
    ad = db.query(Advertisement).filter(Advertisement.id == ad_id).first()
    if not ad:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Advertisement not found"
        )
    
    # Delete file
    try:
        if os.path.exists(ad.file_path):
            os.remove(ad.file_path)
    except Exception as e:
        # Log error but don't fail the deletion
        print(f"Failed to delete file: {e}")
    
    ad_title = ad.title
    db.delete(ad)
    db.commit()
    
    # Log the action
    await log_system_event(
        db, "INFO", "ads", "ad_deleted",
        f"Advertisement '{ad_title}' deleted",
        {"ad_id": ad_id},
        current_user.id
    )
    
    return {"success": True, "message": "Advertisement deleted"}

# Toggle ad status
@router.post("/{ad_id}/toggle")
async def toggle_ad_status(
    ad_id: int,
    current_user: Admin = Depends(require_ads_permission),
    db: Session = Depends(get_db)
):
    ad = db.query(Advertisement).filter(Advertisement.id == ad_id).first()
    if not ad:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Advertisement not found"
        )
    
    ad.is_active = not ad.is_active
    db.commit()
    
    status_text = "activated" if ad.is_active else "deactivated"
    
    # Log the action
    await log_system_event(
        db, "INFO", "ads", "ad_toggled",
        f"Advertisement '{ad.title}' {status_text}",
        {"ad_id": ad.id, "is_active": ad.is_active},
        current_user.id
    )
    
    return {
        "success": True,
        "message": f"Advertisement {status_text}",
        "is_active": ad.is_active
    }

# Get ad analytics
@router.get("/{ad_id}/analytics")
async def get_ad_analytics(
    ad_id: int,
    current_user: Admin = Depends(require_ads_permission),
    db: Session = Depends(get_db)
):
    from ..models.ad_analytics import AdAnalytics
    
    ad = db.query(Advertisement).filter(Advertisement.id == ad_id).first()
    if not ad:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Advertisement not found"
        )
    
    # Get analytics data
    total_views = db.query(func.count(AdAnalytics.id)).filter(
        AdAnalytics.ad_id == ad_id,
        AdAnalytics.event_type == 'view'
    ).scalar() or 0
    
    total_clicks = db.query(func.count(AdAnalytics.id)).filter(
        AdAnalytics.ad_id == ad_id,
        AdAnalytics.event_type == 'click'
    ).scalar() or 0
    
    total_skips = db.query(func.count(AdAnalytics.id)).filter(
        AdAnalytics.ad_id == ad_id,
        AdAnalytics.event_type == 'skip'
    ).scalar() or 0
    
    avg_watch_duration = db.query(func.avg(AdAnalytics.watch_duration)).filter(
        AdAnalytics.ad_id == ad_id,
        AdAnalytics.watch_duration.isnot(None)
    ).scalar() or 0
    
    # Calculate rates
    ctr = (total_clicks / total_views * 100) if total_views > 0 else 0
    completion_rate = ((total_views - total_skips) / total_views * 100) if total_views > 0 else 0
    
    return {
        "ad_id": ad.id,
        "ad_title": ad.title,
        "total_views": total_views,
        "total_clicks": total_clicks,
        "total_skips": total_skips,
        "average_watch_duration": round(avg_watch_duration, 2),
        "click_through_rate": round(ctr, 2),
        "completion_rate": round(completion_rate, 2)
    }
