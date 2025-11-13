import requests
import urllib3
from typing import Optional, Dict
import logging

from ..utils.helpers import decrypt_password

# Disable SSL warnings for self-signed certificates
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)

class OmadaService:
    def __init__(self, controller_url: str, username: str, encrypted_password: str, site_id: str = "Default"):
        self.controller_url = controller_url.rstrip('/')
        self.username = username
        self.password = decrypt_password(encrypted_password)
        self.site_id = site_id
        self.token = None
        self.session = requests.Session()
        self.session.verify = False  # Disable SSL verification for self-signed certs
    
    def login(self) -> bool:
        """Login to Omada controller and get auth token"""
        try:
            login_url = f"{self.controller_url}/api/v2/login"
            payload = {
                "username": self.username,
                "password": self.password
            }
            
            response = self.session.post(login_url, json=payload, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('errorCode') == 0:
                    self.token = data.get('result', {}).get('token')
                    # Set token in session headers
                    self.session.headers.update({
                        'Csrf-Token': self.token
                    })
                    logger.info(f"Successfully logged in to Omada controller")
                    return True
                else:
                    logger.error(f"Login failed: {data.get('msg')}")
                    return False
            else:
                logger.error(f"Login request failed with status {response.status_code}")
                return False
        
        except Exception as e:
            logger.error(f"Exception during login: {str(e)}")
            return False
    
    def test_connection(self) -> Dict:
        """Test connection to Omada controller"""
        try:
            if self.login():
                # Try to get controller info
                info_url = f"{self.controller_url}/api/v2/info"
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
            
            auth_url = f"{self.controller_url}/api/v2/hotspot/extPortal/auth"
            
            payload = {
                "site": self.site_id,
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
            
            unauth_url = f"{self.controller_url}/api/v2/hotspot/extPortal/unauth"
            
            payload = {
                "site": self.site_id,
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
            
            status_url = f"{self.controller_url}/api/v2/sites/{self.site_id}/clients/{mac_address}"
            
            response = self.session.get(status_url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('errorCode') == 0:
                    return {
                        "success": True,
                        "data": data.get('result')
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
    
    def get_online_clients(self) -> Dict:
        """Get list of currently online clients"""
        try:
            if not self.token:
                if not self.login():
                    return {"success": False, "message": "Authentication failed"}
            
            clients_url = f"{self.controller_url}/api/v2/sites/{self.site_id}/clients"
            
            response = self.session.get(clients_url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('errorCode') == 0:
                    return {
                        "success": True,
                        "clients": data.get('result', {}).get('data', []),
                        "total": data.get('result', {}).get('total', 0)
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
            
            sites_url = f"{self.controller_url}/api/v2/sites"
            
            response = self.session.get(sites_url, timeout=10)
            
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
    
    def logout(self):
        """Logout from Omada controller"""
        try:
            if self.token:
                logout_url = f"{self.controller_url}/api/v2/logout"
                self.session.post(logout_url, timeout=5)
                self.token = None
                logger.info("Logged out from Omada controller")
        except:
            pass
    
    def __del__(self):
        """Cleanup on object destruction"""
        self.logout()
