import asyncio
import socket
import re
import logging
from datetime import datetime
from typing import Optional, Dict
import threading
from sqlalchemy.orm import Session

from ..database import SessionLocal
from ..models.ipdr import FirewallLog
from ..models.session import Session as WiFiSession
from ..models.user import User

logger = logging.getLogger(__name__)


class FortiGateSyslogReceiver:
    """
    Real-time syslog receiver for FortiGate firewall logs
    Receives logs via UDP/TCP and stores them in the database
    """
    
    def __init__(self, host: str = "0.0.0.0", port: int = 514, protocol: str = "udp"):
        self.host = host
        self.port = port
        self.protocol = protocol.lower()
        self.running = False
        self.socket = None
        self.thread = None
        
    def start(self):
        """Start the syslog receiver in a background thread"""
        if self.running:
            logger.warning("Syslog receiver already running")
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._run_receiver, daemon=True)
        self.thread.start()
        logger.info(f"FortiGate syslog receiver started on {self.host}:{self.port} ({self.protocol.upper()})")
    
    def stop(self):
        """Stop the syslog receiver"""
        self.running = False
        if self.socket:
            self.socket.close()
        logger.info("FortiGate syslog receiver stopped")
    
    def _run_receiver(self):
        """Main receiver loop"""
        try:
            if self.protocol == "udp":
                self._run_udp_receiver()
            elif self.protocol == "tcp":
                self._run_tcp_receiver()
            else:
                logger.error(f"Unsupported protocol: {self.protocol}")
        except Exception as e:
            logger.error(f"Syslog receiver error: {e}")
            self.running = False
    
    def _run_udp_receiver(self):
        """UDP receiver"""
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind((self.host, self.port))
        
        logger.info(f"Listening for UDP syslog on {self.host}:{self.port}")
        
        while self.running:
            try:
                data, addr = self.socket.recvfrom(65535)  # Max UDP packet size
                message = data.decode('utf-8', errors='ignore')
                self._process_message(message, addr)
            except Exception as e:
                if self.running:
                    logger.error(f"Error processing UDP message: {e}")
    
    def _run_tcp_receiver(self):
        """TCP receiver"""
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind((self.host, self.port))
        self.socket.listen(5)
        
        logger.info(f"Listening for TCP syslog on {self.host}:{self.port}")
        
        while self.running:
            try:
                client_socket, addr = self.socket.accept()
                threading.Thread(
                    target=self._handle_tcp_client,
                    args=(client_socket, addr),
                    daemon=True
                ).start()
            except Exception as e:
                if self.running:
                    logger.error(f"Error accepting TCP connection: {e}")
    
    def _handle_tcp_client(self, client_socket, addr):
        """Handle TCP client connection"""
        try:
            buffer = ""
            while self.running:
                data = client_socket.recv(4096)
                if not data:
                    break
                
                buffer += data.decode('utf-8', errors='ignore')
                
                # Process complete messages (separated by newlines)
                while '\n' in buffer:
                    message, buffer = buffer.split('\n', 1)
                    self._process_message(message, addr)
        except Exception as e:
            logger.error(f"Error handling TCP client: {e}")
        finally:
            client_socket.close()
    
    def _process_message(self, message: str, addr: tuple):
        """Process a single syslog message"""
        try:
            # Parse FortiGate syslog format
            log_data = self._parse_fortigate_log(message)
            
            if log_data and log_data.get('type') == 'traffic':
                # Store in database
                self._store_log(log_data)
        except Exception as e:
            logger.error(f"Error processing message from {addr}: {e}")
    
    def _parse_fortigate_log(self, message: str) -> Optional[Dict]:
        """
        Parse FortiGate syslog message format
        
        Example format:
        <189>date=2024-01-15 time=10:30:45 devname="FG1801G" devid="FG1801G..." logid="0000000013" 
        type="traffic" subtype="forward" level="notice" srcip=192.168.1.100 srcport=54321 
        srcintf="port1" dstip=8.8.8.8 dstport=443 proto=6 action="accept" sentbyte=1500 rcvdbyte=50000
        """
        
        # Extract key-value pairs using regex
        pattern = r'(\w+)=(?:"([^"]*)"|([^\s]+))'
        matches = re.findall(pattern, message)
        
        log_dict = {}
        for key, quoted_value, unquoted_value in matches:
            value = quoted_value if quoted_value else unquoted_value
            log_dict[key] = value
        
        # Only process traffic logs
        if log_dict.get('type') != 'traffic':
            return None
        
        try:
            # Parse date and time
            date_str = log_dict.get('date', '')
            time_str = log_dict.get('time', '')
            
            if not date_str or not time_str:
                return None
            
            log_timestamp = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M:%S")
            
            # Build structured log data
            return {
                'type': log_dict.get('type'),
                'log_date': log_timestamp.date(),
                'log_time': log_timestamp.time(),
                'log_timestamp': log_timestamp,
                'source_ip': log_dict.get('srcip'),
                'source_port': int(log_dict.get('srcport', 0)),
                'source_mac': log_dict.get('srcmac'),
                'source_interface': log_dict.get('srcintf'),
                'translated_ip': log_dict.get('transip'),
                'translated_port': int(log_dict.get('transport', 0)) if log_dict.get('transport') else None,
                'destination_ip': log_dict.get('dstip'),
                'destination_port': int(log_dict.get('dstport', 0)),
                'destination_country': log_dict.get('dstcountry'),
                'protocol': int(log_dict.get('proto', 0)),
                'protocol_name': self._get_protocol_name(log_dict.get('proto', '0')),
                'service': log_dict.get('service'),
                'app_name': log_dict.get('app'),
                'app_category': log_dict.get('appcat'),
                'sent_bytes': int(log_dict.get('sentbyte', 0)),
                'received_bytes': int(log_dict.get('rcvdbyte', 0)),
                'sent_packets': int(log_dict.get('sentpkt', 0)),
                'received_packets': int(log_dict.get('rcvdpkt', 0)),
                'duration': int(log_dict.get('duration', 0)),
                'action': log_dict.get('action'),
                'policy_id': int(log_dict.get('policyid', 0)) if log_dict.get('policyid') else None,
                'domain_name': log_dict.get('hostname') or log_dict.get('dstname'),
                'url': log_dict.get('url'),
                'device_type': log_dict.get('devtype'),
                'os_name': log_dict.get('osname'),
                'raw_log_data': log_dict
            }
        except Exception as e:
            logger.error(f"Error parsing FortiGate log: {e}")
            return None
    
    def _get_protocol_name(self, proto: str) -> str:
        """Convert protocol number to name"""
        proto_map = {
            '6': 'TCP',
            '17': 'UDP',
            '1': 'ICMP',
            '47': 'GRE',
            '50': 'ESP',
            '51': 'AH'
        }
        return proto_map.get(proto, 'OTHER')
    
    def _store_log(self, log_data: Dict):
        """Store log in database with session correlation"""
        db = SessionLocal()
        try:
            # Try to find matching session
            session = self._find_matching_session(
                db,
                log_data['source_ip'],
                log_data.get('source_mac'),
                log_data['log_timestamp']
            )
            
            if session:
                log_data['session_id'] = session.id
                log_data['user_id'] = session.user_id
            
            # Create firewall log entry
            firewall_log = FirewallLog(**log_data)
            db.add(firewall_log)
            db.commit()
            
            logger.debug(f"Stored log: {log_data['source_ip']} -> {log_data['destination_ip']}")
            
        except Exception as e:
            logger.error(f"Error storing log: {e}")
            db.rollback()
        finally:
            db.close()
    
    def _find_matching_session(
        self,
        db: Session,
        ip_address: str,
        mac_address: Optional[str],
        timestamp: datetime
    ) -> Optional[WiFiSession]:
        """Find matching WiFi session for firewall log"""
        from datetime import timedelta
        from sqlalchemy import and_, or_
        
        # Search within ±5 minute window
        time_window = timedelta(minutes=5)
        
        query = db.query(WiFiSession).filter(
            and_(
                or_(
                    WiFiSession.ip_address == ip_address,
                    WiFiSession.mac_address == mac_address
                ) if mac_address else WiFiSession.ip_address == ip_address,
                WiFiSession.start_time <= timestamp + time_window,
                or_(
                    WiFiSession.end_time >= timestamp - time_window,
                    WiFiSession.end_time == None
                )
            )
        ).first()
        
        return query


# Global syslog receiver instance
syslog_receiver = FortiGateSyslogReceiver(
    host="0.0.0.0",
    port=514,
    protocol="udp"
)


def start_syslog_receiver():
    """Start the syslog receiver"""
    syslog_receiver.start()


def stop_syslog_receiver():
    """Stop the syslog receiver"""
    syslog_receiver.stop()
