"""
Session Cleanup Service - Syncs with RADIUS radacct table
"""
import asyncio
import logging
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session as DBSession
from sqlalchemy import and_, text

from ..database import SessionLocal
from ..models.session import Session as WiFiSession
from ..models.portal_settings import PortalSettings

logger = logging.getLogger(__name__)


class SessionCleanupService:
    """Background service that syncs sessions table with RADIUS radacct"""
    
    def __init__(self):
        self.is_running = False
        self.cleanup_interval = 300  # 5 minutes
        
    async def start(self):
        """Start the cleanup service"""
        if self.is_running:
            logger.warning("Session cleanup service already running")
            return
            
        self.is_running = True
        logger.info("🧹 Session Cleanup Service: Started")
        
        # Run cleanup loop
        while self.is_running:
            try:
                await self._cleanup_expired_sessions()
                await asyncio.sleep(self.cleanup_interval)
            except Exception as e:
                logger.error(f"Error in session cleanup loop: {e}")
                await asyncio.sleep(60)
    
    async def stop(self):
        """Stop the cleanup service"""
        self.is_running = False
        logger.info("🧹 Session Cleanup Service: Stopped")
    
    async def _cleanup_expired_sessions(self):
        """Clean up expired sessions - sync with RADIUS radacct table"""
        db = SessionLocal()
        try:
            # Step 1: Sync with RADIUS radacct - sessions ended in RADIUS should be ended in app
            sync_query = text("""
                UPDATE sessions s
                SET 
                    session_status = 'ended',
                    end_time = r.acctstoptime,
                    duration = EXTRACT(EPOCH FROM (r.acctstoptime - r.acctstarttime))::INTEGER,
                    data_upload = r.acctinputoctets,
                    data_download = r.acctoutputoctets,
                    total_data = r.acctinputoctets + r.acctoutputoctets,
                    disconnect_reason = COALESCE(r.acctterminatecause, 'Session completed')
                FROM radacct r
                WHERE 
                    s.session_status = 'active'
                    AND s.end_time IS NULL
                    AND r.acctstoptime IS NOT NULL
                    AND (REPLACE(REPLACE(s.mac_address, ':', ''), '-', '') = REPLACE(REPLACE(REPLACE(r.callingstationid, ':', ''), '-', ''), '.', '')
                         OR s.ip_address = r.framedipaddress)
            """)
            
            result = db.execute(sync_query)
            synced_count = result.rowcount
            db.commit()
            
            if synced_count > 0:
                logger.info(f"🔄 Synced {synced_count} sessions from RADIUS radacct")
            
            # Step 2: Timeout-based cleanup for sessions not in radacct
            portal_settings = db.query(PortalSettings).first()
            session_timeout_seconds = 1800  # Default: 30 minutes
            
            if portal_settings and portal_settings.session_timeout:
                session_timeout_seconds = portal_settings.session_timeout
            
            # Calculate expiry time
            now = datetime.now(timezone.utc)
            expiry_time = now - timedelta(seconds=session_timeout_seconds)
            
            # Find expired active sessions
            expired_sessions = db.query(WiFiSession).filter(
                and_(
                    WiFiSession.session_status == 'active',
                    WiFiSession.end_time == None,
                    WiFiSession.start_time < expiry_time
                )
            ).all()
            
            if expired_sessions:
                logger.info(f"🧹 Found {len(expired_sessions)} expired sessions to clean up")
                
                for session in expired_sessions:
                    # Calculate actual end time (start + timeout)
                    session.end_time = session.start_time + timedelta(seconds=session_timeout_seconds)
                    session.session_status = 'ended'
                    session.disconnect_reason = 'Session timeout (auto-cleanup)'
                    
                    # Calculate duration
                    if session.start_time and session.end_time:
                        duration = (session.end_time - session.start_time).total_seconds()
                        session.duration = int(duration)
                
                db.commit()
                logger.info(f"✓ Cleaned up {len(expired_sessions)} expired sessions")
            
            if synced_count == 0 and not expired_sessions:
                logger.debug("🧹 No sessions to clean")
                
        except Exception as e:
            logger.error(f"Error cleaning up expired sessions: {e}")
            db.rollback()
        finally:
            db.close()
    
    async def cleanup_now(self):
        """Force immediate cleanup (for manual trigger)"""
        logger.info("🧹 Manual cleanup triggered")
        await self._cleanup_expired_sessions()


# Global instance
session_cleanup_service = SessionCleanupService()
