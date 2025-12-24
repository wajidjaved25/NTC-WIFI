"""
Single Device Login Enforcement Service

This service ensures that a user can only be logged in from one device at a time.
When a user tries to login from a new device while already logged in elsewhere,
the old session is automatically disconnected via RADIUS CoA.
"""

from sqlalchemy.orm import Session
from datetime import datetime, timezone
from typing import Optional, Dict
import logging
import asyncio

from ..models.session import Session as WiFiSession
from ..models.user import User
from ..services.coa_service import coa_service

logger = logging.getLogger(__name__)


class SingleDeviceEnforcer:
    """
    Enforces single-device login policy for WiFi users
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    def check_and_disconnect_old_session(self, user_id: int, new_mac_address: str) -> Dict:
        """
        Check if user has active session on different device
        
        POLICY: Block new login if active session exists on different device
        (Don't attempt to disconnect - let sessions expire naturally)
        
        Args:
            user_id: User ID attempting to login
            new_mac_address: MAC address of new device
            
        Returns:
            Dict with status information:
            {
                'allowed': bool,  # True if login allowed, False if blocked
                'had_active_session': bool,
                'old_session_id': int or None,
                'old_mac_address': str or None,
                'message': str
            }
        """
        
        result = {
            'allowed': True,
            'had_active_session': False,
            'old_session_id': None,
            'old_mac_address': None,
            'message': 'No active session found'
        }
        
        # Find active sessions for this user
        active_sessions = self.db.query(WiFiSession).filter(
            WiFiSession.user_id == user_id,
            WiFiSession.session_status == 'active',
            WiFiSession.end_time == None
        ).all()
        
        if not active_sessions:
            logger.info(f"User {user_id}: No active sessions found - login allowed")
            return result
        
        # Check if any active session is on a different device
        for session in active_sessions:
            # Normalize MAC addresses for comparison
            session_mac = self._normalize_mac(session.mac_address)
            new_mac = self._normalize_mac(new_mac_address)
            
            if session_mac != new_mac:
                logger.info(f"User {user_id}: Active session detected on different device")
                logger.info(f"  Old device: {session_mac}")
                logger.info(f"  New device: {new_mac}")
                logger.info(f"  Session started: {session.start_time}")
                
                # Calculate session age
                if session.start_time:
                    from datetime import timezone
                    age_seconds = (datetime.now(timezone.utc) - session.start_time).total_seconds()
                    age_minutes = int(age_seconds / 60)
                    logger.info(f"  Session age: {age_minutes} minutes")
                
                result['allowed'] = False
                result['had_active_session'] = True
                result['old_session_id'] = session.id
                result['old_mac_address'] = session.mac_address
                result['message'] = f'You have an active session on another device ({session_mac}). Please wait for it to expire or disconnect from that device first.'
                
                logger.warning(f"✗ Login blocked: User {user_id} already has active session on {session_mac}")
                break
        
        if result['allowed']:
            logger.info(f"✓ Login allowed: User {user_id} has active session on same device or no conflicts")
        
        return result
    
    def _disconnect_session(self, session: WiFiSession) -> bool:
        """
        Disconnect a WiFi session using RADIUS CoA
        
        Args:
            session: WiFiSession object to disconnect
            
        Returns:
            bool: True if disconnect successful, False otherwise
        """
        
        try:
            # Get user info for logging
            user = self.db.query(User).filter(User.id == session.user_id).first()
            username = user.mobile if user else str(session.user_id)
            
            logger.info(f"Sending RADIUS CoA disconnect for session {session.id}")
            logger.info(f"  Username: {username}")
            logger.info(f"  IP: {session.ip_address}")
            logger.info(f"  MAC: {session.mac_address}")
            logger.info(f"  Site ID: {getattr(session, 'site_id', None)}")
            
            # Send CoA disconnect in a separate thread to avoid event loop conflicts
            # This is necessary because we're being called from an async context (FastAPI)
            # but need to run async code (CoA service)
            import threading
            import concurrent.futures
            
            def run_coa_in_thread():
                """Run CoA disconnect in a separate thread with its own event loop"""
                import asyncio
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    return loop.run_until_complete(
                        coa_service.disconnect_user(
                            username=username,
                            site_id=getattr(session, 'site_id', None),
                            session_id=str(session.id),
                            framed_ip=session.ip_address
                        )
                    )
                finally:
                    loop.close()
            
            # Execute in thread pool with timeout
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(run_coa_in_thread)
                coa_result = future.result(timeout=30)  # 30 second timeout
            
            if coa_result.get('success'):
                logger.info(f"✓ RADIUS CoA disconnect successful for session {session.id}")
                return True
            else:
                logger.error(f"✗ RADIUS CoA disconnect failed for session {session.id}: {coa_result.get('message')}")
                return False
                
        except Exception as e:
            logger.error(f"✗ Error disconnecting session {session.id}: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    def _normalize_mac(self, mac_address: str) -> str:
        """
        Normalize MAC address format for comparison
        
        Converts various formats to uppercase with colons:
        - AA:BB:CC:DD:EE:FF
        - AA-BB-CC-DD-EE-FF
        - AABBCCDDEEFF
        
        All become: AA:BB:CC:DD:EE:FF
        """
        if not mac_address:
            return ""
        
        # Remove all separators
        mac_clean = mac_address.replace(':', '').replace('-', '').replace('.', '').upper()
        
        # Add colons every 2 characters
        return ':'.join(mac_clean[i:i+2] for i in range(0, 12, 2))
    
    def get_active_sessions_count(self, user_id: int) -> int:
        """
        Get count of active sessions for a user
        
        Args:
            user_id: User ID to check
            
        Returns:
            int: Number of active sessions
        """
        count = self.db.query(WiFiSession).filter(
            WiFiSession.user_id == user_id,
            WiFiSession.session_status == 'active',
            WiFiSession.end_time == None
        ).count()
        
        return count
    
    def get_user_sessions_info(self, user_id: int) -> Dict:
        """
        Get detailed information about user's sessions
        
        Args:
            user_id: User ID to check
            
        Returns:
            Dict with session information
        """
        active_sessions = self.db.query(WiFiSession).filter(
            WiFiSession.user_id == user_id,
            WiFiSession.session_status == 'active',
            WiFiSession.end_time == None
        ).all()
        
        return {
            'active_count': len(active_sessions),
            'sessions': [
                {
                    'session_id': s.id,
                    'mac_address': s.mac_address,
                    'ip_address': s.ip_address,
                    'start_time': s.start_time.isoformat() if s.start_time else None,
                    'ap_mac': s.ap_mac,
                    'ssid': s.ssid,
                    'site_id': getattr(s, 'site_id', None)
                }
                for s in active_sessions
            ]
        }
