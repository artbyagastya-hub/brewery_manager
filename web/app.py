"""
Brewery Manager - Flask Web Application
Web interface for comprehensive brewery management in Vietnam
"""

import sys
import os
import json
import secrets
from datetime import datetime, date
from functools import wraps
from typing import Dict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session, g
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_talisman import Talisman
from models.database import Database
from utils.i18n import get_i18n, format_currency as i18n_format_currency
from utils.tax import get_tax_calculator
from utils.auth import get_auth_manager
from utils.backup import get_backup_manager
from utils.rest_api import get_rest_api, api_auth_required
from utils.websocket_manager import get_ws_manager
from utils.traceability import get_traceability_manager
from utils.mimo_engine import get_engine
from utils.ai_tools import get_tools, execute_tool
from utils.ai_prompts import get_system_prompt
from functools import wraps

def login_required(f):
    """Login required decorator"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login to access this page', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

app = Flask(__name__)

# Security Configuration
app.secret_key = os.environ.get('SECRET_KEY', secrets.token_hex(32))
# Only set Secure flag if actually behind HTTPS
is_https = os.environ.get('FLASK_FORCE_HTTPS', 'false').lower() == 'true'
app.config['SESSION_COOKIE_SECURE'] = is_https
app.config['SESSION_COOKIE_HTTPONLY'] = True
# 'None' requires Secure=True; for HTTP use 'Lax'
app.config['SESSION_COOKIE_SAMESITE'] = 'None' if is_https else 'Lax'
app.config['PERMANENT_SESSION_LIFETIME'] = 86400  # 24 hours

# Initialize CSRF protection
csrf = CSRFProtect(app)

# Initialize HTTPS enforcement (Talisman)
csp = {
    'default-src': "'self'",
    'script-src': "'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com https://cdn.socket.io",
    'style-src': "'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com https://fonts.googleapis.com",
    'font-src': "'self' https://fonts.gstatic.com https://cdnjs.cloudflare.com",
    'img-src': "'self' data: https:",
    'connect-src': "'self' ws: wss: https://cdn.jsdelivr.net https://cdn.socket.io",
    'map-src': "'self' https://cdn.jsdelivr.net"
}

talisman = Talisman(
    app,
    force_https=False,
    session_cookie_secure=False,
    content_security_policy=csp,
    referrer_policy='strict-origin-when-cross-origin'
)

# Initialize rate limiter
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["5000 per day", "500 per hour"],
    storage_uri="memory://"
)

db = Database()
i18n = get_i18n()
tax_calc = get_tax_calculator()
auth = get_auth_manager(db)
backup_mgr = get_backup_manager()
ws_manager = get_ws_manager(app)


def format_currency(value):
    """Format number as Vietnamese Dong"""
    if value is None:
        return "0"
    lang = session.get('language', 'vi')
    return i18n_format_currency(value, lang)


def srm_to_hex(srm):
    """Convert SRM color value to hex color code for beer color visualization"""
    if srm is None:
        return "#FFFFFF"
    
    try:
        srm = float(srm)
    except (ValueError, TypeError):
        return "#FFFFFF"
    
    # SRM to RGB conversion based on Morey's approximation
    # Red channel
    if srm <= 0:
        r = 255
    elif srm <= 10:
        r = 255
    elif srm <= 20:
        r = 255 - (srm - 10) * 5.1
    elif srm <= 30:
        r = 204 - (srm - 20) * 5.1
    elif srm <= 40:
        r = 153 - (srm - 30) * 5.1
    else:
        r = max(0, 102 - (srm - 40) * 2.55)
    
    # Green channel
    if srm <= 0:
        g = 255
    elif srm <= 10:
        g = 255 - srm * 2.55
    elif srm <= 20:
        g = 229.5 - (srm - 10) * 12.75
    elif srm <= 30:
        g = 102 - (srm - 20) * 7.65
    elif srm <= 40:
        g = 25.5 - (srm - 30) * 2.55
    else:
        g = 0
    
    # Blue channel
    if srm <= 0:
        b = 255
    elif srm <= 10:
        b = 255 - srm * 25.5
    elif srm <= 20:
        b = 0
    elif srm <= 30:
        b = 0
    elif srm <= 40:
        b = (srm - 30) * 2.55
    else:
        b = min(255, 25.5 + (srm - 40) * 5.1)
    
    # Clamp values
    r = max(0, min(255, int(r)))
    g = max(0, min(255, int(g)))
    b = max(0, min(255, int(b)))
    
    return f"#{r:02x}{g:02x}{b:02x}"


app.jinja_env.filters['currency'] = format_currency
app.jinja_env.filters['srm_to_hex'] = srm_to_hex


@app.before_request
def ensure_session_permanent():
    """Ensure session is marked as permanent on every request for mobile persistence"""
    if 'user_id' in session:
        session.permanent = True


@app.context_processor
def inject_language():
    """Inject language and translation function into all templates"""
    lang = session.get('language', 'vi')
    def translate(key, default=None, **kwargs):
        result = i18n.get(key, lang, **kwargs)
        if result == key and default:
            return default
        return result
    
    # Get unread notification count for logged-in users
    unread_notifications = 0
    if 'user_id' in session:
        try:
            unread_notifications = db.get_unread_notification_count(session['user_id'])
        except:
            pass
    
    return {
        'current_language': lang,
        'available_languages': i18n.get_available_languages(),
        't': translate,
        'unread_notifications': unread_notifications
    }


@app.route('/language/<lang_code>')
def set_language(lang_code):
    """Set language preference"""
    if lang_code in i18n.SUPPORTED_LANGUAGES:
        session['language'] = lang_code
    return redirect(request.referrer or url_for('dashboard'))


# ==================== AUTHENTICATION ====================

@csrf.exempt
@app.route('/login', methods=['GET', 'POST'])
@limiter.limit("30 per minute")
def login():
    """Login page"""
    # If already logged in, redirect to dashboard
    if 'user_id' in session:
        return redirect(url_for('dashboard'))

    # Generate CSRF token for the form
    from flask_wtf.csrf import generate_csrf
    csrf_token = generate_csrf()

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        if not username or not password:
            flash('Please enter both username and password', 'error')
            return render_template('login.html', lang=session.get('language', 'vi'), csrf_token=csrf_token)

        # Authenticate user
        user = auth.authenticate(username, password)

        if user:
            # Set session
            session.permanent = True  # Make session persist across requests
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['user_role'] = user['role']
            session['user_full_name'] = user.get('full_name', username)

            # Log audit
            ip_address = request.remote_addr
            user_agent = request.headers.get('User-Agent', '')
            auth.log_login(user['id'], ip_address, user_agent)

            flash(f'Welcome back, {user.get("full_name", username)}!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password', 'error')

    return render_template('login.html', lang=session.get('language', 'vi'))


@app.route('/logout')
def logout():
    """Logout user"""
    user_id = session.get('user_id')
    if user_id:
        auth.log_logout(user_id)

    session.clear()
    flash('You have been logged out', 'info')
    return redirect(url_for('login'))


@app.route('/profile')
def profile():
    """User profile page"""
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user = db.get_user_by_id(session['user_id'])
    if not user:
        session.clear()
        return redirect(url_for('login'))

    return render_template('profile.html', user=user)


@app.route('/profile/password', methods=['POST'])
def change_password():
    """Change user password"""
    if 'user_id' not in session:
        return redirect(url_for('login'))

    current_password = request.form.get('current_password', '')
    new_password = request.form.get('new_password', '')
    confirm_password = request.form.get('confirm_password', '')

    if not current_password or not new_password:
        flash('Please fill in all fields', 'error')
        return redirect(url_for('profile'))

    if new_password != confirm_password:
        flash('New passwords do not match', 'error')
        return redirect(url_for('profile'))

    if len(new_password) < 6:
        flash('Password must be at least 6 characters', 'error')
        return redirect(url_for('profile'))

    # Verify current password
    user = db.get_user_by_id(session['user_id'])
    if not auth.verify_password(current_password, user['password_hash']):
        flash('Current password is incorrect', 'error')
        return redirect(url_for('profile'))

    # Update password
    new_hash = auth.hash_password(new_password)
    db.update_user_password(session['user_id'], new_hash)

    flash('Password updated successfully', 'success')
    return redirect(url_for('profile'))


# ==================== PASSWORD RESET ====================

@app.route('/forgot-password', methods=['GET', 'POST'])
@csrf.exempt
@limiter.limit("10 per minute")
def forgot_password():
    """Forgot password page"""
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        if not email:
            flash('Please enter your email address', 'error')
            return render_template('forgot_password.html')

        from utils.user_manager import UserManager
        um = UserManager(db)
        success, result = um.generate_reset_token(email)

        if success:
            # In production, send email with reset link
            # For now, show the token (dev only)
            flash(f'Password reset link sent to {email}. (Dev: token={result})', 'success')
        else:
            flash(result, 'error')

        return redirect(url_for('login'))

    return render_template('forgot_password.html')


@app.route('/reset-password/<token>', methods=['GET', 'POST'])
@csrf.exempt
def reset_password(token):
    """Reset password with token"""
    if request.method == 'POST':
        password = request.form.get('password', '')
        confirm = request.form.get('confirm_password', '')

        if not password or not confirm:
            flash('Please fill in all fields', 'error')
            return render_template('reset_password.html', token=token)

        if password != confirm:
            flash('Passwords do not match', 'error')
            return render_template('reset_password.html', token=token)

        if len(password) < 8:
            flash('Password must be at least 8 characters', 'error')
            return render_template('reset_password.html', token=token)

        from utils.user_manager import UserManager
        um = UserManager(db)
        success, msg = um.reset_password_with_token(token, password)

        if success:
            flash('Password reset successfully. Please login.', 'success')
            return redirect(url_for('login'))
        else:
            flash(msg, 'error')
            return render_template('reset_password.html', token=token)

    return render_template('reset_password.html', token=token)


# ==================== USER MANAGEMENT ====================

@app.route('/users')
@login_required
def users():
    """User management page (admin/manager only)"""
    user_role = session.get('user_role', 'viewer')
    if user_role not in ['admin', 'manager']:
        flash('Access denied. Admin/Manager role required.', 'error')
        return redirect(url_for('dashboard'))

    from utils.user_manager import UserManager
    um = UserManager(db)

    role_filter = request.args.get('role')
    team_filter = request.args.get('team_id')

    users_list = um.get_users(
        role=role_filter,
        team_id=int(team_filter) if team_filter else None
    )
    teams = um.get_teams()
    stats = um.get_user_stats()

    return render_template('users.html',
                         users=users_list,
                         teams=teams,
                         stats=stats,
                         role_filter=role_filter,
                         team_filter=team_filter)


@app.route('/users/add', methods=['GET', 'POST'])
@login_required
def add_user():
    """Add new user (admin only)"""
    user_role = session.get('user_role', 'viewer')
    if user_role != 'admin':
        flash('Access denied. Admin role required.', 'error')
        return redirect(url_for('dashboard'))

    from utils.user_manager import UserManager
    um = UserManager(db)

    if request.method == 'POST':
        data = {
            'username': request.form.get('username', '').strip(),
            'email': request.form.get('email', '').strip(),
            'full_name': request.form.get('full_name', '').strip(),
            'password': request.form.get('password') or None,
            'role': request.form.get('role', 'viewer'),
            'phone': request.form.get('phone'),
            'department': request.form.get('department'),
            'team_id': int(request.form['team_id']) if request.form.get('team_id') else None
        }

        if not data['username'] or not data['email']:
            flash('Username and email are required', 'error')
            return render_template('add_user.html', teams=um.get_teams())

        user_id, result = um.create_user(data)
        if user_id:
            temp_password = result
            flash(f'User created successfully!', 'success')
            if temp_password:
                flash(f'Temporary password: {temp_password}', 'warning')
            return redirect(url_for('users'))
        else:
            flash(f'Error: {result}', 'error')
            return render_template('add_user.html', teams=um.get_teams())

    teams = um.get_teams()
    return render_template('add_user.html', teams=teams)


@app.route('/users/<int:user_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_user(user_id):
    """Edit user (admin only)"""
    user_role = session.get('user_role', 'viewer')
    if user_role != 'admin':
        flash('Access denied. Admin role required.', 'error')
        return redirect(url_for('dashboard'))

    from utils.user_manager import UserManager
    um = UserManager(db)

    user = um.get_user(user_id)
    if not user:
        flash('User not found', 'error')
        return redirect(url_for('users'))

    if request.method == 'POST':
        data = {}
        for key in ['username', 'email', 'full_name', 'role', 'phone', 'department']:
            if request.form.get(key):
                data[key] = request.form[key].strip()

        if request.form.get('team_id'):
            data['team_id'] = int(request.form['team_id'])
        elif 'team_id' in request.form:
            data['team_id'] = None

        if request.form.get('is_active') is not None:
            data['is_active'] = 1 if request.form.get('is_active') == '1' else 0

        success, msg = um.update_user(user_id, data)
        if success:
            flash('User updated successfully', 'success')
            return redirect(url_for('users'))
        else:
            flash(f'Error: {msg}', 'error')

    teams = um.get_teams()
    return render_template('edit_user.html', user=user, teams=teams)


@app.route('/users/<int:user_id>/deactivate', methods=['POST'])
@login_required
def deactivate_user(user_id):
    """Deactivate user (admin only)"""
    user_role = session.get('user_role', 'viewer')
    if user_role != 'admin':
        flash('Access denied. Admin role required.', 'error')
        return redirect(url_for('dashboard'))

    # Prevent self-deactivation
    if user_id == session.get('user_id'):
        flash('Cannot deactivate your own account', 'error')
        return redirect(url_for('users'))

    from utils.user_manager import UserManager
    um = UserManager(db)
    success, msg = um.deactivate_user(user_id)
    flash(msg, 'success' if success else 'error')
    return redirect(url_for('users'))


@app.route('/users/<int:user_id>/reset-password', methods=['POST'])
@login_required
def admin_reset_user_password(user_id):
    """Admin reset user password"""
    user_role = session.get('user_role', 'viewer')
    if user_role != 'admin':
        flash('Access denied. Admin role required.', 'error')
        return redirect(url_for('dashboard'))

    from utils.user_manager import UserManager
    um = UserManager(db)
    success, temp_password = um.admin_reset_password(user_id)
    if success:
        flash(f'Password reset. Temporary password: {temp_password}', 'warning')
    else:
        flash('Failed to reset password', 'error')
    return redirect(url_for('edit_user', user_id=user_id))


@app.route('/users/<int:user_id>/permissions', methods=['GET', 'POST'])
@login_required
def user_permissions(user_id):
    """Manage user permissions (admin only)"""
    user_role = session.get('user_role', 'viewer')
    if user_role != 'admin':
        flash('Access denied. Admin role required.', 'error')
        return redirect(url_for('dashboard'))

    from utils.user_manager import UserManager
    um = UserManager(db)

    user = um.get_user(user_id)
    if not user:
        flash('User not found', 'error')
        return redirect(url_for('users'))

    if request.method == 'POST':
        # Get all permissions from DB
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, name FROM permissions")
        all_perms = cursor.fetchall()
        conn.close()

        # Set each permission based on form
        for perm in all_perms:
            granted = request.form.get(f'perm_{perm["id"]}') == '1'
            um.set_user_permission(user_id, perm['id'], granted)

        flash('Permissions updated', 'success')
        return redirect(url_for('users'))

    # Get current permissions
    current_perms = um.get_user_permissions(user_id)

    # Get all available permissions
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM permissions ORDER BY module, name")
    all_permissions = [dict(row) for row in cursor.fetchall()]
    conn.close()

    return render_template('user_permissions.html',
                         user=user,
                         all_permissions=all_permissions,
                         current_perms=current_perms)


@app.route('/users/activity')
@login_required
def user_activity():
    """View user activity log (admin/manager only)"""
    user_role = session.get('user_role', 'viewer')
    if user_role not in ['admin', 'manager']:
        flash('Access denied. Admin/Manager role required.', 'error')
        return redirect(url_for('dashboard'))

    from utils.user_manager import UserManager
    um = UserManager(db)

    user_id_filter = request.args.get('user_id', type=int)
    activity_type = request.args.get('activity_type')
    limit = request.args.get('limit', 100, type=int)

    activities = um.get_user_activity(
        user_id=user_id_filter,
        activity_type=activity_type,
        limit=limit
    )
    users_list = um.get_users()

    return render_template('user_activity.html',
                         activities=activities,
                         users=users_list,
                         user_id_filter=user_id_filter,
                         activity_type=activity_type)


# ==================== TEAMS ====================

@app.route('/teams')
@login_required
def teams():
    """Teams management"""
    user_role = session.get('user_role', 'viewer')
    if user_role not in ['admin', 'manager']:
        flash('Access denied. Admin/Manager role required.', 'error')
        return redirect(url_for('dashboard'))

    from utils.user_manager import UserManager
    um = UserManager(db)
    teams_list = um.get_teams(active_only=False)
    return render_template('teams.html', teams=teams_list)


@app.route('/teams/add', methods=['GET', 'POST'])
@login_required
def add_team():
    """Add new team"""
    user_role = session.get('user_role', 'viewer')
    if user_role not in ['admin', 'manager']:
        flash('Access denied. Admin/Manager role required.', 'error')
        return redirect(url_for('dashboard'))

    from utils.user_manager import UserManager
    um = UserManager(db)

    if request.method == 'POST':
        data = {
            'name': request.form.get('name', '').strip(),
            'description': request.form.get('description', '').strip(),
            'team_lead_id': int(request.form['team_lead_id']) if request.form.get('team_lead_id') else None
        }

        if not data['name']:
            flash('Team name is required', 'error')
            return render_template('add_team.html', users=um.get_users())

        team_id = um.create_team(data)
        flash('Team created successfully', 'success')
        return redirect(url_for('teams'))

    users_list = um.get_users()
    return render_template('add_team.html', users=users_list)


@app.route('/teams/<int:team_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_team(team_id):
    """Edit team"""
    user_role = session.get('user_role', 'viewer')
    if user_role not in ['admin', 'manager']:
        flash('Access denied. Admin/Manager role required.', 'error')
        return redirect(url_for('dashboard'))

    from utils.user_manager import UserManager
    um = UserManager(db)

    team = um.get_team(team_id)
    if not team:
        flash('Team not found', 'error')
        return redirect(url_for('teams'))

    if request.method == 'POST':
        data = {}
        if request.form.get('name'):
            data['name'] = request.form['name'].strip()
        if request.form.get('description') is not None:
            data['description'] = request.form['description'].strip()
        if request.form.get('team_lead_id'):
            data['team_lead_id'] = int(request.form['team_lead_id'])

        um.update_team(team_id, data)
        flash('Team updated successfully', 'success')
        return redirect(url_for('teams'))

    users_list = um.get_users()
    return render_template('edit_team.html', team=team, users=users_list)


@app.route('/teams/<int:team_id>/members', methods=['POST'])
@login_required
def manage_team_members(team_id):
    """Add/remove team members"""
    user_role = session.get('user_role', 'viewer')
    if user_role not in ['admin', 'manager']:
        return jsonify({'error': 'Access denied'}), 403

    from utils.user_manager import UserManager
    um = UserManager(db)

    action = request.form.get('action')
    user_id = int(request.form.get('user_id', 0))

    if action == 'add':
        um.add_team_member(team_id, user_id)
        return jsonify({'success': True, 'message': 'Member added'})
    elif action == 'remove':
        um.remove_team_member(team_id, user_id)
        return jsonify({'success': True, 'message': 'Member removed'})

    return jsonify({'error': 'Invalid action'}), 400


# ==================== CHAT HISTORY ====================

@app.route('/users/<int:user_id>/chat-history')
@login_required
def user_chat_history(user_id):
    """View user's AI chat history (admin only)"""
    user_role = session.get('user_role', 'viewer')
    if user_role != 'admin':
        if user_id != session.get('user_id'):
            flash('Access denied', 'error')
            return redirect(url_for('dashboard'))

    from utils.user_manager import UserManager
    um = UserManager(db)

    user = um.get_user(user_id)
    if not user:
        flash('User not found', 'error')
        return redirect(url_for('users'))

    chat_history = um.get_user_chat_history(user_id)

    return render_template('user_chat_history.html',
                         user=user,
                         chat_history=chat_history)


# ==================== DASHBOARD ====================

@app.route('/')
def dashboard():
    """Main dashboard"""
    data = db.get_dashboard_data()
    low_stock = db.get_low_stock_alerts()
    expiring = db.get_expiring_materials(30)
    tank_assignments = db.get_tank_assignments()
    return render_template('dashboard.html', data=data, low_stock=low_stock, expiring=expiring, tanks=tank_assignments)


@app.route('/api/dashboard/live')
@login_required
def api_dashboard_live():
    """API endpoint for live dashboard updates"""
    try:
        data = db.get_dashboard_data()
        low_stock = db.get_low_stock_alerts()
        expiring = db.get_expiring_materials(30)
        tank_assignments = db.get_tank_assignments()
        
        return jsonify({
            'success': True,
            'data': {
                'monthly_revenue': data.get('monthly_revenue', 0),
                'monthly_expenses': data.get('monthly_expenses', 0),
                'monthly_profit': data.get('monthly_profit', 0),
                'pending_orders': data.get('pending_orders', 0),
                'active_batches': data.get('active_batches', 0),
                'total_customers': data.get('total_customers', 0),
                'total_products': data.get('total_products', 0),
                'total_staff': data.get('total_staff', 0),
                'planned_batches': data.get('planned_batches', 0),
                'brewing_batches': data.get('brewing_batches', 0),
                'fermenting_batches': data.get('fermenting_batches', 0),
                'completed_batches': data.get('completed_batches', 0),
                'low_stock': [{
                    'name': item['name'],
                    'quantity': item['quantity'],
                    'unit': item['unit'],
                    'min_quantity': item['min_quantity'],
                    'shortage': item['shortage']
                } for item in low_stock],
                'expiring': [{
                    'name': item['name'],
                    'expiry_date': item['expiry_date'],
                    'days_remaining': item['days_remaining'],
                    'quantity': item['quantity'],
                    'unit': item['unit']
                } for item in expiring],
                'tanks': [{
                    'id': tank['id'],
                    'name': tank['name'],
                    'capacity': tank['capacity'],
                    'status': tank['status'],
                    'batch_id': tank.get('batch_id'),
                    'product_name': tank.get('product_name'),
                    'batch_status': tank.get('batch_status'),
                    'start_date': tank.get('start_date')
                } for tank in tank_assignments]
            },
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ==================== INVENTORY ====================

@app.route('/inventory')
def inventory():
    """Inventory list"""
    category = request.args.get('category')
    low_stock = request.args.get('low_stock') == 'true'
    materials = db.get_raw_materials(category=category, low_stock=low_stock)
    return render_template('inventory.html', materials=materials, category=category, low_stock=low_stock)


@app.route('/inventory/add', methods=['GET', 'POST'])
def add_material():
    """Add raw material"""
    if request.method == 'POST':
        data = {
            'name': request.form['name'],
            'category': request.form['category'],
            'unit': request.form['unit'],
            'quantity': float(request.form.get('quantity', 0)),
            'min_quantity': float(request.form.get('min_quantity', 0)),
            'cost_per_unit': float(request.form.get('cost_per_unit', 0)),
            'supplier': request.form.get('supplier'),
            'origin': request.form.get('origin'),
            'expiry_date': request.form.get('expiry_date') or None,
            'storage_location': request.form.get('storage_location'),
            'notes': request.form.get('notes')
        }
        material_id = db.add_raw_material(data)
        
        # Broadcast inventory update
        ws_manager.emit_inventory_update({
            'action': 'add',
            'item': {'id': material_id, 'name': data['name'], 'category': data['category']},
            'user': session.get('user_full_name', 'System')
        })
        
        # Check for low stock and broadcast alert
        if data['quantity'] <= data['min_quantity']:
            ws_manager.emit_low_stock_alert({
                'material': {'id': material_id, 'name': data['name'], 
                           'quantity': data['quantity'], 'unit': data['unit']},
                'shortage': data['min_quantity'] - data['quantity']
            })
        
        flash(f'Material "{data["name"]}" added successfully!', 'success')
        return redirect(url_for('inventory'))
    return render_template('add_material.html')


@app.route('/inventory/<int:material_id>/edit', methods=['GET', 'POST'])
def edit_material(material_id):
    """Edit raw material"""
    materials = db.get_raw_materials()
    material = next((m for m in materials if m['id'] == material_id), None)
    if not material:
        flash('Material not found!', 'error')
        return redirect(url_for('inventory'))

    if request.method == 'POST':
        data = {}
        for key in ['name', 'category', 'unit', 'supplier', 'origin', 'storage_location', 'notes']:
            if request.form.get(key):
                data[key] = request.form[key]
        for key in ['quantity', 'min_quantity', 'cost_per_unit']:
            if request.form.get(key):
                data[key] = float(request.form[key])
        if request.form.get('expiry_date'):
            data['expiry_date'] = request.form['expiry_date']

        db.update_raw_material(material_id, data)
        
        # Broadcast inventory update
        ws_manager.emit_inventory_update({
            'action': 'update',
            'item': {'id': material_id, 'name': material.get('name', 'Unknown')},
            'user': session.get('user_full_name', 'System')
        })
        
        flash('Material updated successfully!', 'success')
        return redirect(url_for('inventory'))

    return render_template('edit_material.html', material=material)


@app.route('/inventory/<int:material_id>/adjust', methods=['POST'])
def adjust_stock(material_id):
    """Adjust stock quantity"""
    change = float(request.form['quantity_change'])
    reason = request.form.get('reason', '')
    
    # Get material info before adjustment
    materials = db.get_raw_materials()
    material = next((m for m in materials if m['id'] == material_id), None)
    
    db.adjust_inventory(material_id, change, reason)
    
    # Broadcast inventory update
    if material:
        ws_manager.emit_inventory_update({
            'action': 'adjust',
            'item': {'id': material_id, 'name': material['name'], 'change': change},
            'user': session.get('user_full_name', 'System')
        })
        
        # Check for low stock after adjustment
        updated_materials = db.get_raw_materials()
        updated = next((m for m in updated_materials if m['id'] == material_id), None)
        if updated and updated['quantity'] <= updated['min_quantity']:
            ws_manager.emit_low_stock_alert({
                'material': {'id': material_id, 'name': updated['name'], 
                           'quantity': updated['quantity'], 'unit': updated['unit']},
                'shortage': updated['min_quantity'] - updated['quantity']
            })
    
    flash('Stock adjusted successfully!', 'success')
    return redirect(url_for('inventory'))

@app.route('/inventory/export')
def export_inventory():
    """Export inventory to Excel"""
    import io
    from openpyxl import Workbook
    
    materials = db.get_raw_materials()
    
    wb = Workbook()
    ws = wb.active
    ws.title = "Inventory"
    
    # Headers
    headers = ['ID', 'Name', 'Category', 'Unit', 'Quantity', 'Min Quantity', 
               'Cost/Unit', 'Total Value', 'Supplier', 'Origin', 'Expiry Date', 
               'Storage Location', 'Status']
    ws.append(headers)
    
    # Data
    for m in materials:
        status = 'OK'
        if m['quantity'] <= 0:
            status = 'OUT OF STOCK'
        elif m['quantity'] <= m['min_quantity']:
            status = 'LOW STOCK'
        
        ws.append([
            m['id'], m['name'], m['category'], m['unit'],
            m['quantity'], m['min_quantity'], m['cost_per_unit'],
            m['quantity'] * m['cost_per_unit'], m.get('supplier', ''),
            m.get('origin', ''), m.get('expiry_date', ''),
            m.get('storage_location', ''), status
        ])
    
    # Auto-fit columns
    for column in ws.columns:
        max_length = 0
        column_letter = column[0].column_letter
        for cell in column:
            try:
                if len(str(cell.value)) > max_length:
                    max_length = len(str(cell.value))
            except:
                pass
        ws.column_dimensions[column_letter].width = min(max_length + 2, 50)
    
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    
    from flask import send_file
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=f'inventory_{date.today().isoformat()}.xlsx'
    )


# ==================== PRODUCTS ====================

@app.route('/products')
def products():
    """Products list"""
    products = db.get_products(active_only=False)
    return render_template('products.html', products=products)


@app.route('/products/add', methods=['GET', 'POST'])
def add_product():
    """Add product"""
    if request.method == 'POST':
        data = {
            'name': request.form['name'],
            'style': request.form.get('style'),
            'abv': float(request.form.get('abv', 0)),
            'ibu': int(request.form.get('ibu', 0)),
            'description': request.form.get('description'),
            'price_per_unit': float(request.form.get('price_per_unit', 0))
        }
        product_id = db.add_product(data)
        flash(f'Product "{data["name"]}" added successfully!', 'success')
        return redirect(url_for('products'))
    return render_template('add_product.html')


@app.route('/products/<int:product_id>/edit', methods=['GET', 'POST'])
def edit_product(product_id):
    """Edit product"""
    products = db.get_products(active_only=False)
    product = next((p for p in products if p['id'] == product_id), None)
    if not product:
        flash('Product not found!', 'error')
        return redirect(url_for('products'))

    if request.method == 'POST':
        data = {}
        for key in ['name', 'style', 'description']:
            if request.form.get(key):
                data[key] = request.form[key]
        for key in ['abv', 'ibu', 'price_per_unit']:
            if request.form.get(key):
                data[key] = float(request.form[key])

        db.update_product(product_id, data)
        flash('Product updated successfully!', 'success')
        return redirect(url_for('products'))

    return render_template('edit_product.html', product=product)


# ==================== PRODUCTION ====================

@app.route('/production')
def production():
    """Production batches"""
    status = request.args.get('status')
    batches = db.get_batches(status=status)
    return render_template('production.html', batches=batches, status=status)


@app.route('/production/add', methods=['GET', 'POST'])
def add_batch():
    """Create new batch"""
    if request.method == 'POST':
        data = {
            'product_id': int(request.form['product_id']),
            'tank_id': int(request.form['tank_id']) if request.form.get('tank_id') else None,
            'recipe_id': int(request.form['recipe_id']) if request.form.get('recipe_id') else None,
            'planned_quantity': float(request.form['volume_liters']),
            'start_date': request.form.get('start_date'),
            'end_date': request.form.get('end_date'),
            'status': request.form.get('status', 'planned'),
            'brewer_id': session.get('user_id'),
            'actual_abv': float(request.form['actual_abv']) if request.form.get('actual_abv') else None,
            'actual_ibu': int(request.form['actual_ibu']) if request.form.get('actual_ibu') else None,
            'notes': request.form.get('notes')
        }
        batch_id = db.create_batch(data)
        
        # Broadcast batch update
        ws_manager.emit_batch_update({
            'action': 'create',
            'batch_id': batch_id,
            'product_id': data['product_id'],
            'status': data['status'],
            'user': session.get('user_full_name', 'System')
        })
        
        flash('Batch created successfully!', 'success')
        return redirect(url_for('production'))

    products = db.get_products()
    staff = db.get_staff(department='brewing')
    tanks = db.get_equipment(equipment_type='fermenter')
    recipes = db.get_recipes(active_only=True)
    return render_template('add_batch.html', products=products, staff=staff, tanks=tanks, recipes=recipes)


@app.route('/production/<int:batch_id>/status', methods=['POST'])
def update_batch_status(batch_id):
    """Update batch status"""
    status = request.form['status']
    actual_qty = float(request.form['actual_quantity']) if request.form.get('actual_quantity') else None
    db.update_batch_status(batch_id, status, actual_qty)
    
    # Broadcast batch update
    ws_manager.emit_batch_update({
        'action': 'status_change',
        'batch_id': batch_id,
        'status': status,
        'user': session.get('user_full_name', 'System')
    })
    
    flash('Batch status updated!', 'success')
    return redirect(url_for('production'))


@app.route('/production/<int:batch_id>/ingredients', methods=['GET', 'POST'])
def batch_ingredients(batch_id):
    """Add batch ingredients"""
    if request.method == 'POST':
        ingredients = []
        i = 0
        while True:
            mat_id = request.form.get(f'material_id_{i}')
            if not mat_id:
                break
            ingredients.append({
                'material_id': int(mat_id),
                'quantity_used': float(request.form[f'quantity_{i}']),
                'cost_at_time': float(request.form.get(f'cost_{i}', 0))
            })
            i += 1

        if ingredients:
            db.add_batch_ingredients(batch_id, ingredients)
            flash(f'{len(ingredients)} ingredients added!', 'success')
        return redirect(url_for('production'))

    batches = db.get_batches()
    batch = next((b for b in batches if b['id'] == batch_id), None)
    materials = db.get_raw_materials()
    return render_template('batch_ingredients.html', batch=batch, materials=materials)


@app.route('/quality/add', methods=['GET', 'POST'])
def add_quality():
    """Add quality record"""
    if request.method == 'POST':
        data = {
            'batch_id': int(request.form['batch_id']),
            'check_type': request.form['check_type'],
            'value': float(request.form.get('value', 0)),
            'unit': request.form.get('unit'),
            'passed': 1 if request.form.get('passed') == '1' else 0,
            'inspector': request.form.get('inspector'),
            'notes': request.form.get('notes')
        }
        db.add_quality_record(data)
        flash('Quality record added!', 'success')
        return redirect(url_for('quality'))

    batches = db.get_batches()
    return render_template('add_quality.html', batches=batches)


@app.route('/quality')
def quality():
    """Quality records"""
    records = db.get_quality_records()
    return render_template('quality.html', records=records)


# ==================== CUSTOMERS ====================

@app.route('/customers')
def customers():
    """Customers list"""
    customers = db.get_customers(active_only=False)
    return render_template('customers.html', customers=customers)


@app.route('/customers/add', methods=['GET', 'POST'])
def add_customer():
    """Add customer"""
    if request.method == 'POST':
        data = {
            'name': request.form['name'],
            'type': request.form.get('type', 'retail'),
            'contact_person': request.form.get('contact_person'),
            'phone': request.form.get('phone'),
            'email': request.form.get('email'),
            'address': request.form.get('address'),
            'city': request.form.get('city'),
            'province': request.form.get('province'),
            'tax_id': request.form.get('tax_id'),
            'credit_limit': float(request.form.get('credit_limit', 0)),
            'payment_terms': request.form.get('payment_terms', 'COD'),
            'notes': request.form.get('notes')
        }
        customer_id = db.add_customer(data)
        flash(f'Customer "{data["name"]}" added!', 'success')
        return redirect(url_for('customers'))
    return render_template('add_customer.html')


@app.route('/customers/<int:customer_id>/edit', methods=['GET', 'POST'])
def edit_customer(customer_id):
    """Edit customer"""
    customers = db.get_customers(active_only=False)
    customer = next((c for c in customers if c['id'] == customer_id), None)
    if not customer:
        flash('Customer not found!', 'error')
        return redirect(url_for('customers'))

    if request.method == 'POST':
        data = {}
        for key in ['name', 'type', 'contact_person', 'phone', 'email', 'address', 'city', 'province', 'tax_id', 'payment_terms', 'notes']:
            if request.form.get(key):
                data[key] = request.form[key]
        if request.form.get('credit_limit'):
            data['credit_limit'] = float(request.form['credit_limit'])

        db.update_customer(customer_id, data)
        flash('Customer updated!', 'success')
        return redirect(url_for('customers'))

    return render_template('edit_customer.html', customer=customer)


@app.route('/customers/top')
def top_customers():
    """Top customers"""
    customers = db.get_top_customers(20)
    return render_template('top_customers.html', customers=customers)


# ==================== SALES ====================

@app.route('/sales')
def sales():
    """Sales orders"""
    status = request.args.get('status')
    orders = db.get_sales_orders(status=status)
    return render_template('sales.html', orders=orders, status=status)


@app.route('/sales/add', methods=['GET', 'POST'])
def add_order():
    """Create sales order"""
    if request.method == 'POST':
        items = []
        i = 0
        while True:
            prod_id = request.form.get(f'product_id_{i}')
            if not prod_id:
                break
            items.append({
                'product_id': int(prod_id),
                'quantity': float(request.form[f'quantity_{i}']),
                'unit_price': float(request.form[f'price_{i}']),
                'discount': float(request.form.get(f'discount_{i}', 0))
            })
            i += 1

        if not items:
            flash('Please add at least one item!', 'error')
            return redirect(url_for('add_order'))

        data = {
            'customer_id': int(request.form['customer_id']),
            'order_date': request.form['order_date'],
            'delivery_date': request.form.get('delivery_date') or None,
            'notes': request.form.get('notes'),
            'items': items
        }
        order_id = db.create_sales_order(data)
        
        # Broadcast order update
        ws_manager.emit_order_update({
            'action': 'create',
            'order_id': order_id,
            'customer_id': data['customer_id'],
            'status': 'pending',
            'user': session.get('user_full_name', 'System')
        })
        
        flash('Order created successfully!', 'success')
        return redirect(url_for('sales'))

    customers = db.get_customers()
    products = db.get_products()
    return render_template('add_order.html', customers=customers, products=products)


@app.route('/sales/<int:order_id>')
def order_detail(order_id):
    """Order details"""
    order = db.get_order_details(order_id)
    if not order:
        flash('Order not found', 'error')
        return redirect(url_for('sales'))
    return render_template('order_detail.html', order=order)


@app.route('/sales/<int:order_id>/status', methods=['POST'])
def update_order_status(order_id):
    """Update order status"""
    status = request.form['status']
    db.update_order_status(order_id, status)
    
    # Broadcast order update
    ws_manager.emit_order_update({
        'action': 'status_change',
        'order_id': order_id,
        'status': status,
        'user': session.get('user_full_name', 'System')
    })
    
    flash('Order status updated!', 'success')
    return redirect(url_for('order_detail', order_id=order_id))


@app.route('/sales/<int:order_id>/payment', methods=['POST'])
def update_payment(order_id):
    """Update payment status"""
    status = request.form['payment_status']
    db.update_payment_status(order_id, status)
    
    # Broadcast order update
    ws_manager.emit_order_update({
        'action': 'payment_update',
        'order_id': order_id,
        'payment_status': status,
        'user': session.get('user_full_name', 'System')
    })
    
    flash('Payment status updated!', 'success')
    return redirect(url_for('order_detail', order_id=order_id))


# ==================== FINANCE ====================

@app.route('/finance')
def finance():
    """Financial overview"""
    type_filter = request.args.get('type')
    summary = db.get_financial_summary()
    transactions = db.get_transactions(type_filter=type_filter)
    return render_template('finance.html', summary=summary, transactions=transactions, type=type_filter)


@app.route('/finance/transactions')
def transactions():
    """View transactions"""
    start = request.args.get('start_date')
    end = request.args.get('end_date')
    ttype = request.args.get('type')
    transactions = db.get_transactions(start, end, ttype)
    return render_template('transactions.html', transactions=transactions, start=start, end=end, type=ttype)


@app.route('/finance/add', methods=['GET', 'POST'])
def add_transaction():
    """Add transaction"""
    if request.method == 'POST':
        data = {
            'transaction_date': request.form['transaction_date'],
            'type': request.form['type'],
            'category': request.form['category'],
            'amount': float(request.form['amount']),
            'description': request.form.get('description'),
            'payment_method': request.form.get('payment_method')
        }
        db.add_transaction(data)
        flash('Transaction added!', 'success')
        return redirect(url_for('finance'))
    return render_template('add_transaction.html')


@app.route('/finance/production-report')
def production_report():
    """Production report"""
    start = request.args.get('start_date')
    end = request.args.get('end_date')
    report = db.get_production_report(start, end)
    return render_template('production_report.html', report=report, start=start, end=end)


@app.route('/finance/sales-report')
def sales_report():
    """Sales report"""
    start = request.args.get('start_date')
    end = request.args.get('end_date')
    report = db.get_sales_report(start, end)
    return render_template('sales_report.html', report=report, start=start, end=end)


# ==================== ACCOUNTING ====================

@app.route('/accounting')
def accounting():
    """Accounting overview"""
    invoices = db.get_invoices()
    tax_report = db.get_tax_report()
    return render_template('accounting.html', invoices=invoices, tax_report=tax_report)


@app.route('/accounting/invoice/create', methods=['GET', 'POST'])
def create_invoice():
    """Create invoice"""
    if request.method == 'POST':
        # Get form data
        customer_id = int(request.form['customer_id'])
        invoice_date = request.form['invoice_date']
        payment_method = request.form.get('payment_method', 'cash')
        notes = request.form.get('notes', '')
        
        # Collect items
        items = []
        i = 0
        while True:
            product_id = request.form.get(f'product_id_{i}')
            if not product_id:
                break
            items.append({
                'product_id': int(product_id),
                'quantity': float(request.form[f'quantity_{i}']),
                'unit_price': float(request.form[f'unit_price_{i}']),
                'unit': request.form.get(f'unit_{i}', 'chai')
            })
            i += 1
        
        if not items:
            flash('Please add at least one item!', 'error')
            return redirect(url_for('create_invoice'))
        
        # Calculate taxes
        tax_result = tax_calc.calculate_invoice_totals(items)
        
        # Create invoice
        invoice_data = {
            'customer_id': customer_id,
            'invoice_date': invoice_date,
            'payment_method': payment_method,
            'notes': notes,
            'items': items,
            'subtotal': tax_result['subtotal'],
            'sct_amount': tax_result['sct_amount'],
            'vat_amount': tax_result['vat_amount'],
            'environmental_tax': tax_result['environmental_tax'],
            'total': tax_result['total']
        }
        
        invoice_id = db.create_invoice(invoice_data)
        flash('Invoice created successfully!', 'success')
        return redirect(url_for('view_invoice', invoice_id=invoice_id))
    
    # GET request
    customers = db.get_customers()
    products = db.get_products()
    next_number = db.get_next_invoice_number()
    from datetime import date
    today = date.today().isoformat()
    
    return render_template('invoice.html', 
                         customers=customers, 
                         products=products,
                         next_invoice_number=next_number,
                         today=today)


@app.route('/accounting/invoice/<int:invoice_id>')
def view_invoice(invoice_id):
    """View invoice"""
    invoice = db.get_invoice_details(invoice_id)
    return render_template('view_invoice.html', invoice=invoice)


@app.route('/accounting/tax-report')
def tax_report():
    """Tax report"""
    start = request.args.get('start_date')
    end = request.args.get('end_date')
    report = db.get_tax_report(start, end)
    return render_template('tax_report.html', report=report, start=start, end=end)


# ==================== ZALO MESSAGING ====================

@app.route('/zalo')
def zalo():
    """Zalo messaging dashboard"""
    messages = db.get_zalo_messages(limit=50)
    templates = db.get_zalo_templates()
    return render_template('zalo.html', messages=messages, templates=templates)


@app.route('/zalo/send', methods=['POST'])
def send_zalo_message():
    """Send Zalo message (demo mode)"""
    recipient = request.form.get('recipient')
    message = request.form.get('message')
    template_id = request.form.get('template_id')
    
    if template_id:
        templates = db.get_zalo_templates()
        template = next((t for t in templates if t['id'] == int(template_id)), None)
        if template:
            message = template['content']
    
    # Log message (demo mode - no actual sending)
    db.log_zalo_message(recipient, message, 'demo')
    flash('Message logged (Demo mode - no actual Zalo API)', 'info')
    return redirect(url_for('zalo'))


@app.route('/zalo/broadcast', methods=['POST'])
def broadcast_zalo():
    """Broadcast to all customers"""
    message = request.form.get('message')
    customers = db.get_customers()
    
    for customer in customers:
        if customer.get('phone'):
            db.log_zalo_message(customer['phone'], message, 'demo')
    
    flash(f'Broadcast sent to {len(customers)} customers (Demo mode)', 'info')
    return redirect(url_for('zalo'))


# ==================== SUPERVISION ====================

@app.route('/supervision')
def supervision():
    """Supervision dashboard - shift handover and SOPs"""
    today = date.today().isoformat()
    handovers = db.get_shift_handovers(limit=10)
    sops = db.get_sops()
    performance = db.get_performance_metrics()
    training = db.get_training_records()
    
    return render_template('supervision.html',
                         handovers=handovers,
                         sops=sops,
                         performance=performance,
                         training=training,
                         today=today)


@app.route('/supervision/handover/create', methods=['GET', 'POST'])
def create_handover():
    """Create shift handover"""
    if request.method == 'POST':
        data = {
            'shift_date': request.form['shift_date'],
            'shift_type': request.form['shift_type'],
            'from_staff_id': int(request.form['from_staff_id']),
            'to_staff_id': int(request.form['to_staff_id']) if request.form.get('to_staff_id') else None,
            'production_status': request.form.get('production_status'),
            'quality_notes': request.form.get('quality_notes'),
            'equipment_status': request.form.get('equipment_status'),
            'pending_tasks': request.form.get('pending_tasks'),
            'safety_notes': request.form.get('safety_notes'),
            'notes': request.form.get('notes')
        }
        db.create_shift_handover(data)
        flash('Shift handover created!', 'success')
        return redirect(url_for('supervision'))
    
    staff = db.get_staff()
    return render_template('create_handover.html', staff=staff)


@app.route('/supervision/sop/create', methods=['GET', 'POST'])
def create_sop():
    """Create SOP"""
    if request.method == 'POST':
        data = {
            'title': request.form['title'],
            'category': request.form['category'],
            'content': request.form['content'],
            'version': request.form.get('version', '1.0'),
            'created_by': int(request.form.get('created_by', 1))
        }
        db.create_sop(data)
        flash('SOP created!', 'success')
        return redirect(url_for('supervision'))
    
    return render_template('create_sop.html')


@app.route('/supervision/performance', methods=['GET', 'POST'])
def add_performance():
    """Add performance metrics"""
    if request.method == 'POST':
        data = {
            'metric_date': request.form['metric_date'],
            'category': request.form['category'],
            'metric_name': request.form['metric_name'],
            'value': float(request.form['value']),
            'unit': request.form.get('unit'),
            'target': float(request.form['target']) if request.form.get('target') else None,
            'notes': request.form.get('notes')
        }
        db.add_performance_metric(data)
        flash('Performance metric added!', 'success')
        return redirect(url_for('supervision'))
    
    return render_template('add_performance.html')


@app.route('/supervision/training', methods=['GET', 'POST'])
def add_training():
    """Add training record"""
    if request.method == 'POST':
        data = {
            'staff_id': int(request.form['staff_id']),
            'training_date': request.form['training_date'],
            'topic': request.form['topic'],
            'trainer': request.form.get('trainer'),
            'duration_hours': float(request.form.get('duration_hours', 0)),
            'result': request.form.get('result'),
            'certificate_number': request.form.get('certificate_number'),
            'notes': request.form.get('notes')
        }
        db.add_training_record(data)
        flash('Training record added!', 'success')
        return redirect(url_for('supervision'))
    
    staff = db.get_staff()
    return render_template('add_training.html', staff=staff)


# ==================== STAFF ====================

@app.route('/staff')
def staff():
    """Staff list"""
    department = request.args.get('department')
    staff = db.get_staff(department=department, active_only=False)
    return render_template('staff.html', staff=staff, department=department)


@app.route('/staff/add', methods=['GET', 'POST'])
def add_staff():
    """Add staff"""
    if request.method == 'POST':
        data = {
            'name': request.form['name'],
            'position': request.form['position'],
            'department': request.form.get('department'),
            'phone': request.form.get('phone'),
            'email': request.form.get('email'),
            'hire_date': request.form.get('hire_date') or None,
            'salary': float(request.form.get('salary', 0)),
            'emergency_contact': request.form.get('emergency_contact'),
            'notes': request.form.get('notes')
        }
        staff_id = db.add_staff(data)
        flash(f'Staff member "{data["name"]}" added!', 'success')
        return redirect(url_for('staff'))
    return render_template('add_staff.html')


@app.route('/staff/<int:staff_id>/edit', methods=['GET', 'POST'])
def edit_staff(staff_id):
    """Edit staff"""
    staff_list = db.get_staff(active_only=False)
    staff_member = next((s for s in staff_list if s['id'] == staff_id), None)
    if not staff_member:
        flash('Staff not found!', 'error')
        return redirect(url_for('staff'))

    if request.method == 'POST':
        data = {}
        for key in ['name', 'position', 'department', 'phone', 'email', 'emergency_contact', 'notes']:
            if request.form.get(key):
                data[key] = request.form[key]
        if request.form.get('salary'):
            data['salary'] = float(request.form['salary'])

        db.update_staff(staff_id, data)
        flash('Staff updated!', 'success')
        return redirect(url_for('staff'))

    return render_template('edit_staff.html', staff=staff_member)


@app.route('/staff/schedule')
def schedule():
    """Staff schedule"""
    schedule_date = request.args.get('date', date.today().isoformat())
    schedule = db.get_schedule(date=schedule_date)
    return render_template('schedule.html', schedule=schedule, schedule_date=schedule_date)


@app.route('/staff/schedule/add', methods=['GET', 'POST'])
def add_schedule():
    """Add schedule"""
    if request.method == 'POST':
        data = {
            'staff_id': int(request.form['staff_id']),
            'schedule_date': request.form['schedule_date'],
            'shift': request.form['shift'],
            'start_time': request.form.get('start_time'),
            'end_time': request.form.get('end_time'),
            'notes': request.form.get('notes')
        }
        db.add_schedule(data)
        flash('Schedule added!', 'success')
        return redirect(url_for('schedule'))

    staff = db.get_staff()
    return render_template('add_schedule.html', staff=staff)


# ==================== EQUIPMENT ====================

@app.route('/equipment')
def equipment():
    """Equipment overview"""
    eq_type = request.args.get('type')
    equipment_list = db.get_equipment(equipment_type=eq_type)
    tank_assignments = db.get_tank_assignments()
    return render_template('equipment.html', equipment=equipment_list, tanks=tank_assignments, type=eq_type)


@app.route('/equipment/tanks')
def tanks():
    """Tank assignments view"""
    tank_assignments = db.get_tank_assignments()
    return render_template('tanks.html', tanks=tank_assignments)


@app.route('/equipment/<int:equipment_id>/clean', methods=['POST'])
def clean_equipment(equipment_id):
    """Mark equipment as cleaned"""
    db.mark_tank_cleaned(equipment_id)
    flash('Equipment marked as cleaned!', 'success')
    return redirect(url_for('equipment'))


@app.route('/equipment/<int:equipment_id>/status', methods=['POST'])
def update_equipment_status_route(equipment_id):
    """Update equipment status"""
    status = request.form['status']
    db.update_equipment_status(equipment_id, status)
    flash('Equipment status updated!', 'success')
    return redirect(url_for('equipment'))


# ==================== MAINTENANCE ====================

@app.route('/maintenance')
def maintenance():
    """Maintenance schedule"""
    status = request.args.get('status')
    schedule = db.get_maintenance_schedule(status=status)
    overdue = db.get_overdue_maintenance()
    return render_template('maintenance.html', schedule=schedule, overdue=overdue, status=status, now=datetime.now())


@app.route('/maintenance/<int:maintenance_id>/complete', methods=['POST'])
def complete_maintenance_route(maintenance_id):
    """Complete maintenance task"""
    notes = request.form.get('notes')
    db.complete_maintenance(maintenance_id, notes)
    flash('Maintenance task completed!', 'success')
    return redirect(url_for('maintenance'))


# ==================== DAILY BRIEFINGS ====================

@app.route('/briefings')
def briefings():
    """Daily briefings and tasks"""
    task_date = request.args.get('date', date.today().isoformat())
    tasks = db.get_daily_tasks(task_date=task_date)
    briefing = db.generate_daily_briefing(task_date)
    return render_template('briefings.html', tasks=tasks, briefing=briefing, task_date=task_date)


@app.route('/briefings/add-task', methods=['GET', 'POST'])
def add_daily_task():
    """Add daily task"""
    if request.method == 'POST':
        data = {
            'task_date': request.form['task_date'],
            'task_type': request.form['task_type'],
            'title': request.form['title'],
            'description': request.form.get('description'),
            'assigned_to': int(request.form['assigned_to']) if request.form.get('assigned_to') else None,
            'priority': request.form.get('priority', 'normal'),
            'notes': request.form.get('notes')
        }
        db.create_daily_task(data)
        flash('Task added!', 'success')
        return redirect(url_for('briefings', date=data['task_date']))

    staff = db.get_staff()
    task_date = request.args.get('date', date.today().isoformat())
    return render_template('add_task.html', staff=staff, task_date=task_date)


@app.route('/briefings/<int:task_id>/complete', methods=['POST'])
def complete_task(task_id):
    """Complete a daily task"""
    completed_by = int(request.form.get('completed_by', 1))
    notes = request.form.get('notes')
    db.complete_daily_task(task_id, completed_by, notes)
    flash('Task completed!', 'success')
    return redirect(url_for('briefings'))


@app.route('/briefings/send', methods=['POST'])
def send_briefing():
    """Send daily briefing via Zalo"""
    task_date = request.form.get('task_date', date.today().isoformat())
    briefing = db.generate_daily_briefing(task_date)

    # Format briefing message
    message = format_briefing_message(briefing)

    # Log the briefing
    db.log_briefing(task_date, 'morning', message)

    flash('Briefing logged! (Zalo integration requires API key)', 'info')
    return redirect(url_for('briefings', date=task_date))


def format_briefing_message(briefing: Dict) -> str:
    """Format briefing as a message"""
    lines = [
        f"🍺 DAILY BRIEFING - {briefing['date']}",
        "=" * 40,
        "",
        f"📋 Tasks: {briefing['summary']['pending_tasks']} pending / {briefing['summary']['completed_tasks']} completed",
        f"🏭 Tanks in use: {briefing['summary']['tanks_in_use']}",
        f"⚠️ Low stock alerts: {briefing['summary']['low_stock_count']}",
        f"🔧 Overdue maintenance: {briefing['summary']['overdue_maintenance_count']}",
        ""
    ]

    if briefing['tasks']:
        lines.append("📋 TODAY'S TASKS:")
        for task in briefing['tasks']:
            status_icon = "✅" if task['status'] == 'completed' else "⏳"
            lines.append(f"  {status_icon} [{task['priority'].upper()}] {task['title']}")
            if task.get('assigned_to_name'):
                lines.append(f"     → Assigned to: {task['assigned_to_name']}")
        lines.append("")

    if briefing['overdue_maintenance']:
        lines.append("🔧 OVERDUE MAINTENANCE:")
        for item in briefing['overdue_maintenance']:
            lines.append(f"  ⚠️ {item['equipment_name']}: {item['task_name']}")
        lines.append("")

    if briefing['tank_status']:
        lines.append("🏭 TANK STATUS:")
        for tank in briefing['tank_status']:
            if tank['batch_id']:
                lines.append(f"  🔴 {tank['name']}: {tank['product_name']} ({tank['batch_status']})")
            else:
                lines.append(f"  🟢 {tank['name']}: Available")
        lines.append("")

    if briefing['low_stock_alerts']:
        lines.append("⚠️ LOW STOCK ALERTS:")
        for item in briefing['low_stock_alerts']:
            lines.append(f"  ⚠️ {item['name']}: {item['quantity']} {item['unit']} (need {item['shortage']} more)")
        lines.append("")

    return "\n".join(lines)


# ==================== AGENT & ANALYTICS ====================

@app.route('/analytics')
def analytics():
    """Analytics dashboard with agent status"""
    from utils.agent import get_agent
    from utils.scheduler import get_scheduler_status
    
    agent = get_agent(db)
    agent_status = agent.get_agent_status()
    scheduler_status = get_scheduler_status()
    dashboard = db.get_dashboard_data()
    
    # Get monthly data for charts from actual data range
    from datetime import datetime, timedelta
    conn = db.get_connection()
    cursor = conn.cursor()
    
    # Get the most recent 6 months that have data
    cursor.execute("""
        SELECT strftime('%Y-%m', transaction_date) as month,
               SUM(CASE WHEN type = 'income' THEN amount ELSE 0 END) as revenue,
               SUM(CASE WHEN type = 'expense' THEN amount ELSE 0 END) as expenses
        FROM financial_transactions
        GROUP BY strftime('%Y-%m', transaction_date)
        ORDER BY month DESC
        LIMIT 6
    """)
    trend_rows = cursor.fetchall()
    trend_rows.reverse()  # chronological order
    
    if trend_rows:
        months = [row['month'] for row in trend_rows]
        revenues = [row['revenue'] for row in trend_rows]
        expenses = [row['expenses'] for row in trend_rows]
    else:
        months = []
        revenues = []
        expenses = []
    
    # Get batch status for pie chart
    cursor.execute("SELECT status, COUNT(*) as cnt FROM production_batches GROUP BY status")
    status_counts = {row['status']: row['cnt'] for row in cursor.fetchall()}
    batch_labels = ['Planning', 'Brewing', 'Fermenting', 'Completed']
    batch_counts = [
        status_counts.get('planned', 0),
        status_counts.get('brewing', 0),
        status_counts.get('fermenting', 0),
        status_counts.get('completed', 0)
    ]
    conn.close()
    
    return render_template('analytics.html',
                         agent_status=agent_status,
                         scheduler_status=scheduler_status,
                         dashboard=dashboard,
                         months=months,
                         revenues=revenues,
                         expenses=expenses,
                         batch_labels=batch_labels,
                         batch_counts=batch_counts)


@app.route('/notifications')
def notifications():
    """User notifications page"""
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))
    
    notifications = db.get_notifications(user_id=user_id)
    unread_count = db.get_unread_notification_count(user_id)
    
    return render_template('notifications.html',
                         notifications=notifications,
                         unread_count=unread_count)


@app.route('/notifications/<int:notification_id>/read', methods=['POST'])
def mark_notification_read(notification_id):
    """Mark notification as read"""
    db.mark_notification_read(notification_id)
    return redirect(url_for('notifications'))


@app.route('/notifications/mark-all-read', methods=['POST'])
def mark_all_notifications_read():
    """Mark all notifications as read"""
    user_id = session.get('user_id')
    if user_id:
        db.mark_all_notifications_read(user_id)
    return redirect(url_for('notifications'))


@app.route('/agent/logs')
def agent_logs():
    """Agent activity logs"""
    category = request.args.get('category')
    logs = db.get_agent_logs(category=category, limit=100)
    return render_template('agent_logs.html', logs=logs, category_filter=category)


@app.route('/agent/rules')
def agent_rules():
    """Agent rules management"""
    from utils.agent import get_agent
    agent = get_agent(db)
    status = agent.get_agent_status()
    return render_template('agent_rules.html', rules_by_category=status['rules_by_category'])


@app.route('/agent/rules/<int:rule_id>/toggle', methods=['POST'])
def toggle_agent_rule(rule_id):
    """Toggle agent rule enabled/disabled"""
    db.toggle_agent_rule(rule_id)
    flash('Rule updated!', 'success')
    return redirect(url_for('agent_rules'))


# ==================== API ENDPOINTS ====================



@app.route('/api/materials')
@limiter.limit("30 per minute")
def api_materials():
    """API: Raw materials"""
    category = request.args.get('category')
    return jsonify(db.get_raw_materials(category=category))


@app.route('/api/products')
@limiter.limit("30 per minute")
def api_products():
    """API: Products"""
    return jsonify(db.get_products())


@app.route('/api/batches')
@limiter.limit("30 per minute")
def api_batches():
    """API: Production batches"""
    status = request.args.get('status')
    return jsonify(db.get_batches(status=status))


@app.route('/api/orders')
@limiter.limit("30 per minute")
def api_orders():
    """API: Sales orders"""
    status = request.args.get('status')
    return jsonify(db.get_sales_orders(status=status))


@app.route('/api/customers')
@limiter.limit("30 per minute")
def api_customers():
    """API: Customers"""
    return jsonify(db.get_customers())


@app.route('/api/finance/summary')
@limiter.limit("20 per minute")
def api_finance_summary():
    """API: Financial summary"""
    start = request.args.get('start_date')
    end = request.args.get('end_date')
    return jsonify(db.get_financial_summary(start, end))


@app.route('/api/alerts/low-stock')
@limiter.limit("10 per minute")
def api_low_stock():
    """API: Low stock alerts"""
    return jsonify(db.get_low_stock_alerts())


@app.route('/api/alerts/expiring')
@limiter.limit("10 per minute")
def api_expiring():
    """API: Expiring materials"""
    days = int(request.args.get('days', 30))
    return jsonify(db.get_expiring_materials(days))


# ==================== RECIPES ====================

@app.route('/recipes')
@login_required
def recipes():
    """Recipe list page"""
    recipes_list = db.get_recipes(active_only=False)
    return render_template('recipes.html', recipes=recipes_list)


@app.route('/recipes/import', methods=['GET', 'POST'])
@login_required
def import_recipes():
    """Import recipes from BeerSmith .bsmx file"""
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file selected', 'error')
            return redirect(request.url)
        
        file = request.files['file']
        if file.filename == '':
            flash('No file selected', 'error')
            return redirect(request.url)
        
        if not file.filename.endswith('.bsmx'):
            flash('Please upload a .bsmx file', 'error')
            return redirect(request.url)
        
        try:
            from utils.beersmith_import import BeerSmithParser, validate_recipe
            import tempfile
            import os
            
            # Save uploaded file temporarily
            with tempfile.NamedTemporaryFile(delete=False, suffix='.bsmx') as tmp:
                file.save(tmp.name)
                tmp_path = tmp.name
            
            try:
                # Parse the file
                parser = BeerSmithParser()
                recipes = parser.parse_file(tmp_path)
                
                imported_count = 0
                errors = []
                
                for recipe_data in recipes:
                    # Import recipe to database (even if incomplete)
                    try:
                        # Use style as name if no name provided
                        if not recipe_data.get('name'):
                            recipe_data['name'] = recipe_data.get('style', 'Unnamed Recipe')
                        db_data = {
                            'name': recipe_data.get('name'),
                            'style': recipe_data.get('style'),
                            'batch_size': recipe_data.get('batch_size', 20),
                            'batch_size_unit': 'L',
                            'boil_time': int(recipe_data.get('boil_time', 60)),
                            'efficiency': recipe_data.get('efficiency', 75),
                            'og': recipe_data.get('target_og'),
                            'fg': recipe_data.get('target_fg'),
                            'abv': recipe_data.get('target_abv'),
                            'ibu': recipe_data.get('target_ibu'),
                            'srm': recipe_data.get('target_srm'),
                            'notes': recipe_data.get('notes', ''),
                            'created_by': None  # No staff association for imported recipes
                        }
                        
                        recipe_id = db.create_recipe(db_data)
                        
                        # Add fermentables
                        for fermentable in recipe_data.get('fermentables', []):
                            db.add_recipe_ingredient(recipe_id, {
                                'ingredient_type': 'fermentable',
                                'name': fermentable.get('name'),
                                'amount': fermentable.get('amount_kg', 0),
                                'unit': 'kg',
                                'notes': fermentable.get('notes', '')
                            })
                        
                        # Add hops
                        for hop in recipe_data.get('hops', []):
                            db.add_recipe_ingredient(recipe_id, {
                                'ingredient_type': 'hop',
                                'name': hop.get('name'),
                                'amount': hop.get('amount_kg', 0) * 1000,  # Convert to grams
                                'unit': 'g',
                                'use_time': hop.get('boil_time_min', 0),
                                'notes': hop.get('notes', '')
                            })
                        
                        # Add yeasts
                        for yeast in recipe_data.get('yeasts', []):
                            db.add_recipe_ingredient(recipe_id, {
                                'ingredient_type': 'yeast',
                                'name': yeast.get('name'),
                                'amount': 1,
                                'unit': 'unit',
                                'notes': f"{yeast.get('lab', '')} - {yeast.get('product_id', '')}"
                            })
                        
                        imported_count += 1
                    except Exception as e:
                        errors.append(f"{recipe_data.get('name', 'Unknown')}: {str(e)}")
                
                # Clean up temp file
                os.unlink(tmp_path)
                
                if imported_count > 0:
                    flash(f'Successfully imported {imported_count} recipes', 'success')
                
                if errors:
                    for error in errors[:5]:  # Show first 5 errors
                        flash(error, 'warning')
                    if len(errors) > 5:
                        flash(f'And {len(errors)-5} more errors...', 'warning')
                
                return redirect(url_for('recipes'))
                
            except Exception as e:
                os.unlink(tmp_path)
                raise e
                
        except Exception as e:
            flash(f'Error importing file: {str(e)}', 'error')
            return redirect(request.url)
    
    return render_template('import_recipes.html')


@app.route('/recipes/add', methods=['GET', 'POST'])
@login_required
def add_recipe():
    """Add new recipe"""
    if request.method == 'POST':
        data = {
            'name': request.form.get('name'),
            'product_id': request.form.get('product_id', type=int) or None,
            'style': request.form.get('style'),
            'batch_size': request.form.get('batch_size', 20, type=float),
            'batch_size_unit': request.form.get('batch_size_unit', 'L'),
            'boil_time': request.form.get('boil_time', 60, type=int),
            'efficiency': request.form.get('efficiency', 75, type=float),
            'og': request.form.get('og', type=float) or None,
            'fg': request.form.get('fg', type=float) or None,
            'abv': request.form.get('abv', type=float) or None,
            'ibu': request.form.get('ibu', type=float) or None,
            'srm': request.form.get('srm', type=float) or None,
            'description': request.form.get('description'),
            'notes': request.form.get('notes'),
            'created_by': session.get('user_id')
        }
        recipe_id = db.create_recipe(data)
        flash('Recipe added successfully!', 'success')
        return redirect(url_for('recipe_details', recipe_id=recipe_id))
    
    products = db.get_products()
    return render_template('add_recipe.html', products=products)


@app.route('/recipes/<int:recipe_id>')
@login_required
def recipe_details(recipe_id):
    """Recipe details page"""
    recipe = db.get_recipe_details(recipe_id)
    if not recipe:
        flash('Recipe not found', 'error')
        return redirect(url_for('recipes'))
    return render_template('recipe_details.html', recipe=recipe)


@app.route('/recipes/<int:recipe_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_recipe(recipe_id):
    """Edit recipe"""
    recipe = db.get_recipe_details(recipe_id)
    if not recipe:
        flash('Recipe not found', 'error')
        return redirect(url_for('recipes'))
    
    if request.method == 'POST':
        data = {
            'name': request.form.get('name'),
            'product_id': request.form.get('product_id', type=int) or None,
            'style': request.form.get('style'),
            'batch_size': request.form.get('batch_size', type=float),
            'batch_size_unit': request.form.get('batch_size_unit', 'L'),
            'boil_time': request.form.get('boil_time', type=int),
            'efficiency': request.form.get('efficiency', type=float),
            'og': request.form.get('og', type=float) or None,
            'fg': request.form.get('fg', type=float) or None,
            'abv': request.form.get('abv', type=float) or None,
            'ibu': request.form.get('ibu', type=float) or None,
            'srm': request.form.get('srm', type=float) or None,
            'description': request.form.get('description'),
            'notes': request.form.get('notes')
        }
        db.update_recipe(recipe_id, data)
        flash('Recipe updated successfully!', 'success')
        return redirect(url_for('recipe_details', recipe_id=recipe_id))
    
    products = db.get_products()
    return render_template('edit_recipe.html', recipe=recipe, products=products)


@app.route('/recipes/<int:recipe_id>/delete', methods=['POST'])
@login_required
def delete_recipe(recipe_id):
    """Delete recipe"""
    recipe = db.get_recipe_details(recipe_id)
    if not recipe:
        flash('Recipe not found', 'error')
        return redirect(url_for('recipes'))
    
    db.delete_recipe(recipe_id)
    flash('Recipe deleted successfully!', 'success')
    return redirect(url_for('recipes'))


@app.route('/recipes/<int:recipe_id>/add-fermentable', methods=['POST'])
@login_required
def add_recipe_fermentable(recipe_id):
    """Add fermentable to recipe"""
    data = {
        'recipe_id': recipe_id,
        'material_id': request.form.get('material_id', type=int) or None,
        'name': request.form.get('name'),
        'amount': request.form.get('amount', type=float),
        'unit': request.form.get('unit', 'kg'),
        'percentage': request.form.get('percentage', 0, type=float),
        'potential': request.form.get('potential', 0, type=float),
        'color': request.form.get('color', 0, type=float),
        'notes': request.form.get('notes')
    }
    db.add_recipe_fermentable(data)
    flash('Fermentable added!', 'success')
    return redirect(url_for('edit_recipe', recipe_id=recipe_id))


@app.route('/recipes/<int:recipe_id>/add-hop', methods=['POST'])
@login_required
def add_recipe_hop(recipe_id):
    """Add hop to recipe"""
    data = {
        'recipe_id': recipe_id,
        'material_id': request.form.get('material_id', type=int) or None,
        'name': request.form.get('name'),
        'amount': request.form.get('amount', type=float),
        'unit': request.form.get('unit', 'g'),
        'alpha_acid': request.form.get('alpha_acid', 0, type=float),
        'boil_time': request.form.get('boil_time', 60, type=int),
        'use_type': request.form.get('use_type', 'boil'),
        'notes': request.form.get('notes')
    }
    db.add_recipe_hop(data)
    flash('Hop added!', 'success')
    return redirect(url_for('edit_recipe', recipe_id=recipe_id))


@app.route('/recipes/<int:recipe_id>/add-yeast', methods=['POST'])
@login_required
def add_recipe_yeast(recipe_id):
    """Add yeast to recipe"""
    data = {
        'recipe_id': recipe_id,
        'yeast_id': request.form.get('yeast_id', type=int) or None,
        'name': request.form.get('name'),
        'lab': request.form.get('lab'),
        'product_id': request.form.get('product_id'),
        'form': request.form.get('form', 'liquid'),
        'attenuation': request.form.get('attenuation', 75, type=float),
        'min_temp': request.form.get('min_temp', 18, type=float),
        'max_temp': request.form.get('max_temp', 22, type=float),
        'notes': request.form.get('notes')
    }
    db.add_recipe_yeast(data)
    flash('Yeast added!', 'success')
    return redirect(url_for('edit_recipe', recipe_id=recipe_id))


@app.route('/recipes/<int:recipe_id>/add-mash-step', methods=['POST'])
@login_required
def add_recipe_mash_step(recipe_id):
    """Add mash step to recipe"""
    data = {
        'recipe_id': recipe_id,
        'step_number': request.form.get('step_number', type=int),
        'name': request.form.get('name'),
        'step_type': request.form.get('step_type', 'temperature'),
        'temperature': request.form.get('temperature', type=float),
        'duration': request.form.get('duration', type=int),
        'notes': request.form.get('notes')
    }
    db.add_recipe_mash_step(data)
    flash('Mash step added!', 'success')
    return redirect(url_for('edit_recipe', recipe_id=recipe_id))


@app.route('/recipes/<int:recipe_id>/calculate', methods=['POST'])
@login_required
def calculate_recipe(recipe_id):
    """Calculate recipe stats"""
    from utils.recipe_calculator import calculate_recipe_stats
    
    recipe = db.get_recipe_details(recipe_id)
    if not recipe:
        return jsonify({'error': 'Recipe not found'}), 404
    
    stats = calculate_recipe_stats(recipe)
    return jsonify(stats)


# ==================== YEAST MANAGEMENT ====================

@app.route('/yeast')
@login_required
def yeast_strains():
    """Yeast strains list page"""
    strains = db.get_yeast_strains(active_only=False)
    return render_template('yeast.html', strains=strains)


@app.route('/yeast/add', methods=['GET', 'POST'])
@login_required
def add_yeast_strain():
    """Add new yeast strain"""
    if request.method == 'POST':
        data = {
            'name': request.form.get('name'),
            'lab': request.form.get('lab'),
            'product_id': request.form.get('product_id'),
            'yeast_type': request.form.get('yeast_type', 'ale'),
            'form': request.form.get('form', 'liquid'),
            'attenuation_min': request.form.get('attenuation_min', 70, type=float),
            'attenuation_max': request.form.get('attenuation_max', 80, type=float),
            'flocculation': request.form.get('flocculation', 'medium'),
            'min_temp': request.form.get('min_temp', 18, type=float),
            'max_temp': request.form.get('max_temp', 22, type=float),
            'alcohol_tolerance': request.form.get('alcohol_tolerance', 10, type=float),
            'description': request.form.get('description'),
            'notes': request.form.get('notes')
        }
        db.add_yeast_strain(data)
        flash('Yeast strain added!', 'success')
        return redirect(url_for('yeast_strains'))
    
    return render_template('add_yeast.html')


@app.route('/yeast/inventory')
@login_required
def yeast_inventory():
    """Yeast inventory page"""
    inventory = db.get_yeast_inventory()
    return render_template('yeast_inventory.html', inventory=inventory)


@app.route('/yeast/inventory/add', methods=['POST'])
@login_required
def add_yeast_inventory():
    """Add yeast to inventory"""
    data = {
        'yeast_id': request.form.get('yeast_id', type=int),
        'lot_number': request.form.get('lot_number'),
        'quantity': request.form.get('quantity', 0, type=float),
        'unit': request.form.get('unit', 'packs'),
        'viability': request.form.get('viability', 100, type=float),
        'manufacture_date': request.form.get('manufacture_date'),
        'expiry_date': request.form.get('expiry_date'),
        'storage_location': request.form.get('storage_location'),
        'notes': request.form.get('notes')
    }
    db.add_yeast_inventory(data)
    flash('Yeast added to inventory!', 'success')
    return redirect(url_for('yeast_inventory'))


@app.route('/yeast/usage')
@login_required
def yeast_usage():
    """Yeast usage log page"""
    usage_log = db.get_yeast_usage_log()
    return render_template('yeast_usage.html', usage_log=usage_log)


@app.route('/yeast/usage/log', methods=['POST'])
@login_required
def log_yeast_usage():
    """Log yeast usage"""
    data = {
        'yeast_id': request.form.get('yeast_id', type=int),
        'batch_id': request.form.get('batch_id', type=int) or None,
        'generation': request.form.get('generation', 1, type=int),
        'quantity_used': request.form.get('quantity_used', type=float),
        'unit': request.form.get('unit', 'mL'),
        'source': request.form.get('source', 'new'),
        'viability': request.form.get('viability', type=float),
        'notes': request.form.get('notes')
    }
    db.log_yeast_usage(data)
    flash('Yeast usage logged!', 'success')
    return redirect(url_for('yeast_usage'))


@app.route('/yeast/calculate-pitch', methods=['POST'])
@login_required
def calculate_pitch_rate():
    """Calculate yeast pitch rate"""
    from utils.recipe_calculator import YeastCalculator
    
    batch_size = request.form.get('batch_size', 20, type=float)
    og = request.form.get('og', 1.050, type=float)
    yeast_type = request.form.get('yeast_type', 'ale')
    
    result = YeastCalculator.calculate_pitch_rate(batch_size, og, yeast_type)
    return jsonify(result)


# ==================== LOT TRACKING ====================

@app.route('/lots')
@login_required
def lots():
    """Lot tracking page"""
    item_type = request.args.get('type')
    status = request.args.get('status')
    lots_list = db.get_lots(item_type=item_type, status=status)
    return render_template('lots.html', lots=lots_list, type=item_type, status=status)


@app.route('/lots/receive', methods=['GET', 'POST'])
@login_required
def receive_lot():
    """Receive materials with lot tracking"""
    if request.method == 'POST':
        data = {
            'material_id': request.form.get('material_id', type=int),
            'item_type': 'raw_material',
            'quantity': request.form.get('quantity', type=float),
            'unit': request.form.get('unit'),
            'received_date': request.form.get('received_date'),
            'expiry_date': request.form.get('expiry_date') or None,
            'supplier': request.form.get('supplier'),
            'supplier_lot': request.form.get('supplier_lot'),
            'storage_location': request.form.get('storage_location'),
            'notes': request.form.get('notes')
        }
        lot_id = db.create_lot(data)
        
        # Also update raw material quantity
        if data['material_id']:
            db.adjust_inventory(data['material_id'], data['quantity'])
        
        flash('Lot received successfully!', 'success')
        return redirect(url_for('lots'))
    
    materials = db.get_raw_materials()
    return render_template('receive_lot.html', materials=materials)


@app.route('/lots/<int:lot_id>')
@login_required
def lot_details(lot_id):
    """Lot details with traceability"""
    lot = db.get_lot_by_id(lot_id)
    if not lot:
        flash('Lot not found', 'error')
        return redirect(url_for('lots'))
    
    # Get traceability info
    forward_trace = db.trace_lot_forward(lot_id)
    backward_trace = db.trace_lot_backward(lot_id)
    
    return render_template('lot_details.html', lot=lot, 
                         forward_trace=forward_trace, backward_trace=backward_trace)


@app.route('/lots/<int:lot_id>/status', methods=['POST'])
@login_required
def update_lot_status_route(lot_id):
    """Update lot status"""
    status = request.form.get('status')
    db.update_lot_status(lot_id, status)
    flash('Lot status updated!', 'success')
    return redirect(url_for('lot_details', lot_id=lot_id))


# ==================== BATCH COGS ====================

@app.route('/production/<int:batch_id>/cogs')
@login_required
def batch_cogs(batch_id):
    """Batch COGS page"""
    batches = db.get_batches()
    batch = next((b for b in batches if b['id'] == batch_id), None)
    if not batch:
        flash('Batch not found', 'error')
        return redirect(url_for('production'))
    
    cogs_items = db.get_batch_cogs(batch_id)
    cogs_summary = db.get_batch_cogs_summary(batch_id)
    
    return render_template('batch_cogs.html', batch=batch, 
                         cogs_items=cogs_items, cogs_summary=cogs_summary)


@app.route('/production/<int:batch_id>/cogs/add', methods=['POST'])
@login_required
def add_batch_cogs(batch_id):
    """Add COGS item to batch"""
    data = {
        'batch_id': batch_id,
        'category': request.form.get('category'),
        'item_name': request.form.get('item_name'),
        'planned_cost': request.form.get('planned_cost', 0, type=float),
        'actual_cost': request.form.get('actual_cost', 0, type=float),
        'notes': request.form.get('notes')
    }
    db.add_batch_cogs_item(data)
    flash('COGS item added!', 'success')
    return redirect(url_for('batch_cogs', batch_id=batch_id))


@app.route('/production/<int:batch_id>/cogs/calculate', methods=['POST'])
@login_required
def calculate_batch_cogs(batch_id):
    """Auto-calculate COGS from ingredients"""
    db.calculate_batch_cogs_from_ingredients(batch_id)
    flash('COGS calculated from ingredients!', 'success')
    return redirect(url_for('batch_cogs', batch_id=batch_id))


# ==================== FINISHED GOODS LOTS ====================

@app.route('/finished-goods')
@login_required
def finished_goods():
    """Finished goods inventory page"""
    product_id = request.args.get('product_id', type=int)
    status = request.args.get('status')
    fg_lots = db.get_finished_goods_lots(product_id=product_id, status=status)
    products = db.get_products()
    return render_template('finished_goods.html', fg_lots=fg_lots, products=products, 
                         product_id=product_id, status=status)


@app.route('/production/<int:batch_id>/complete', methods=['GET', 'POST'])
@login_required
def complete_batch(batch_id):
    """Complete batch and create finished goods lot"""
    batches = db.get_batches()
    batch = next((b for b in batches if b['id'] == batch_id), None)
    if not batch:
        flash('Batch not found', 'error')
        return redirect(url_for('production'))
    
    if request.method == 'POST':
        actual_qty = request.form.get('actual_quantity', type=float)
        
        # Update batch status
        db.update_batch_status(batch_id, 'completed', actual_qty)
        
        # Create finished goods lot
        fg_data = {
            'batch_id': batch_id,
            'product_id': batch['product_id'],
            'quantity_produced': actual_qty,
            'production_date': request.form.get('completion_date', date.today().isoformat()),
            'expiry_date': request.form.get('expiry_date'),
            'abv': request.form.get('abv', type=float),
            'ibu': request.form.get('ibu', type=float),
            'ph': request.form.get('ph', type=float),
            'notes': request.form.get('notes')
        }
        fg_lot_id = db.create_finished_goods_lot(fg_data)
        
        # Auto-calculate COGS
        db.calculate_batch_cogs_from_ingredients(batch_id)
        
        flash('Batch completed and FG lot created!', 'success')
        return redirect(url_for('finished_goods'))
    
    return render_template('complete_batch.html', batch=batch)


# ==================== INVENTORY VALUE REPORT ====================

@app.route('/reports/inventory-value')
@login_required
def inventory_value_report():
    """Inventory value report with lot details"""
    report = db.get_inventory_value_report()
    
    # Transform data for template compatibility
    raw_materials = report.get('raw_material_lots', [])
    finished_goods = report.get('finished_goods_lots', [])
    
    # Get WIP batches (fermenting and conditioning)
    all_batches = db.get_batches()
    wip_batches = [b for b in all_batches if b.get('status') in ('fermenting', 'conditioning')]
    for batch in wip_batches:
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT SUM(actual_cost) FROM batch_costs WHERE batch_id = ?", (batch['id'],))
        result = cursor.fetchone()
        batch['total_cost'] = result[0] if result[0] else 0
        conn.close()
    
    summary = {
        'raw_materials': {
            'total_value': report.get('raw_material_total', 0),
            'item_count': len(raw_materials)
        },
        'finished_goods': {
            'total_value': report.get('finished_goods_total', 0),
            'item_count': len(finished_goods)
        },
        'work_in_progress': {
            'total_value': sum(b.get('total_cost', 0) for b in wip_batches),
            'item_count': len(wip_batches)
        },
        'total_value': report.get('grand_total', 0) + sum(b.get('total_cost', 0) for b in wip_batches)
    }
    
    return render_template('inventory_value_report.html', 
                         summary=summary,
                         raw_materials=raw_materials,
                         finished_goods=finished_goods,
                         work_in_progress=wip_batches)


# ==================== BACKUP MANAGEMENT ====================

@app.route('/backup')
@login_required
def backup():
    """Backup management page"""
    backup_info = backup_mgr.get_backup_info()
    db_stats = backup_mgr._get_db_stats()
    return render_template('backup.html', backup_info=backup_info, db_stats=db_stats)


@app.route('/backup/create', methods=['POST'])
@login_required
def create_backup():
    """Create a new backup"""
    compress = request.form.get('compress', 'true') == 'true'
    result = backup_mgr.create_backup(compress=compress)
    
    if result['success']:
        flash(f'Backup created: {result["backup_name"]} ({result["backup_size_mb"]} MB)', 'success')
    else:
        flash(f'Backup failed: {result["error"]}', 'error')
    
    return redirect(url_for('backup'))


@app.route('/backup/restore/<filename>', methods=['POST'])
@login_required
def restore_backup(filename):
    """Restore from a backup"""
    result = backup_mgr.restore_backup(filename)
    
    if result['success']:
        flash(f'Database restored from {filename}. Pre-restore backup: {result["pre_restore_backup"]}', 'success')
    else:
        flash(f'Restore failed: {result["error"]}', 'error')
    
    return redirect(url_for('backup'))


@app.route('/backup/download/<filename>')
@login_required
def download_backup(filename):
    """Download a backup file"""
    from flask import send_file
    
    backup_path = os.path.join(backup_mgr.backup_dir, filename)
    
    if not os.path.exists(backup_path):
        flash('Backup file not found', 'error')
        return redirect(url_for('backup'))
    
    return send_file(backup_path, as_attachment=True, download_name=filename)


@app.route('/backup/delete/<filename>', methods=['POST'])
@login_required
def delete_backup(filename):
    """Delete a backup"""
    result = backup_mgr.delete_backup(filename)
    
    if result['success']:
        flash(f'Backup deleted: {filename}', 'success')
    else:
        flash(f'Delete failed: {result["error"]}', 'error')
    
    return redirect(url_for('backup'))


@app.route('/backup/cleanup', methods=['POST'])
@login_required
def cleanup_backups():
    """Clean up old backups"""
    keep_count = int(request.form.get('keep_count', 10))
    result = backup_mgr.cleanup_old_backups(keep_count=keep_count)
    
    if result['success']:
        flash(f'Cleanup complete: deleted {result["deleted_count"]} old backups, kept {result["kept_count"]}', 'success')
    else:
        flash(f'Cleanup failed: {result["error"]}', 'error')
    
    return redirect(url_for('backup'))


@app.route('/backup/export', methods=['POST'])
@login_required
def export_database():
    """Export database to JSON"""
    result = backup_mgr.export_to_json()
    
    if result['success']:
        flash(f'Database exported: {result["export_name"]} ({result["export_size_mb"]} MB, {result["tables_exported"]} tables)', 'success')
    else:
        flash(f'Export failed: {result["error"]}', 'error')
    
    return redirect(url_for('backup'))


# ==================== REST API ====================

@app.route('/api/v1/dashboard', methods=['GET'])
@api_auth_required('read')
def api_v1_dashboard():
    """GET /api/v1/dashboard - Dashboard summary"""
    try:
        api = g.api
        data = api.get_dashboard()
        return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/v1/materials', methods=['GET'])
@api_auth_required('read')
def api_get_materials():
    """GET /api/v1/materials - List materials"""
    try:
        api = g.api
        data = api.get_materials(request.args)
        return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/v1/materials/<int:material_id>', methods=['GET'])
@api_auth_required('read')
def api_get_material(material_id):
    """GET /api/v1/materials/:id - Get material"""
    try:
        api = g.api
        data = api.get_material(material_id)
        if data:
            return jsonify(data)
        return jsonify({'error': 'Material not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/v1/materials', methods=['POST'])
@api_auth_required('write')
def api_create_material():
    """POST /api/v1/materials - Create material"""
    try:
        api = g.api
        data = api.create_material(request.json)
        return jsonify(data), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/v1/materials/<int:material_id>', methods=['PUT'])
@api_auth_required('write')
def api_update_material(material_id):
    """PUT /api/v1/materials/:id - Update material"""
    try:
        api = g.api
        success = api.update_material(material_id, request.json)
        if success:
            return jsonify({'success': True})
        return jsonify({'error': 'Update failed'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/v1/products', methods=['GET'])
@api_auth_required('read')
def api_get_products():
    """GET /api/v1/products - List products"""
    try:
        api = g.api
        data = api.get_products(request.args)
        return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/v1/products/<int:product_id>', methods=['GET'])
@api_auth_required('read')
def api_get_product(product_id):
    """GET /api/v1/products/:id - Get product"""
    try:
        api = g.api
        data = api.get_product(product_id)
        if data:
            return jsonify(data)
        return jsonify({'error': 'Product not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/v1/products', methods=['POST'])
@api_auth_required('write')
def api_create_product():
    """POST /api/v1/products - Create product"""
    try:
        api = g.api
        data = api.create_product(request.json)
        return jsonify(data), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/v1/batches', methods=['GET'])
@api_auth_required('read')
def api_get_batches():
    """GET /api/v1/batches - List batches"""
    try:
        api = g.api
        data = api.get_batches(request.args)
        return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/v1/batches/<int:batch_id>', methods=['GET'])
@api_auth_required('read')
def api_get_batch(batch_id):
    """GET /api/v1/batches/:id - Get batch"""
    try:
        api = g.api
        data = api.get_batch(batch_id)
        if data:
            return jsonify(data)
        return jsonify({'error': 'Batch not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/v1/batches', methods=['POST'])
@api_auth_required('write')
def api_create_batch():
    """POST /api/v1/batches - Create batch"""
    try:
        api = g.api
        data = api.create_batch(request.json)
        return jsonify(data), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/v1/batches/<int:batch_id>/status', methods=['PUT'])
@api_auth_required('write')
def api_update_batch_status(batch_id):
    """PUT /api/v1/batches/:id/status - Update batch status"""
    try:
        api = g.api
        success = api.update_batch_status(batch_id, request.json)
        if success:
            return jsonify({'success': True})
        return jsonify({'error': 'Update failed'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/v1/customers', methods=['GET'])
@api_auth_required('read')
def api_get_customers():
    """GET /api/v1/customers - List customers"""
    try:
        api = g.api
        data = api.get_customers(request.args)
        return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/v1/customers/<int:customer_id>', methods=['GET'])
@api_auth_required('read')
def api_get_customer(customer_id):
    """GET /api/v1/customers/:id - Get customer"""
    try:
        api = g.api
        data = api.get_customer(customer_id)
        if data:
            return jsonify(data)
        return jsonify({'error': 'Customer not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/v1/customers', methods=['POST'])
@api_auth_required('write')
def api_create_customer():
    """POST /api/v1/customers - Create customer"""
    try:
        api = g.api
        data = api.create_customer(request.json)
        return jsonify(data), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/v1/orders', methods=['GET'])
@api_auth_required('read')
def api_get_orders():
    """GET /api/v1/orders - List orders"""
    try:
        api = g.api
        data = api.get_orders(request.args)
        return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/v1/orders/<int:order_id>', methods=['GET'])
@api_auth_required('read')
def api_get_order(order_id):
    """GET /api/v1/orders/:id - Get order"""
    try:
        api = g.api
        data = api.get_order(order_id)
        if data:
            return jsonify(data)
        return jsonify({'error': 'Order not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/v1/orders', methods=['POST'])
@api_auth_required('write')
def api_create_order():
    """POST /api/v1/orders - Create order"""
    try:
        api = g.api
        data = api.create_order(request.json)
        return jsonify(data), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/v1/transactions', methods=['GET'])
@api_auth_required('read')
def api_get_transactions():
    """GET /api/v1/transactions - List transactions"""
    try:
        api = g.api
        data = api.get_transactions(request.args)
        return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/v1/transactions', methods=['POST'])
@api_auth_required('write')
def api_create_transaction():
    """POST /api/v1/transactions - Create transaction"""
    try:
        api = g.api
        data = api.create_transaction(request.json)
        return jsonify(data), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/v1/finance/summary', methods=['GET'])
@api_auth_required('read')
def api_financial_summary():
    """GET /api/v1/finance/summary - Financial summary"""
    try:
        api = g.api
        data = api.get_financial_summary(request.args)
        return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/v1/recipes', methods=['GET'])
@api_auth_required('read')
def api_get_recipes():
    """GET /api/v1/recipes - List recipes"""
    try:
        api = g.api
        data = api.get_recipes(request.args)
        return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/v1/recipes/<int:recipe_id>', methods=['GET'])
@api_auth_required('read')
def api_get_recipe(recipe_id):
    """GET /api/v1/recipes/:id - Get recipe"""
    try:
        api = g.api
        data = api.get_recipe(recipe_id)
        if data:
            return jsonify(data)
        return jsonify({'error': 'Recipe not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/v1/equipment', methods=['GET'])
@api_auth_required('read')
def api_get_equipment():
    """GET /api/v1/equipment - List equipment"""
    try:
        api = g.api
        data = api.get_equipment(request.args)
        return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/v1/tanks', methods=['GET'])
@api_auth_required('read')
def api_get_tanks():
    """GET /api/v1/tanks - List tanks"""
    try:
        api = g.api
        data = api.get_tanks(request.args)
        return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/v1/staff', methods=['GET'])
@api_auth_required('read')
def api_get_staff():
    """GET /api/v1/staff - List staff"""
    try:
        api = g.api
        data = api.get_staff(request.args)
        return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/v1/keys', methods=['GET'])
@login_required
def api_list_keys():
    """GET /api/v1/keys - List API keys"""
    try:
        keys = db.get_api_keys_by_user(session['user_id'])
        return jsonify({'keys': keys})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/v1/keys', methods=['POST'])
@login_required
def api_create_key():
    """POST /api/v1/keys - Create API key"""
    try:
        data = request.json or {}
        api = get_rest_api(db)
        result = api.generate_api_key(
            user_id=session['user_id'],
            name=data.get('name', 'API Key'),
            permissions=data.get('permissions', ['read'])
        )
        return jsonify(result), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/v1/keys/<int:key_id>', methods=['DELETE'])
@login_required
def api_delete_key(key_id):
    """DELETE /api/v1/keys/:id - Delete API key"""
    try:
        db.deactivate_api_key(key_id, session['user_id'])
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/docs')
def api_docs():
    """API Documentation page"""
    return render_template('api_docs.html')


# ==================== TRACEABILITY & COSTING ====================

@app.route('/traceability/lots')
@login_required
def traceability_lots():
    """Lot inventory management"""
    trace_mgr = get_traceability_manager(db)
    lots = trace_mgr.get_lot_inventory_report()
    return render_template('traceability/lots.html', lots=lots)


@app.route('/traceability/lots/receive', methods=['GET', 'POST'])
@login_required
def traceability_receive_lot():
    """Receive new material lot"""
    if request.method == 'POST':
        trace_mgr = get_traceability_manager(db)
        lot_data = {
            'material_id': int(request.form['material_id']),
            'supplier': request.form.get('supplier'),
            'quantity_received': float(request.form['quantity_received']),
            'unit': request.form['unit'],
            'cost_per_unit': float(request.form.get('cost_per_unit', 0)),
            'received_date': request.form.get('received_date', date.today().isoformat()),
            'expiry_date': request.form.get('expiry_date') or None,
            'certificate_of_analysis': request.form.get('certificate_of_analysis'),
            'storage_location': request.form.get('storage_location'),
            'notes': request.form.get('notes')
        }
        
        lot_id = trace_mgr.create_lot(lot_data)
        flash(f'Lot created successfully!', 'success')
        return redirect(url_for('traceability_lots'))
    
    materials = db.get_raw_materials()
    return render_template('traceability/receive_lot.html', materials=materials)


@app.route('/traceability/lots/<int:lot_id>')
@login_required
def traceability_lot_details(lot_id):
    """Lot details and usage history"""
    conn = db.get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT l.*, rm.name as material_name, rm.category
        FROM lots l
        JOIN raw_materials rm ON l.material_id = rm.id
        WHERE l.id = ?
    """, (lot_id,))
    lot = cursor.fetchone()
    
    if not lot:
        conn.close()
        flash('Lot not found', 'error')
        return redirect(url_for('traceability_lots'))
    
    # Get usage history
    cursor.execute("""
        SELECT lu.*, pb.batch_number, p.name as product_name, s.name as used_by_name
        FROM lot_usage lu
        LEFT JOIN production_batches pb ON lu.batch_id = pb.id
        LEFT JOIN products p ON pb.product_id = p.id
        LEFT JOIN staff s ON lu.used_by = s.id
        WHERE lu.lot_id = ?
        ORDER BY lu.used_date DESC
    """, (lot_id,))
    usage = cursor.fetchall()
    
    conn.close()
    
    return render_template('traceability/lot_details.html', lot=dict(lot), usage=[dict(u) for u in usage])


@app.route('/traceability/batch/<int:batch_id>/cogs')
@login_required
def traceability_batch_cogs(batch_id):
    """Batch COGS calculation"""
    trace_mgr = get_traceability_manager(db)
    try:
        cogs = trace_mgr.calculate_batch_cogs(batch_id)
        return render_template('traceability/batch_cogs.html', cogs=cogs)
    except ValueError as e:
        flash(str(e), 'error')
        return redirect(url_for('production'))


@app.route('/traceability/forward', methods=['GET', 'POST'])
@login_required
def forward_trace():
    """Forward traceability: Lot → Batches → Orders"""
    result = None
    if request.method == 'POST':
        lot_number = request.form.get('lot_number')
        if lot_number:
            trace_mgr = get_traceability_manager(db)
            try:
                result = trace_mgr.forward_trace(lot_number)
            except ValueError as e:
                flash(str(e), 'error')
    
    return render_template('traceability/forward_trace.html', result=result)


@app.route('/traceability/backward', methods=['GET', 'POST'])
@login_required
def backward_trace():
    """Backward traceability: Order → Batches → Lots"""
    result = None
    if request.method == 'POST':
        order_number = request.form.get('order_number')
        if order_number:
            trace_mgr = get_traceability_manager(db)
            try:
                result = trace_mgr.backward_trace(order_number)
            except ValueError as e:
                flash(str(e), 'error')
    
    return render_template('traceability/backward_trace.html', result=result)


@app.route('/traceability/cogs-summary')
@login_required
def cogs_summary():
    """COGS summary report"""
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    if start_date:
        start_date = date.fromisoformat(start_date)
    if end_date:
        end_date = date.fromisoformat(end_date)
    
    trace_mgr = get_traceability_manager(db)
    summary = trace_mgr.get_cogs_summary(start_date, end_date)
    
    return render_template('traceability/cogs_summary.html', summary=summary)


@app.route('/traceability/variance-report')
@login_required
def variance_report():
    """Variance analysis report"""
    batch_id = request.args.get('batch_id', type=int)
    
    trace_mgr = get_traceability_manager(db)
    report = trace_mgr.get_variance_report(batch_id)
    
    batches = db.get_batches(status='completed')
    
    return render_template('traceability/variance_report.html', report=report, batches=batches, selected_batch=batch_id)


# ==================== REPORTS ====================

@app.route('/reports')
@login_required
def reports_dashboard():
    """Analytics dashboard"""
    from utils.reports import BreweryReports
    
    period = request.args.get('period', 30, type=int)
    period_labels = {7: 'Last 7 Days', 30: 'Last 30 Days', 90: 'Last 90 Days', 365: 'Last Year'}
    period_label = period_labels.get(period, f'Last {period} Days')
    
    reports = BreweryReports(db)
    
    executive = reports.get_executive_summary()
    sales = reports.get_sales_analytics(days=period)
    production = reports.get_production_analytics(days=period)
    inventory = reports.get_inventory_analytics()
    financial = reports.get_financial_analytics(days=period)
    quality = reports.get_quality_analytics(days=period)
    customers = reports.get_customer_analytics(days=period)
    
    return render_template('reports/dashboard.html',
                         executive=executive,
                         sales=sales,
                         production=production,
                         inventory=inventory,
                         financial=financial,
                         quality=quality,
                         customers=customers,
                         period=period,
                         period_label=period_label)


@app.route('/reports/sales')
@login_required
def reports_sales():
    """Sales report"""
    from utils.reports import BreweryReports
    
    period = request.args.get('period', 30, type=int)
    reports = BreweryReports(db)
    sales = reports.get_sales_analytics(days=period)
    
    return render_template('reports/sales.html', sales=sales, period=period)


@app.route('/reports/production')
@login_required
def reports_production():
    """Production report"""
    from utils.reports import BreweryReports
    
    period = request.args.get('period', 90, type=int)
    reports = BreweryReports(db)
    production = reports.get_production_analytics(days=period)
    
    return render_template('reports/production.html', production=production, period=period)


@app.route('/reports/inventory')
@login_required
def reports_inventory():
    """Inventory report"""
    from utils.reports import BreweryReports
    
    reports = BreweryReports(db)
    inventory = reports.get_inventory_analytics()
    
    return render_template('reports/inventory.html', inventory=inventory)


@app.route('/reports/financial')
@login_required
def reports_financial():
    """Financial report"""
    from utils.reports import BreweryReports
    
    period = request.args.get('period', 30, type=int)
    reports = BreweryReports(db)
    financial = reports.get_financial_analytics(days=period)
    
    return render_template('reports/financial.html', financial=financial, period=period)


@app.route('/reports/customers')
@login_required
def reports_customers():
    """Customer report"""
    from utils.reports import BreweryReports
    
    period = request.args.get('period', 90, type=int)
    reports = BreweryReports(db)
    customers = reports.get_customer_analytics(days=period)
    
    return render_template('reports/customers.html', customers=customers, period=period)


# ==================== PRODUCTION PLANNING ====================

@app.route('/production-planning')
@login_required
def production_planning():
    """Production planning calendar view"""
    from utils.production_planning import ProductionPlanner
    
    planner = ProductionPlanner(db)
    month = request.args.get('month', date.today().strftime('%Y-%m'))
    
    try:
        year, month_num = map(int, month.split('-'))
    except:
        year, month_num = date.today().year, date.today().month
    
    schedule = planner.get_monthly_schedule(year, month_num)
    capacity = planner.get_capacity_utilization()
    products = db.get_products()
    equipment = db.get_equipment(equipment_type='fermenter')
    
    return render_template('production_planning.html',
                         schedule=schedule,
                         capacity=capacity,
                         products=products,
                         equipment=equipment,
                         current_month=month)


@app.route('/capacity-planning')
@login_required
def capacity_planning():
    """Capacity planning view"""
    from utils.production_planning import ProductionPlanner
    
    planner = ProductionPlanner(db)
    capacity = planner.get_capacity_utilization()
    conflicts = planner.detect_conflicts()
    
    return render_template('capacity_planning.html',
                         capacity=capacity,
                         conflicts=conflicts)


@app.route('/production-planning/add', methods=['GET', 'POST'])
@login_required
def add_production_schedule():
    """Add production schedule entry"""
    if request.method == 'POST':
        schedule_date = request.form.get('schedule_date')
        product_id = int(request.form.get('product_id'))
        tank_id = request.form.get('tank_id')
        tank_id = int(tank_id) if tank_id else None
        planned_quantity = float(request.form.get('planned_quantity'))
        notes = request.form.get('notes', '')
        
        conn = db.get_connection()
        conn.execute('''
            INSERT INTO production_schedule (schedule_date, product_id, tank_id, planned_quantity, notes)
            VALUES (?, ?, ?, ?, ?)
        ''', (schedule_date, product_id, tank_id, planned_quantity, notes))
        conn.commit()
        conn.close()
        
        flash('Schedule entry added successfully!', 'success')
        return redirect(url_for('production_planning'))
    
    products = db.get_products()
    equipment = db.get_equipment(equipment_type='fermenter')
    return render_template('add_schedule.html', products=products, equipment=equipment)


@app.route('/production-planning/<int:schedule_id>/update-status', methods=['POST'])
@login_required
def update_schedule_status(schedule_id):
    """Update schedule entry status"""
    status = request.form.get('status')
    conn = db.get_connection()
    conn.execute('UPDATE production_schedule SET status = ? WHERE id = ?', (status, schedule_id))
    conn.commit()
    conn.close()
    flash('Schedule status updated!', 'success')
    return redirect(url_for('production_planning'))


@app.route('/production-planning/<int:schedule_id>/delete', methods=['POST'])
@login_required
def delete_schedule(schedule_id):
    """Delete schedule entry"""
    conn = db.get_connection()
    conn.execute('DELETE FROM production_schedule WHERE id = ?', (schedule_id,))
    conn.commit()
    conn.close()
    flash('Schedule entry deleted!', 'success')
    return redirect(url_for('production_planning'))


# ==================== AI MANAGER ====================

@app.route('/ai')
@login_required
def ai_manager():
    """AI Manager chat interface"""
    return render_template('ai_manager.html')

@app.route('/ai-dashboard')
@login_required
def ai_dashboard():
    """AI Dashboard with real-time monitoring and analytics"""
    return render_template('ai_dashboard.html')


def detect_message_language(text):
    """Detect if a message is primarily English or Vietnamese"""
    import re
    # Vietnamese diacritics pattern
    vietnamese_pattern = re.compile(r'[àáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđÀÁẠẢÃÂẦẤẬẨẪĂẰẮẶẲẴÈÉẸẺẼÊỀẾỆỂỄÌÍỊỈĨÒÓỌỎÕÔỒỐỘỔỖƠỜỚỢỞỠÙÚỤỦŨƯỪỨỰỬỮỲÝỴỶỸĐ]')
    
    # Count Vietnamese characters
    vietnamese_chars = len(vietnamese_pattern.findall(text))
    # Count total alphabetic characters
    alpha_chars = len(re.findall(r'[a-zA-ZàáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđÀÁẠẢÃÂẦẤẬẨẪĂẰẮẶẲẴÈÉẸẺẼÊỀẾỆỂỄÌÍỊỈĨÒÓỌỎÕÔỒỐỘỔỖƠỜỚỢỞỠÙÚỤỦŨƯỪỨỰỬỮỲÝỴỶỸĐ]', text))
    
    if alpha_chars == 0:
        return 'en'  # Default to English if no alphabetic characters
    
    # If more than 10% of alphabetic characters are Vietnamese diacritics, it's Vietnamese
    if vietnamese_chars / alpha_chars > 0.1:
        return 'vi'
    return 'en'

@app.route('/ai/chat', methods=['POST'])
@login_required
@csrf.exempt
@limiter.limit("30 per minute")
def ai_chat():
    """Handle AI chat messages"""
    import asyncio
    
    try:
        data = request.json
        user_message = data.get('message', '').strip()
        
        if not user_message:
            return jsonify({'error': 'No message provided'}), 400
        
        # Use session_id based on user_id for per-user persistence
        session_id = f"user_{session.get('user_id', 'anonymous')}"
        
        # Call MiMo engine with process_message which handles DB persistence
        engine = get_engine()
        
        # Run async function in sync context
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            context = {'session_id': session_id}
            result = loop.run_until_complete(engine.process_message(user_message, context))
            final_content = result.get('content', '')
            tools_called = result.get('tools_called', [])
        finally:
            loop.close()
        
        # Keep a lightweight session reference for frontend (no full history)
        if 'ai_session_id' not in session:
            session['ai_session_id'] = session_id
        
        # Format response to match what the template expects
        response_data = {
            'success': True,
            'response': final_content,
            'tool_results': tools_called if tools_called else None
        }
        
        return jsonify(response_data)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/ai/clear', methods=['POST'])
@login_required
@csrf.exempt
def ai_clear():
    """Clear AI chat history"""
    from utils.mimo_engine import get_engine
    from models.database import Database
    
    session_id = f"user_{session.get('user_id', 'anonymous')}"
    
    # Clear in-memory conversation
    engine = get_engine()
    engine.clear_history(session_id)
    
    # Clear database history
    try:
        db = Database()
        db.clear_chat_history(session_id)
    except Exception:
        pass
    
    # Also clear legacy session storage if present
    session.pop('ai_messages', None)
    session.modified = True
    
    return jsonify({'success': True})


@app.route('/api/ai/suggestions', methods=['GET'])
@login_required
def ai_get_suggestions():
    """Get proactive suggestions from AI"""
    try:
        from utils.ai_planner import get_planner
        
        planner = get_planner()
        suggestions = planner.get_proactive_suggestions()
        
        return jsonify({
            'success': True,
            'suggestions': suggestions,
            'mode': planner.mode
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e), 'suggestions': []}), 500


@app.route('/api/ai/planning-mode', methods=['POST'])
@login_required
def ai_planning_mode():
    """Set AI planning mode"""
    try:
        from utils.ai_planner import get_planner
        
        data = request.json
        mode = data.get('mode', 'proactive')
        
        planner = get_planner()
        planner.set_mode(mode)
        
        return jsonify({'success': True, 'mode': mode})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/ai/autonomy', methods=['GET'])
@login_required
def ai_get_autonomy():
    """Get current AI autonomy level"""
    try:
        from utils.agent import get_proactive_agent
        agent = get_proactive_agent()
        config = agent.get_autonomy_config()
        return jsonify({'success': True, 'config': config})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/ai/autonomy', methods=['POST'])
@login_required
@csrf.exempt
def ai_set_autonomy():
    """Set AI autonomy level"""
    try:
        from utils.agent import get_proactive_agent
        data = request.json
        level = data.get('level', 'observer')
        agent = get_proactive_agent()
        agent.set_autonomy_level(level)
        return jsonify({'success': True, 'level': level})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/ai/scan', methods=['POST'])
@login_required
@csrf.exempt
def ai_proactive_scan():
    """Run a proactive scan for opportunities and issues"""
    try:
        from utils.agent import get_proactive_agent
        agent = get_proactive_agent()
        suggestions = agent.run_proactive_scan()
        return jsonify({
            'success': True,
            'suggestions': suggestions,
            'count': len(suggestions)
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/ai/suggestions/pending', methods=['GET'])
@login_required
def ai_pending_suggestions():
    """Get pending AI suggestions"""
    try:
        from utils.agent import get_proactive_agent
        agent = get_proactive_agent()
        suggestions = agent.get_pending_suggestions()
        return jsonify({'success': True, 'suggestions': suggestions})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/ai/suggestions/<int:index>/approve', methods=['POST'])
@login_required
@csrf.exempt
def ai_approve_suggestion(index):
    """Approve a pending suggestion"""
    try:
        from utils.agent import get_proactive_agent
        agent = get_proactive_agent()
        success = agent.approve_suggestion(index)
        return jsonify({'success': success})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/ai/suggestions/<int:index>/dismiss', methods=['POST'])
@login_required
@csrf.exempt
def ai_dismiss_suggestion(index):
    """Dismiss a pending suggestion"""
    try:
        from utils.agent import get_proactive_agent
        agent = get_proactive_agent()
        success = agent.dismiss_suggestion(index)
        return jsonify({'success': success})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/ai/goals', methods=['GET'])
@login_required
def ai_get_goals():
    """Get brewery goals and progress"""
    try:
        from utils.agent import get_proactive_agent
        agent = get_proactive_agent()
        goals = agent.get_goal_progress()
        return jsonify({'success': True, 'goals': goals})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/ai/goals', methods=['POST'])
@login_required
@csrf.exempt
def ai_add_goal():
    """Add a new brewery goal"""
    try:
        from utils.agent import get_proactive_agent
        data = request.json
        agent = get_proactive_agent()
        goal_id = agent.add_goal(
            name=data.get('name'),
            description=data.get('description', ''),
            target_value=data.get('target_value', 0),
            current_value=data.get('current_value', 0),
            unit=data.get('unit', ''),
            priority=data.get('priority', 'normal'),
            category=data.get('category', 'general')
        )
        return jsonify({'success': goal_id > 0, 'goal_id': goal_id})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/ai/goals/<int:goal_id>', methods=['PUT'])
@login_required
@csrf.exempt
def ai_update_goal(goal_id):
    """Update goal progress"""
    try:
        from utils.agent import get_proactive_agent
        data = request.json
        agent = get_proactive_agent()
        agent.update_goal_progress(goal_id, data.get('current_value', 0))
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/ai/activity-log', methods=['GET'])
@login_required
def ai_activity_log():
    """Get proactive AI activity log"""
    try:
        from utils.agent import get_proactive_agent
        limit = request.args.get('limit', 50, type=int)
        agent = get_proactive_agent()
        activities = agent.get_activity_log(limit)
        return jsonify({'success': True, 'activities': activities})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/ai/anomalies', methods=['GET'])
@login_required
def ai_detect_anomalies():
    """Detect anomalies in brewery operations"""
    try:
        from utils.ai_tools import detect_anomalies
        result = detect_anomalies()
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/ai/tts', methods=['POST'])
@login_required
@csrf.exempt
def ai_tts():
    """Generate TTS audio for AI responses"""
    import asyncio
    import re
    from flask import Response
    from utils.mimo_engine import get_engine
    
    try:
        data = request.json
        text = data.get('text', '')
        if not text:
            return jsonify({'error': 'No text provided'}), 400
            
        # Clean text for TTS
        text = re.sub(r'<thinking>[\s\S]*?<\/thinking>', '', text, flags=re.IGNORECASE)
        text = re.sub(r'```[\s\S]*?```', ' Code snippet omitted. ', text)
        text = re.sub(r'[#*`\[\]]', '', text)
        text = text.strip()
        
        if not text:
            return jsonify({'error': 'No readable text after filtering'}), 400
        
        engine = get_engine()
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            audio_bytes = loop.run_until_complete(engine.generate_speech(text[:4000]))
        finally:
            loop.close()
            
        if not audio_bytes:
            return jsonify({'error': 'Failed to generate audio'}), 500
            
        return Response(audio_bytes, mimetype='audio/wav')
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/ai/health')
@login_required
def ai_health():
    """Check AI engine health"""
    engine = get_engine()
    health = engine.health_check()
    return jsonify(health)


# ==================== RUN ====================

def run_server(host='0.0.0.0', port=5000, debug=True):
    """Run the Flask server"""
    app.run(host=host, port=port, debug=debug)


if __name__ == '__main__':
    run_server()
