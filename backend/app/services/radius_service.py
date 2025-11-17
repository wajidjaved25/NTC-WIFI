"""
RADIUS Service - Helper for RADIUS user management
"""

from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional, List, Dict
import hashlib
from datetime import datetime


class RadiusService:
    """Service for managing RADIUS authentication users"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_radius_user(
        self,
        username: str,
        password: str,
        session_timeout: int = 3600,
        bandwidth_up: Optional[int] = None,
        bandwidth_down: Optional[int] = None
    ) -> bool:
        """Create or update RADIUS user"""
        
        try:
            # Delete existing user entries
            self.db.execute(
                text("DELETE FROM radcheck WHERE username = :username"),
                {"username": username}
            )
            self.db.execute(
                text("DELETE FROM radreply WHERE username = :username"),
                {"username": username}
            )
            
            # Insert authentication credentials (Cleartext-Password)
            self.db.execute(
                text("""
                    INSERT INTO radcheck (username, attribute, op, value)
                    VALUES (:username, 'Cleartext-Password', ':=', :password)
                """),
                {"username": username, "password": password}
            )
            
            # Insert Session-Timeout attribute
            self.db.execute(
                text("""
                    INSERT INTO radreply (username, attribute, op, value)
                    VALUES (:username, 'Session-Timeout', '=', :timeout)
                """),
                {"username": username, "timeout": str(session_timeout)}
            )
            
            # Insert bandwidth limits if provided
            if bandwidth_up:
                self.db.execute(
                    text("""
                        INSERT INTO radreply (username, attribute, op, value)
                        VALUES (:username, 'WISPr-Bandwidth-Max-Up', '=', :bw_up)
                    """),
                    {"username": username, "bw_up": str(bandwidth_up)}
                )
            
            if bandwidth_down:
                self.db.execute(
                    text("""
                        INSERT INTO radreply (username, attribute, op, value)
                        VALUES (:username, 'WISPr-Bandwidth-Max-Down', '=', :bw_down)
                    """),
                    {"username": username, "bw_down": str(bandwidth_down)}
                )
            
            self.db.commit()
            return True
            
        except Exception as e:
            self.db.rollback()
            print(f"Error creating RADIUS user: {e}")
            return False
    
    def delete_radius_user(self, username: str) -> bool:
        """Delete RADIUS user"""
        
        try:
            self.db.execute(
                text("DELETE FROM radcheck WHERE username = :username"),
                {"username": username}
            )
            self.db.execute(
                text("DELETE FROM radreply WHERE username = :username"),
                {"username": username}
            )
            self.db.commit()
            return True
            
        except Exception as e:
            self.db.rollback()
            print(f"Error deleting RADIUS user: {e}")
            return False
    
    def get_active_sessions(self) -> List[Dict]:
        """Get currently active RADIUS sessions"""
        
        try:
            result = self.db.execute(
                text("""
                    SELECT 
                        username,
                        nasipaddress,
                        acctstarttime,
                        acctsessiontime,
                        acctinputoctets,
                        acctoutputoctets,
                        framedipaddress,
                        callingstationid as mac_address
                    FROM radacct
                    WHERE acctstoptime IS NULL
                    ORDER BY acctstarttime DESC
                """)
            )
            
            sessions = []
            for row in result:
                sessions.append({
                    "username": row[0],
                    "nas_ip": row[1],
                    "start_time": row[2],
                    "session_time": row[3],
                    "bytes_in": row[4],
                    "bytes_out": row[5],
                    "ip_address": row[6],
                    "mac_address": row[7]
                })
            
            return sessions
            
        except Exception as e:
            print(f"Error getting active sessions: {e}")
            return []
    
    def get_user_sessions(self, username: str) -> List[Dict]:
        """Get session history for a specific user"""
        
        try:
            result = self.db.execute(
                text("""
                    SELECT 
                        acctstarttime,
                        acctstoptime,
                        acctsessiontime,
                        acctinputoctets,
                        acctoutputoctets,
                        framedipaddress,
                        callingstationid as mac_address,
                        acctterminatecause
                    FROM radacct
                    WHERE username = :username
                    ORDER BY acctstarttime DESC
                    LIMIT 50
                """),
                {"username": username}
            )
            
            sessions = []
            for row in result:
                sessions.append({
                    "start_time": row[0],
                    "stop_time": row[1],
                    "duration": row[2],
                    "bytes_in": row[3],
                    "bytes_out": row[4],
                    "ip_address": row[5],
                    "mac_address": row[6],
                    "terminate_cause": row[7]
                })
            
            return sessions
            
        except Exception as e:
            print(f"Error getting user sessions: {e}")
            return []
    
    def disconnect_user(self, username: str) -> bool:
        """
        Disconnect user by updating radacct
        Note: Actual disconnect requires RADIUS COA/DM packet
        """
        
        try:
            # Close any open sessions in accounting
            self.db.execute(
                text("""
                    UPDATE radacct 
                    SET acctstoptime = NOW(),
                        acctterminatecause = 'Admin-Disconnect'
                    WHERE username = :username 
                    AND acctstoptime IS NULL
                """),
                {"username": username}
            )
            self.db.commit()
            return True
            
        except Exception as e:
            self.db.rollback()
            print(f"Error disconnecting user: {e}")
            return False
    
    def update_session_timeout(self, username: str, timeout: int) -> bool:
        """Update session timeout for a user"""
        
        try:
            # Update or insert Session-Timeout
            self.db.execute(
                text("DELETE FROM radreply WHERE username = :username AND attribute = 'Session-Timeout'"),
                {"username": username}
            )
            
            self.db.execute(
                text("""
                    INSERT INTO radreply (username, attribute, op, value)
                    VALUES (:username, 'Session-Timeout', '=', :timeout)
                """),
                {"username": username, "timeout": str(timeout)}
            )
            
            self.db.commit()
            return True
            
        except Exception as e:
            self.db.rollback()
            print(f"Error updating session timeout: {e}")
            return False
