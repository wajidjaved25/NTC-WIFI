"""
Data Limit Enforcement Service
Real-time monitoring and enforcement of data usage limits
"""

import asyncio
from datetime import datetime, timezone
from sqlalchemy import text
from sqlalchemy.orm import Session
import subprocess
import logging # Added for better error tracking

from ..database import SessionLocal
from ..models.radius_settings import RadiusSettings

# Configure logging if not already done elsewhere
# logging.basicConfig(level=logging.INFO)

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
        logging.info(f"📊 Data Limit Enforcer started (checking every {self.check_interval}s)")
    
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
        logging.info("📊 Data Limit Enforcer stopped")
    
    async def _enforcement_loop(self):
        """Main enforcement loop"""
        while self.running:
            try:
                await self._check_and_enforce()
            except Exception as e:
                print(f"❌ Data limit enforcement error: {e}")
                logging.error(f"❌ Data limit enforcement error: {e}", exc_info=True)
            
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
        logging.warning(f"⚠️ Disconnecting {username}: {reason}")
        
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
            nas_ip = session_info[1] if session_info else None
            acct_session_id = session_info[2] if session_info else None
            
            # Method 1: Disconnect via Omada API (most effective - needs correct OmadaService impl)
            if mac_address:
                await self._disconnect_via_omada(db, mac_address)
            
            # Method 2: Send RADIUS Disconnect-Request (CoA) - Requires radclient
            if nas_ip and acct_session_id:
                await self._send_radius_disconnect(username, nas_ip, acct_session_id)
            
            # Method 3: Mark session as stopped in radacct
            rows_affected = db.execute(
                text("""
                    UPDATE radacct 
                    SET acctstoptime = NOW(),
                        acctterminatecause = :reason
                    WHERE username = :username 
                    AND acctstoptime IS NULL
                """),
                {"username": username, "reason": "Data-Limit-Exceeded"}
            ).rowcount
            db.commit()
            
            if rows_affected > 0:
                print(f"✓ Disconnected {username} (marked session stopped)")
                logging.info(f"✓ Disconnected {username} (marked session stopped)")
            else:
                print(f"! User {username} had no active radacct session to mark stopped.")
                logging.warning(f"! User {username} had no active radacct session to mark stopped.")
            
        except Exception as e:
            print(f"❌ Failed to disconnect {username}: {e}")
            logging.error(f"❌ Failed to disconnect {username}: {e}", exc_info=True)
            db.rollback()
    
    async def _disconnect_via_omada(self, db: Session, mac_address: str):
        """
        Disconnect user via Omada controller API.
        Note: Requires the OmadaService's unauthorize_client method to be correctly implemented
        according to the Omada Controller's main API documentation (not the portal API).
        Expected endpoint: DELETE /api/v2/sites/{siteId}/clients/{clientMac}
        """
        try:
            from ..models.omada_config import OmadaConfig
            from ..services.omada_service import OmadaService
            
            # Get active Omada config
            omada_config = db.query(OmadaConfig).filter(OmadaConfig.is_active == True).first()
            
            if not omada_config:
                print("⚠️ No active Omada configuration found for disconnection")
                logging.warning("No active Omada configuration found for disconnection")
                return
            
            # Create Omada service instance
            omada_service = OmadaService(
                controller_url=omada_config.controller_url,
                username=omada_config.username,
                encrypted_password=omada_config.password_encrypted,
                controller_id=omada_config.controller_id,
                site_id=omada_config.site_id or "Default"
            )
            
            # Normalize MAC address format (e.g., aa:bb:cc:dd:ee:ff)
            mac_clean = mac_address.replace('-', '').replace(':', '').replace('.', '').lower()
            mac_formatted = ':'.join(mac_clean[i:i+2] for i in range(0, 12, 2))
            
            print(f"Attempting to disconnect client {mac_formatted} via Omada API...")
            logging.info(f"Attempting to disconnect client {mac_formatted} via Omada API...")

            # Call the Omada service method to disconnect the client
            # This method needs to correctly implement: DELETE /api/v2/sites/{siteId}/clients/{mac_formatted}
            result = omada_service.unauthorize_client(mac_formatted) 

            print(f"Omada API response: {result}") # Log the raw response for debugging
            logging.debug(f"Omada API response for {mac_formatted}: {result}")

            # Assuming the OmadaService method returns a dictionary like {'success': True/False, 'message': '...'}
            if result and result.get('success'):
                print(f"✓ Omada: Successfully disconnected client {mac_formatted}")
                logging.info(f"Successfully disconnected client {mac_formatted} via Omada API")
            else:
                # Log the specific error message from the Omada service
                error_msg = result.get('message', 'Unknown error from Omada API') if isinstance(result, dict) else 'Invalid response format from Omada API'
                print(f"⚠️ Omada: Failed to disconnect client {mac_formatted}. Reason: {error_msg}")
                logging.error(f"Failed to disconnect client {mac_formatted} via Omada API. Reason: {error_msg}")

        except ImportError as e:
            print(f"⚠️ Omada modules not found: {e}")
            logging.error(f"Omada modules import failed: {e}")
        except AttributeError as e:
            print(f"⚠️ OmadaService might be missing the 'unauthorize_client' method: {e}")
            logging.error(f"OmadaService method error: {e}")
        except Exception as e:
            # Catch any other unexpected errors during the Omada disconnection attempt
            print(f"⚠️ Unexpected error during Omada disconnection for {mac_address}: {e}")
            logging.error(f"Unexpected error during Omada disconnection for {mac_address}: {e}", exc_info=True)
            # Do not raise the exception here - let other disconnection methods proceed

    async def _send_radius_disconnect(self, username: str, nas_ip: str, session_id: str):
        """
        Send RADIUS Disconnect-Request to NAS using radclient.
        This method requires 'freeradius-utils' package to be installed.
        """
        try:
            # Check if radclient is available
            # You might want to cache this check
            process = await asyncio.create_subprocess_shell(
                "command -v radclient",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            _, _ = await process.communicate()
            if process.returncode != 0:
                print(f"⚠️ radclient not found, cannot send RADIUS disconnect for {username}")
                logging.warning(f"radclient not found, cannot send RADIUS disconnect for {username}")
                return

            # Build disconnect command
            # Format: echo "User-Name=xxx\nAcct-Session-Id=yyy" | radclient nas_ip:3799 disconnect secret
            disconnect_cmd = f"""echo -e "User-Name={username}\\nAcct-Session-Id={session_id}" | radclient {nas_ip}:3799 disconnect testing123"""
            
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
                logging.info(f"✓ RADIUS disconnect sent to {nas_ip} for {username}")
            else:
                print(f"⚠️ RADIUS disconnect failed for {username}: {stderr.decode()}")
                logging.error(f"⚠️ RADIUS disconnect failed for {username}: {stderr.decode()}")
                
        except asyncio.TimeoutError:
            print(f"⚠️ RADIUS disconnect timed out for {username}")
            logging.error(f"⚠️ RADIUS disconnect timed out for {username}")
        except Exception as e:
            print(f"⚠️ RADIUS disconnect error for {username}: {e}")
            logging.error(f"⚠️ RADIUS disconnect error for {username}: {e}", exc_info=True)


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
