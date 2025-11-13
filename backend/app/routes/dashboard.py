from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.admin import Admin
from ..utils.security import get_current_user
from ..services.dashboard_service import DashboardService

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

@router.get("/overview")
async def get_dashboard_overview(
    days: int = 30,
    current_user: Admin = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get dashboard overview statistics"""
    # All roles can view dashboard
    stats = DashboardService.get_overview_stats(db, days)
    return stats

@router.get("/sessions-chart")
async def get_sessions_chart(
    days: int = 7,
    current_user: Admin = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get sessions chart data"""
    data = DashboardService.get_sessions_chart_data(db, days)
    return {"data": data}

@router.get("/data-usage-chart")
async def get_data_usage_chart(
    days: int = 7,
    current_user: Admin = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get data usage chart"""
    data = DashboardService.get_data_usage_chart(db, days)
    return {"data": data}

@router.get("/top-users")
async def get_top_users(
    limit: int = 10,
    current_user: Admin = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get top users"""
    users = DashboardService.get_top_users(db, limit)
    return {"users": users}

@router.get("/peak-hours")
async def get_peak_hours(
    days: int = 7,
    current_user: Admin = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get peak usage hours"""
    data = DashboardService.get_peak_hours(db, days)
    return {"data": data}

@router.get("/ad-performance")
async def get_ad_performance(
    days: int = 30,
    current_user: Admin = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get advertisement performance metrics"""
    # Only users with ad access can view ad stats
    if current_user.role not in ["superadmin", "admin", "ads_user"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    data = DashboardService.get_ad_performance(db, days)
    return {"ads": data}

@router.get("/real-time")
async def get_real_time_stats(
    current_user: Admin = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get real-time statistics"""
    stats = DashboardService.get_real_time_stats(db)
    return stats


# Aliases for frontend compatibility
@router.get("/stats")
async def get_dashboard_stats(
    days: int = 30,
    current_user: Admin = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get dashboard statistics (alias for /overview)"""
    stats = DashboardService.get_overview_stats(db, days)
    
    # Format for frontend compatibility
    return {
        "totalUsers": stats["users"]["total"],
        "newUsers": stats["users"]["new"],
        "returningUsers": stats["users"]["active"],
        "blockedUsers": stats["users"]["blocked"],
        "activeSessions": stats["sessions"]["active"],
        "todaySessions": stats["sessions"]["total"],
        "totalDataUsage": stats["data_usage"]["total"],
        "activeAds": stats["advertisements"]["active_count"],
        "adViews": stats["advertisements"]["total_views"],
        "averageSessionDuration": stats["sessions"]["average_duration"]
    }


@router.get("/session-trends")
async def get_session_trends(
    days: int = 7,
    current_user: Admin = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get session trends (alias for /sessions-chart)"""
    data = DashboardService.get_sessions_chart_data(db, days)
    return {"trends": data}
