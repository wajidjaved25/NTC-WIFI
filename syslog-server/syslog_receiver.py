#!/usr/bin/env python3
"""
High-Performance Syslog Receiver for NTC WiFi
Optimized for 12 cores, 24GB RAM
Handles 25,000+ logs/second
"""

import os
import socket
import re
import json
import logging
import threading
import queue
import time
from datetime import datetime
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration from .env
LOGS_DB_HOST = os.getenv('LOGS_DB_HOST', 'localhost')
LOGS_DB_PORT = os.getenv('LOGS_DB_PORT', '5432')
LOGS_DB_NAME = os.getenv('LOGS_DB_NAME', 'ntc_wifi_logs')
LOGS_DB_USER = os.getenv('LOGS_DB_USER', 'syslog_user')
LOGS_DB_PASSWORD = os.getenv('LOGS_DB_PASSWORD', 'SecureLogPassword123')

SYSLOG_HOST = os.getenv('SYSLOG_HOST', '0.0.0.0')
SYSLOG_PORT = int(os.getenv('SYSLOG_PORT', '514'))
QUEUE_SIZE = int(os.getenv('QUEUE_SIZE', '20000'))
BATCH_SIZE = int(os.getenv('BATCH_SIZE', '2000'))
BATCH_TIMEOUT = float(os.getenv('BATCH_TIMEOUT', '0.5'))
NUM_WORKERS = int(os.getenv('NUM_WORKERS', '4'))

# Build database URL
DATABASE_URL = f"postgresql://{LOGS_DB_USER}:{LOGS_DB_PASSWORD}@{LOGS_DB_HOST}:{LOGS_DB_PORT}/{LOGS_DB_NAME}"

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Database engine
engine = create_engine(DATABASE_URL, pool_pre_ping=True, pool_size=10)
SessionLocal = sessionmaker(bind=engine)


class SyslogReceiver:
    def __init__(self):
        self.running = False
        self.raw_queue = queue.Queue(maxsize=QUEUE_SIZE)
        self.parsed_queue = queue.Queue(maxsize=QUEUE_SIZE)
        self.threads = []
        self.stats = {
            'received': 0,
            'parsed': 0,
            'stored': 0,
            'dropped': 0,
            'start_time': datetime.now()
        }
    
    def start(self):
        self.running = True
        logger.info("="*60)
        logger.info("NTC WiFi Syslog Receiver Starting")
        logger.info(f"Listening: {SYSLOG_HOST}:{SYSLOG_PORT}")
        logger.info(f"Queue: {QUEUE_SIZE}, Batch: {BATCH_SIZE}, Workers: {NUM_WORKERS}")
        logger.info("="*60)
        
        # Start UDP receiver
        t = threading.Thread(target=self._udp_receiver, daemon=True)
        t.start()
        self.threads.append(t)
        
        # Start parser workers
        for i in range(NUM_WORKERS):
            t = threading.Thread(target=self._parser_worker, daemon=True)
            t.start()
            self.threads.append(t)
        
        # Start batch writer
        t = threading.Thread(target=self._batch_writer, daemon=True)
        t.start()
        self.threads.append(t)
        
        # Start stats logger
        t = threading.Thread(target=self._stats_logger, daemon=True)
        t.start()
        self.threads.append(t)
        
        logger.info(f"✅ Started {len(self.threads)} threads")
    
    def _udp_receiver(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 2 * 1024 * 1024)
        sock.bind((SYSLOG_HOST, SYSLOG_PORT))
        
        logger.info(f"📡 UDP Receiver listening on {SYSLOG_HOST}:{SYSLOG_PORT}")
        
        while self.running:
            try:
                data, addr = sock.recvfrom(65535)
                message = data.decode('utf-8', errors='ignore')
                self.stats['received'] += 1
                
                try:
                    self.raw_queue.put_nowait(message)
                except queue.Full:
                    self.stats['dropped'] += 1
            except Exception as e:
                if self.running:
                    logger.error(f"Receive error: {e}")
    
    def _parser_worker(self):
        while self.running:
            try:
                message = self.raw_queue.get(timeout=1)
                
                try:
                    log_data = self._parse_log(message)
                    if log_data and log_data.get('type') == 'traffic':
                        self.stats['parsed'] += 1
                        try:
                            self.parsed_queue.put_nowait(log_data)
                        except queue.Full:
                            self.stats['dropped'] += 1
                except Exception as e:
                    logger.debug(f"Parse error: {e}")
                finally:
                    self.raw_queue.task_done()
            except queue.Empty:
                continue
    
    def _batch_writer(self):
        batch = []
        last_write = time.time()
        
        while self.running:
            try:
                log_data = self.parsed_queue.get(timeout=0.1)
                batch.append(log_data)
                self.parsed_queue.task_done()
            except queue.Empty:
                pass
            
            should_write = (
                len(batch) >= BATCH_SIZE or
                (len(batch) > 0 and time.time() - last_write >= BATCH_TIMEOUT)
            )
            
            if should_write:
                stored = self._bulk_insert(batch)
                self.stats['stored'] += stored
                batch = []
                last_write = time.time()
        
        if batch:
            self._bulk_insert(batch)
    
    def _bulk_insert(self, logs):
        if not logs:
            return 0
        
        session = SessionLocal()
        try:
            insert_query = text("""
                INSERT INTO firewall_logs (
                    log_timestamp, log_date, log_time,
                    source_ip, source_port, source_mac, source_interface,
                    translated_ip, translated_port,
                    destination_ip, destination_port, destination_country,
                    protocol, protocol_name, service, app_name, app_category,
                    sent_bytes, received_bytes, sent_packets, received_packets, duration,
                    action, policy_id, url, domain_name, device_type, os_name, raw_log_data
                ) VALUES (
                    :log_timestamp, :log_date, :log_time,
                    :source_ip, :source_port, :source_mac, :source_interface,
                    :translated_ip, :translated_port,
                    :destination_ip, :destination_port, :destination_country,
                    :protocol, :protocol_name, :service, :app_name, :app_category,
                    :sent_bytes, :received_bytes, :sent_packets, :received_packets, :duration,
                    :action, :policy_id, :url, :domain_name, :device_type, :os_name, :raw_log_data
                )
            """)
            
            for log in logs:
                log.pop('type', None)
                # Convert raw_log_data dict to JSON string for JSONB column
                if 'raw_log_data' in log and isinstance(log['raw_log_data'], dict):
                    log['raw_log_data'] = json.dumps(log['raw_log_data'])
                session.execute(insert_query, log)
            
            session.commit()
            logger.debug(f"📝 Stored {len(logs)} logs")
            return len(logs)
        except Exception as e:
            logger.error(f"Insert error: {e}")
            session.rollback()
            return 0
        finally:
            session.close()
    
    def _parse_log(self, message):
        pattern = r'(\w+)=(?:"([^"]*)"|([^\s]+))'
        matches = re.findall(pattern, message)
        
        log_dict = {}
        for key, quoted, unquoted in matches:
            log_dict[key] = quoted if quoted else unquoted
        
        if log_dict.get('type') != 'traffic':
            return None
        
        try:
            date_str = log_dict.get('date', '')
            time_str = log_dict.get('time', '')
            
            if not date_str or not time_str:
                return None
            
            log_timestamp = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M:%S")
            
            return {
                'type': 'traffic',
                'log_timestamp': log_timestamp,
                'log_date': log_timestamp.date(),
                'log_time': log_timestamp.time(),
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
                'protocol_name': self._get_protocol(log_dict.get('proto', '0')),
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
        except:
            return None
    
    def _get_protocol(self, proto):
        proto_map = {'6': 'TCP', '17': 'UDP', '1': 'ICMP'}
        return proto_map.get(proto, 'OTHER')
    
    def _stats_logger(self):
        while self.running:
            time.sleep(60)
            uptime = (datetime.now() - self.stats['start_time']).total_seconds()
            recv_rate = self.stats['received'] / uptime if uptime > 0 else 0
            store_rate = self.stats['stored'] / uptime if uptime > 0 else 0
            drop_rate = (self.stats['dropped'] / self.stats['received'] * 100) if self.stats['received'] > 0 else 0
            
            logger.info(
                f"📊 Recv={recv_rate:.1f}/s, Store={store_rate:.1f}/s, "
                f"Queue={self.raw_queue.qsize()}+{self.parsed_queue.qsize()}, "
                f"Drop={drop_rate:.2f}%, Total={self.stats['stored']:,}"
            )


if __name__ == "__main__":
    receiver = SyslogReceiver()
    receiver.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        receiver.running = False
