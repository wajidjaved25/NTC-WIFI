"""
Data Limit Enforcement Service
Real-time monitoring and enforcement of data usage limits using Session-Timeout method
"""

import asyncio
import logging
from datetime import datetime, timezone
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..database import SessionLocal
from ..models.radius_settings import RadiusSettings


class DataLimitEnforcer:
    """
    Monitors active sessions and enforces data usage limits.
    Uses Session-Timeout approach to force re-authentication.
    """
    
    def __init__(self, check_interval: int = 60):
        """
        Initialize the enforcer
        
        Args:
            check_interval: How often to check data usage (seconds)
        """
        self.check_interval = check_interval
        self.running = False
        self._task = None
        # Track users who have been marked for short timeout to avoid repeated updates
        self._users_timeout_set = set()

    async def start(self):
        """Start the enforcement loop"""
        self.running = True
        self._task = asyncio.create_task(self._enforcement_loop())
        print(f"📊 Data Limit Enforcer started (checking every {self.check_interval}s)")
        logging.info(f"Data Limit Enforcer started (checking every {self.check_interval}s)")
    
    async def stop(self):
        """Stop the enforcement loop"""
        self.running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        print("📊 Data Limit Enforcer stopped")
        logging.info("Data Limit Enforcer stopped")
    
    async def _enforcement_loop(self):
        """Main enforcement loop"""
        while self.running:
            try:
                await self._check_and_enforce()
            except Exception as e:
                print(f"❌ Data limit enforcement error: {e}")
                logging.error(f"Data limit enforcement error: {e}", exc_info=True)
            
            await asyncio.sleep(self.check_interval)

    async def _check_and_enforce(self):
        """Check all active sessions and enforce limits"""
        db = SessionLocal()
        
        try:
            # Get global settings
            settings = db.query(RadiusSettings).first()
            
            if not settings:
                return
            
            global_daily_limit = settings.daily_data_limit * 1048576 if settings.daily_data_limit else 0
            global_monthly_limit = settings.monthly_data_limit * 1048576 if settings.monthly_data_limit else 0
            
            # Skip if no limits configured
            if global_daily_limit == 0 and global_monthly_limit == 0:
                return
            
            # Get all active sessions
            active_users = db.execute(
                text("""
                    SELECT DISTINCT username 
                    FROM radacct 
                    WHERE acctstoptime IS NULL
                    AND username IS NOT NULL
                    AND username != ''
                """)
            ).fetchall()
            
            for (username,) in active_users:
                exceeded = await self._check_user_limits(
                    db, 
                    username, 
                    global_daily_limit, 
                    global_monthly_limit
                )
                
                if exceeded:
                    await self._enforce_limit(db, username, exceeded)
                else:
                    # User is within limits, remove from timeout set if they were there
                    self._users_timeout_set.discard(username)
        
        finally:
            db.close()
    
    async def _check_user_limits(
        self, 
        db: Session, 
        username: str, 
        global_daily_limit: int, 
        global_monthly_limit: int
    ) -> str:
        """
        Check if user has exceeded their limits
        
        Returns:
            str: Reason for exceeding limit, or empty string if within limits
        """
        
        # Get user-specific limits from radcheck (override global)
        user_daily = db.execute(
            text("""
                SELECT CAST(value AS BIGINT) FROM radcheck 
                WHERE username = :username AND attribute = 'Max-Daily-Data'
            """),
            {"username": username}
        ).scalar()
        
        user_monthly = db.execute(
            text("""
                SELECT CAST(value AS BIGINT) FROM radcheck 
                WHERE username = :username AND attribute = 'Max-Monthly-Data'
            """),
            {"username": username}
        ).scalar()
        
        # Use user-specific or global limits
        daily_limit = user_daily if user_daily else global_daily_limit
        monthly_limit = user_monthly if user_monthly else global_monthly_limit
        
        # Check daily usage
        if daily_limit > 0:
            daily_usage = db.execute(
                text("""
                    SELECT COALESCE(SUM(acctinputoctets + acctoutputoctets), 0)
                    FROM radacct
                    WHERE username = :username
                    AND acctstarttime >= date_trunc('day', CURRENT_TIMESTAMP)
                """),
                {"username": username}
            ).scalar()
            
            if daily_usage >= daily_limit:
                return f"daily_limit_exceeded ({daily_usage / 1048576:.2f} MB / {daily_limit / 1048576:.2f} MB)"
        
        # Check monthly usage
        if monthly_limit > 0:
            monthly_usage = db.execute(
                text("""
                    SELECT COALESCE(SUM(acctinputoctets + acctoutputoctets), 0)
                    FROM radacct
                    WHERE username = :username
                    AND acctstarttime >= date_trunc('month', CURRENT_TIMESTAMP)
                """),
                {"username": username}
            ).scalar()
            
            if monthly_usage >= monthly_limit:
                return f"monthly_limit_exceeded ({monthly_usage / 1048576:.2f} MB / {monthly_limit / 1048576:.2f} MB)"
        
        return ""
    
    async def _enforce_limit(self, db: Session, username: str, reason: str):
        """
        Enforce data limit by:
        1. Sending RADIUS CoA Disconnect to immediately kick user
        2. Setting short Session-Timeout to prevent long sessions if they reconnect
        3. Marking session as stopped in radacct
        
        Args:
            db: Database session
            username: User who exceeded limit
            reason: Why they exceeded the limit
        """
        
        # Skip if we already processed this user
        if username in self._users_timeout_set:
            return
        
        print(f"⚠️ Enforcing limit for {username}: {reason}")
        logging.warning(f"Enforcing limit for {username}: {reason}")
        
        try:
            # Get session info for CoA
            session_info = db.execute(
                text("""
                    SELECT acctsessionid, callingstationid, nasipaddress, framedipaddress
                    FROM radacct
                    WHERE username = :username
                    AND acctstoptime IS NULL
                    ORDER BY acctstarttime DESC
                    LIMIT 1
                """),
                {"username": username}
            ).fetchone()
            
            coa_success = False
            if session_info:
                session_id = session_info[0]
                mac_address = session_info[1]
                nas_ip = str(session_info[2]) if session_info[2] else "192.168.3.254"
                
                # Send RADIUS CoA Disconnect
                coa_success = await self._send_radius_coa_disconnect(
                    db, username, session_id, mac_address, nas_ip
                )
            
            # Set short Session-Timeout for future connections
            SHORT_TIMEOUT = 60  # seconds
            
            existing = db.execute(
                text("""
                    SELECT id FROM radreply 
                    WHERE username = :username AND attribute = 'Session-Timeout'
                """),
                {"username": username}
            ).fetchone()
            
            if existing:
                db.execute(
                    text("""
                        UPDATE radreply 
                        SET value = :timeout 
                        WHERE username = :username AND attribute = 'Session-Timeout'
                    """),
                    {"username": username, "timeout": str(SHORT_TIMEOUT)}
                )
            else:
                db.execute(
                    text("""
                        INSERT INTO radreply (username, attribute, op, value)
                        VALUES (:username, 'Session-Timeout', '=', :timeout)
                    """),
                    {"username": username, "timeout": str(SHORT_TIMEOUT)}
                )
            
            # Mark session as stopped if CoA succeeded
            if coa_success:
                db.execute(
                    text("""
                        UPDATE radacct 
                        SET acctstoptime = NOW(),
                            acctterminatecause = 'Data-Limit-Exceeded'
                        WHERE username = :username 
                        AND acctstoptime IS NULL
                    """),
                    {"username": username}
                )
            
            db.commit()
            
            # Add to tracked set
            self._users_timeout_set.add(username)
            
            if coa_success:
                print(f"✓ Successfully disconnected {username} via RADIUS CoA")
                logging.info(f"Successfully disconnected {username} via RADIUS CoA")
            else:
                print(f"⚠️ CoA failed for {username}, but Session-Timeout set to {SHORT_TIMEOUT}s")
                logging.warning(f"CoA failed for {username}, Session-Timeout set to {SHORT_TIMEOUT}s")
            
        except Exception as e:
            print(f"❌ Failed to enforce limit for {username}: {e}")
            logging.error(f"Failed to enforce limit for {username}: {e}", exc_info=True)
            db.rollback()
    
    async def _send_radius_coa_disconnect(self, db: Session, username: str, session_id: str, mac_address: str, nas_ip: str) -> bool:
        """
        Send RADIUS CoA Disconnect-Request to immediately disconnect user.
        
        Returns:
            bool: True if disconnect was acknowledged, False otherwise
        """
        try:
            import shutil
            
            # Check if radclient is available (try common paths)
            radclient_path = shutil.which('radclient')
            if not radclient_path:
                # Try common installation paths
                for path in ['/usr/bin/radclient', '/usr/local/bin/radclient']:
                    if shutil.which(path) or __import__('os').path.exists(path):
                        radclient_path = path
                        break
            
            if not radclient_path:
                print("⚠️ radclient not found - install with: sudo apt install freeradius-utils")
                return False
            
            # Get RADIUS shared secret from settings
            settings = db.query(RadiusSettings).first()
            coa_secret = settings.radius_secret if settings and settings.radius_secret else "MySecretRadius2024!"
            
            # Build the disconnect request
            # Using here-doc style for proper attribute formatting
            disconnect_cmd = f'''{radclient_path} -x {nas_ip}:3799 disconnect {coa_secret} << EOF
User-Name = "{username}"
Acct-Session-Id = "{session_id}"
Calling-Station-Id = "{mac_address}"
NAS-IP-Address = {nas_ip}
EOF'''
            
            print(f"Sending RADIUS CoA Disconnect to {nas_ip}:3799 for {username}")
            
            # Execute the command
            process = await asyncio.create_subprocess_shell(
                disconnect_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=10.0
            )
            
            output = stdout.decode() + stderr.decode()
            
            if 'Disconnect-ACK' in output:
                print(f"✓ RADIUS CoA Disconnect-ACK received for {username}")
                return True
            elif 'Disconnect-NAK' in output:
                print(f"⚠️ RADIUS CoA Disconnect-NAK for {username}: {output}")
                return False
            else:
                print(f"⚠️ RADIUS CoA unexpected response for {username}: {output}")
                return False
                
        except asyncio.TimeoutError:
            print(f"⚠️ RADIUS CoA timed out for {username}")
            return False
        except Exception as e:
            print(f"⚠️ RADIUS CoA error for {username}: {e}")
            return False


# Global enforcer instance
data_limit_enforcer = DataLimitEnforcer(check_interval=60)


async def get_user_data_usage(username: str) -> dict:
    """
    Get current data usage for a user
    
    Returns:
        dict: Usage information with daily and monthly totals
    """
    db = SessionLocal()
    
    try:
        # Get limits
        settings = db.query(RadiusSettings).first()
        
        daily_limit = 0
        monthly_limit = 0
        
        if settings:
            daily_limit = settings.daily_data_limit * 1048576 if settings.daily_data_limit else 0
            monthly_limit = settings.monthly_data_limit * 1048576 if settings.monthly_data_limit else 0
        
        # Check for user-specific limits
        user_daily = db.execute(
            text("""
                SELECT CAST(value AS BIGINT) FROM radcheck 
                WHERE username = :username AND attribute = 'Max-Daily-Data'
            """),
            {"username": username}
        ).scalar()
        
        user_monthly = db.execute(
            text("""
                SELECT CAST(value AS BIGINT) FROM radcheck 
                WHERE username = :username AND attribute = 'Max-Monthly-Data'
            """),
            {"username": username}
        ).scalar()
        
        if user_daily:
            daily_limit = user_daily
        if user_monthly:
            monthly_limit = user_monthly
        
        # Get usage
        daily_usage = db.execute(
            text("""
                SELECT COALESCE(SUM(acctinputoctets + acctoutputoctets), 0)
                FROM radacct
                WHERE username = :username
                AND acctstarttime >= date_trunc('day', CURRENT_TIMESTAMP)
            """),
            {"username": username}
        ).scalar()
        
        monthly_usage = db.execute(
            text("""
                SELECT COALESCE(SUM(acctinputoctets + acctoutputoctets), 0)
                FROM radacct
                WHERE username = :username
                AND acctstarttime >= date_trunc('month', CURRENT_TIMESTAMP)
            """),
            {"username": username}
        ).scalar()
        
        return {
            "username": username,
            "daily": {
                "used_bytes": daily_usage,
                "used_mb": round(daily_usage / 1048576, 2),
                "limit_bytes": daily_limit,
                "limit_mb": round(daily_limit / 1048576, 2) if daily_limit else 0,
                "percentage": round((daily_usage / daily_limit) * 100, 1) if daily_limit else 0,
                "exceeded": daily_usage >= daily_limit if daily_limit else False
            },
            "monthly": {
                "used_bytes": monthly_usage,
                "used_mb": round(monthly_usage / 1048576, 2),
                "limit_bytes": monthly_limit,
                "limit_mb": round(monthly_limit / 1048576, 2) if monthly_limit else 0,
                "percentage": round((monthly_usage / monthly_limit) * 100, 1) if monthly_limit else 0,
                "exceeded": monthly_usage >= monthly_limit if monthly_limit else False
            }
        }
        
    finally:
        db.close()
