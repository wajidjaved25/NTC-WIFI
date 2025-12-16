"""
RADIUS CoA (Change of Authorization) Service
Handles disconnect requests on multiple ports for multi-site deployments
"""

import asyncio
import socket
import struct
from typing import Dict, Optional, List
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import text

from ..database import SessionLocal


class CoAService:
    """
    Service to send RADIUS Disconnect-Request (DM) packets
    Supports multiple sites with different CoA ports
    """
    
    def __init__(self):
        self.sites_config: Dict[int, Dict] = {}  # site_id -> config
        self.running = False
    
    def load_sites_config(self, db: Session):
        """Load all active sites and their CoA configuration"""
        result = db.execute(text("""
            SELECT 
                id, site_name, site_code,
                radius_nas_ip, radius_secret, radius_coa_port
            FROM sites
            WHERE is_active = TRUE
        """))
        
        self.sites_config = {}
        for row in result:
            site_id, site_name, site_code, nas_ip, secret, coa_port = row
            self.sites_config[site_id] = {
                'site_name': site_name,
                'site_code': site_code,
                'nas_ip': nas_ip,
                'secret': secret,
                'coa_port': coa_port
            }
        
        print(f"✅ Loaded {len(self.sites_config)} sites for CoA service")
        return self.sites_config
    
    def _create_disconnect_packet(
        self,
        username: str,
        nas_ip: str,
        secret: str,
        session_id: Optional[str] = None,
        framed_ip: Optional[str] = None
    ) -> bytes:
        """
        Create RADIUS Disconnect-Request packet (RFC 3576)
        Packet Code: 40 (Disconnect-Request)
        """
        
        # RADIUS Header
        code = 40  # Disconnect-Request
        identifier = 1
        authenticator = b'\x00' * 16  # Will be calculated
        
        # Attributes
        attributes = b''
        
        # User-Name (Attribute 1)
        if username:
            username_bytes = username.encode('utf-8')
            attr_length = 2 + len(username_bytes)
            attributes += struct.pack('BB', 1, attr_length) + username_bytes
        
        # Acct-Session-Id (Attribute 44)
        if session_id:
            session_bytes = session_id.encode('utf-8')
            attr_length = 2 + len(session_bytes)
            attributes += struct.pack('BB', 44, attr_length) + session_bytes
        
        # Framed-IP-Address (Attribute 8)
        if framed_ip:
            ip_parts = [int(p) for p in framed_ip.split('.')]
            attributes += struct.pack('BB4B', 8, 6, *ip_parts)
        
        # NAS-IP-Address (Attribute 4)
        nas_parts = [int(p) for p in nas_ip.split('.')]
        attributes += struct.pack('BB4B', 4, 6, *nas_parts)
        
        # Calculate length
        length = 20 + len(attributes)
        
        # Build packet
        packet = struct.pack('!BBH', code, identifier, length)
        packet += authenticator
        packet += attributes
        
        return packet
    
    async def disconnect_user(
        self,
        username: str,
        site_id: Optional[int] = None,
        session_id: Optional[str] = None,
        framed_ip: Optional[str] = None
    ) -> Dict[str, any]:
        """
        Send Disconnect-Request to Omada controller for a specific site
        
        Args:
            username: User to disconnect
            site_id: Which site to disconnect from (if None, tries all sites)
            session_id: Optional session ID for more specific disconnect
            framed_ip: Optional IP address for more specific disconnect
        
        Returns:
            Dict with success status and message
        """
        
        # Reload config in case sites changed
        db = SessionLocal()
        self.load_sites_config(db)
        db.close()
        
        if site_id:
            # Disconnect from specific site
            if site_id not in self.sites_config:
                return {
                    'success': False,
                    'message': f'Site {site_id} not found or inactive'
                }
            
            config = self.sites_config[site_id]
            result = await self._send_disconnect(
                username, config['nas_ip'], config['secret'],
                config['coa_port'], session_id, framed_ip
            )
            
            return {
                'success': result['success'],
                'message': f"Disconnect request sent to {config['site_name']}",
                'site': config['site_name'],
                'details': result
            }
        
        else:
            # Disconnect from all sites
            results = []
            for sid, config in self.sites_config.items():
                result = await self._send_disconnect(
                    username, config['nas_ip'], config['secret'],
                    config['coa_port'], session_id, framed_ip
                )
                results.append({
                    'site_id': sid,
                    'site_name': config['site_name'],
                    'success': result['success'],
                    'message': result['message']
                })
            
            success_count = sum(1 for r in results if r['success'])
            
            return {
                'success': success_count > 0,
                'message': f'Disconnect sent to {success_count}/{len(results)} sites',
                'results': results
            }
    
    async def _send_disconnect(
        self,
        username: str,
        nas_ip: str,
        secret: str,
        coa_port: int,
        session_id: Optional[str] = None,
        framed_ip: Optional[str] = None
    ) -> Dict[str, any]:
        """Internal method to send disconnect packet to specific NAS"""
        
        try:
            # Create disconnect packet
            packet = self._create_disconnect_packet(
                username, nas_ip, secret, session_id, framed_ip
            )
            
            # Send UDP packet
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(5.0)
            
            print(f"📡 Sending Disconnect-Request to {nas_ip}:{coa_port} for user {username}")
            sock.sendto(packet, (nas_ip, coa_port))
            
            # Wait for response (Disconnect-ACK or Disconnect-NAK)
            try:
                response, addr = sock.recvfrom(4096)
                response_code = struct.unpack('!B', response[0:1])[0]
                
                if response_code == 41:  # Disconnect-ACK
                    print(f"✅ Disconnect-ACK received from {nas_ip}")
                    return {
                        'success': True,
                        'message': 'User disconnected successfully'
                    }
                elif response_code == 42:  # Disconnect-NAK
                    print(f"❌ Disconnect-NAK received from {nas_ip}")
                    return {
                        'success': False,
                        'message': 'Disconnect rejected by NAS'
                    }
                else:
                    return {
                        'success': False,
                        'message': f'Unexpected response code: {response_code}'
                    }
            
            except socket.timeout:
                print(f"⏱️  Timeout waiting for response from {nas_ip}")
                return {
                    'success': False,
                    'message': 'Timeout - no response from NAS'
                }
            
            finally:
                sock.close()
        
        except Exception as e:
            print(f"❌ Error sending disconnect to {nas_ip}: {e}")
            return {
                'success': False,
                'message': f'Error: {str(e)}'
            }
    
    async def disconnect_by_session_id(
        self,
        session_id: str,
        db: Session
    ) -> Dict[str, any]:
        """
        Disconnect user by looking up active session in database
        """
        
        # Find active session
        result = db.execute(text("""
            SELECT username, framedipaddress, nasipaddress, site_id
            FROM radacct
            WHERE acctsessionid = :session_id
            AND acctstoptime IS NULL
            LIMIT 1
        """), {"session_id": session_id})
        
        row = result.fetchone()
        if not row:
            return {
                'success': False,
                'message': 'Session not found or already closed'
            }
        
        username, framed_ip, nas_ip, site_id = row
        
        # Send disconnect
        return await self.disconnect_user(
            username=username,
            site_id=site_id,
            session_id=session_id,
            framed_ip=framed_ip
        )
    
    async def disconnect_by_mac(
        self,
        mac_address: str,
        site_id: Optional[int] = None,
        db: Session = None
    ) -> Dict[str, any]:
        """
        Disconnect user by MAC address
        """
        
        # Find active sessions with this MAC
        result = db.execute(text("""
            SELECT username, acctsessionid, framedipaddress, site_id
            FROM radacct
            WHERE callingstationid = :mac
            AND acctstoptime IS NULL
        """), {"mac": mac_address})
        
        rows = result.fetchall()
        if not rows:
            return {
                'success': False,
                'message': 'No active sessions found for this MAC'
            }
        
        # Disconnect all sessions
        results = []
        for username, session_id, framed_ip, sid in rows:
            if site_id and sid != site_id:
                continue
            
            result = await self.disconnect_user(
                username=username,
                site_id=sid,
                session_id=session_id,
                framed_ip=framed_ip
            )
            results.append(result)
        
        success_count = sum(1 for r in results if r['success'])
        
        return {
            'success': success_count > 0,
            'message': f'Disconnected {success_count}/{len(results)} sessions',
            'results': results
        }


# Global CoA service instance
coa_service = CoAService()
