from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_, desc
from datetime import datetime, timedelta
from typing import Dict, List, Any

from ..models.session import Session as WiFiSession
from ..models.user import User
from ..models.advertisement import Advertisement
from ..models.ad_analytics import AdAnalytics
from ..models.daily_usage import DailyUsage

class DashboardService:
    
    @staticmethod
    def get_overview_stats(db: Session, days: int = 30) -> Dict[str, Any]:
        """Get overview statistics for dashboard"""
        start_date = datetime.utcnow() - timedelta(days=days)
        
        # Total users
        total_users = db.query(func.count(User.id)).scalar()
        
        # New users in period
        new_users = db.query(func.count(User.id)).filter(
            User.created_at >= start_date
        ).scalar()
        
        # Active users (users with sessions in period)
        active_users = db.query(func.count(func.distinct(WiFiSession.user_id))).filter(
            WiFiSession.start_time >= start_date
        ).scalar()
        
        # Total sessions
        total_sessions = db.query(func.count(WiFiSession.id)).filter(
            WiFiSession.start_time >= start_date
        ).scalar()
        
        # Active sessions (currently connected)
        active_sessions = db.query(func.count(WiFiSession.id)).filter(
            WiFiSession.session_status == 'active'
        ).scalar()
        
        # Total data usage
        data_stats = db.query(
            func.sum(WiFiSession.total_data).label('total'),
            func.avg(WiFiSession.total_data).label('average')
        ).filter(
            WiFiSession.start_time >= start_date,
            WiFiSession.total_data.isnot(None)
        ).first()
        
        # Total session duration
        duration_stats = db.query(
            func.sum(WiFiSession.duration).label('total'),
            func.avg(WiFiSession.duration).label('average')
        ).filter(
            WiFiSession.start_time >= start_date,
            WiFiSession.duration.isnot(None)
        ).first()
        
        # Active advertisements
        active_ads = db.query(func.count(Advertisement.id)).filter(
            Advertisement.is_active == True
        ).scalar()
        
        # Blocked users
        blocked_users = db.query(func.count(User.id)).filter(
            User.is_blocked == True
        ).scalar()
        
        # Ad impressions
        ad_views = db.query(func.count(AdAnalytics.id)).filter(
            AdAnalytics.event_type == 'view',
            AdAnalytics.event_timestamp >= start_date
        ).scalar()
        
        return {
            "users": {
                "total": total_users or 0,
                "new": new_users or 0,
                "active": active_users or 0,
                "blocked": blocked_users or 0
            },
            "sessions": {
                "total": total_sessions or 0,
                "active": active_sessions or 0,
                "average_duration": int(duration_stats.average) if duration_stats.average else 0
            },
            "data_usage": {
                "total": int(data_stats.total) if data_stats.total else 0,
                "average_per_session": int(data_stats.average) if data_stats.average else 0
            },
            "advertisements": {
                "active_count": active_ads or 0,
                "total_views": ad_views or 0
            },
            "period_days": days
        }
    
    @staticmethod
    def get_sessions_chart_data(db: Session, days: int = 7) -> List[Dict[str, Any]]:
        """Get daily session counts for chart"""
        start_date = datetime.utcnow() - timedelta(days=days)
        
        # Query sessions grouped by date
        daily_sessions = db.query(
            func.date(WiFiSession.start_time).label('date'),
            func.count(WiFiSession.id).label('count')
        ).filter(
            WiFiSession.start_time >= start_date
        ).group_by(
            func.date(WiFiSession.start_time)
        ).order_by(
            func.date(WiFiSession.start_time)
        ).all()
        
        # Format for chart
        chart_data = []
        for record in daily_sessions:
            chart_data.append({
                "date": record.date.strftime("%Y-%m-%d"),
                "sessions": record.count
            })
        
        return chart_data
    
    @staticmethod
    def get_data_usage_chart(db: Session, days: int = 7) -> List[Dict[str, Any]]:
        """Get daily data usage for chart"""
        start_date = datetime.utcnow() - timedelta(days=days)
        
        daily_data = db.query(
            func.date(WiFiSession.start_time).label('date'),
            func.sum(WiFiSession.data_upload).label('upload'),
            func.sum(WiFiSession.data_download).label('download'),
            func.sum(WiFiSession.total_data).label('total')
        ).filter(
            WiFiSession.start_time >= start_date,
            WiFiSession.total_data.isnot(None)
        ).group_by(
            func.date(WiFiSession.start_time)
        ).order_by(
            func.date(WiFiSession.start_time)
        ).all()
        
        chart_data = []
        for record in daily_data:
            chart_data.append({
                "date": record.date.strftime("%Y-%m-%d"),
                "upload": int(record.upload or 0),
                "download": int(record.download or 0),
                "total": int(record.total or 0)
            })
        
        return chart_data
    
    @staticmethod
    def get_top_users(db: Session, limit: int = 10) -> List[Dict[str, Any]]:
        """Get top users by session count or data usage"""
        top_users = db.query(
            User.id,
            User.name,
            User.mobile,
            func.count(WiFiSession.id).label('session_count'),
            func.sum(WiFiSession.total_data).label('total_data'),
            func.sum(WiFiSession.duration).label('total_duration')
        ).join(
            WiFiSession, WiFiSession.user_id == User.id
        ).group_by(
            User.id
        ).order_by(
            desc('session_count')
        ).limit(limit).all()
        
        result = []
        for user in top_users:
            result.append({
                "id": user.id,
                "name": user.name,
                "mobile": user.mobile,
                "sessions": user.session_count,
                "data_usage": int(user.total_data or 0),
                "total_duration": int(user.total_duration or 0)
            })
        
        return result
    
    @staticmethod
    def get_peak_hours(db: Session, days: int = 7) -> List[Dict[str, Any]]:
        """Get peak usage hours"""
        start_date = datetime.utcnow() - timedelta(days=days)
        
        hourly_data = db.query(
            func.extract('hour', WiFiSession.start_time).label('hour'),
            func.count(WiFiSession.id).label('count')
        ).filter(
            WiFiSession.start_time >= start_date
        ).group_by(
            func.extract('hour', WiFiSession.start_time)
        ).order_by(
            func.extract('hour', WiFiSession.start_time)
        ).all()
        
        result = []
        for record in hourly_data:
            result.append({
                "hour": int(record.hour),
                "sessions": record.count
            })
        
        return result
    
    @staticmethod
    def get_ad_performance(db: Session, days: int = 30) -> List[Dict[str, Any]]:
        """Get advertisement performance metrics"""
        start_date = datetime.utcnow() - timedelta(days=days)
        
        ad_stats = db.query(
            Advertisement.id,
            Advertisement.title,
            Advertisement.ad_type,
            func.count(
                and_(
                    AdAnalytics.event_type == 'view',
                    AdAnalytics.event_timestamp >= start_date
                )
            ).label('views'),
            func.count(
                and_(
                    AdAnalytics.event_type == 'click',
                    AdAnalytics.event_timestamp >= start_date
                )
            ).label('clicks'),
            func.count(
                and_(
                    AdAnalytics.event_type == 'skip',
                    AdAnalytics.event_timestamp >= start_date
                )
            ).label('skips')
        ).outerjoin(
            AdAnalytics, AdAnalytics.ad_id == Advertisement.id
        ).filter(
            Advertisement.is_active == True
        ).group_by(
            Advertisement.id
        ).all()
        
        result = []
        for ad in ad_stats:
            ctr = (ad.clicks / ad.views * 100) if ad.views > 0 else 0
            result.append({
                "id": ad.id,
                "title": ad.title,
                "type": ad.ad_type,
                "views": ad.views,
                "clicks": ad.clicks,
                "skips": ad.skips,
                "ctr": round(ctr, 2)
            })
        
        return result
    
    @staticmethod
    def get_real_time_stats(db: Session) -> Dict[str, Any]:
        """Get real-time statistics"""
        # Currently active sessions
        active_now = db.query(func.count(WiFiSession.id)).filter(
            WiFiSession.session_status == 'active'
        ).scalar()
        
        # Active sessions by AP
        sessions_by_ap = db.query(
            WiFiSession.ap_name,
            func.count(WiFiSession.id).label('count')
        ).filter(
            WiFiSession.session_status == 'active',
            WiFiSession.ap_name.isnot(None)
        ).group_by(
            WiFiSession.ap_name
        ).all()
        
        # Sessions today
        today = datetime.utcnow().date()
        sessions_today = db.query(func.count(WiFiSession.id)).filter(
            func.date(WiFiSession.start_time) == today
        ).scalar()
        
        # Data usage today
        data_today = db.query(func.sum(WiFiSession.total_data)).filter(
            func.date(WiFiSession.start_time) == today
        ).scalar()
        
        return {
            "active_sessions": active_now or 0,
            "sessions_by_ap": [
                {"ap": ap.ap_name, "count": ap.count} 
                for ap in sessions_by_ap
            ],
            "today": {
                "sessions": sessions_today or 0,
                "data_usage": int(data_today or 0)
            }
        }
