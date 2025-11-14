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
        """Login to Omada controller and get auth token for hotspot portal"""
        try:
            # Note: Hotspot API uses 'name' not 'username'
            payload = {
                "name": self.username,
                "password": self.password
            }
            
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json"
            }
            
            # Debug: Log what we're sending
            logger.info(f"=== Omada Login Attempt ===")
            logger.info(f"Controller URL: {self.controller_url}")
            logger.info(f"Controller ID: {self.controller_id}")
            logger.info(f"Username: {self.username}")
            logger.info(f"Password length: {len(self.password)} chars")
            logger.info(f"Password first 3 chars: {self.password[:3]}...")
            
            # If controller_id is available, use it (required for hotspot portal)
            if self.controller_id:
                login_url = f"{self.controller_url}/{self.controller_id}/api/v2/hotspot/login"
                logger.info(f"Full login URL: {login_url}")
                logger.info(f"Payload: {payload}")
                
                try:
                    response = self.session.post(login_url, json=payload, headers=headers, timeout=10)
                    logger.info(f"Response status: {response.status_code}")
                    logger.info(f"Response headers: {dict(response.headers)}")
                    logger.info(f"Response text: {response.text}")
                    
                    if response.status_code == 200:
                        data = response.json()
                        logger.info(f"Response JSON: {data}")
                        if data.get('errorCode') == 0:
                            self.token = data.get('result', {}).get('token')
                            self.session.headers.update({'Csrf-Token': self.token})
                            logger.info(f"✓ Successfully logged in! Token: {self.token[:20]}...")
                            return True
                        else:
                            logger.error(f"✗ Login failed - errorCode: {data.get('errorCode')}, msg: {data.get('msg')}")
                    else:
                        logger.error(f"✗ HTTP {response.status_code}: {response.text}")
                except Exception as e:
                    logger.error(f"✗ Exception during request: {str(e)}")
                    import traceback
                    logger.error(traceback.format_exc())
            else:
                logger.error("✗ Controller ID is required for hotspot portal login")
            
            return False
        
        except Exception as e:
            logger.error(f"✗ Exception during login: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return False
    
    def test_connection(self) -> Dict:
        """Test connection to Omada controller"""
        try:
            logger.info("=== Starting test_connection ===")
            logger.info(f"About to call login() with controller_id: {self.controller_id}")
            
            login_result = self.login()
            logger.info(f"Login result: {login_result}")
            
            if login_result:
                # Try to get controller info
                base_url = self._get_base_api_url()
                info_url = f"{base_url}/info"
                logger.info(f"Fetching controller info from: {info_url}")
                
                response = self.session.get(info_url, timeout=10)
                logger.info(f"Info endpoint status: {response.status_code}")
                logger.info(f"Info endpoint response text (first 200 chars): {response.text[:200]}")
                
                if response.status_code == 200:
                    try:
                        data = response.json()
                        logger.info(f"Info endpoint JSON: {data}")
                        return {
                            "success": True,
                            "message": "Connection successful",
                            "controller_info": data.get('result', {})
                        }
                    except Exception as json_err:
                        logger.error(f"Failed to parse JSON response: {json_err}")
                        logger.error(f"Response text: {response.text}")
                        return {
                            "success": False,
                            "message": f"Invalid JSON response from controller: {str(json_err)}"
                        }
                else:
                    return {
                        "success": False,
                        "message": f"Failed to get controller info: HTTP {response.status_code}"
                    }
            else:
                logger.error("Login returned False - authentication failed")
                return {
                    "success": False,
                    "message": "Authentication failed"
                }
        
        except Exception as e:
            logger.error(f"Exception in test_connection: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
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
            # Method 1: Try loginStatus endpoint
            info_url = f"{self.controller_url}/api/v2/loginStatus"
            logger.info(f"Attempting to detect controller ID from {info_url}")
            
            response = self.session.get(info_url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"loginStatus response: {data}")
                if data.get('errorCode') == 0:
                    result = data.get('result', {})
                    omadac_id = result.get('omadacId')
                    if omadac_id:
                        logger.info(f"Detected controller ID: {omadac_id}")
                        return {
                            "success": True,
                            "controller_id": omadac_id
                        }
            
            # Method 2: Try accessing the web interface and extract from redirect
            logger.info("Trying to detect from web interface...")
            web_response = self.session.get(self.controller_url, allow_redirects=False, timeout=10)
            if web_response.status_code in [301, 302, 303, 307, 308]:
                location = web_response.headers.get('Location', '')
                logger.info(f"Redirect location: {location}")
                # Extract controller ID from URL like: /abc123def456/login
                import re
                match = re.search(r'/([a-f0-9]{32})/', location)
                if match:
                    controller_id = match.group(1)
                    logger.info(f"Detected controller ID from redirect: {controller_id}")
                    return {
                        "success": True,
                        "controller_id": controller_id
                    }
            
            return {
                "success": False,
                "message": "Could not detect controller ID. Please enter it manually."
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
