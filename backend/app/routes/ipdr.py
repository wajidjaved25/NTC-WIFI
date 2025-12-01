from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List
import io
import csv
from datetime import datetime

from ..database import get_db
from ..models.admin import Admin
from ..schemas.ipdr import (
    IPDRSearchRequest, IPDRSearchResponse, 
    CSVImportRequest, ImportJobResponse,
    IPDRExportRequest, IPDRRecord
)
from ..utils.security import get_current_user, has_permission
from ..services.ipdr_service import IPDRService

router = APIRouter(prefix="/ipdr", tags=["IPDR Reports"])


def require_ipdr_permission(current_user: Admin = Depends(get_current_user)):
    """Check if user has permission to access IPDR"""
    if not has_permission(current_user, "view_ipdr"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to access IPDR reports"
        )
    return current_user


@router.post("/search", response_model=IPDRSearchResponse)
async def search_ipdr_records(
    search_request: IPDRSearchRequest,
    request: Request,
    current_user: Admin = Depends(require_ipdr_permission),
    db: Session = Depends(get_db)
):
    """
    Search IPDR records by:
    - CNIC/Passport Number
    - Mobile Number
    - Date Range
    - IP Address
    - MAC Address
    """
    try:
        client_ip = request.client.host
        results = IPDRService.search_ipdr(
            db, 
            search_request, 
            current_user.id,
            client_ip
        )
        return results
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error searching IPDR records: {str(e)}"
        )


@router.post("/import/csv", response_model=ImportJobResponse)
async def import_firewall_csv(
    file: UploadFile = File(...),
    current_user: Admin = Depends(require_ipdr_permission),
    db: Session = Depends(get_db)
):
    """
    Import firewall logs from CSV file
    Supports FortiGate log format
    """
    try:
        # Validate file type
        if not file.filename.endswith('.csv'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only CSV files are supported"
            )
        
        # Read file content
        content = await file.read()
        csv_content = content.decode('utf-8')
        
        # Import CSV
        result = IPDRService.import_csv(
            db, 
            csv_content, 
            file.filename,
            current_user.id
        )
        
        return result
        
    except UnicodeDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid CSV file encoding. Please use UTF-8"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error importing CSV: {str(e)}"
        )


@router.get("/import/jobs", response_model=List[ImportJobResponse])
async def get_import_jobs(
    limit: int = 50,
    current_user: Admin = Depends(require_ipdr_permission),
    db: Session = Depends(get_db)
):
    """Get recent CSV import jobs"""
    try:
        jobs = IPDRService.get_import_jobs(db, limit)
        return jobs
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching import jobs: {str(e)}"
        )


@router.post("/export")
async def export_ipdr_records(
    export_request: IPDRExportRequest,
    request: Request,
    current_user: Admin = Depends(require_ipdr_permission),
    db: Session = Depends(get_db)
):
    """
    Export IPDR search results
    Formats: CSV, PDF
    """
    try:
        # Get search results
        client_ip = request.client.host
        search_results = IPDRService.search_ipdr(
            db,
            export_request.search_params,
            current_user.id,
            client_ip
        )
        
        if export_request.format == 'csv':
            return await _export_csv(search_results.records)
        elif export_request.format == 'pdf':
            return await _export_pdf(search_results.records)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unsupported export format"
            )
            
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error exporting IPDR records: {str(e)}"
        )


async def _export_csv(records: List[IPDRRecord]) -> StreamingResponse:
    """Export records as CSV"""
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header - All IPDR fields
    writer.writerow([
        'Full Name',
        'CNIC/Passport Number',
        'Mobile Number',
        'Login Date & Time',
        'Logout Date & Time',
        'Session Duration (seconds)',
        'MAC Address',
        'Source IP Address',
        'Source IP Port',
        'Translated IP Address',
        'Translated IP Port',
        'Destination IP Address',
        'Destination IP Port',
        'Data Consumption (MB)',
        'Internet Access Log - URL',
        'Protocol',
        'Service',
        'Application Name',
        'Log Timestamp'
    ])
    
    # Write data
    for record in records:
        writer.writerow([
            record.full_name or 'N/A',
            record.cnic or record.passport or 'N/A',
            record.mobile or 'N/A',
            record.login_time.isoformat() if record.login_time else 'N/A',
            record.logout_time.isoformat() if record.logout_time else 'Active',
            record.session_duration or 'N/A',
            record.mac_address or 'N/A',
            record.source_ip,
            record.source_port,
            record.translated_ip or 'N/A',
            record.translated_port or 'N/A',
            record.destination_ip,
            record.destination_port,
            f"{(record.data_consumption / (1024 * 1024)):.2f}",
            record.url or 'N/A',
            record.protocol or 'N/A',
            record.service or 'N/A',
            record.app_name or 'N/A',
            record.log_timestamp.isoformat()
        ])
    
    output.seek(0)
    
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=ipdr_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        }
    )


async def _export_pdf(records: List[IPDRRecord]) -> StreamingResponse:
    """Export records as PDF"""
    # TODO: Implement PDF export using reportlab or similar
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="PDF export not yet implemented"
    )


@router.get("/stats")
async def get_ipdr_stats(
    current_user: Admin = Depends(require_ipdr_permission),
    db: Session = Depends(get_db)
):
    """Get IPDR statistics"""
    from sqlalchemy import func
    from ..models.ipdr import FirewallLog
    
    try:
        total_logs = db.query(func.count(FirewallLog.id)).scalar()
        logs_with_users = db.query(func.count(FirewallLog.id)).filter(
            FirewallLog.user_id.isnot(None)
        ).scalar()
        
        today = datetime.now().date()
        today_logs = db.query(func.count(FirewallLog.id)).filter(
            FirewallLog.log_date == today
        ).scalar()
        
        return {
            "total_firewall_logs": total_logs,
            "logs_with_user_correlation": logs_with_users,
            "correlation_percentage": round((logs_with_users / total_logs * 100), 2) if total_logs > 0 else 0,
            "todays_logs": today_logs
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching IPDR stats: {str(e)}"
        )


@router.get("/syslog/status")
async def get_syslog_status(
    current_user: Admin = Depends(require_ipdr_permission)
):
    """Get FortiGate syslog receiver status"""
    from ..services.fortigate_syslog_receiver import syslog_receiver
    
    return {
        "running": syslog_receiver.running,
        "host": syslog_receiver.host,
        "port": syslog_receiver.port,
        "protocol": syslog_receiver.protocol,
        "status": "active" if syslog_receiver.running else "stopped"
    }


@router.post("/syslog/restart")
async def restart_syslog_receiver(
    current_user: Admin = Depends(require_ipdr_permission)
):
    """Restart the syslog receiver"""
    from ..services.fortigate_syslog_receiver import syslog_receiver
    
    try:
        syslog_receiver.stop()
        import time
        time.sleep(1)
        syslog_receiver.start()
        
        return {
            "message": "Syslog receiver restarted successfully",
            "status": "running"
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error restarting syslog receiver: {str(e)}"
        )
