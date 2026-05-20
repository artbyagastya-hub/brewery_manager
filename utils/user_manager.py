"""
User Management Utility
Handles user CRUD operations, permissions, teams, and activity logging
"""

import os
import secrets
import string
import bcrypt
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple


class UserManager:
    """Manages users, teams, and permissions"""

    def __init__(self, db):
        self.db = db

    # ==================== USER CRUD ====================

    def create_user(self, data: Dict) -> Tuple[Optional[int], str]:
        """
        Create a new user account.
        Returns (user_id, error_message)
        """
        conn = self.db.get_connection()
        cursor = conn.cursor()

        # Check if email already exists
        cursor.execute("SELECT id FROM users WHERE email = ?", (data['email'],))
        if cursor.fetchone():
            conn.close()
            return None, "Email already exists"

        # Hash password
        password = data.get('password') or self._generate_temp_password()
        hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

        try:
            cursor.execute("""
                INSERT INTO users (username, email, password_hash, role, full_name,
                    phone, department, team_id, is_active, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, CURRENT_TIMESTAMP)
            """, (
                data['username'],
                data['email'],
                hashed,
                data.get('role', 'viewer'),
                data.get('full_name', data['username']),
                data.get('phone'),
                data.get('department'),
                data.get('team_id'),
            ))

            user_id = cursor.lastrowid

            # Add to team if specified
            if data.get('team_id'):
                cursor.execute("""
                    INSERT INTO team_members (team_id, user_id, role)
                    VALUES (?, ?, 'member')
                """, (data['team_id'], user_id))

            conn.commit()
            conn.close()
            return user_id, password if not data.get('password') else None
        except Exception as e:
            conn.rollback()
            conn.close()
            return None, str(e)

    def update_user(self, user_id: int, data: Dict) -> Tuple[bool, str]:
        """Update user profile fields"""
        conn = self.db.get_connection()
        cursor = conn.cursor()

        # Check if user exists
        cursor.execute("SELECT id FROM users WHERE id = ?", (user_id,))
        if not cursor.fetchone():
            conn.close()
            return False, "User not found"

        # Check email uniqueness if changing
        if 'email' in data:
            cursor.execute("SELECT id FROM users WHERE email = ? AND id != ?",
                           (data['email'], user_id))
            if cursor.fetchone():
                conn.close()
                return False, "Email already in use"

        # Check username uniqueness if changing
        if 'username' in data:
            cursor.execute("SELECT id FROM users WHERE username = ? AND id != ?",
                           (data['username'], user_id))
            if cursor.fetchone():
                conn.close()
                return False, "Username already in use"

        allowed_fields = [
            'username', 'email', 'full_name', 'role', 'phone',
            'department', 'team_id', 'is_active', 'avatar_url', 'preferences'
        ]

        fields = []
        values = []
        for key, value in data.items():
            if key in allowed_fields:
                fields.append(f"{key} = ?")
                values.append(value)

        if not fields:
            conn.close()
            return False, "No valid fields to update"

        values.append(user_id)
        try:
            cursor.execute(
                f"UPDATE users SET {', '.join(fields)}, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                values
            )

            # Update team membership if team changed
            if 'team_id' in data:
                # Remove from old team
                cursor.execute("DELETE FROM team_members WHERE user_id = ?", (user_id,))
                # Add to new team
                if data['team_id']:
                    cursor.execute("""
                        INSERT OR REPLACE INTO team_members (team_id, user_id, role)
                        VALUES (?, ?, 'member')
                    """, (data['team_id'], user_id))

            conn.commit()
            conn.close()
            return True, "User updated successfully"
        except Exception as e:
            conn.rollback()
            conn.close()
            return False, str(e)

    def deactivate_user(self, user_id: int) -> Tuple[bool, str]:
        """Deactivate (soft delete) a user"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE users SET is_active = 0, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (user_id,))
        conn.commit()
        result = cursor.rowcount > 0
        conn.close()
        return result, "User deactivated" if result else "User not found"

    def get_users(self, role: str = None, team_id: int = None,
                  active_only: bool = True) -> List[Dict]:
        """Get list of users with optional filters"""
        conn = self.db.get_connection()
        cursor = conn.cursor()

        query = """
            SELECT u.id, u.username, u.email, u.full_name, u.role, u.phone,
                   u.department, u.avatar_url, u.team_id, u.is_active,
                   u.last_login, u.created_at, t.name as team_name,
                   s.name as staff_name
            FROM users u
            LEFT JOIN teams t ON u.team_id = t.id
            LEFT JOIN staff s ON u.email LIKE '%' || s.email || '%'
            WHERE 1=1
        """
        params = []

        if active_only:
            query += " AND u.is_active = 1"
        if role:
            query += " AND u.role = ?"
            params.append(role)
        if team_id:
            query += " AND u.team_id = ?"
            params.append(team_id)

        query += " ORDER BY u.full_name, u.username"
        cursor.execute(query, params)
        result = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return result

    def get_user(self, user_id: int) -> Optional[Dict]:
        """Get single user by ID with full details"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT u.*, t.name as team_name
            FROM users u
            LEFT JOIN teams t ON u.team_id = t.id
            WHERE u.id = ?
        """, (user_id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

    def get_user_by_email(self, email: str) -> Optional[Dict]:
        """Get user by email address"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM users WHERE email = ? AND is_active = 1
        """, (email,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

    # ==================== PASSWORD MANAGEMENT ====================

    def change_password(self, user_id: int, current_password: str,
                        new_password: str) -> Tuple[bool, str]:
        """Change user's password (requires current password)"""
        conn = self.db.get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT password_hash FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        if not row:
            conn.close()
            return False, "User not found"

        if not bcrypt.checkpw(current_password.encode('utf-8'), row['password_hash']):
            conn.close()
            return False, "Current password is incorrect"

        hashed = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt())
        cursor.execute("""
            UPDATE users SET password_hash = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?
        """, (hashed, user_id))
        conn.commit()
        conn.close()
        return True, "Password changed successfully"

    def admin_reset_password(self, user_id: int) -> Tuple[bool, str]:
        """Admin resets a user's password to a temporary one"""
        temp_password = self._generate_temp_password()
        hashed = bcrypt.hashpw(temp_password.encode('utf-8'), bcrypt.gensalt())

        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE users SET password_hash = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?
        """, (hashed, user_id))
        conn.commit()
        conn.close()
        return True, temp_password

    def generate_reset_token(self, email: str) -> Tuple[bool, str]:
        """Generate password reset token for email"""
        conn = self.db.get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT id FROM users WHERE email = ? AND is_active = 1", (email,))
        user = cursor.fetchone()
        if not user:
            conn.close()
            return False, "No account found with this email"

        token = secrets.token_urlsafe(32)
        expires = (datetime.now() + timedelta(hours=1)).isoformat()

        cursor.execute("""
            UPDATE users SET reset_token = ?, reset_token_expires = ?
            WHERE id = ?
        """, (token, expires, user['id']))
        conn.commit()
        conn.close()
        return True, token

    def reset_password_with_token(self, token: str, new_password: str) -> Tuple[bool, str]:
        """Reset password using a valid token"""
        conn = self.db.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, reset_token_expires FROM users
            WHERE reset_token = ? AND is_active = 1
        """, (token,))
        user = cursor.fetchone()

        if not user:
            conn.close()
            return False, "Invalid reset token"

        if user['reset_token_expires'] < datetime.now().isoformat():
            conn.close()
            return False, "Reset token has expired"

        hashed = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt())
        cursor.execute("""
            UPDATE users SET password_hash = ?, reset_token = NULL,
                reset_token_expires = NULL, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (hashed, user['id']))
        conn.commit()
        conn.close()
        return True, "Password reset successfully"

    def verify_password(self, email: str, password: str) -> Optional[Dict]:
        """Verify user credentials and return user dict if valid"""
        conn = self.db.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM users WHERE email = ? AND is_active = 1
        """, (email,))
        user = cursor.fetchone()

        if not user:
            conn.close()
            return None

        # Check if account is locked
        if user['locked_until'] and user['locked_until'] > datetime.now().isoformat():
            conn.close()
            return None

        if not bcrypt.checkpw(password.encode('utf-8'), user['password_hash']):
            # Increment failed attempts
            attempts = (user['failed_login_attempts'] or 0) + 1
            locked_until = None
            if attempts >= 5:
                locked_until = (datetime.now() + timedelta(minutes=15)).isoformat()

            cursor.execute("""
                UPDATE users SET failed_login_attempts = ?, locked_until = ?
                WHERE id = ?
            """, (attempts, locked_until, user['id']))
            conn.commit()
            conn.close()
            return None

        # Reset failed attempts on successful login
        cursor.execute("""
            UPDATE users SET failed_login_attempts = 0, locked_until = NULL,
                last_login = CURRENT_TIMESTAMP WHERE id = ?
        """, (user['id'],))
        conn.commit()
        conn.close()

        result = dict(user)
        del result['password_hash']
        return result

    # ==================== PERMISSIONS ====================

    def get_user_permissions(self, user_id: int) -> List[str]:
        """Get all permission names for a user (role + user overrides)"""
        conn = self.db.get_connection()
        cursor = conn.cursor()

        # Get user role
        cursor.execute("SELECT role FROM users WHERE id = ?", (user_id,))
        user = cursor.fetchone()
        if not user:
            conn.close()
            return []

        role = user['role']

        # Get role permissions
        cursor.execute("""
            SELECT p.name FROM permissions p
            JOIN role_permissions rp ON p.id = rp.permission_id
            WHERE rp.role = ?
        """, (role,))
        role_perms = {row['name'] for row in cursor.fetchall()}

        # Get user-specific overrides
        cursor.execute("""
            SELECT p.name, up.granted FROM user_permissions up
            JOIN permissions p ON p.id = up.permission_id
            WHERE up.user_id = ?
        """, (user_id,))
        for row in cursor.fetchall():
            if row['granted']:
                role_perms.add(row['name'])
            else:
                role_perms.discard(row['name'])

        conn.close()
        return sorted(list(role_perms))

    def has_permission(self, user_id: int, permission: str) -> bool:
        """Check if user has a specific permission"""
        permissions = self.get_user_permissions(user_id)
        return permission in permissions

    def set_user_permission(self, user_id: int, permission_id: int,
                            granted: bool = True) -> bool:
        """Grant or revoke a specific permission for a user"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO user_permissions (user_id, permission_id, granted)
            VALUES (?, ?, ?)
        """, (user_id, permission_id, 1 if granted else 0))
        conn.commit()
        conn.close()
        return True

    # ==================== TEAMS ====================

    def create_team(self, data: Dict) -> int:
        """Create a new team"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO teams (name, description, team_lead_id)
            VALUES (?, ?, ?)
        """, (data['name'], data.get('description'), data.get('team_lead_id')))
        team_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return team_id

    def update_team(self, team_id: int, data: Dict) -> bool:
        """Update team details"""
        conn = self.db.get_connection()
        cursor = conn.cursor()

        fields = []
        values = []
        for key in ['name', 'description', 'team_lead_id', 'is_active']:
            if key in data:
                fields.append(f"{key} = ?")
                values.append(data[key])

        if fields:
            values.append(team_id)
            cursor.execute(
                f"UPDATE teams SET {', '.join(fields)}, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                values
            )
            conn.commit()

        conn.close()
        return True

    def get_teams(self, active_only: bool = True) -> List[Dict]:
        """Get all teams with member count"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        query = """
            SELECT t.*, u.full_name as team_lead_name,
                   COUNT(tm.user_id) as member_count
            FROM teams t
            LEFT JOIN users u ON t.team_lead_id = u.id
            LEFT JOIN team_members tm ON t.id = tm.team_id
            WHERE 1=1
        """
        if active_only:
            query += " AND t.is_active = 1"
        query += " GROUP BY t.id ORDER BY t.name"

        cursor.execute(query)
        result = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return result

    def get_team(self, team_id: int) -> Optional[Dict]:
        """Get team with members"""
        conn = self.db.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT t.*, u.full_name as team_lead_name
            FROM teams t
            LEFT JOIN users u ON t.team_lead_id = u.id
            WHERE t.id = ?
        """, (team_id,))
        team = cursor.fetchone()
        if not team:
            conn.close()
            return None

        team = dict(team)

        # Get members
        cursor.execute("""
            SELECT u.id, u.full_name, u.email, u.role, tm.role as team_role
            FROM team_members tm
            JOIN users u ON tm.user_id = u.id
            WHERE tm.team_id = ? AND u.is_active = 1
            ORDER BY u.full_name
        """, (team_id,))
        team['members'] = [dict(row) for row in cursor.fetchall()]

        conn.close()
        return team

    def add_team_member(self, team_id: int, user_id: int, role: str = 'member') -> bool:
        """Add user to team"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO team_members (team_id, user_id, role)
            VALUES (?, ?, ?)
        """, (team_id, user_id, role))

        # Update user's team_id
        cursor.execute("UPDATE users SET team_id = ? WHERE id = ?", (team_id, user_id))

        conn.commit()
        conn.close()
        return True

    def remove_team_member(self, team_id: int, user_id: int) -> bool:
        """Remove user from team"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM team_members WHERE team_id = ? AND user_id = ?",
                       (team_id, user_id))

        # Clear user's team_id if it matches
        cursor.execute("UPDATE users SET team_id = NULL WHERE id = ? AND team_id = ?",
                       (user_id, team_id))

        conn.commit()
        conn.close()
        return True

    # ==================== ACTIVITY LOGGING ====================

    def log_activity(self, user_id: int, activity_type: str,
                     page_path: str = None, action_detail: str = None,
                     ip_address: str = None, user_agent: str = None):
        """Log user activity"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO user_activity_log
            (user_id, activity_type, page_path, action_detail, ip_address, user_agent)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (user_id, activity_type, page_path, action_detail, ip_address, user_agent))
        conn.commit()
        conn.close()

    def get_user_activity(self, user_id: int = None, activity_type: str = None,
                          limit: int = 100) -> List[Dict]:
        """Get activity log entries"""
        conn = self.db.get_connection()
        cursor = conn.cursor()

        query = """
            SELECT al.*, u.full_name, u.email
            FROM user_activity_log al
            JOIN users u ON al.user_id = u.id
            WHERE 1=1
        """
        params = []

        if user_id:
            query += " AND al.user_id = ?"
            params.append(user_id)
        if activity_type:
            query += " AND al.activity_type = ?"
            params.append(activity_type)

        query += " ORDER BY al.created_at DESC LIMIT ?"
        params.append(limit)

        cursor.execute(query, params)
        result = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return result

    # ==================== CHAT HISTORY ====================

    def get_user_chat_history(self, user_id: int, limit: int = 50) -> List[Dict]:
        """Get AI chat history for a user"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM chat_history
            WHERE user_id = ? AND is_archived = 0
            ORDER BY timestamp DESC LIMIT ?
        """, (user_id, limit))
        result = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return result

    def get_all_chat_history(self, limit: int = 200) -> List[Dict]:
        """Get all chat history (admin only)"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT ch.*, u.full_name, u.email
            FROM chat_history ch
            LEFT JOIN users u ON ch.user_id = u.id
            WHERE ch.is_archived = 0
            ORDER BY ch.timestamp DESC LIMIT ?
        """, (limit,))
        result = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return result

    # ==================== UTILITIES ====================

    def _generate_temp_password(self, length: int = 12) -> str:
        """Generate a secure temporary password"""
        alphabet = string.ascii_letters + string.digits + "!@#$%"
        return ''.join(secrets.choice(alphabet) for _ in range(length))

    def get_user_stats(self) -> Dict:
        """Get user management statistics"""
        conn = self.db.get_connection()
        cursor = conn.cursor()

        stats = {}

        cursor.execute("SELECT COUNT(*) FROM users WHERE is_active = 1")
        stats['total_users'] = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM users WHERE last_login > datetime('now', '-7 days')")
        stats['active_this_week'] = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM teams WHERE is_active = 1")
        stats['total_teams'] = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM user_activity_log WHERE created_at > datetime('now', '-24 hours')")
        stats['activities_today'] = cursor.fetchone()[0]

        cursor.execute("""
            SELECT role, COUNT(*) as count FROM users
            WHERE is_active = 1 GROUP BY role
        """)
        stats['by_role'] = {row['role']: row['count'] for row in cursor.fetchall()}

        conn.close()
        return stats