"""
Brewery Manager - Input Validation Utilities
Provides input sanitization and validation functions
"""

import re
import bleach
from typing import Optional, Any


def sanitize_string(value: str, max_length: int = 500) -> str:
    """Sanitize string input by removing HTML tags and limiting length"""
    if not value:
        return ""
    
    # Remove HTML tags
    cleaned = bleach.clean(value, tags=[], strip=True)
    
    # Limit length
    if len(cleaned) > max_length:
        cleaned = cleaned[:max_length]
    
    return cleaned.strip()


def validate_email(email: str) -> bool:
    """Validate email format"""
    if not email:
        return False
    
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def validate_phone(phone: str) -> bool:
    """Validate Vietnamese phone number format"""
    if not phone:
        return False
    
    # Remove spaces and dashes
    cleaned = re.sub(r'[\s\-]', '', phone)
    
    # Vietnamese phone patterns
    patterns = [
        r'^0[0-9]{9,10}$',  # Local format
        r'^\+84[0-9]{9,10}$',  # International format
        r'^84[0-9]{9,10}$'  # Without +
    ]
    
    return any(re.match(p, cleaned) for p in patterns)


def validate_positive_number(value: Any, allow_zero: bool = True) -> bool:
    """Validate that value is a positive number"""
    try:
        num = float(value)
        if allow_zero:
            return num >= 0
        return num > 0
    except (ValueError, TypeError):
        return False


def validate_integer(value: Any, min_val: int = None, max_val: int = None) -> bool:
    """Validate that value is an integer within range"""
    try:
        num = int(value)
        if min_val is not None and num < min_val:
            return False
        if max_val is not None and num > max_val:
            return False
        return True
    except (ValueError, TypeError):
        return False


def validate_date(date_str: str) -> bool:
    """Validate date format (YYYY-MM-DD)"""
    if not date_str:
        return False
    
    pattern = r'^\d{4}-\d{2}-\d{2}$'
    if not re.match(pattern, date_str):
        return False
    
    try:
        from datetime import datetime
        datetime.strptime(date_str, '%Y-%m-%d')
        return True
    except ValueError:
        return False


def sanitize_form_data(data: dict, rules: dict = None) -> dict:
    """
    Sanitize form data dictionary
    
    Args:
        data: Dictionary of form data
        rules: Optional dict of field rules, e.g. {'name': {'max_length': 100}}
    
    Returns:
        Sanitized dictionary
    """
    sanitized = {}
    
    for key, value in data.items():
        if value is None:
            sanitized[key] = None
            continue
        
        if isinstance(value, str):
            field_rules = rules.get(key, {}) if rules else {}
            max_length = field_rules.get('max_length', 500)
            sanitized[key] = sanitize_string(value, max_length)
        else:
            sanitized[key] = value
    
    return sanitized


def validate_required_fields(data: dict, required: list) -> list:
    """
    Check that all required fields are present and non-empty
    
    Returns:
        List of missing field names (empty if all present)
    """
    missing = []
    
    for field in required:
        value = data.get(field)
        if value is None or (isinstance(value, str) and not value.strip()):
            missing.append(field)
    
    return missing


# Common validation rules
VALIDATION_RULES = {
    'name': {'max_length': 200},
    'description': {'max_length': 2000},
    'notes': {'max_length': 2000},
    'email': {'max_length': 200},
    'phone': {'max_length': 20},
    'address': {'max_length': 500},
    'city': {'max_length': 100},
    'province': {'max_length': 100},
    'supplier': {'max_length': 200},
    'origin': {'max_length': 200},
    'style': {'max_length': 100},
    'category': {'max_length': 100},
    'unit': {'max_length': 20},
}