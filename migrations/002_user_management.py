"""
Database Migration - User Management System
Adds teams, permissions, activity logging, and enhanced user fields
"""

import sqlite3
import os
import bcrypt

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'brewery.db')


def migrate():
    """Apply user management schema changes"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    print("Running User Management migration...")
    
    # Enable foreign keys
    cursor.execute("PRAGMA foreign_keys = ON")
    
    # ==================== NEW TABLES ====================
    
    # Teams table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS teams (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            team_lead_id INTEGER,
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (team_lead_id) REFERENCES users(id)
        )
    """)
    print("  ✓ Created teams table")
    
    # Team members junction table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS team_members (
            team_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            role TEXT DEFAULT 'member',
            joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (team_id, user_id),
            FOREIGN KEY (team_id) REFERENCES teams(id) ON DELETE CASCADE,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)
    print("  ✓ Created team_members table")
    
    # Permissions table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS permissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            description TEXT,
            category TEXT NOT NULL
        )
    """)
    print("  ✓ Created permissions table")
    
    # Role permissions junction table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS role_permissions (
            role TEXT NOT NULL,
            permission_id INTEGER NOT NULL,
            PRIMARY KEY (role, permission_id),
            FOREIGN KEY (permission_id) REFERENCES permissions(id) ON DELETE CASCADE
        )
    """)
    print("  ✓ Created role_permissions table")
    
    # User-specific permissions (overrides)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_permissions (
            user_id INTEGER NOT NULL,
            permission_id INTEGER NOT NULL,
            granted INTEGER DEFAULT 1,
            PRIMARY KEY (user_id, permission_id),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (permission_id) REFERENCES permissions(id) ON DELETE CASCADE
        )
    """)
    print("  ✓ Created user_permissions table")
    
    # User activity log
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_activity_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            activity_type TEXT NOT NULL,
            page_path TEXT,
            action_detail TEXT,
            ip_address TEXT,
            user_agent TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    print("  ✓ Created user_activity_log table")
    
    # ==================== ALTER USERS TABLE ====================
    
    # Add new columns to users table (using ALTER TABLE ADD COLUMN with IF NOT EXISTS equivalent)
    new_columns = [
        ("phone", "TEXT"),
        ("department", "TEXT"),
        ("avatar_url", "TEXT"),
        ("preferences", "TEXT DEFAULT '{}'"),
        ("team_id", "INTEGER REFERENCES teams(id)"),
        ("failed_login_attempts", "INTEGER DEFAULT 0"),
        ("locked_until", "TIMESTAMP"),
        ("reset_token", "TEXT"),
        ("reset_token_expires", "TIMESTAMP"),
    ]
    
    # Get existing columns
    cursor.execute("PRAGMA table_info(users)")
    existing_columns = {row[1] for row in cursor.fetchall()}
    
    for col_name, col_type in new_columns:
        if col_name not in existing_columns:
            cursor.execute(f"ALTER TABLE users ADD COLUMN {col_name} {col_type}")
            print(f"  ✓ Added column: users.{col_name}")
    
    # ==================== ALTER CHAT_HISTORY TABLE ====================
    
    # Check if user_id column exists in chat_history
    cursor.execute("PRAGMA table_info(chat_history)")
    chat_columns = {row[1] for row in cursor.fetchall()}
    
    if "user_id" not in chat_columns:
        cursor.execute("ALTER TABLE chat_history ADD COLUMN user_id INTEGER REFERENCES users(id)")
        print("  ✓ Added column: chat_history.user_id")
    
    if "title" not in chat_columns:
        cursor.execute("ALTER TABLE chat_history ADD COLUMN title TEXT")
        print("  ✓ Added column: chat_history.title")
    
    if "is_archived" not in chat_columns:
        cursor.execute("ALTER TABLE chat_history ADD COLUMN is_archived INTEGER DEFAULT 0")
        print("  ✓ Added column: chat_history.is_archived")
    
    # ==================== SEED DATA ====================
    
    # Insert permissions
    cursor.execute("SELECT COUNT(*) FROM permissions")
    if cursor.fetchone()[0] == 0:
        permissions = [
            # Inventory
            ('inventory.view', 'View inventory items', 'Inventory'),
            ('inventory.create', 'Add inventory items', 'Inventory'),
            ('inventory.edit', 'Edit inventory items', 'Inventory'),
            ('inventory.delete', 'Delete inventory items', 'Inventory'),
            
            # Production
            ('production.view', 'View production batches', 'Production'),
            ('production.create', 'Create production batches', 'Production'),
            ('production.edit', 'Edit production batches', 'Production'),
            ('quality.log', 'Log quality records', 'Production'),
            
            # Sales
            ('sales.view', 'View sales orders', 'Sales'),
            ('sales.create', 'Create sales orders', 'Sales'),
            ('sales.edit', 'Edit sales orders', 'Sales'),
            
            # Finance
            ('finance.view', 'View financial data', 'Finance'),
            ('finance.create', 'Create transactions', 'Finance'),
            ('finance.reports', 'View financial reports', 'Finance'),
            
            # Customers
            ('customers.view', 'View customers', 'Customers'),
            ('customers.manage', 'Manage customers', 'Customers'),
            
            # Users (Admin only)
            ('users.view', 'View user accounts', 'Users'),
            ('users.create', 'Create user accounts', 'Users'),
            ('users.edit', 'Edit user accounts', 'Users'),
            ('users.delete', 'Deactivate user accounts', 'Users'),
            ('users.reset_password', 'Reset user passwords', 'Users'),
            
            # Teams
            ('teams.view', 'View teams', 'Teams'),
            ('teams.manage', 'Manage teams', 'Teams'),
            
            # AI
            ('ai.chat', 'Use AI assistant chat', 'AI'),
            ('ai.view_all_history', 'View all AI chat history', 'AI'),
            
            # Activity Logs
            ('activity.view', 'View activity logs', 'Activity'),
        ]
        
        for name, description, category in permissions:
            cursor.execute("""
                INSERT INTO permissions (name, description, category)
                VALUES (?, ?, ?)
            """, (name, description, category))
        print(f"  ✓ Seeded {len(permissions)} permissions")
    
    # Assign permissions to roles
    cursor.execute("SELECT COUNT(*) FROM role_permissions")
    if cursor.fetchone()[0] == 0:
        # Get permission IDs
        cursor.execute("SELECT id, name FROM permissions")
        perm_map = {row[1]: row[0] for row in cursor.fetchall()}
        
        role_perms = {
            'admin': list(perm_map.values()),  # All permissions
            
            'director': [
                perm_map['inventory.view'], perm_map['production.view'],
                perm_map['sales.view'], perm_map['finance.view'],
                perm_map['finance.reports'], perm_map['customers.view'],
                perm_map['users.view'], perm_map['teams.view'],
                perm_map['teams.manage'], perm_map['ai.chat'],
                perm_map['ai.view_all_history'], perm_map['activity.view'],
            ],
            
            'manager': [
                perm_map['inventory.view'], perm_map['inventory.create'],
                perm_map['inventory.edit'], perm_map['inventory.delete'],
                perm_map['production.view'], perm_map['production.create'],
                perm_map['production.edit'], perm_map['quality.log'],
                perm_map['sales.view'], perm_map['sales.create'],
                perm_map['sales.edit'], perm_map['finance.view'],
                perm_map['finance.create'], perm_map['finance.reports'],
                perm_map['customers.view'], perm_map['customers.manage'],
                perm_map['teams.view'], perm_map['ai.chat'],
            ],
            
            'brewer': [
                perm_map['inventory.view'], perm_map['inventory.create'],
                perm_map['inventory.edit'], perm_map['production.view'],
                perm_map['production.create'], perm_map['production.edit'],
                perm_map['quality.log'], perm_map['teams.view'],
                perm_map['ai.chat'],
            ],
            
            'general_worker': [
                perm_map['inventory.view'], perm_map['production.view'],
                perm_map['quality.log'], perm_map['teams.view'],
            ],
            
            'accountant': [
                perm_map['inventory.view'], perm_map['sales.view'],
                perm_map['finance.view'], perm_map['finance.create'],
                perm_map['finance.reports'], perm_map['customers.view'],
                perm_map['teams.view'],
            ],
            
            'sales': [
                perm_map['inventory.view'], perm_map['production.view'],
                perm_map['sales.view'], perm_map['sales.create'],
                perm_map['sales.edit'], perm_map['customers.view'],
                perm_map['customers.manage'], perm_map['teams.view'],
            ],
            
            'viewer': [
                perm_map['inventory.view'], perm_map['production.view'],
                perm_map['sales.view'], perm_map['customers.view'],
                perm_map['teams.view'],
            ],
        }
        
        for role, perm_ids in role_perms.items():
            for perm_id in perm_ids:
                cursor.execute("""
                    INSERT INTO role_permissions (role, permission_id)
                    VALUES (?, ?)
                """, (role, perm_id))
        print(f"  ✓ Seeded role permissions for {len(role_perms)} roles")
    
    # ==================== INDICES ====================
    
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_team ON users(team_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_role ON users(role)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_active ON users(is_active)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_team_members_team ON team_members(team_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_team_members_user ON team_members(user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_activity_user ON user_activity_log(user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_activity_type ON user_activity_log(activity_type)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_chat_history_user ON chat_history(user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_role_permissions_role ON role_permissions(role)")
    print("  ✓ Created indices")
    
    conn.commit()
    conn.close()
    
    print("\n✅ User Management migration completed successfully!")


if __name__ == '__main__':
    migrate()