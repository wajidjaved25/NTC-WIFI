from fastapi import APIRouter, Depends, HTTPException, status, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from datetime import datetime, timedelta, date
from typing import List, Optional
import io
import csv

from ..database import get_db
from ..models.admin import Admin
from ..models.session import Session as WiFiSession
from ..models.user import User
from ..schemas.records import SessionResponse, RecordFilters, ExportRequest, DashboardStats
from ..utils.security import get_current_user, has_permission
from ..services.export_service import ExportService

router = APIRouter(prefix="/records", tags=["Records & Reports"])

# Middleware to check reports permission
def require_reports_permission(current_user: Admin = Depends(get_current_user)):
    if not has_permission(current_user, "view_records"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to view records"
        )
    return current_user

# Get dashboard statistics
@router.get("/dashboard-stats", response_model=DashboardStats)
async def get_dashboard_stats(
    current_user: Admin = Depends(require_reports_permission),
    db: Session = Depends(get_db)
):
    today = date.today()
    today_start = datetime.combine(today, datetime.min.time())
    
    # Total unique users
    total_users = db.query(func.count(User.id)).scalar()
    
    # Active sessions (currently connected)
    active_sessions = db.query(func.count(WiFiSession.id)).filter(
        WiFiSession.session_status == 'active'
    ).scalar()
    
    # Today's sessions
    today_sessions = db.query(func.count(WiFiSession.id)).filter(
        WiFiSession.start_time >= today_start
    ).scalar()
    
    # Today's total data usage
    today_data = db.query(func.sum(WiFiSession.total_data)).filter(
        WiFiSession.start_time >= today_start
    ).scalar() or 0
    
    # Total sessions
    total_sessions = db.query(func.count(WiFiSession.id)).scalar()
    
    # Average session duration
    avg_duration = db.query(func.avg(WiFiSession.duration)).filter(
        WiFiSession.duration.isnot(None)
    ).scalar() or 0
    
    # Peak hour (hour with most sessions today)
    peak_hour_query = db.query(
        func.extract('hour', WiFiSession.start_time).label('hour'),
        func.count(WiFiSession.id).label('count')
    ).filter(
        WiFiSession.start_time >= today_start
    ).group_by('hour').order_by(func.count(WiFiSession.id).desc()).first()
    
    peak_hour = f"{int(peak_hour_query.hour):02d}:00" if peak_hour_query else "N/A"
    
    # Top 10 users by session count
    top_users = db.query(
        User.id,
        User.name,
        User.mobile,
        func.count(WiFiSession.id).label('session_count'),
        func.sum(WiFiSession.total_data).label('total_data')
    ).join(WiFiSession).group_by(User.id).order_by(
        func.count(WiFiSession.id).desc()
    ).limit(10).all()
    
    top_users_list = [
        {
            "user_id": user.id,
            "name": user.name,
            "mobile": user.mobile,
            "session_count": user.session_count,
            "total_data": user.total_data or 0
        }
        for user in top_users
    ]
    
    return {
        "total_users": total_users,
        "active_sessions": active_sessions,
        "today_sessions": today_sessions,
        "today_data_usage": today_data,
        "total_sessions": total_sessions,
        "average_session_duration": int(avg_duration),
        "peak_hour": peak_hour,
        "top_users": top_users_list
    }

# Get filtered records
@router.get("/sessions")
async def get_sessions(
    page: int = 1,
    page_size: int = 25,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    mobile: Optional[str] = None,
    cnic: Optional[str] = None,
    passport: Optional[str] = None,
    mac_address: Optional[str] = None,
    status: Optional[str] = None,
    min_duration: Optional[int] = None,
    max_duration: Optional[int] = None,
    current_user: Admin = Depends(require_reports_permission),
    db: Session = Depends(get_db)
):
    # Build query
    query = db.query(
        WiFiSession,
        User.name,
        User.mobile,
        User.cnic,
        User.passport
    ).outerjoin(User, WiFiSession.user_id == User.id)
    
    # Apply filters
    conditions = []
    
    if start_date:
        start_datetime = datetime.combine(datetime.fromisoformat(start_date).date(), datetime.min.time())
        conditions.append(WiFiSession.start_time >= start_datetime)
    
    if end_date:
        end_datetime = datetime.combine(datetime.fromisoformat(end_date).date(), datetime.max.time())
        conditions.append(WiFiSession.start_time <= end_datetime)
    
    if mobile:
        conditions.append(User.mobile.like(f"%{mobile}%"))
    
    if cnic:
        conditions.append(User.cnic.like(f"%{cnic}%"))
    
    if passport:
        conditions.append(User.passport.like(f"%{passport}%"))
    
    if mac_address:
        conditions.append(WiFiSession.mac_address.like(f"%{mac_address}%"))
    
    if status:
        conditions.append(WiFiSession.session_status == status)
    
    if min_duration:
        conditions.append(WiFiSession.duration >= min_duration)
    
    if max_duration:
        conditions.append(WiFiSession.duration <= max_duration)
    
    if conditions:
        query = query.filter(and_(*conditions))
    
    # Get total count
    total_count = query.count()
    
    # Apply pagination
    offset = (page - 1) * page_size
    results = query.order_by(WiFiSession.start_time.desc()).offset(offset).limit(page_size).all()
    
    # Format response
    sessions = []
    for session, user_name, user_mobile, user_cnic, user_passport in results:
        sessions.append({
            "id": session.id,
            "user_id": session.user_id,
            "user_name": user_name,
            "user_mobile": user_mobile,
            "user_cnic": user_cnic,
            "user_passport": user_passport,
            "mac_address": session.mac_address,
            "ip_address": session.ip_address,
            "ap_name": session.ap_name,
            "ssid": session.ssid,
            "start_time": session.start_time,
            "end_time": session.end_time,
            "duration": session.duration,
            "total_data": session.total_data,
            "data_upload": session.data_upload,
            "data_download": session.data_download,
            "disconnect_reason": session.disconnect_reason,
            "session_status": session.session_status
        })
    
    return {
        "sessions": sessions,
        "total_count": total_count,
        "page": page,
        "page_size": page_size,
        "total_pages": (total_count + page_size - 1) // page_size
    }

# Export records
@router.post("/export")
async def export_records(
    export_request: ExportRequest,
    current_user: Admin = Depends(require_reports_permission),
    db: Session = Depends(get_db)
):
    if not has_permission(current_user, "export_records"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to export records"
        )
    
    # Build query with filters
    query = db.query(
        WiFiSession,
        User.name,
        User.mobile,
        User.cnic,
        User.passport
    ).outerjoin(User, WiFiSession.user_id == User.id)
    
    # Apply same filters as in get_sessions
    filters = export_request.filters
    conditions = []
    
    if filters.start_date:
        start_datetime = datetime.combine(filters.start_date, datetime.min.time())
        conditions.append(WiFiSession.start_time >= start_datetime)
    
    if filters.end_date:
        end_datetime = datetime.combine(filters.end_date, datetime.max.time())
        conditions.append(WiFiSession.start_time <= end_datetime)
    
    if filters.mobile:
        conditions.append(User.mobile.like(f"%{filters.mobile}%"))
    
    if hasattr(filters, 'cnic') and filters.cnic:
        conditions.append(User.cnic.like(f"%{filters.cnic}%"))
    
    if hasattr(filters, 'passport') and filters.passport:
        conditions.append(User.passport.like(f"%{filters.passport}%"))
    
    if filters.mac_address:
        conditions.append(WiFiSession.mac_address.like(f"%{filters.mac_address}%"))
    
    if filters.status:
        conditions.append(WiFiSession.session_status == filters.status)
    
    if filters.min_duration:
        conditions.append(WiFiSession.duration >= filters.min_duration)
    
    if filters.max_duration:
        conditions.append(WiFiSession.duration <= filters.max_duration)
    
    if conditions:
        query = query.filter(and_(*conditions))
    
    # Get all matching records
    results = query.order_by(WiFiSession.start_time.desc()).all()
    
    # Prepare data
    data = []
    for session, user_name, user_mobile, user_cnic, user_passport in results:
        data.append({
            "ID": session.id,
            "User Name": user_name or "N/A",
            "Mobile": user_mobile or "N/A",
            "CNIC": user_cnic or "N/A",
            "Passport": user_passport or "N/A",
            "MAC Address": session.mac_address,
            "IP Address": session.ip_address or "N/A",
            "AP Name": session.ap_name or "N/A",
            "SSID": session.ssid or "N/A",
            "Start Time": session.start_time.strftime("%Y-%m-%d %H:%M:%S"),
            "End Time": session.end_time.strftime("%Y-%m-%d %H:%M:%S") if session.end_time else "Active",
            "Duration (sec)": session.duration or 0,
            "Data Upload (bytes)": session.data_upload or 0,
            "Data Download (bytes)": session.data_download or 0,
            "Total Data (bytes)": session.total_data or 0,
            "Status": session.session_status,
            "Disconnect Reason": session.disconnect_reason or "N/A"
        })
    
    # Generate export based on format
    export_service = ExportService()
    
    if export_request.format == "csv":
        return export_service.export_to_csv(data)
    elif export_request.format == "excel":
        return export_service.export_to_excel(data)
    elif export_request.format == "pdf":
        return export_service.export_to_pdf(data)
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid export format. Use 'csv', 'excel', or 'pdf'"
        )

# Get user session history
@router.get("/users/{user_id}/sessions")
async def get_user_sessions(
    user_id: int,
    current_user: Admin = Depends(require_reports_permission),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    sessions = db.query(WiFiSession).filter(
        WiFiSession.user_id == user_id
    ).order_by(WiFiSession.start_time.desc()).all()
    
    return {
        "user": {
            "id": user.id,
            "name": user.name,
            "mobile": user.mobile,
            "total_sessions": user.total_sessions,
            "total_data_usage": user.total_data_usage
        },
        "sessions": [
            {
                "id": s.id,
                "start_time": s.start_time,
                "end_time": s.end_time,
                "duration": s.duration,
                "total_data": s.total_data,
                "status": s.session_status,
                "disconnect_reason": s.disconnect_reason
            }
            for s in sessions
        ]
    }
