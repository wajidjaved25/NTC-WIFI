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

from ..models.session import Session as WiFiSession
from ..models.user import User
from ..services.radius_auth_client import RadiusAuthClient

logger = logging.getLogger(__name__)


class SingleDeviceEnforcer:
    """
    Enforces single-device login policy for WiFi users
    """
    
    def __init__(self, db: Session, radius_server: str = "127.0.0.1", radius_secret: str = "testing123"):
        self.db = db
        self.radius_server = radius_server
        self.radius_secret = radius_secret
        self.radius_client = RadiusAuthClient(radius_server, radius_secret)
    
    def check_and_disconnect_old_session(self, user_id: int, new_mac_address: str) -> Dict:
        """
        Check if user has active session on different device and disconnect it
        
        Args:
            user_id: User ID attempting to login
            new_mac_address: MAC address of new device
            
        Returns:
            Dict with status information:
            {
                'had_active_session': bool,
                'old_session_id': int or None,
                'old_mac_address': str or None,
                'disconnected': bool,
                'message': str
            }
        """
        
        result = {
            'had_active_session': False,
            'old_session_id': None,
            'old_mac_address': None,
            'disconnected': False,
            'message': 'No active session found'
        }
        
        # Find active sessions for this user
        active_sessions = self.db.query(WiFiSession).filter(
            WiFiSession.user_id == user_id,
            WiFiSession.session_status == 'active',
            WiFiSession.end_time == None
        ).all()
        
        if not active_sessions:
            logger.info(f"User {user_id}: No active sessions found")
            return result
        
        # Check if any active session is on a different device
        for session in active_sessions:
            # Normalize MAC addresses for comparison
            session_mac = self._normalize_mac(session.mac_address)
            new_mac = self._normalize_mac(new_mac_address)
            
            if session_mac != new_mac:
                logger.info(f"User {user_id}: Found active session on different device")
                logger.info(f"  Old device: {session_mac}")
                logger.info(f"  New device: {new_mac}")
                
                result['had_active_session'] = True
                result['old_session_id'] = session.id
                result['old_mac_address'] = session.mac_address
                
                # Disconnect old session via RADIUS CoA
                disconnect_success = self._disconnect_session(session)
                
                if disconnect_success:
                    # Update session status in database
                    session.session_status = 'terminated'
                    session.end_time = datetime.now(timezone.utc)
                    session.termination_cause = 'Single-device policy - New login from different device'
                    
                    # Calculate duration
                    if session.start_time:
                        duration_seconds = (session.end_time - session.start_time).total_seconds()
                        session.duration = int(duration_seconds)
                    
                    self.db.commit()
                    
                    result['disconnected'] = True
                    result['message'] = f'Old session on {session_mac} disconnected successfully'
                    
                    logger.info(f"✓ Old session {session.id} disconnected and marked as terminated")
                else:
                    result['message'] = f'Failed to disconnect old session on {session_mac}'
                    logger.warning(f"✗ Failed to disconnect session {session.id}")
        
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
            
            # Send CoA disconnect packet
            result = self.radius_client.disconnect_session(
                username=username,
                nas_ip_address=session.ip_address or "192.168.3.254",
                framed_ip_address=session.ip_address,
                calling_station_id=session.mac_address
            )
            
            if result.get('success'):
                logger.info(f"✓ RADIUS CoA disconnect successful for session {session.id}")
                return True
            else:
                logger.error(f"✗ RADIUS CoA disconnect failed for session {session.id}: {result.get('message')}")
                return False
                
        except Exception as e:
            logger.error(f"✗ Error disconnecting session {session.id}: {str(e)}")
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
                    'ssid': s.ssid
                }
                for s in active_sessions
            ]
        }
