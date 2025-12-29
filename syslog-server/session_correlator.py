#!/usr/bin/env python3
"""
Session Correlator for NTC WiFi
Correlates firewall logs with WiFi sessions from main server
Runs every 5 minutes
"""

import os
import time
import logging
from datetime import datetime, timedelta, timezone
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration from .env
MAIN_SERVER_IP = os.getenv('MAIN_SERVER_IP', 'localhost')
MAIN_DB_PORT = os.getenv('MAIN_DB_PORT', '5432')
MAIN_DB_NAME = os.getenv('MAIN_DB_NAME', 'ntc_wifi_admin')
MAIN_DB_USER = os.getenv('MAIN_DB_USER', 'ntc_admin')
MAIN_DB_PASSWORD = os.getenv('MAIN_DB_PASSWORD', 'NTCWifi2024!')

LOGS_DB_HOST = os.getenv('LOGS_DB_HOST', 'localhost')
LOGS_DB_PORT = os.getenv('LOGS_DB_PORT', '5432')
LOGS_DB_NAME = os.getenv('LOGS_DB_NAME', 'ntc_wifi_logs')
LOGS_DB_USER = os.getenv('LOGS_DB_USER', 'syslog_user')
LOGS_DB_PASSWORD = os.getenv('LOGS_DB_PASSWORD', 'SecureLogPassword123')

CORRELATION_INTERVAL = int(os.getenv('CORRELATION_INTERVAL', '300'))  # 5 minutes
LOOKBACK_MINUTES = int(os.getenv('LOOKBACK_MINUTES', '30'))

# Build database URLs
MAIN_DB_URL = f"postgresql://{MAIN_DB_USER}:{MAIN_DB_PASSWORD}@{MAIN_SERVER_IP}:{MAIN_DB_PORT}/{MAIN_DB_NAME}"
LOGS_DB_URL = f"postgresql://{LOGS_DB_USER}:{LOGS_DB_PASSWORD}@{LOGS_DB_HOST}:{LOGS_DB_PORT}/{LOGS_DB_NAME}"

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Database engines
main_engine = create_engine(MAIN_DB_URL, pool_pre_ping=True)
logs_engine = create_engine(LOGS_DB_URL, pool_pre_ping=True)

MainSession = sessionmaker(bind=main_engine)
LogsSession = sessionmaker(bind=logs_engine)


def correlate_logs():
    """Correlate firewall logs with WiFi sessions"""
    main_db = MainSession()
    logs_db = LogsSession()
    
    try:
        cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=LOOKBACK_MINUTES)
        
        # Get active sessions from main server
        sessions_query = text("""
            SELECT id, user_id, ip_address, start_time, end_time
            FROM sessions
            WHERE start_time > :cutoff_time
            ORDER BY start_time DESC
        """)
        
        sessions = main_db.execute(sessions_query, {'cutoff_time': cutoff_time}).fetchall()
        logger.info(f"Found {len(sessions)} sessions to correlate")
        
        # Update firewall logs with session info
        update_query = text("""
            UPDATE firewall_logs
            SET session_id = :session_id, user_id = :user_id
            WHERE source_ip = :ip_address
            AND log_timestamp >= :start_time
            AND (:end_time IS NULL OR log_timestamp <= :end_time + INTERVAL '5 minutes')
            AND session_id IS NULL
        """)
        
        correlated = 0
        for session in sessions:
            result = logs_db.execute(update_query, {
                'session_id': session.id,
                'user_id': session.user_id,
                'ip_address': session.ip_address,
                'start_time': session.start_time,
                'end_time': session.end_time
            })
            correlated += result.rowcount
        
        logs_db.commit()
        logger.info(f"🔗 Correlated {correlated} logs with sessions")
        
        return correlated
    except Exception as e:
        logger.error(f"Correlation error: {e}")
        logs_db.rollback()
        return 0
    finally:
        main_db.close()
        logs_db.close()


def main():
    """Main correlation loop"""
    logger.info("="*60)
    logger.info("Session Correlator Starting")
    logger.info(f"Main Server: {MAIN_SERVER_IP}:{MAIN_DB_PORT}")
    logger.info(f"Interval: {CORRELATION_INTERVAL}s")
    logger.info(f"Lookback: {LOOKBACK_MINUTES}min")
    logger.info("="*60)
    
    while True:
        try:
            correlate_logs()
        except Exception as e:
            logger.error(f"Main loop error: {e}")
        
        time.sleep(CORRELATION_INTERVAL)


if __name__ == "__main__":
    main()
