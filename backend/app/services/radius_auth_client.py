"""
RADIUS Authentication Client
Performs programmatic RADIUS authentication for auto-login
"""

import subprocess
import re
from typing import Dict, Optional


class RadiusAuthClient:
    """Client for performing RADIUS authentication programmatically"""
    
    def __init__(self, radius_server: str = "127.0.0.1", radius_secret: str = "MySecretRadius2024!"):
        self.radius_server = radius_server
        self.radius_secret = radius_secret
    
    def authenticate(
        self,
        username: str,
        password: str,
        nas_ip: str = "192.168.3.254:8043"  # Omada controller IP
    ) -> Dict:
        """
        Authenticate user via RADIUS using radclient
        
        Args:
            username: User's mobile number
            password: User's CNIC or passport
            nas_ip: NAS IP address (Omada controller)
        
        Returns:
            Dict with success status and details
        """
        try:
            # Build RADIUS Access-Request packet
            radius_request = f"""User-Name = "{username}"
User-Password = "{password}"
NAS-IP-Address = {nas_ip}
NAS-Port = 0
Message-Authenticator = 0x00
"""
            
            # Execute radclient command
            cmd = [
                'radclient',
                '-x',  # Debug output
                f'{self.radius_server}:1812',  # RADIUS server:port
                'auth',  # Request type
                self.radius_secret  # Shared secret
            ]
            
            print(f"\n=== RADIUS AUTHENTICATION ===")
            print(f"Username: {username}")
            print(f"Server: {self.radius_server}")
            print(f"NAS IP: {nas_ip}")
            
            # Run radclient
            result = subprocess.run(
                cmd,
                input=radius_request,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            print(f"RADIUS Response: {result.stdout}")
            
            # Parse response
            if "Access-Accept" in result.stdout:
                # Extract session timeout if present
                timeout_match = re.search(r'Session-Timeout = (\d+)', result.stdout)
                session_timeout = int(timeout_match.group(1)) if timeout_match else 3600
                
                print(f"✓ RADIUS Authentication SUCCESS")
                print(f"Session Timeout: {session_timeout} seconds\n")
                
                return {
                    "success": True,
                    "message": "RADIUS authentication successful",
                    "session_timeout": session_timeout,
                    "response": result.stdout
                }
            
            elif "Access-Reject" in result.stdout:
                print(f"✗ RADIUS Authentication REJECTED\n")
                return {
                    "success": False,
                    "message": "RADIUS authentication rejected - invalid credentials",
                    "response": result.stdout
                }
            
            else:
                print(f"✗ RADIUS Authentication FAILED\n")
                return {
                    "success": False,
                    "message": "No response from RADIUS server",
                    "response": result.stdout
                }
        
        except subprocess.TimeoutExpired:
            print(f"✗ RADIUS request timed out\n")
            return {
                "success": False,
                "message": "RADIUS authentication timeout"
            }
        
        except Exception as e:
            print(f"✗ RADIUS authentication error: {str(e)}\n")
            return {
                "success": False,
                "message": f"RADIUS authentication error: {str(e)}"
            }
    
    def test_connection(self) -> Dict:
        """Test RADIUS server connectivity"""
        try:
            # Send a test authentication request
            result = self.authenticate("test_user", "test_pass")
            
            # Even if authentication fails, if we get a response, server is reachable
            if result.get("response"):
                return {
                    "success": True,
                    "message": "RADIUS server is reachable"
                }
            
            return {
                "success": False,
                "message": "Cannot reach RADIUS server"
            }
        
        except Exception as e:
            return {
                "success": False,
                "message": f"RADIUS connection test failed: {str(e)}"
            }
