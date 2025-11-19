from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_, desc, text
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
        
        # Total users (from radcheck - RADIUS users)
        total_users = db.execute(
            text("SELECT COUNT(DISTINCT username) FROM radcheck WHERE attribute = 'Cleartext-Password'")
        ).scalar() or 0
        
        # New users in period (from users table if available, otherwise estimate from radacct)
        try:
            new_users = db.query(func.count(User.id)).filter(
                User.created_at >= start_date
            ).scalar() or 0
        except:
            new_users = 0
        
        # Active users (users with sessions in period from radacct)
        active_users = db.execute(
            text("""
                SELECT COUNT(DISTINCT username) FROM radacct 
                WHERE acctstarttime >= :start_date
            """),
            {"start_date": start_date}
        ).scalar() or 0
        
        # Total sessions from radacct
        total_sessions = db.execute(
            text("""
                SELECT COUNT(*) FROM radacct 
                WHERE acctstarttime >= :start_date
            """),
            {"start_date": start_date}
        ).scalar() or 0
        
        # Active sessions (currently connected) from radacct
        active_sessions = db.execute(
            text("SELECT COUNT(*) FROM radacct WHERE acctstoptime IS NULL")
        ).scalar() or 0
        
        # Total data usage from radacct
        data_stats = db.execute(
            text("""
                SELECT 
                    COALESCE(SUM(CAST(acctinputoctets AS BIGINT) + CAST(acctoutputoctets AS BIGINT)), 0) as total,
                    COALESCE(AVG(CAST(acctinputoctets AS BIGINT) + CAST(acctoutputoctets AS BIGINT)), 0) as average
                FROM radacct 
                WHERE acctstarttime >= :start_date
            """),
            {"start_date": start_date}
        ).fetchone()
        
        # Total session duration from radacct
        duration_stats = db.execute(
            text("""
                SELECT 
                    COALESCE(SUM(acctsessiontime), 0) as total,
                    COALESCE(AVG(acctsessiontime), 0) as average
                FROM radacct 
                WHERE acctstarttime >= :start_date
                AND acctsessiontime IS NOT NULL
            """),
            {"start_date": start_date}
        ).fetchone()
        
        # Active advertisements
        active_ads = db.query(func.count(Advertisement.id)).filter(
            Advertisement.is_active == True
        ).scalar() or 0
        
        # Blocked users
        try:
            blocked_users = db.query(func.count(User.id)).filter(
                User.is_blocked == True
            ).scalar() or 0
        except:
            blocked_users = 0
        
        # Ad impressions
        try:
            ad_views = db.query(func.count(AdAnalytics.id)).filter(
                AdAnalytics.event_type == 'view',
                AdAnalytics.event_timestamp >= start_date
            ).scalar() or 0
        except:
            ad_views = 0
        
        return {
            "users": {
                "total": total_users,
                "new": new_users,
                "active": active_users,
                "blocked": blocked_users
            },
            "sessions": {
                "total": total_sessions,
                "active": active_sessions,
                "average_duration": int(duration_stats[1]) if duration_stats else 0
            },
            "data_usage": {
                "total": int(data_stats[0]) if data_stats else 0,
                "average_per_session": int(data_stats[1]) if data_stats else 0
            },
            "advertisements": {
                "active_count": active_ads,
                "total_views": ad_views
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
        """Get real-time statistics from radacct"""
        # Currently active sessions from radacct
        active_now = db.execute(
            text("SELECT COUNT(*) FROM radacct WHERE acctstoptime IS NULL")
        ).scalar() or 0
        
        # Active sessions by AP (using calledstationid which contains AP info)
        sessions_by_ap = db.execute(
            text("""
                SELECT 
                    COALESCE(nasportid, 'Unknown') as ap_name,
                    COUNT(*) as count
                FROM radacct 
                WHERE acctstoptime IS NULL
                GROUP BY nasportid
                ORDER BY count DESC
            """)
        ).fetchall()
        
        # Sessions today from radacct
        sessions_today = db.execute(
            text("""
                SELECT COUNT(*) FROM radacct 
                WHERE DATE(acctstarttime) = CURRENT_DATE
            """)
        ).scalar() or 0
        
        # Data usage today from radacct
        data_today = db.execute(
            text("""
                SELECT COALESCE(SUM(acctinputoctets + acctoutputoctets), 0)
                FROM radacct 
                WHERE DATE(acctstarttime) = CURRENT_DATE
            """)
        ).scalar() or 0
        
        return {
            "active_sessions": active_now,
            "sessions_by_ap": [
                {"ap": ap[0] or 'Unknown', "count": ap[1]} 
                for ap in sessions_by_ap
            ],
            "today": {
                "sessions": sessions_today,
                "data_usage": int(data_today)
            }
        }
