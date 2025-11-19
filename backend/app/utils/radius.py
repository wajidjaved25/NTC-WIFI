"""
RADIUS Integration Module
Handles user creation, deletion, and session management with FreeRADIUS
"""
from sqlalchemy import text
from ..database import SessionLocal
import subprocess
import os

def create_radius_user(username: str, password: str, session_timeout: int = 3600, bandwidth_limit: int = None):
    """
    Create RADIUS user in database
    
    Args:
        username: Mobile number (e.g., 03001234567)
        password: CNIC or Passport number
        session_timeout: Session time in seconds (default 1 hour = 3600)
        bandwidth_limit: Bandwidth in kbps (optional)
    
    Returns:
        bool: True if successful
    """
    db = SessionLocal()
    
    try:
        # Check if user already exists
        result = db.execute(
            text("SELECT id FROM radcheck WHERE username = :username"),
            {"username": username}
        ).fetchone()
        
        if result:
            # User exists, update password
            db.execute(
                text("""
                    UPDATE radcheck 
                    SET value = :password 
                    WHERE username = :username AND attribute = 'Cleartext-Password'
                """),
                {"username": username, "password": password}
            )
            print(f"✓ Updated RADIUS user: {username}")
        else:
            # Create new user
            db.execute(
                text("""
                    INSERT INTO radcheck (username, attribute, op, value)
                    VALUES (:username, 'Cleartext-Password', ':=', :password)
                """),
                {"username": username, "password": password}
            )
            print(f"✓ Created RADIUS user: {username}")
        
        # Add/Update session timeout
        timeout_exists = db.execute(
            text("""
                SELECT id FROM radreply 
                WHERE username = :username AND attribute = 'Session-Timeout'
            """),
            {"username": username}
        ).fetchone()
        
        if timeout_exists:
            db.execute(
                text("""
                    UPDATE radreply 
                    SET value = :timeout 
                    WHERE username = :username AND attribute = 'Session-Timeout'
                """),
                {"username": username, "timeout": str(session_timeout)}
            )
        else:
            db.execute(
                text("""
                    INSERT INTO radreply (username, attribute, op, value)
                    VALUES (:username, 'Session-Timeout', ':=', :timeout)
                """),
                {"username": username, "timeout": str(session_timeout)}
            )
        
        # Add bandwidth limit if specified
        if bandwidth_limit:
            bandwidth_exists = db.execute(
                text("""
                    SELECT id FROM radreply 
                    WHERE username = :username AND attribute = 'WISPr-Bandwidth-Max-Down'
                """),
                {"username": username}
            ).fetchone()
            
            if bandwidth_exists:
                db.execute(
                    text("""
                        UPDATE radreply 
                        SET value = :bandwidth 
                        WHERE username = :username AND attribute = 'WISPr-Bandwidth-Max-Down'
                    """),
                    {"username": username, "bandwidth": str(bandwidth_limit * 1000)}
                )
            else:
                db.execute(
                    text("""
                        INSERT INTO radreply (username, attribute, op, value)
                        VALUES (:username, 'WISPr-Bandwidth-Max-Down', ':=', :bandwidth)
                    """),
                    {"username": username, "bandwidth": str(bandwidth_limit * 1000)}
                )
        
        db.commit()
        return True
        
    except Exception as e:
        print(f"✗ Error creating RADIUS user: {e}")
        db.rollback()
        return False
        
    finally:
        db.close()


def delete_radius_user(username: str):
    """Delete RADIUS user from database"""
    db = SessionLocal()
    
    try:
        db.execute(
            text("DELETE FROM radcheck WHERE username = :username"),
            {"username": username}
        )
        db.execute(
            text("DELETE FROM radreply WHERE username = :username"),
            {"username": username}
        )
        db.commit()
        print(f"✓ Deleted RADIUS user: {username}")
        return True
    except Exception as e:
        print(f"✗ Error deleting RADIUS user: {e}")
        db.rollback()
        return False
    finally:
        db.close()


def get_active_radius_sessions():
    """
    Get all active RADIUS sessions from accounting table
    
    Returns:
        list: List of active session dictionaries
    """
    db = SessionLocal()
    
    try:
        result = db.execute(
            text("""
                SELECT username, acctsessionid, nasipaddress, 
                       acctstarttime, 
                       acctinputoctets, acctoutputoctets,
                       callingstationid, framedipaddress,
                       calledstationid, nasportid,
                       EXTRACT(EPOCH FROM (NOW() - acctstarttime))::int as duration
                FROM radacct 
                WHERE acctstoptime IS NULL
                ORDER BY acctstarttime DESC
            """)
        ).fetchall()
        
        sessions = []
        for row in result:
            # Parse SSID from calledstationid (format: MAC:SSID or just MAC)
            called_station = row[8] or ""
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
            
            sessions.append({
                "username": row[0],
                "session_id": row[1],
                "nas_ip": str(row[2]) if row[2] else "",
                "start_time": row[3].isoformat() if row[3] else None,
                "bytes_in": row[4] or 0,
                "bytes_out": row[5] or 0,
                "mac_address": row[6],
                "ip_address": str(row[7]) if row[7] else "",
                "ssid": ssid,
                "ap_mac": ap_mac,
                "ap_name": row[9] or "",  # nasportid often contains AP name/port info
                "duration": row[10] or 0
            })
        
        return sessions
        
    finally:
        db.close()


def get_user_session_history(username: str, limit: int = 10):
    """
    Get session history for a specific user
    
    Args:
        username: Mobile number
        limit: Number of sessions to return
    
    Returns:
        list: List of session history dictionaries
    """
    db = SessionLocal()
    
    try:
        result = db.execute(
            text("""
                SELECT acctsessionid, nasipaddress, 
                       acctstarttime, acctstoptime,
                       acctsessiontime,
                       acctinputoctets, acctoutputoctets,
                       acctterminatecause,
                       callingstationid, framedipaddress,
                       calledstationid, nasportid
                FROM radacct 
                WHERE username = :username
                ORDER BY acctstarttime DESC
                LIMIT :limit
            """),
            {"username": username, "limit": limit}
        ).fetchall()
        
        history = []
        for row in result:
            # Parse SSID from calledstationid
            called_station = row[10] or ""
            ssid = ""
            ap_mac = ""
            if ":" in called_station:
                parts = called_station.split(":")
                if len(parts) > 6:
                    ap_mac = ":".join(parts[:6])
                    ssid = ":".join(parts[6:])
                else:
                    ap_mac = called_station
            else:
                ap_mac = called_station
            
            history.append({
                "session_id": row[0],
                "nas_ip": str(row[1]) if row[1] else "",
                "start_time": row[2].isoformat() if row[2] else None,
                "stop_time": row[3].isoformat() if row[3] else None,
                "duration": row[4] or 0,
                "bytes_in": row[5] or 0,
                "bytes_out": row[6] or 0,
                "terminate_cause": row[7],
                "mac_address": row[8],
                "ip_address": str(row[9]) if row[9] else "",
                "ssid": ssid,
                "ap_mac": ap_mac,
                "ap_name": row[11] or ""
            })
        
        return history
        
    finally:
        db.close()


def disconnect_user_session(username: str, nas_ip: str = "192.168.3.50", secret: str = "testing123"):
    """
    Send RADIUS disconnect message to terminate user session
    
    Args:
        username: Mobile number to disconnect
        nas_ip: Omada controller IP
        secret: RADIUS shared secret
    
    Returns:
        bool: True if command executed successfully
    """
    try:
        # Create disconnect request
        disconnect_cmd = [
            'echo',
            f'User-Name={username}',
            '|',
            'radclient',
            f'{nas_ip}:3799',  # CoA/Disconnect port
            'disconnect',
            secret
        ]
        
        # Execute disconnect command
        result = subprocess.run(
            ' '.join(disconnect_cmd),
            shell=True,
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode == 0:
            print(f"✓ Sent disconnect request for user: {username}")
            return True
        else:
            print(f"✗ Failed to disconnect user: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"✗ Error disconnecting user: {e}")
        return False


def get_radius_statistics():
    """
    Get overall RADIUS statistics
    
    Returns:
        dict: Statistics dictionary
    """
    db = SessionLocal()
    
    try:
        # Total users
        total_users = db.execute(
            text("SELECT COUNT(DISTINCT username) FROM radcheck")
        ).scalar()
        
        # Active sessions
        active_sessions = db.execute(
            text("SELECT COUNT(*) FROM radacct WHERE acctstoptime IS NULL")
        ).scalar()
        
        # Total sessions today
        sessions_today = db.execute(
            text("""
                SELECT COUNT(*) FROM radacct 
                WHERE DATE(acctstarttime) = CURRENT_DATE
            """)
        ).scalar()
        
        # Total data usage today (in bytes)
        data_today = db.execute(
            text("""
                SELECT 
                    COALESCE(SUM(acctinputoctets), 0) as total_in,
                    COALESCE(SUM(acctoutputoctets), 0) as total_out
                FROM radacct 
                WHERE DATE(acctstarttime) = CURRENT_DATE
            """)
        ).fetchone()
        
        return {
            "total_users": total_users or 0,
            "active_sessions": active_sessions or 0,
            "sessions_today": sessions_today or 0,
            "data_in_today": data_today[0] if data_today else 0,
            "data_out_today": data_today[1] if data_today else 0,
            "total_data_today": (data_today[0] + data_today[1]) if data_today else 0
        }
        
    finally:
        db.close()


def update_user_session_timeout(username: str, new_timeout: int):
    """
    Update session timeout for a user
    
    Args:
        username: Mobile number
        new_timeout: New timeout in seconds
    
    Returns:
        bool: True if successful
    """
    db = SessionLocal()
    
    try:
        db.execute(
            text("""
                UPDATE radreply 
                SET value = :timeout 
                WHERE username = :username AND attribute = 'Session-Timeout'
            """),
            {"username": username, "timeout": str(new_timeout)}
        )
        db.commit()
        print(f"✓ Updated session timeout for {username} to {new_timeout}s")
        return True
        
    except Exception as e:
        print(f"✗ Error updating session timeout: {e}")
        db.rollback()
        return False
        
    finally:
        db.close()
