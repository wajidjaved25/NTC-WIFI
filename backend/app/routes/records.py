from fastapi import APIRouter, Depends, HTTPException, status, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_, text
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
    """
    Get sessions from both WiFi sessions table AND RADIUS accounting table (merged)
    """
    
    all_sessions = []
    
    try:
        # Get sessions from WiFi sessions table
        wifi_query = db.query(
            WiFiSession.id.label('session_id'),
            WiFiSession.user_id,
            User.name.label('user_name'),
            User.mobile.label('user_mobile'),
            User.cnic.label('user_cnic'),
            User.passport.label('user_passport'),
            User.email.label('user_email'),
            User.id_type.label('user_id_type'),
            WiFiSession.mac_address,
            WiFiSession.ip_address,
            WiFiSession.ssid,
            WiFiSession.ap_mac,
            WiFiSession.ap_name,
            WiFiSession.start_time,
            WiFiSession.end_time,
            WiFiSession.duration,
            WiFiSession.data_upload,
            WiFiSession.data_download,
            WiFiSession.total_data,
            WiFiSession.session_status,
            WiFiSession.disconnect_reason
        ).outerjoin(User, WiFiSession.user_id == User.id)
        
        # Apply filters to WiFi sessions
        wifi_conditions = []
        
        if start_date:
            start_datetime = datetime.combine(datetime.fromisoformat(start_date).date(), datetime.min.time())
            wifi_conditions.append(WiFiSession.start_time >= start_datetime)
        
        if end_date:
            end_datetime = datetime.combine(datetime.fromisoformat(end_date).date(), datetime.max.time())
            wifi_conditions.append(WiFiSession.start_time <= end_datetime)
        
        if mobile:
            wifi_conditions.append(User.mobile.like(f"%{mobile}%"))
        
        if cnic:
            wifi_conditions.append(User.cnic.like(f"%{cnic}%"))
        
        if passport:
            wifi_conditions.append(User.passport.like(f"%{passport}%"))
        
        if mac_address:
            wifi_conditions.append(WiFiSession.mac_address.like(f"%{mac_address}%"))
        
        if status:
            wifi_conditions.append(WiFiSession.session_status == status)
        
        if min_duration:
            wifi_conditions.append(WiFiSession.duration >= min_duration)
        
        if max_duration:
            wifi_conditions.append(WiFiSession.duration <= max_duration)
        
        if wifi_conditions:
            wifi_query = wifi_query.filter(and_(*wifi_conditions))
        
        wifi_sessions = wifi_query.all()
        
        # Add WiFi sessions to results
        for s in wifi_sessions:
            all_sessions.append({
                "id": f"wifi_{s.session_id}",
                "source": "wifi",
                "user_id": s.user_id,
                "user_name": s.user_name,
                "user_mobile": s.user_mobile,
                "user_cnic": s.user_cnic,
                "user_passport": s.user_passport,
                "user_email": s.user_email,
                "user_id_type": s.user_id_type,
                "mac_address": s.mac_address,
                "ip_address": s.ip_address or "",
                "ssid": s.ssid or "",
                "ap_mac": s.ap_mac or "",
                "ap_name": s.ap_name or "",
                "start_time": s.start_time.isoformat() if s.start_time else None,
                "end_time": s.end_time.isoformat() if s.end_time else None,
                "duration": s.duration,
                "data_upload": s.data_upload or 0,
                "data_download": s.data_download or 0,
                "total_data": s.total_data or 0,
                "session_status": s.session_status,
                "disconnect_reason": s.disconnect_reason
            })
    except Exception as e:
        print(f"Error querying WiFi sessions: {e}")
        import traceback
        traceback.print_exc()
    
    # Try to get RADIUS sessions (may fail if radacct table doesn't exist)
    try:
        radius_query = """
            SELECT 
                ra.radacctid as session_id,
                u.id as user_id,
                u.name as user_name,
                ra.username as user_mobile,
                u.cnic as user_cnic,
                u.passport as user_passport,
                u.email as user_email,
                u.id_type as user_id_type,
                ra.callingstationid as mac_address,
                ra.framedipaddress as ip_address,
                ra.calledstationid as called_station,
                ra.nasportid as ap_name,
                ra.acctstarttime as start_time,
                ra.acctstoptime as end_time,
                ra.acctsessiontime as duration,
                ra.acctinputoctets as data_upload,
                ra.acctoutputoctets as data_download,
                (COALESCE(ra.acctinputoctets, 0) + COALESCE(ra.acctoutputoctets, 0)) as total_data,
                CASE 
                    WHEN ra.acctstoptime IS NULL THEN 'active'
                    ELSE 'completed'
                END as session_status,
                ra.acctterminatecause as disconnect_reason
            FROM radacct ra
            LEFT JOIN users u ON ra.username = u.mobile
            WHERE 1=1
        """
        
        # Build RADIUS filter conditions
        radius_conditions = []
        radius_params = {}
        
        if start_date:
            radius_conditions.append("ra.acctstarttime >= :start_date")
            radius_params['start_date'] = datetime.combine(datetime.fromisoformat(start_date).date(), datetime.min.time())
        
        if end_date:
            radius_conditions.append("ra.acctstarttime <= :end_date")
            radius_params['end_date'] = datetime.combine(datetime.fromisoformat(end_date).date(), datetime.max.time())
        
        if mobile:
            radius_conditions.append("ra.username LIKE :mobile")
            radius_params['mobile'] = f"%{mobile}%"
        
        if mac_address:
            radius_conditions.append("ra.callingstationid LIKE :mac_address")
            radius_params['mac_address'] = f"%{mac_address}%"
        
        if status:
            if status == 'active':
                radius_conditions.append("ra.acctstoptime IS NULL")
            else:
                radius_conditions.append("ra.acctstoptime IS NOT NULL")
        
        if min_duration:
            radius_conditions.append("ra.acctsessiontime >= :min_duration")
            radius_params['min_duration'] = min_duration
        
        if max_duration:
            radius_conditions.append("ra.acctsessiontime <= :max_duration")
            radius_params['max_duration'] = max_duration
        
        if radius_conditions:
            radius_query += " AND " + " AND ".join(radius_conditions)
        
        radius_query += " ORDER BY ra.acctstarttime DESC"
        
        radius_sessions = db.execute(text(radius_query), radius_params).fetchall()
        
        # Add RADIUS sessions to results
        for s in radius_sessions:
            # Parse SSID from calledstationid (format: MAC:SSID or just MAC)
            called_station = s.called_station or ""
            ssid = ""
            ap_mac = ""
            if ":" in called_station:
                parts = called_station.split(":")
                if len(parts) > 6:  # Has SSID after MAC
                    ap_mac = ":".join(parts[:6])
                    ssid = ":".join(parts[6:])
                else:
                    ap_mac = called_station
            else:
                ap_mac = called_station
            
            all_sessions.append({
                "id": f"radius_{s.session_id}",
                "source": "radius",
                "user_id": s.user_id,
                "user_name": s.user_name,
                "user_mobile": s.user_mobile,
                "user_cnic": s.user_cnic,
                "user_passport": s.user_passport,
                "user_email": s.user_email,
                "user_id_type": s.user_id_type,
                "mac_address": s.mac_address,
                "ip_address": str(s.ip_address) if s.ip_address else "",
                "ssid": ssid,
                "ap_mac": ap_mac,
                "ap_name": s.ap_name or "",
                "start_time": s.start_time.isoformat() if s.start_time else None,
                "end_time": s.end_time.isoformat() if s.end_time else None,
                "duration": s.duration,
                "data_upload": s.data_upload or 0,
                "data_download": s.data_download or 0,
                "total_data": s.total_data or 0,
                "session_status": s.session_status,
                "disconnect_reason": s.disconnect_reason
            })
    except Exception as e:
        print(f"Error querying RADIUS sessions (radacct table may not exist): {e}")
        import traceback
        traceback.print_exc()
    
    # Sort by start_time descending (handle None values)
    def sort_key(x):
        st = x.get('start_time')
        if st is None:
            return ''
        return st
    
    all_sessions.sort(key=sort_key, reverse=True)
    
    # Apply pagination
    total_count = len(all_sessions)
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    paginated_sessions = all_sessions[start_idx:end_idx]
    
    return {
        "sessions": paginated_sessions,
        "total_count": total_count,
        "page": page,
        "page_size": page_size,
        "total_pages": (total_count + page_size - 1) // page_size if total_count > 0 else 0
    }

# Export records - GET endpoint for direct download
@router.get("/export/{format}")
async def export_records_get(
    format: str,
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
    """Export records as CSV, Excel, or PDF"""
    
    if not has_permission(current_user, "export_records"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to export records"
        )
    
    if format not in ['csv', 'excel', 'pdf']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid export format. Use 'csv', 'excel', or 'pdf'"
        )
    
    # Build query with filters
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
            "MAC Address": session.mac_address or "N/A",
            "Start Time": session.start_time.strftime("%Y-%m-%d %H:%M:%S") if session.start_time else "N/A",
            "End Time": session.end_time.strftime("%Y-%m-%d %H:%M:%S") if session.end_time else "Active",
            "Duration (sec)": session.duration or 0,
            "Data Upload (bytes)": session.data_upload or 0,
            "Data Download (bytes)": session.data_download or 0,
            "Total Data (bytes)": session.total_data or 0,
            "Status": session.session_status or "N/A",
            "Disconnect Reason": session.disconnect_reason or "N/A"
        })
    
    # Generate export based on format
    export_service = ExportService()
    
    if format == "csv":
        return export_service.export_to_csv(data)
    elif format == "excel":
        return export_service.export_to_excel(data)
    elif format == "pdf":
        return export_service.export_to_pdf(data)

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
