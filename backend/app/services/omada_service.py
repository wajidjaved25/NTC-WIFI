import requests
import urllib3
from typing import Optional, Dict
import logging

from ..utils.helpers import decrypt_password

# Disable SSL warnings for self-signed certificates
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)

class OmadaService:
    def __init__(self, controller_url: str, username: str, encrypted_password: str, controller_id: str = None, site_id: str = "Default"):
        self.controller_url = controller_url.rstrip('/')
        self.username = username
        self.password = decrypt_password(encrypted_password)
        self.controller_id = controller_id
        self.site_id = site_id
        self.token = None
        self.session = requests.Session()
        self.session.verify = False  # Disable SSL verification for self-signed certs
    
    def _get_base_api_url(self) -> str:
        """Get base API URL with controller ID if available"""
        if self.controller_id:
            return f"{self.controller_url}/{self.controller_id}/api/v2"
        return f"{self.controller_url}/api/v2"
    
    def login(self) -> bool:
        """Login to Omada controller and get auth token"""
        try:
            # Try both login endpoints
            login_urls = [
                f"{self.controller_url}/{self.controller_id}/api/v2/login" if self.controller_id else None,
                f"{self.controller_url}/api/v2/login"
            ]
            
            login_urls = [url for url in login_urls if url]
            
            payload = {
                "username": self.username,
                "password": self.password
            }
            
            for login_url in login_urls:
                try:
                    response = self.session.post(login_url, json=payload, timeout=10)
                    
                    if response.status_code == 200:
                        data = response.json()
                        if data.get('errorCode') == 0:
                            self.token = data.get('result', {}).get('token')
                            # Set token in session headers
                            self.session.headers.update({
                                'Csrf-Token': self.token
                            })
                            logger.info(f"Successfully logged in to Omada controller at {login_url}")
                            return True
                        else:
                            logger.error(f"Login failed at {login_url}: {data.get('msg')}")
                except Exception as e:
                    logger.error(f"Failed to connect to {login_url}: {str(e)}")
                    continue
            
            logger.error("Failed to login with all attempted URLs")
            return False
        
        except Exception as e:
            logger.error(f"Exception during login: {str(e)}")
            return False
    
    def test_connection(self) -> Dict:
        """Test connection to Omada controller"""
        try:
            if self.login():
                # Try to get controller info
                base_url = self._get_base_api_url()
                info_url = f"{base_url}/info"
                response = self.session.get(info_url, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    return {
                        "success": True,
                        "message": "Connection successful",
                        "controller_info": data.get('result', {})
                    }
                else:
                    return {
                        "success": False,
                        "message": f"Failed to get controller info: {response.status_code}"
                    }
            else:
                return {
                    "success": False,
                    "message": "Authentication failed"
                }
        
        except Exception as e:
            return {
                "success": False,
                "message": f"Connection error: {str(e)}"
            }
    
    def authorize_client(
        self,
        mac_address: str,
        duration: int = 3600,
        upload_limit: Optional[int] = None,
        download_limit: Optional[int] = None
    ) -> Dict:
        """Authorize a client to access WiFi"""
        try:
            if not self.token:
                if not self.login():
                    return {"success": False, "message": "Authentication failed"}
            
            base_url = self._get_base_api_url()
            auth_url = f"{base_url}/hotspot/sites/{self.site_id}/clients/{mac_address}/authorize"
            
            payload = {
                "mac": mac_address,
                "duration": duration,  # seconds
                "authType": 1  # External portal auth
            }
            
            # Add bandwidth limits if specified
            if upload_limit:
                payload['uploadLimit'] = upload_limit
            if download_limit:
                payload['downloadLimit'] = download_limit
            
            response = self.session.post(auth_url, json=payload, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('errorCode') == 0:
                    return {
                        "success": True,
                        "message": "Client authorized successfully",
                        "data": data.get('result')
                    }
                else:
                    return {
                        "success": False,
                        "message": f"Authorization failed: {data.get('msg')}"
                    }
            else:
                return {
                    "success": False,
                    "message": f"Request failed with status {response.status_code}"
                }
        
        except Exception as e:
            logger.error(f"Exception during client authorization: {str(e)}")
            return {"success": False, "message": str(e)}
    
    def unauthorize_client(self, mac_address: str) -> Dict:
        """Disconnect/unauthorize a client"""
        try:
            if not self.token:
                if not self.login():
                    return {"success": False, "message": "Authentication failed"}
            
            base_url = self._get_base_api_url()
            unauth_url = f"{base_url}/hotspot/sites/{self.site_id}/clients/{mac_address}/unauthorize"
            
            payload = {
                "mac": mac_address
            }
            
            response = self.session.post(unauth_url, json=payload, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('errorCode') == 0:
                    return {
                        "success": True,
                        "message": "Client unauthorized successfully"
                    }
                else:
                    return {
                        "success": False,
                        "message": f"Unauthorization failed: {data.get('msg')}"
                    }
            else:
                return {
                    "success": False,
                    "message": f"Request failed with status {response.status_code}"
                }
        
        except Exception as e:
            logger.error(f"Exception during client unauthorization: {str(e)}")
            return {"success": False, "message": str(e)}
    
    def get_client_status(self, mac_address: str) -> Dict:
        """Get client connection status"""
        try:
            if not self.token:
                if not self.login():
                    return {"success": False, "message": "Authentication failed"}
            
            base_url = self._get_base_api_url()
            status_url = f"{base_url}/sites/{self.site_id}/clients"
            
            # Query with MAC filter
            params = {
                "currentPage": 1,
                "currentPageSize": 100,
                "filters.mac": mac_address
            }
            
            response = self.session.get(status_url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('errorCode') == 0:
                    clients = data.get('result', {}).get('data', [])
                    if clients:
                        return {
                            "success": True,
                            "data": clients[0]
                        }
                    else:
                        return {
                            "success": False,
                            "message": "Client not found"
                        }
                else:
                    return {
                        "success": False,
                        "message": f"Failed to get status: {data.get('msg')}"
                    }
            else:
                return {
                    "success": False,
                    "message": f"Request failed with status {response.status_code}"
                }
        
        except Exception as e:
            logger.error(f"Exception getting client status: {str(e)}")
            return {"success": False, "message": str(e)}
    
    def get_online_clients(self, page: int = 1, page_size: int = 100) -> Dict:
        """Get list of currently online clients"""
        try:
            if not self.token:
                if not self.login():
                    return {"success": False, "message": "Authentication failed"}
            
            base_url = self._get_base_api_url()
            clients_url = f"{base_url}/sites/{self.site_id}/clients"
            
            params = {
                "currentPage": page,
                "currentPageSize": page_size
            }
            
            response = self.session.get(clients_url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('errorCode') == 0:
                    result = data.get('result', {})
                    return {
                        "success": True,
                        "clients": result.get('data', []),
                        "total": result.get('totalRows', 0),
                        "page": page,
                        "page_size": page_size
                    }
                else:
                    return {
                        "success": False,
                        "message": f"Failed to get clients: {data.get('msg')}"
                    }
            else:
                return {
                    "success": False,
                    "message": f"Request failed with status {response.status_code}"
                }
        
        except Exception as e:
            logger.error(f"Exception getting online clients: {str(e)}")
            return {"success": False, "message": str(e)}
    
    def get_sites(self) -> Dict:
        """Get list of sites from controller"""
        try:
            if not self.token:
                if not self.login():
                    return {"success": False, "message": "Authentication failed"}
            
            base_url = self._get_base_api_url()
            sites_url = f"{base_url}/sites"
            
            params = {
                "currentPage": 1,
                "currentPageSize": 100
            }
            
            response = self.session.get(sites_url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('errorCode') == 0:
                    return {
                        "success": True,
                        "sites": data.get('result', {}).get('data', [])
                    }
                else:
                    return {
                        "success": False,
                        "message": f"Failed to get sites: {data.get('msg')}"
                    }
            else:
                return {
                    "success": False,
                    "message": f"Request failed with status {response.status_code}"
                }
        
        except Exception as e:
            logger.error(f"Exception getting sites: {str(e)}")
            return {"success": False, "message": str(e)}
    
    def get_controller_id(self) -> Dict:
        """Auto-detect controller ID from login response or API"""
        try:
            # Try to get controller info without controller_id
            info_url = f"{self.controller_url}/api/v2/loginStatus"
            response = self.session.get(info_url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('errorCode') == 0:
                    result = data.get('result', {})
                    omadac_id = result.get('omadacId')
                    if omadac_id:
                        return {
                            "success": True,
                            "controller_id": omadac_id
                        }
            
            return {
                "success": False,
                "message": "Could not detect controller ID"
            }
        
        except Exception as e:
            logger.error(f"Exception detecting controller ID: {str(e)}")
            return {"success": False, "message": str(e)}
    
    def logout(self):
        """Logout from Omada controller"""
        try:
            if self.token:
                base_url = self._get_base_api_url()
                logout_url = f"{base_url}/logout"
                self.session.post(logout_url, timeout=5)
                self.token = None
                logger.info("Logged out from Omada controller")
        except:
            pass
    
    def __del__(self):
        """Cleanup on object destruction"""
        self.logout()
