"""
Omada Controller Manager - Handles multiple controllers with automatic failover
"""
import logging
from typing import Optional, Dict, List
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from ..models.omada_config import OmadaConfig
from .omada_service import OmadaService

logger = logging.getLogger(__name__)

class OmadaControllerManager:
    """
    Manages multiple Omada controllers with automatic failover.
    
    Features:
    - Automatic failover to backup controllers
    - Health checking and monitoring
    - Connection pooling and reuse
    - Automatic recovery when primary comes back online
    """
    
    def __init__(self, db: Session):
        self.db = db
        self._controllers_cache = {}  # Cache OmadaService instances
        self._last_cache_refresh = None
        self._cache_ttl = timedelta(minutes=5)
        self.health_check_interval = timedelta(minutes=2)
        self.max_failures = 3  # Mark unhealthy after 3 consecutive failures
    
    def _refresh_controllers(self) -> List[OmadaConfig]:
        """Refresh list of active controllers from database"""
        now = datetime.now()
        
        # Refresh cache if expired or empty
        if (not self._last_cache_refresh or 
            now - self._last_cache_refresh > self._cache_ttl):
            
            # Get all active controllers ordered by priority
            controllers = (
                self.db.query(OmadaConfig)
                .filter(OmadaConfig.is_active == True)
                .order_by(OmadaConfig.priority.asc())
                .all()
            )
            
            self._last_cache_refresh = now
            logger.info(f"Refreshed controller list: {len(controllers)} active controllers")
            return controllers
        
        return None
    
    def _get_controller_instance(self, config: OmadaConfig) -> OmadaService:
        """Get or create OmadaService instance for a controller"""
        cache_key = f"{config.id}_{config.controller_url}"
        
        if cache_key not in self._controllers_cache:
            self._controllers_cache[cache_key] = OmadaService(
                controller_url=config.controller_url,
                username=config.username,
                encrypted_password=config.password_encrypted,
                controller_id=config.controller_id,
                site_id=config.site_id
            )
            logger.info(f"Created new OmadaService instance for controller: {config.config_name}")
        
        return self._controllers_cache[cache_key]
    
    def _check_controller_health(self, config: OmadaConfig) -> bool:
        """Check if a controller is healthy"""
        try:
            now = datetime.now()
            
            # Skip health check if done recently
            if config.last_health_check:
                time_since_check = now - config.last_health_check.replace(tzinfo=None)
                if time_since_check < self.health_check_interval:
                    logger.debug(f"Skipping health check for {config.config_name} (checked {time_since_check.seconds}s ago)")
                    return config.is_healthy
            
            # Perform health check
            logger.info(f"Checking health of controller: {config.config_name}")
            omada = self._get_controller_instance(config)
            result = omada.test_connection()
            
            # Update health status
            if result.get('success'):
                config.is_healthy = True
                config.failure_count = 0
                logger.info(f"✓ Controller {config.config_name} is healthy")
            else:
                config.failure_count += 1
                if config.failure_count >= self.max_failures:
                    config.is_healthy = False
                    logger.warning(f"✗ Controller {config.config_name} marked unhealthy after {config.failure_count} failures")
                else:
                    logger.warning(f"⚠ Controller {config.config_name} failed ({config.failure_count}/{self.max_failures})")
            
            config.last_health_check = now
            self.db.commit()
            
            return config.is_healthy
            
        except Exception as e:
            logger.error(f"Health check failed for {config.config_name}: {str(e)}")
            config.failure_count += 1
            if config.failure_count >= self.max_failures:
                config.is_healthy = False
            config.last_health_check = datetime.now()
            self.db.commit()
            return False
    
    def get_active_controller(self, force_refresh: bool = False) -> tuple[OmadaConfig, OmadaService]:
        """
        Get the active healthy controller with automatic failover.
        
        Returns:
            tuple: (OmadaConfig, OmadaService) of the active healthy controller
        
        Raises:
            Exception: If no healthy controller is available
        """
        if force_refresh:
            self._last_cache_refresh = None
        
        # Get all active controllers ordered by priority
        controllers = (
            self.db.query(OmadaConfig)
            .filter(OmadaConfig.is_active == True)
            .order_by(OmadaConfig.priority.asc())
            .all()
        )
        
        if not controllers:
            raise Exception("No active Omada controllers configured")
        
        logger.info(f"Checking {len(controllers)} active controllers for healthy instance...")
        
        # Try each controller in priority order
        for config in controllers:
            logger.info(f"Trying controller: {config.config_name} (priority {config.priority}, healthy: {config.is_healthy})")
            
            # Check health
            if self._check_controller_health(config):
                logger.info(f"✓ Using controller: {config.config_name} (priority {config.priority})")
                omada_service = self._get_controller_instance(config)
                return config, omada_service
            else:
                logger.warning(f"Skipping unhealthy controller: {config.config_name}")
        
        # No healthy controller found
        raise Exception("All Omada controllers are unhealthy. Please check controller status.")
    
    def execute_with_failover(self, operation: str, *args, **kwargs) -> Dict:
        """
        Execute an operation with automatic failover.
        
        Args:
            operation: Method name to call on OmadaService
            *args, **kwargs: Arguments to pass to the method
        
        Returns:
            Dict: Result from the operation
        """
        try:
            config, omada_service = self.get_active_controller()
            
            # Get the method from OmadaService
            method = getattr(omada_service, operation)
            
            logger.info(f"Executing {operation} on controller: {config.config_name}")
            result = method(*args, **kwargs)
            
            # If operation failed, try failover
            if not result.get('success'):
                logger.warning(f"Operation failed on {config.config_name}, attempting failover...")
                
                # Mark as failed and try next controller
                config.failure_count += 1
                if config.failure_count >= self.max_failures:
                    config.is_healthy = False
                self.db.commit()
                
                # Try with next controller
                config, omada_service = self.get_active_controller(force_refresh=True)
                method = getattr(omada_service, operation)
                logger.info(f"Retrying {operation} on failover controller: {config.config_name}")
                result = method(*args, **kwargs)
            
            return result
            
        except Exception as e:
            logger.error(f"Operation {operation} failed on all controllers: {str(e)}")
            return {
                "success": False,
                "message": f"All controllers failed: {str(e)}"
            }
    
    def authorize_client(
        self,
        mac_address: str,
        duration: int = 3600,
        upload_limit: Optional[int] = None,
        download_limit: Optional[int] = None,
        ap_mac: Optional[str] = None,
        ssid: Optional[str] = None,
        gateway_mac: Optional[str] = None,
        vid: Optional[str] = None,
        radio_id: Optional[str] = None
    ) -> Dict:
        """Authorize client with automatic failover"""
        return self.execute_with_failover(
            'authorize_client',
            mac_address=mac_address,
            duration=duration,
            upload_limit=upload_limit,
            download_limit=download_limit,
            ap_mac=ap_mac,
            ssid=ssid,
            gateway_mac=gateway_mac,
            vid=vid,
            radio_id=radio_id
        )
    
    def unauthorize_client(self, mac_address: str) -> Dict:
        """Unauthorize client with automatic failover"""
        return self.execute_with_failover('unauthorize_client', mac_address)
    
    def get_client_status(self, mac_address: str) -> Dict:
        """Get client status with automatic failover"""
        return self.execute_with_failover('get_client_status', mac_address)
    
    def get_online_clients(self, page: int = 1, page_size: int = 100) -> Dict:
        """Get online clients with automatic failover"""
        return self.execute_with_failover('get_online_clients', page, page_size)
    
    def get_controller_status(self) -> Dict:
        """Get status of all controllers"""
        controllers = (
            self.db.query(OmadaConfig)
            .filter(OmadaConfig.is_active == True)
            .order_by(OmadaConfig.priority.asc())
            .all()
        )
        
        status_list = []
        for config in controllers:
            status_list.append({
                'id': config.id,
                'name': config.config_name,
                'priority': config.priority,
                'is_healthy': config.is_healthy,
                'failure_count': config.failure_count,
                'last_health_check': config.last_health_check.isoformat() if config.last_health_check else None,
                'controller_url': config.controller_url
            })
        
        return {
            'success': True,
            'controllers': status_list,
            'total': len(status_list)
        }
