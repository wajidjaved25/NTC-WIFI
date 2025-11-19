"""
Data Limit Enforcement Service
Real-time monitoring and enforcement of data usage limits
"""

import asyncio
from datetime import datetime, timezone
from sqlalchemy import text
from sqlalchemy.orm import Session
import subprocess

from ..database import SessionLocal
from ..models.radius_settings import RadiusSettings


class DataLimitEnforcer:
    """
    Monitors active sessions and disconnects users who exceed their data limits
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
    
    async def start(self):
        """Start the enforcement loop"""
        self.running = True
        self._task = asyncio.create_task(self._enforcement_loop())
        print(f"📊 Data Limit Enforcer started (checking every {self.check_interval}s)")
    
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
    
    async def _enforcement_loop(self):
        """Main enforcement loop"""
        while self.running:
            try:
                await self._check_and_enforce()
            except Exception as e:
                print(f"❌ Data limit enforcement error: {e}")
            
            await asyncio.sleep(self.check_interval)
    
    async def _check_and_enforce(self):
        """Check all active sessions and enforce limits"""
        db = SessionLocal()
        
        try:
            # Get global settings
            settings = db.query(RadiusSettings).first()
            
            if not settings:
                return
            
            global_daily_limit = settings.daily_data_limit * 1048576 if settings.daily_data_limit else 0  # MB to bytes
            global_monthly_limit = settings.monthly_data_limit * 1048576 if settings.monthly_data_limit else 0
            
            # Skip if no limits configured
            if global_daily_limit == 0 and global_monthly_limit == 0:
                return
            
            # Get all active sessions with their data usage
            active_users = db.execute(
                text("""
                    SELECT DISTINCT username 
                    FROM radacct 
                    WHERE acctstoptime IS NULL
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
                    await self._disconnect_user(db, username, exceeded)
        
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
    
    async def _disconnect_user(self, db: Session, username: str, reason: str):
        """
        Disconnect user from the network
        
        Args:
            db: Database session
            username: User to disconnect
            reason: Why they're being disconnected
        """
        
        print(f"⚠️ Disconnecting {username}: {reason}")
        
        try:
            # Get the user's MAC address from active session
            session_info = db.execute(
                text("""
                    SELECT callingstationid, nasipaddress, acctsessionid
                    FROM radacct
                    WHERE username = :username
                    AND acctstoptime IS NULL
                    ORDER BY acctstarttime DESC
                    LIMIT 1
                """),
                {"username": username}
            ).fetchone()
            
            mac_address = session_info[0] if session_info else None
            
            # Method 1: Disconnect via Omada API (most effective)
            if mac_address:
                await self._disconnect_via_omada(db, mac_address)
            
            # Method 2: Send RADIUS Disconnect-Request (CoA)
            await self._send_radius_disconnect(username)
            
            # Method 3: Mark session as stopped in radacct
            db.execute(
                text("""
                    UPDATE radacct 
                    SET acctstoptime = NOW(),
                        acctterminatecause = :reason
                    WHERE username = :username 
                    AND acctstoptime IS NULL
                """),
                {"username": username, "reason": "Data-Limit-Exceeded"}
            )
            db.commit()
            
            print(f"✓ Disconnected {username}")
            
        except Exception as e:
            print(f"❌ Failed to disconnect {username}: {e}")
            db.rollback()
    
    async def _disconnect_via_omada(self, db: Session, mac_address: str):
        """
        Disconnect user via Omada controller API
        """
        try:
            from ..models.omada_config import OmadaConfig
            from ..services.omada_service import OmadaService
            
            # Get active Omada config
            omada_config = db.query(OmadaConfig).filter(OmadaConfig.is_active == True).first()
            
            if not omada_config:
                print("⚠️ No active Omada configuration found")
                return
            
            # Create Omada service instance
            omada = OmadaService(
                controller_url=omada_config.controller_url,
                username=omada_config.username,
                encrypted_password=omada_config.password,
                controller_id=omada_config.controller_id,
                site_id=omada_config.site_id or "Default"
            )
            
            # Normalize MAC address format
            mac_clean = mac_address.replace('-', '').replace(':', '').replace('.', '').lower()
            mac_formatted = ':'.join(mac_clean[i:i+2] for i in range(0, 12, 2))
            
            # Unauthorize the client
            result = omada.unauthorize_client(mac_formatted)
            
            if result.get('success'):
                print(f"✓ Omada: Unauthorized client {mac_formatted}")
            else:
                print(f"⚠️ Omada: {result.get('message')}")
                
        except Exception as e:
            print(f"⚠️ Omada disconnect error: {e}")
    
    async def _send_radius_disconnect(self, username: str):
        """
        Send RADIUS Disconnect-Request to NAS
        
        This uses radclient to send a CoA disconnect message
        """
        
        try:
            # Get NAS IP from active session
            db = SessionLocal()
            try:
                nas_info = db.execute(
                    text("""
                        SELECT nasipaddress, acctsessionid
                        FROM radacct
                        WHERE username = :username
                        AND acctstoptime IS NULL
                        ORDER BY acctstarttime DESC
                        LIMIT 1
                    """),
                    {"username": username}
                ).fetchone()
                
                if not nas_info:
                    return
                
                nas_ip = str(nas_info[0])
                session_id = nas_info[1]
                
            finally:
                db.close()
            
            # Build disconnect command
            # Format: echo "User-Name=xxx\nAcct-Session-Id=yyy" | radclient nas_ip:3799 disconnect secret
            disconnect_cmd = f"""echo "User-Name={username}
Acct-Session-Id={session_id}" | radclient {nas_ip}:3799 disconnect testing123"""
            
            # Execute asynchronously
            process = await asyncio.create_subprocess_shell(
                disconnect_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=5.0
            )
            
            if process.returncode == 0:
                print(f"✓ RADIUS disconnect sent to {nas_ip} for {username}")
            else:
                print(f"⚠️ RADIUS disconnect may have failed: {stderr.decode()}")
                
        except asyncio.TimeoutError:
            print(f"⚠️ RADIUS disconnect timed out for {username}")
        except Exception as e:
            print(f"⚠️ RADIUS disconnect error: {e}")


# Global enforcer instance
data_limit_enforcer = DataLimitEnforcer(check_interval=60)  # Check every 60 seconds


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
