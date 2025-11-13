"""
Session Management Service
Handles WiFi session creation, monitoring, and enforcement
"""

from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from typing import Optional, Dict
import asyncio

from ..models.session import Session as WiFiSession
from ..models.user import User
from ..models.daily_usage import DailyUsage
from ..models.omada_config import OmadaConfig
from ..utils.helpers import log_system_event


class SessionManager:
    def __init__(self, db: Session):
        self.db = db
    
    async def create_session(
        self,
        user_id: int,
        mac_address: str,
        ip_address: str,
        ap_mac: str = None,
        ap_name: str = None,
        ssid: str = None,
        site: str = None
    ) -> Dict:
        """Create new WiFi session for user"""
        
        try:
            # Get active Omada configuration
            config = self.db.query(OmadaConfig).filter(
                OmadaConfig.is_active == True
            ).first()
            
            if not config:
                raise Exception("No active Omada configuration found")
            
            # Check if user can start new session
            can_start, reason = await self.can_start_session(user_id, config)
            if not can_start:
                return {
                    "success": False,
                    "reason": reason
                }
            
            # Create session record
            new_session = WiFiSession(
                user_id=user_id,
                mac_address=mac_address,
                ip_address=ip_address,
                ap_mac=ap_mac,
                ap_name=ap_name,
                ssid=ssid,
                site=site,
                start_time=datetime.utcnow(),
                session_status='active'
            )
            
            self.db.add(new_session)
            self.db.commit()
            self.db.refresh(new_session)
            
            # Update user's total sessions
            user = self.db.query(User).filter(User.id == user_id).first()
            user.total_sessions += 1
            user.last_login = datetime.utcnow()
            
            # Update daily usage record
            await self.update_daily_usage(user_id, session_count=1)
            
            self.db.commit()
            
            # Log session creation
            await log_system_event(
                self.db,
                level="INFO",
                module="session",
                action="session_created",
                message=f"Session created for user {user_id}",
                details={
                    "session_id": new_session.id,
                    "mac_address": mac_address,
                    "ip_address": ip_address
                },
                user_id=user_id
            )
            
            return {
                "success": True,
                "session_id": new_session.id,
                "session_timeout": config.session_timeout,
                "idle_timeout": config.idle_timeout
            }
        
        except Exception as e:
            self.db.rollback()
            raise Exception(f"Failed to create session: {str(e)}")
    
    async def can_start_session(self, user_id: int, config: OmadaConfig) -> tuple:
        """Check if user can start a new session based on limits"""
        
        # Check if user is blocked
        user = self.db.query(User).filter(User.id == user_id).first()
        if user.is_blocked:
            return False, f"User account is blocked: {user.block_reason}"
        
        # Get today's date
        today = datetime.utcnow().date()
        
        # Get daily usage
        daily_usage = self.db.query(DailyUsage).filter(
            and_(
                DailyUsage.user_id == user_id,
                DailyUsage.usage_date == today
            )
        ).first()
        
        if daily_usage:
            # Check daily session limit
            if config.max_daily_sessions and daily_usage.session_count >= config.max_daily_sessions:
                return False, f"Daily session limit reached ({config.max_daily_sessions} sessions)"
            
            # Check daily time limit
            if config.daily_time_limit and daily_usage.total_duration >= config.daily_time_limit:
                return False, f"Daily time limit reached ({config.daily_time_limit} seconds)"
            
            # Check daily data limit
            if config.daily_data_limit and daily_usage.total_data >= config.daily_data_limit:
                return False, f"Daily data limit reached"
        
        # Check for active session
        active_session = self.db.query(WiFiSession).filter(
            and_(
                WiFiSession.user_id == user_id,
                WiFiSession.session_status == 'active'
            )
        ).first()
        
        if active_session:
            return False, "User already has an active session"
        
        return True, "OK"
    
    async def end_session(
        self,
        session_id: int,
        disconnect_reason: str = "user",
        data_upload: int = 0,
        data_download: int = 0
    ) -> Dict:
        """End WiFi session and update statistics"""
        
        try:
            session = self.db.query(WiFiSession).filter(
                WiFiSession.id == session_id
            ).first()
            
            if not session:
                raise Exception("Session not found")
            
            if session.session_status != 'active':
                return {"success": False, "reason": "Session already ended"}
            
            # Calculate duration
            end_time = datetime.utcnow()
            duration = int((end_time - session.start_time).total_seconds())
            
            # Update session
            session.end_time = end_time
            session.duration = duration
            session.data_upload = data_upload
            session.data_download = data_download
            session.total_data = data_upload + data_download
            session.disconnect_reason = disconnect_reason
            session.session_status = 'completed'
            
            # Update daily usage
            await self.update_daily_usage(
                session.user_id,
                duration=duration,
                data_upload=data_upload,
                data_download=data_download
            )
            
            # Update user's total data usage
            user = self.db.query(User).filter(User.id == session.user_id).first()
            user.total_data_usage += data_upload + data_download
            
            self.db.commit()
            
            # Log session end
            await log_system_event(
                self.db,
                level="INFO",
                module="session",
                action="session_ended",
                message=f"Session ended for user {session.user_id}",
                details={
                    "session_id": session_id,
                    "duration": duration,
                    "disconnect_reason": disconnect_reason
                },
                user_id=session.user_id
            )
            
            return {
                "success": True,
                "duration": duration,
                "total_data": session.total_data
            }
        
        except Exception as e:
            self.db.rollback()
            raise Exception(f"Failed to end session: {str(e)}")
    
    async def update_daily_usage(
        self,
        user_id: int,
        session_count: int = 0,
        duration: int = 0,
        data_upload: int = 0,
        data_download: int = 0
    ):
        """Update or create daily usage record"""
        
        today = datetime.utcnow().date()
        
        daily_usage = self.db.query(DailyUsage).filter(
            and_(
                DailyUsage.user_id == user_id,
                DailyUsage.usage_date == today
            )
        ).first()
        
        if daily_usage:
            # Update existing record
            daily_usage.session_count += session_count
            daily_usage.total_duration += duration
            daily_usage.data_upload += data_upload
            daily_usage.data_download += data_download
            daily_usage.total_data += (data_upload + data_download)
            daily_usage.last_session_at = datetime.utcnow()
        else:
            # Create new record
            daily_usage = DailyUsage(
                user_id=user_id,
                usage_date=today,
                session_count=session_count,
                total_duration=duration,
                data_upload=data_upload,
                data_download=data_download,
                total_data=(data_upload + data_download),
                last_session_at=datetime.utcnow()
            )
            self.db.add(daily_usage)
        
        self.db.commit()
    
    async def check_session_limits(self, session_id: int) -> Dict:
        """Check if session has exceeded any limits"""
        
        session = self.db.query(WiFiSession).filter(
            WiFiSession.id == session_id
        ).first()
        
        if not session or session.session_status != 'active':
            return {"should_disconnect": False}
        
        config = self.db.query(OmadaConfig).filter(
            OmadaConfig.is_active == True
        ).first()
        
        if not config:
            return {"should_disconnect": False}
        
        reasons = []
        
        # Check session timeout
        if config.session_timeout:
            elapsed = int((datetime.utcnow() - session.start_time).total_seconds())
            if elapsed >= config.session_timeout:
                reasons.append("session_timeout")
        
        # Check daily time limit
        if config.daily_time_limit:
            today = datetime.utcnow().date()
            daily_usage = self.db.query(DailyUsage).filter(
                and_(
                    DailyUsage.user_id == session.user_id,
                    DailyUsage.usage_date == today
                )
            ).first()
            
            if daily_usage and daily_usage.total_duration >= config.daily_time_limit:
                reasons.append("daily_time_limit")
        
        # Check session data limit
        if config.session_data_limit and session.total_data >= config.session_data_limit:
            reasons.append("session_data_limit")
        
        # Check daily data limit
        if config.daily_data_limit:
            today = datetime.utcnow().date()
            daily_usage = self.db.query(DailyUsage).filter(
                and_(
                    DailyUsage.user_id == session.user_id,
                    DailyUsage.usage_date == today
                )
            ).first()
            
            if daily_usage and daily_usage.total_data >= config.daily_data_limit:
                reasons.append("daily_data_limit")
        
        if reasons:
            return {
                "should_disconnect": True,
                "reasons": reasons,
                "disconnect_reason": reasons[0]  # Use first reason
            }
        
        return {"should_disconnect": False}
    
    async def get_active_sessions(self, limit: int = 100) -> list:
        """Get all active sessions"""
        
        sessions = self.db.query(WiFiSession).filter(
            WiFiSession.session_status == 'active'
        ).order_by(WiFiSession.start_time.desc()).limit(limit).all()
        
        return sessions
    
    async def terminate_session(self, session_id: int, reason: str = "admin") -> Dict:
        """Forcefully terminate a session (admin action)"""
        
        return await self.end_session(
            session_id,
            disconnect_reason=reason
        )
    
    async def monitor_sessions(self):
        """Background task to monitor and enforce session limits"""
        
        while True:
            try:
                active_sessions = await self.get_active_sessions()
                
                for session in active_sessions:
                    check_result = await self.check_session_limits(session.id)
                    
                    if check_result.get("should_disconnect"):
                        # Disconnect session
                        await self.end_session(
                            session.id,
                            disconnect_reason=check_result.get("disconnect_reason", "limit_reached")
                        )
                        
                        # TODO: Send disconnect command to Omada controller
                        # This would require Omada API integration
                
                # Wait before next check (every 30 seconds)
                await asyncio.sleep(30)
            
            except Exception as e:
                print(f"Error in session monitor: {str(e)}")
                await asyncio.sleep(60)  # Wait longer on error
