import re
from typing import Tuple, Optional

def format_mobile_to_92(mobile: str) -> str:
    """
    Convert any mobile number format to 92XXXXX format for Superapp.
    
    Handles formats like:
    - 03001234567 -> 923001234567
    - +923001234567 -> 923001234567
    - 00923001234567 -> 923001234567
    - 3001234567 -> 923001234567
    """
    # Remove all non-digit characters
    digits = re.sub(r'\D', '', mobile)
    
    # Remove leading zeros
    digits = digits.lstrip('0')
    
    # If starts with 92, return as is
    if digits.startswith('92'):
        return digits
    
    # If starts with 3 (Pakistani mobile), add 92
    if digits.startswith('3'):
        return f'92{digits}'
    
    # Otherwise, assume it needs 92 prefix
    return f'92{digits}'


def validate_cnic(cnic: str) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Validate Pakistani CNIC number.
    
    Returns: (is_valid, formatted_cnic, error_message)
    
    Accepts:
    - 13 digits: 1234567890123
    - 15 characters with dashes: 12345-1234567-1
    """
    if not cnic:
        return False, None, "CNIC is required"
    
    # Remove all non-alphanumeric characters
    digits_only = re.sub(r'\D', '', cnic)
    
    # Check if 13 digits
    if len(digits_only) != 13:
        return False, None, "CNIC must be 13 digits"
    
    # Check if all digits
    if not digits_only.isdigit():
        return False, None, "CNIC must contain only digits"
    
    # Format with dashes: XXXXX-XXXXXXX-X
    formatted = f"{digits_only[:5]}-{digits_only[5:12]}-{digits_only[12]}"
    
    return True, formatted, None


def validate_passport(passport: str) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Validate passport number.
    
    Returns: (is_valid, formatted_passport, error_message)
    
    Basic validation - accepts alphanumeric, 6-20 characters
    """
    if not passport:
        return False, None, "Passport number is required"
    
    # Remove leading/trailing whitespace
    passport = passport.strip().upper()
    
    # Check length (most passports are 6-20 characters)
    if len(passport) < 6 or len(passport) > 20:
        return False, None, "Passport number must be 6-20 characters"
    
    # Check if alphanumeric
    if not re.match(r'^[A-Z0-9]+$', passport):
        return False, None, "Passport number must be alphanumeric"
    
    return True, passport, None


def validate_id_document(id_type: str, id_value: str) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Validate ID document based on type.
    
    Returns: (is_valid, formatted_value, error_message)
    """
    if id_type == 'cnic':
        return validate_cnic(id_value)
    elif id_type == 'passport':
        return validate_passport(id_value)
    else:
        return False, None, "Invalid ID type"


def format_mobile_display(mobile: str) -> str:
    """
    Format mobile number for display.
    
    92XXXXX -> +92-XXX-XXXXXXX
    """
    if mobile.startswith('92'):
        digits = mobile[2:]
        return f"+92-{digits[:3]}-{digits[3:]}"
    return mobile
