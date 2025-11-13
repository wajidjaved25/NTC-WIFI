"""
Advertisement Display Service
Handles ad sequencing, scheduling, and analytics for public portal
"""

from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import List, Dict, Optional

from ..models.advertisement import Advertisement
from ..models.ad_analytics import AdAnalytics
from ..utils.helpers import is_within_schedule


class AdDisplayService:
    def __init__(self, db: Session):
        self.db = db
    
    def get_active_ads(self) -> List[Advertisement]:
        """Get all active advertisements in display order"""
        
        now = datetime.utcnow()
        
        # Query active ads
        ads = self.db.query(Advertisement).filter(
            Advertisement.is_active == True
        ).all()
        
        # Filter by schedule
        active_ads = []
        for ad in ads:
            # Check if within schedule
            if ad.start_date and now < ad.start_date:
                continue  # Not started yet
            
            if ad.end_date and now > ad.end_date:
                # Check if auto-disable
                if ad.auto_disable:
                    ad.is_active = False
                    self.db.commit()
                continue  # Expired
            
            active_ads.append(ad)
        
        # Sort by display_order
        active_ads.sort(key=lambda x: x.display_order)
        
        return active_ads
    
    def get_ads_for_display(self, user_id: int = None, mac_address: str = None) -> List[Dict]:
        """Get ads formatted for display in public portal"""
        
        active_ads = self.get_active_ads()
        
        ad_list = []
        for ad in active_ads:
            ad_data = {
                "id": ad.id,
                "title": ad.title,
                "description": ad.description,
                "ad_type": ad.ad_type,
                "file_path": ad.file_path,
                "file_name": ad.file_name,
                "display_duration": ad.display_duration,
                "auto_skip": ad.auto_skip,
                "skip_after": ad.skip_after,
                "display_order": ad.display_order
            }
            ad_list.append(ad_data)
        
        return ad_list
    
    async def track_ad_view(
        self,
        ad_id: int,
        user_id: int = None,
        mac_address: str = None,
        ip_address: str = None,
        user_agent: str = None
    ) -> bool:
        """Track when an ad is viewed"""
        
        try:
            # Create analytics record
            analytics = AdAnalytics(
                ad_id=ad_id,
                user_id=user_id,
                mac_address=mac_address,
                event_type='view',
                event_timestamp=datetime.utcnow(),
                ip_address=ip_address,
                user_agent=user_agent
            )
            self.db.add(analytics)
            
            # Increment view count on ad
            ad = self.db.query(Advertisement).filter(
                Advertisement.id == ad_id
            ).first()
            if ad:
                ad.view_count += 1
            
            self.db.commit()
            return True
        
        except Exception as e:
            self.db.rollback()
            print(f"Error tracking ad view: {str(e)}")
            return False
    
    async def track_ad_click(
        self,
        ad_id: int,
        user_id: int = None,
        mac_address: str = None,
        ip_address: str = None,
        user_agent: str = None
    ) -> bool:
        """Track when an ad is clicked"""
        
        try:
            # Create analytics record
            analytics = AdAnalytics(
                ad_id=ad_id,
                user_id=user_id,
                mac_address=mac_address,
                event_type='click',
                event_timestamp=datetime.utcnow(),
                ip_address=ip_address,
                user_agent=user_agent
            )
            self.db.add(analytics)
            
            # Increment click count on ad
            ad = self.db.query(Advertisement).filter(
                Advertisement.id == ad_id
            ).first()
            if ad:
                ad.click_count += 1
            
            self.db.commit()
            return True
        
        except Exception as e:
            self.db.rollback()
            print(f"Error tracking ad click: {str(e)}")
            return False
    
    async def track_ad_skip(
        self,
        ad_id: int,
        watch_duration: int,
        user_id: int = None,
        mac_address: str = None,
        ip_address: str = None,
        user_agent: str = None
    ) -> bool:
        """Track when an ad is skipped"""
        
        try:
            # Create analytics record
            analytics = AdAnalytics(
                ad_id=ad_id,
                user_id=user_id,
                mac_address=mac_address,
                event_type='skip',
                event_timestamp=datetime.utcnow(),
                watch_duration=watch_duration,
                ip_address=ip_address,
                user_agent=user_agent
            )
            self.db.add(analytics)
            
            # Increment skip count on ad
            ad = self.db.query(Advertisement).filter(
                Advertisement.id == ad_id
            ).first()
            if ad:
                ad.skip_count += 1
            
            self.db.commit()
            return True
        
        except Exception as e:
            self.db.rollback()
            print(f"Error tracking ad skip: {str(e)}")
            return False
    
    async def track_ad_complete(
        self,
        ad_id: int,
        watch_duration: int,
        user_id: int = None,
        mac_address: str = None,
        ip_address: str = None,
        user_agent: str = None
    ) -> bool:
        """Track when an ad is watched completely"""
        
        try:
            # Create analytics record
            analytics = AdAnalytics(
                ad_id=ad_id,
                user_id=user_id,
                mac_address=mac_address,
                event_type='complete',
                event_timestamp=datetime.utcnow(),
                watch_duration=watch_duration,
                ip_address=ip_address,
                user_agent=user_agent
            )
            self.db.add(analytics)
            
            self.db.commit()
            return True
        
        except Exception as e:
            self.db.rollback()
            print(f"Error tracking ad complete: {str(e)}")
            return False
    
    def get_ad_analytics(self, ad_id: int, days: int = 30) -> Dict:
        """Get analytics for a specific ad"""
        
        from datetime import timedelta
        
        start_date = datetime.utcnow() - timedelta(days=days)
        
        analytics = self.db.query(AdAnalytics).filter(
            and_(
                AdAnalytics.ad_id == ad_id,
                AdAnalytics.event_timestamp >= start_date
            )
        ).all()
        
        # Calculate metrics
        total_views = sum(1 for a in analytics if a.event_type == 'view')
        total_clicks = sum(1 for a in analytics if a.event_type == 'click')
        total_skips = sum(1 for a in analytics if a.event_type == 'skip')
        total_completes = sum(1 for a in analytics if a.event_type == 'complete')
        
        # Calculate average watch duration for skips
        skip_durations = [a.watch_duration for a in analytics if a.event_type == 'skip' and a.watch_duration]
        avg_watch_duration = sum(skip_durations) / len(skip_durations) if skip_durations else 0
        
        # Calculate engagement rate
        engagement_rate = (total_clicks / total_views * 100) if total_views > 0 else 0
        completion_rate = (total_completes / total_views * 100) if total_views > 0 else 0
        skip_rate = (total_skips / total_views * 100) if total_views > 0 else 0
        
        return {
            "ad_id": ad_id,
            "period_days": days,
            "total_views": total_views,
            "total_clicks": total_clicks,
            "total_skips": total_skips,
            "total_completes": total_completes,
            "avg_watch_duration": round(avg_watch_duration, 2),
            "engagement_rate": round(engagement_rate, 2),
            "completion_rate": round(completion_rate, 2),
            "skip_rate": round(skip_rate, 2)
        }
    
    def get_all_ads_analytics(self, days: int = 30) -> List[Dict]:
        """Get analytics for all ads"""
        
        ads = self.db.query(Advertisement).all()
        
        analytics_list = []
        for ad in ads:
            ad_analytics = self.get_ad_analytics(ad.id, days)
            ad_analytics['title'] = ad.title
            ad_analytics['ad_type'] = ad.ad_type
            ad_analytics['is_active'] = ad.is_active
            analytics_list.append(ad_analytics)
        
        return analytics_list
    
    async def cleanup_expired_ads(self) -> int:
        """Automatically disable expired ads with auto_disable=True"""
        
        now = datetime.utcnow()
        
        # Find expired ads with auto_disable
        expired_ads = self.db.query(Advertisement).filter(
            and_(
                Advertisement.is_active == True,
                Advertisement.auto_disable == True,
                Advertisement.end_date < now
            )
        ).all()
        
        count = 0
        for ad in expired_ads:
            ad.is_active = False
            count += 1
        
        if count > 0:
            self.db.commit()
        
        return count
