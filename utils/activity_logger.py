"""
Activity Logger Middleware
Logs user actions and page visits for audit trail
"""

from functools import wraps
from flask import request, g


def log_activity(activity_type, page_path=None, action_detail=None):
    """Decorator to log user activity on routes"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            result = f(*args, **kwargs)

            if hasattr(g, 'user_id') and g.user_id:
                try:
                    from flask import current_app
                    db = current_app.config.get('db')
                    if db:
                        from utils.user_manager import UserManager
                        um = UserManager(db)
                        um.log_activity(
                            user_id=g.user_id,
                            activity_type=activity_type,
                            page_path=page_path or request.path,
                            action_detail=action_detail,
                            ip_address=request.remote_addr,
                            user_agent=request.headers.get('User-Agent', '')[:500]
                        )
                except Exception:
                    pass  # Silently fail - don't break the request

            return result
        return decorated_function
    return decorator


def log_login(user_id, db, ip_address=None, user_agent=None):
    """Log login event"""
    try:
        from utils.user_manager import UserManager
        um = UserManager(db)
        um.log_activity(
            user_id=user_id,
            activity_type='login',
            page_path='/login',
            action_detail='User logged in',
            ip_address=ip_address,
            user_agent=user_agent
        )
    except Exception:
        pass


def log_logout(user_id, db, ip_address=None):
    """Log logout event"""
    try:
        from utils.user_manager import UserManager
        um = UserManager(db)
        um.log_activity(
            user_id=user_id,
            activity_type='logout',
            page_path='/logout',
            action_detail='User logged out',
            ip_address=ip_address
        )
    except Exception:
        pass


def log_action(user_id, activity_type, detail, db, ip_address=None):
    """Log a specific action"""
    try:
        from utils.user_manager import UserManager
        um = UserManager(db)
        um.log_activity(
            user_id=user_id,
            activity_type=activity_type,
            action_detail=detail,
            ip_address=ip_address
        )
    except Exception:
        pass