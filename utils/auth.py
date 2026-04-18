"""
Authentication utilities for Brewery Manager
Provides password hashing, session management, and role-based access control
"""

import bcrypt
import functools
from datetime import datetime, timedelta
from flask import session, redirect, url_for, flash, request, jsonify
from typing import Optional, Dict, List


# Role hierarchy (higher number = more permissions)
ROLE_HIERARCHY = {
    'viewer': 1,
    'sales': 2,
    'brewer': 3,
    'manager': 4,
    'admin': 5
}

# Role descriptions
ROLE_DESCRIPTIONS = {
    'admin': 'Full system access',
    'manager': 'Manage all operations, staff, and reports',
    'brewer': 'Manage production, inventory, and quality',
    'sales': 'Manage customers, orders, and sales',
    'viewer': 'View-only access to reports and dashboards'
}


def hash_password(password: str) -> str:
    """Hash a password using bcrypt"""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')


def verify_password(password: str, hashed: str) -> bool:
    """Verify a password against its hash"""
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))


def generate_session_token() -> str:
    """Generate a unique session token"""
    import secrets
    return secrets.token_urlsafe(32)


def get_current_user() -> Optional[Dict]:
    """Get current logged-in user from session"""
    if 'user_id' in session:
        return {
            'id': session.get('user_id'),
            'username': session.get('username'),
            'full_name': session.get('full_name'),
            'role': session.get('role'),
            'email': session.get('email')
        }
    return None


def is_authenticated() -> bool:
    """Check if user is authenticated"""
    return 'user_id' in session


def has_role(required_role: str) -> bool:
    """Check if current user has required role or higher"""
    if not is_authenticated():
        return False
    
    user_role = session.get('role', 'viewer')
    user_level = ROLE_HIERARCHY.get(user_role, 0)
    required_level = ROLE_HIERARCHY.get(required_role, 0)
    
    return user_level >= required_level


def has_any_role(roles: List[str]) -> bool:
    """Check if current user has any of the specified roles"""
    if not is_authenticated():
        return False
    
    user_role = session.get('role', 'viewer')
    return user_role in roles


def login_required(f):
    """Decorator to require authentication"""
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        if not is_authenticated():
            # Check if it's an API request
            if request.path.startswith('/api/'):
                return jsonify({'error': 'Authentication required'}), 401
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function


def role_required(min_role: str):
    """Decorator to require minimum role level"""
    def decorator(f):
        @functools.wraps(f)
        @login_required
        def decorated_function(*args, **kwargs):
            if not has_role(min_role):
                if request.path.startswith('/api/'):
                    return jsonify({'error': 'Insufficient permissions'}), 403
                flash('You do not have permission to access this page.', 'danger')
                return redirect(url_for('dashboard'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def admin_required(f):
    """Decorator to require admin role"""
    @functools.wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if not has_role('admin'):
            if request.path.startswith('/api/'):
                return jsonify({'error': 'Admin access required'}), 403
            flash('Admin access required.', 'danger')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function


def manager_required(f):
    """Decorator to require manager role or higher"""
    @functools.wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if not has_role('manager'):
            if request.path.startswith('/api/'):
                return jsonify({'error': 'Manager access required'}), 403
            flash('Manager access required.', 'danger')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function


def brewer_required(f):
    """Decorator to require brewer role or higher"""
    @functools.wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if not has_role('brewer'):
            if request.path.startswith('/api/'):
                return jsonify({'error': 'Brewer access required'}), 403
            flash('Brewer access required.', 'danger')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function


def sales_required(f):
    """Decorator to require sales role or higher"""
    @functools.wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if not has_role('sales'):
            if request.path.startswith('/api/'):
                return jsonify({'error': 'Sales access required'}), 403
            flash('Sales access required.', 'danger')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function


def validate_password_strength(password: str) -> tuple[bool, str]:
    """Validate password strength"""
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    if not any(c.isupper() for c in password):
        return False, "Password must contain at least one uppercase letter"
    if not any(c.islower() for c in password):
        return False, "Password must contain at least one lowercase letter"
    if not any(c.isdigit() for c in password):
        return False, "Password must contain at least one number"
    return True, "Password is strong"


def get_role_permissions(role: str) -> Dict[str, bool]:
    """Get permissions for a role"""
    permissions = {
        'view_dashboard': True,
        'view_inventory': True,
        'edit_inventory': False,
        'view_production': True,
        'edit_production': False,
        'view_customers': True,
        'edit_customers': False,
        'view_sales': True,
        'edit_sales': False,
        'view_finance': True,
        'edit_finance': False,
        'view_staff': False,
        'edit_staff': False,
        'view_equipment': True,
        'edit_equipment': False,
        'view_reports': True,
        'manage_users': False,
        'view_audit_log': False,
        'manage_settings': False,
    }
    
    if role == 'sales':
        permissions.update({
            'edit_customers': True,
            'edit_sales': True,
        })
    elif role == 'brewer':
        permissions.update({
            'edit_inventory': True,
            'edit_production': True,
            'edit_equipment': True,
        })
    elif role == 'manager':
        permissions.update({
            'edit_inventory': True,
            'edit_production': True,
            'edit_customers': True,
            'edit_sales': True,
            'edit_finance': True,
            'view_staff': True,
            'edit_staff': True,
            'edit_equipment': True,
            'view_audit_log': True,
        })
    elif role == 'admin':
        for key in permissions:
            permissions[key] = True
    
    return permissions


class AuthManager:
    """Authentication manager for Brewery Manager"""
    
    def __init__(self, db):
        self.db = db
    
    def authenticate(self, username: str, password: str) -> Optional[Dict]:
        """Authenticate user with username and password"""
        user = self.db.get_user_by_username(username)
        if user and verify_password(password, user['password_hash']):
            return user
        return None
    
    def hash_password(self, password: str) -> str:
        """Hash a password"""
        return hash_password(password)
    
    def verify_password(self, password: str, hashed: str) -> bool:
        """Verify a password against its hash"""
        return verify_password(password, hashed)
    
    def log_login(self, user_id: int, ip_address: str, user_agent: str):
        """Log user login"""
        import json
        details = json.dumps({'ip': ip_address, 'user_agent': user_agent})
        self.db.log_audit(user_id, 'login', 'user', user_id, None, details)
    
    def log_logout(self, user_id: int):
        """Log user logout"""
        self.db.log_audit(user_id, 'logout', 'user', user_id, None, None)


def get_auth_manager(db):
    """Get authentication manager instance"""
    return AuthManager(db)
