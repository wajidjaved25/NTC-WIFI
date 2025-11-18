"""
RADIUS Authentication Client
Performs programmatic RADIUS authentication using pyrad library
No external dependencies on radclient command-line tool
"""

import socket
from typing import Dict
from pyrad.client import Client
from pyrad.dictionary import Dictionary
from pyrad import packet


class RadiusAuthClient:
    """Client for performing RADIUS authentication programmatically using pyrad"""
    
    def __init__(self, radius_server: str = "127.0.0.1", radius_secret: str = "testing123", radius_port: int = 1812):
        self.radius_server = radius_server
        self.radius_secret = radius_secret
        self.radius_port = radius_port
        
        # Create RADIUS dictionary inline (minimal required attributes)
        self.dict_content = """
ATTRIBUTE   User-Name               1   string
ATTRIBUTE   User-Password           2   string
ATTRIBUTE   NAS-IP-Address          4   ipaddr
ATTRIBUTE   NAS-Port                5   integer
ATTRIBUTE   Service-Type            6   integer
ATTRIBUTE   Framed-Protocol         7   integer
ATTRIBUTE   Framed-IP-Address       8   ipaddr
ATTRIBUTE   Session-Timeout         27  integer
ATTRIBUTE   Calling-Station-Id      31  string
ATTRIBUTE   NAS-Identifier          32  string
ATTRIBUTE   Acct-Status-Type        40  integer
ATTRIBUTE   Acct-Session-Id         44  string
ATTRIBUTE   Reply-Message           18  string
"""
    
    def authenticate(
        self,
        username: str,
        password: str,
        nas_ip: str = "192.168.3.254"
    ) -> Dict:
        """
        Authenticate user via RADIUS using pyrad library
        
        Args:
            username: User's mobile number
            password: User's CNIC or passport
            nas_ip: NAS IP address (Omada controller)
        
        Returns:
            Dict with success status and details
        """
        try:
            print(f"\n=== RADIUS AUTHENTICATION ===")
            print(f"Username: {username}")
            print(f"Server: {self.radius_server}:{self.radius_port}")
            print(f"NAS IP: {nas_ip}")
            
            # Create dictionary from string
            import io
            dict_io = io.StringIO(self.dict_content)
            
            # Create RADIUS client
            srv = Client(
                server=self.radius_server,
                secret=self.radius_secret.encode('utf-8'),
                dict=Dictionary(dict_io)
            )
            srv.timeout = 10
            srv.retries = 3
            
            # Create authentication request
            req = srv.CreateAuthPacket(code=packet.AccessRequest)
            req["User-Name"] = username
            req["User-Password"] = req.PwCrypt(password)
            req["NAS-IP-Address"] = nas_ip
            req["NAS-Port"] = 0
            
            print(f"Sending RADIUS request...")
            
            # Send request and get response
            reply = srv.SendPacket(req)
            
            # Check response code
            if reply.code == packet.AccessAccept:
                # Extract session timeout if present
                session_timeout = 3600  # Default
                if "Session-Timeout" in reply:
                    session_timeout = reply["Session-Timeout"][0]
                
                print(f"✓ RADIUS Authentication SUCCESS")
                print(f"Session Timeout: {session_timeout} seconds\n")
                
                return {
                    "success": True,
                    "message": "RADIUS authentication successful",
                    "session_timeout": session_timeout,
                    "code": "Access-Accept"
                }
            
            elif reply.code == packet.AccessReject:
                # Get reject message if present
                reject_msg = "Invalid credentials"
                if "Reply-Message" in reply:
                    reject_msg = reply["Reply-Message"][0]
                
                print(f"✗ RADIUS Authentication REJECTED: {reject_msg}\n")
                return {
                    "success": False,
                    "message": f"RADIUS authentication rejected - {reject_msg}",
                    "code": "Access-Reject"
                }
            
            elif reply.code == packet.AccessChallenge:
                print(f"✗ RADIUS Authentication requires CHALLENGE\n")
                return {
                    "success": False,
                    "message": "RADIUS authentication requires challenge (not supported)",
                    "code": "Access-Challenge"
                }
            
            else:
                print(f"✗ RADIUS Authentication UNKNOWN response: {reply.code}\n")
                return {
                    "success": False,
                    "message": f"Unknown RADIUS response code: {reply.code}",
                    "code": "Unknown"
                }
        
        except socket.timeout:
            print(f"✗ RADIUS request timed out\n")
            return {
                "success": False,
                "message": "RADIUS authentication timeout - server not responding"
            }
        
        except socket.error as e:
            print(f"✗ RADIUS socket error: {str(e)}\n")
            return {
                "success": False,
                "message": f"RADIUS connection error: {str(e)}"
            }
        
        except Exception as e:
            print(f"✗ RADIUS authentication error: {str(e)}\n")
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "message": f"RADIUS authentication error: {str(e)}"
            }
    
    def test_connection(self) -> Dict:
        """Test RADIUS server connectivity"""
        try:
            # Send a test authentication request
            # Even if it fails auth, we'll know if server is reachable
            result = self.authenticate("test_user", "test_pass")
            
            # If we got any response (even reject), server is reachable
            if result.get("code") in ["Access-Accept", "Access-Reject", "Access-Challenge"]:
                return {
                    "success": True,
                    "message": "RADIUS server is reachable"
                }
            
            return {
                "success": False,
                "message": result.get("message", "Cannot reach RADIUS server")
            }
        
        except Exception as e:
            return {
                "success": False,
                "message": f"RADIUS connection test failed: {str(e)}"
            }
