import requests
import asyncio
from cryptography.fernet import Fernet
from typing import Optional
import json

from ..config import settings

# Initialize Fernet cipher - use the key from settings
def _get_cipher():
    """Get Fernet cipher using key from settings"""
    try:
        # Ensure the key is valid base64 and 32 bytes when decoded
        key = settings.ENCRYPTION_KEY
        if isinstance(key, str):
            key = key.encode()
        return Fernet(key)
    except Exception as e:
        raise Exception(f"Invalid ENCRYPTION_KEY in .env: {str(e)}. Key must be 44 characters (base64-encoded 32 bytes). Generate with: python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'")

async def send_otp_sms(mobile: str, otp: str) -> dict:
    """Send OTP via SMS using connect.smsapp.pk v3 API (Superapp)"""
    try:
        from .validators import format_mobile_to_92
        
        # Ensure mobile is in 92XXXXX format
        formatted_mobile = format_mobile_to_92(mobile)
        
        # SMS API v3 configuration
        api_url = "https://connect.smsapp.pk/api/v3/sms/send"
        api_key = settings.SUPERAPP_API_KEY  # Bearer token
        sender_id = settings.SUPERAPP_SENDER_ID
        
        message = f"Your OTP for NTC WiFi is: {otp}. Valid for 5 minutes. Do not share this code."
        
        # v3 API format
        payload = {
            "recipient": formatted_mobile,  # 92XXXXX format
            "sender_id": sender_id,
            "message": message
        }
        
        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        print(f"SMS API URL: {api_url}")
        print(f"Formatted mobile: {formatted_mobile}")
        print(f"Sender ID: {sender_id}")
        
        # Use asyncio to make non-blocking request
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: requests.post(api_url, json=payload, headers=headers, timeout=10)
        )
        
        print(f"SMS API Response Status: {response.status_code}")
        print(f"SMS API Response: {response.text}")
        
        if response.status_code == 200:
            result = response.json()
            if result.get('status') == 'success':
                return {
                    "success": True,
                    "message": "OTP sent successfully",
                    "mobile": formatted_mobile,
                    "response": result
                }
            else:
                return {
                    "success": False,
                    "message": f"SMS API error: {result.get('message', 'Unknown error')}"
                }
        else:
            return {
                "success": False,
                "message": f"Failed to send SMS: HTTP {response.status_code}"
            }
    
    except Exception as e:
        raise Exception(f"SMS sending failed: {str(e)}")

def generate_otp(length: int = 6) -> str:
    """Generate random OTP code"""
    import random
    return ''.join([str(random.randint(0, 9)) for _ in range(length)])

def encrypt_password(password: str) -> str:
    """Encrypt password for Omada config storage"""
    cipher_suite = _get_cipher()
    encrypted = cipher_suite.encrypt(password.encode())
    return encrypted.decode()

def decrypt_password(encrypted_password: str) -> str:
    """Decrypt password from Omada config"""
    try:
        cipher_suite = _get_cipher()
        decrypted = cipher_suite.decrypt(encrypted_password.encode())
        return decrypted.decode()
    except Exception as e:
        raise Exception(f"Failed to decrypt password. This usually means the ENCRYPTION_KEY has changed. Error: {str(e)}")

def format_bytes(bytes_value: int) -> str:
    """Format bytes to human readable format"""
    if bytes_value is None:
        return "0 B"
    
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_value < 1024.0:
            return f"{bytes_value:.2f} {unit}"
        bytes_value /= 1024.0
    return f"{bytes_value:.2f} PB"

def format_duration(seconds: int) -> str:
    """Format seconds to human readable duration"""
    if seconds is None:
        return "0s"
    
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    
    parts = []
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")
    if secs > 0 or not parts:
        parts.append(f"{secs}s")
    
    return " ".join(parts)

def validate_mac_address(mac: str) -> bool:
    """Validate MAC address format"""
    import re
    pattern = re.compile(r'^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$')
    return bool(pattern.match(mac))

def sanitize_filename(filename: str) -> str:
    """Sanitize filename for safe storage"""
    import re
    # Remove any non-alphanumeric characters except dots, underscores, and hyphens
    filename = re.sub(r'[^\w\s.-]', '', filename)
    # Replace spaces with underscores
    filename = filename.replace(' ', '_')
    return filename

async def check_file_size(file_path: str) -> int:
    """Get file size in bytes"""
    import os
    try:
        return os.path.getsize(file_path)
    except:
        return 0

def generate_session_id() -> str:
    """Generate unique session ID"""
    import uuid
    return str(uuid.uuid4())

def calculate_time_until_midnight() -> int:
    """Calculate seconds until midnight (for daily limits reset)"""
    from datetime import datetime, time, timedelta
    now = datetime.now()
    midnight = datetime.combine(now.date() + timedelta(days=1), time.min)
    return int((midnight - now).total_seconds())

def is_within_schedule(start_date, end_date) -> bool:
    """Check if current time is within scheduled period"""
    from datetime import datetime
    now = datetime.now()
    
    if start_date and now < start_date:
        return False
    if end_date and now > end_date:
        return False
    
    return True

async def log_system_event(db, level: str, module: str, action: str, message: str, details: dict = None, user_id: int = None):
    """Log system events to database"""
    from ..models.system_log import SystemLog
    
    log_entry = SystemLog(
        log_level=level,
        module=module,
        action=action,
        message=message,
        details=details,
        user_id=user_id
    )
    db.add(log_entry)
    db.commit()


# File Upload Helpers

def get_file_extension(filename: str) -> str:
    """Get file extension from filename"""
    return filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''


def generate_unique_filename(original_filename: str) -> str:
    """Generate unique filename with timestamp"""
    import uuid
    from datetime import datetime
    
    ext = get_file_extension(original_filename)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    unique_id = str(uuid.uuid4())[:8]
    
    return f"{timestamp}_{unique_id}.{ext}"


async def save_uploaded_file(file, upload_dir: str, allowed_extensions: list = None) -> dict:
    """Save uploaded file to disk"""
    import os
    import shutil
    from pathlib import Path
    
    try:
        # Validate file extension
        ext = get_file_extension(file.filename)
        if allowed_extensions and ext not in allowed_extensions:
            raise ValueError(f"File type .{ext} not allowed")
        
        # Create upload directory if it doesn't exist
        Path(upload_dir).mkdir(parents=True, exist_ok=True)
        
        # Generate unique filename
        unique_filename = generate_unique_filename(file.filename)
        file_path = os.path.join(upload_dir, unique_filename)
        
        # Save file
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Get file size
        file_size = os.path.getsize(file_path)
        
        return {
            "success": True,
            "filename": unique_filename,
            "original_filename": file.filename,
            "file_path": file_path,
            "file_size": file_size,
            "mime_type": file.content_type
        }
    
    except Exception as e:
        raise Exception(f"File upload failed: {str(e)}")


async def delete_file(file_path: str) -> bool:
    """Delete file from disk"""
    import os
    
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            return True
        return False
    except Exception as e:
        print(f"Error deleting file: {str(e)}")
        return False


# Image Processing Helpers

async def resize_image(image_path: str, max_width: int = 1920, max_height: int = 1080) -> bool:
    """Resize image to max dimensions while maintaining aspect ratio"""
    try:
        from PIL import Image
        
        with Image.open(image_path) as img:
            # Calculate new dimensions
            img.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
            
            # Save resized image
            img.save(image_path, optimize=True, quality=85)
        
        return True
    except Exception as e:
        print(f"Error resizing image: {str(e)}")
        return False


async def create_thumbnail(image_path: str, thumbnail_size: tuple = (300, 300)) -> str:
    """Create thumbnail from image"""
    try:
        from PIL import Image
        import os
        
        # Generate thumbnail filename
        base_path = os.path.splitext(image_path)[0]
        ext = os.path.splitext(image_path)[1]
        thumbnail_path = f"{base_path}_thumb{ext}"
        
        with Image.open(image_path) as img:
            img.thumbnail(thumbnail_size, Image.Resampling.LANCZOS)
            img.save(thumbnail_path, optimize=True, quality=75)
        
        return thumbnail_path
    except Exception as e:
        print(f"Error creating thumbnail: {str(e)}")
        return image_path


async def optimize_image(image_path: str) -> bool:
    """Optimize image for web"""
    try:
        from PIL import Image
        
        with Image.open(image_path) as img:
            # Convert RGBA to RGB if needed
            if img.mode == 'RGBA':
                rgb_img = Image.new('RGB', img.size, (255, 255, 255))
                rgb_img.paste(img, mask=img.split()[3])
                img = rgb_img
            
            # Save optimized
            img.save(image_path, optimize=True, quality=85)
        
        return True
    except Exception as e:
        print(f"Error optimizing image: {str(e)}")
        return False
