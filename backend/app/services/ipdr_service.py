from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from datetime import datetime, timedelta
import csv
import io
import re
from typing import List, Dict, Optional, Tuple
import logging

from ..models.ipdr import FirewallLog, FirewallImportJob, IPDRSearchHistory
from ..models.user import User
from ..models.session import Session as WiFiSession
from ..schemas.ipdr import (
    FirewallLogCreate, IPDRSearchRequest, IPDRRecord, 
    IPDRSearchResponse, ImportJobResponse
)

logger = logging.getLogger(__name__)


class IPDRService:
    
    @staticmethod
    def parse_fortigate_csv(csv_content: str, filename: str) -> List[Dict]:
        """Parse FortiGate firewall CSV logs"""
        logs = []
        reader = csv.DictReader(io.StringIO(csv_content))
        
        for row in reader:
            try:
                # Parse FortiGate log format
                log_entry = IPDRService._parse_fortigate_row(row)
                if log_entry:
                    log_entry['csv_filename'] = filename
                    logs.append(log_entry)
            except Exception as e:
                logger.error(f"Error parsing row: {str(e)}")
                continue
        
        return logs
    
    @staticmethod
    def _parse_fortigate_row(row: Dict) -> Optional[Dict]:
        """Parse a single FortiGate log row"""
        # Extract date and time
        log_date = row.get('date')
        log_time = row.get('time')
        
        if not log_date or not log_time:
            return None
        
        # Combine date and time
        log_timestamp = datetime.strptime(
            f"{log_date} {log_time}", 
            "%Y-%m-%d %H:%M:%S"
        )
        
        return {
            'log_date': datetime.strptime(log_date, "%Y-%m-%d").date(),
            'log_time': datetime.strptime(log_time, "%H:%M:%S").time(),
            'log_timestamp': log_timestamp,
            'source_ip': row.get('srcip'),
            'source_port': int(row.get('srcport', 0)),
            'source_mac': row.get('srcmac'),
            'source_interface': row.get('srcintf'),
            'translated_ip': row.get('transip'),
            'translated_port': int(row.get('transport', 0)) if row.get('transport') else None,
            'destination_ip': row.get('dstip'),
            'destination_port': int(row.get('dstport', 0)),
            'destination_country': row.get('dstcountry'),
            'protocol': int(row.get('proto', 0)),
            'protocol_name': 'TCP' if int(row.get('proto', 0)) == 6 else 'UDP' if int(row.get('proto', 0)) == 17 else 'OTHER',
            'service': row.get('service'),
            'app_name': row.get('app'),
            'app_category': row.get('appcat'),
            'sent_bytes': int(row.get('sentbyte', 0)),
            'received_bytes': int(row.get('rcvdbyte', 0)),
            'sent_packets': int(row.get('sentpkt', 0)),
            'received_packets': int(row.get('rcvdpkt', 0)),
            'duration': int(row.get('duration', 0)),
            'action': row.get('action'),
            'policy_id': int(row.get('policyid', 0)) if row.get('policyid') else None,
            'domain_name': row.get('dstname'),
            'device_type': row.get('devtype'),
            'os_name': row.get('osname'),
            'raw_log_data': row
        }
    
    @staticmethod
    def import_csv(db: Session, csv_content: str, filename: str, admin_id: int) -> ImportJobResponse:
        """Import firewall logs from CSV"""
        # Create import job
        job = FirewallImportJob(
            filename=filename,
            file_size=len(csv_content),
            status='processing',
            started_at=datetime.now(),
            imported_by=admin_id
        )
        db.add(job)
        db.commit()
        db.refresh(job)
        
        try:
            # Parse CSV
            logs = IPDRService.parse_fortigate_csv(csv_content, filename)
            job.total_rows = len(logs)
            db.commit()
            
            # Import logs in batches
            batch_size = 1000
            imported_count = 0
            failed_count = 0
            
            for i in range(0, len(logs), batch_size):
                batch = logs[i:i + batch_size]
                
                for log_data in batch:
                    try:
                        # Try to correlate with existing session
                        session = IPDRService._find_matching_session(
                            db, 
                            log_data['source_ip'], 
                            log_data['source_mac'],
                            log_data['log_timestamp']
                        )
                        
                        if session:
                            log_data['session_id'] = session.id
                            log_data['user_id'] = session.user_id
                        
                        # Create firewall log entry
                        firewall_log = FirewallLog(**log_data)
                        db.add(firewall_log)
                        imported_count += 1
                        
                    except Exception as e:
                        logger.error(f"Error importing log: {str(e)}")
                        failed_count += 1
                        continue
                
                # Commit batch
                db.commit()
                
                # Update progress
                job.processed_rows = min(i + batch_size, len(logs))
                job.imported_rows = imported_count
                job.failed_rows = failed_count
                db.commit()
            
            # Mark job as completed
            job.status = 'completed'
            job.completed_at = datetime.now()
            job.imported_rows = imported_count
            job.failed_rows = failed_count
            db.commit()
            
        except Exception as e:
            job.status = 'failed'
            job.error_message = str(e)
            job.completed_at = datetime.now()
            db.commit()
            logger.error(f"CSV import failed: {str(e)}")
        
        db.refresh(job)
        return ImportJobResponse.from_orm(job)
    
    @staticmethod
    def _find_matching_session(
        db: Session, 
        ip_address: str, 
        mac_address: Optional[str],
        timestamp: datetime
    ) -> Optional[WiFiSession]:
        """Find matching WiFi session for firewall log"""
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
    
    @staticmethod
    def search_ipdr(
        db: Session, 
        search_request: IPDRSearchRequest,
        admin_id: int,
        ip_address: str
    ) -> IPDRSearchResponse:
        """Search IPDR records based on various criteria"""
        
        # Build query
        query = db.query(
            FirewallLog,
            User.name.label('user_name'),
            User.mobile.label('user_mobile'),
            WiFiSession.mac_address.label('session_mac'),
            WiFiSession.start_time.label('login_time'),
            WiFiSession.end_time.label('logout_time'),
            WiFiSession.duration.label('session_duration')
        ).outerjoin(
            WiFiSession, FirewallLog.session_id == WiFiSession.id
        ).outerjoin(
            User, FirewallLog.user_id == User.id
        )
        
        # Apply filters based on search type
        if search_request.search_type == 'mobile' and search_request.mobile:
            query = query.filter(User.mobile == search_request.mobile)
        
        elif search_request.search_type == 'cnic' and search_request.cnic:
            # Assuming CNIC is stored in a user field (adjust as needed)
            query = query.filter(User.cnic == search_request.cnic)
        
        elif search_request.search_type == 'passport' and search_request.passport:
            query = query.filter(User.passport == search_request.passport)
        
        elif search_request.search_type == 'ip' and search_request.ip_address:
            query = query.filter(FirewallLog.source_ip == search_request.ip_address)
        
        elif search_request.search_type == 'mac' and search_request.mac_address:
            query = query.filter(WiFiSession.mac_address == search_request.mac_address)
        
        elif search_request.search_type == 'date_range':
            if search_request.start_date:
                query = query.filter(FirewallLog.log_timestamp >= search_request.start_date)
            if search_request.end_date:
                query = query.filter(FirewallLog.log_timestamp <= search_request.end_date)
        
        # Count total results
        total_records = query.count()
        
        # Apply pagination
        offset = (search_request.page - 1) * search_request.page_size
        results = query.order_by(FirewallLog.log_timestamp.desc())\
            .offset(offset)\
            .limit(search_request.page_size)\
            .all()
        
        # Transform to IPDR records
        ipdr_records = []
        for result in results:
            log, user_name, user_mobile, session_mac, login_time, logout_time, session_duration = result
            
            ipdr_record = IPDRRecord(
                full_name=user_name,
                mobile=user_mobile,
                login_time=login_time,
                logout_time=logout_time,
                session_duration=session_duration,
                mac_address=session_mac or log.source_mac,
                source_ip=log.source_ip,
                source_port=log.source_port,
                translated_ip=log.translated_ip,
                translated_port=log.translated_port,
                destination_ip=log.destination_ip,
                destination_port=log.destination_port,
                data_consumption=log.sent_bytes + log.received_bytes,
                url=log.url,
                protocol=log.protocol_name,
                service=log.service,
                app_name=log.app_name,
                log_timestamp=log.log_timestamp
            )
            ipdr_records.append(ipdr_record)
        
        # Log search for audit
        search_history = IPDRSearchHistory(
            admin_id=admin_id,
            search_type=search_request.search_type,
            search_params=search_request.dict(),
            results_count=total_records,
            ip_address=ip_address
        )
        db.add(search_history)
        db.commit()
        
        # Calculate pagination
        total_pages = (total_records + search_request.page_size - 1) // search_request.page_size
        
        return IPDRSearchResponse(
            total_records=total_records,
            page=search_request.page,
            page_size=search_request.page_size,
            total_pages=total_pages,
            records=ipdr_records
        )
    
    @staticmethod
    def get_import_jobs(db: Session, limit: int = 50) -> List[ImportJobResponse]:
        """Get recent import jobs"""
        jobs = db.query(FirewallImportJob)\
            .order_by(FirewallImportJob.created_at.desc())\
            .limit(limit)\
            .all()
        
        return [ImportJobResponse.from_orm(job) for job in jobs]
