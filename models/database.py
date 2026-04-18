"""
Brewery Manager - Database Layer
SQLite database for comprehensive brewery management in Vietnam
"""

import sqlite3
import os
from datetime import datetime, date, timedelta
from typing import List, Dict, Optional, Tuple
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.performance import (
    init_connection_pool, get_connection_pool, 
    cached, DatabaseContext, optimize_database
)

# Python 3.12+ datetime adapters to avoid deprecation warnings
def adapt_date(val):
    """Adapt date to ISO 8601 string."""
    return val.isoformat()

def adapt_datetime(val):
    """Adapt datetime to ISO 8601 string."""
    return val.isoformat()

def convert_date(val):
    """Convert ISO 8601 string to date."""
    return date.fromisoformat(val.decode())

def convert_datetime(val):
    """Convert ISO 8601 string to datetime."""
    return datetime.fromisoformat(val.decode())

# Register adapters and converters
sqlite3.register_adapter(date, adapt_date)
sqlite3.register_adapter(datetime, adapt_datetime)
sqlite3.register_converter("date", convert_date)
sqlite3.register_converter("timestamp", convert_datetime)

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'brewery.db')


class Database:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.init_database()

    def get_connection(self):
        conn = sqlite3.connect(self.db_path, detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def execute_query(self, query: str, params: tuple = ()) -> List[Dict]:
        """Execute a raw SQL query safely with connection pooling"""
        with DatabaseContext() as ctx:
            ctx.execute(query, params)
            if query.strip().upper().startswith('SELECT'):
                results = ctx.fetchall()
                return [dict(row) for row in results]
            elif query.strip().upper().startswith('INSERT'):
                return ctx.lastrowid
            else:
                return []

    def init_database(self):
        conn = self.get_connection()
        cursor = conn.cursor()

        # Raw Materials
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS raw_materials (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                category TEXT NOT NULL,
                unit TEXT NOT NULL,
                quantity REAL DEFAULT 0,
                min_quantity REAL DEFAULT 0,
                cost_per_unit REAL DEFAULT 0,
                supplier TEXT,
                origin TEXT,
                expiry_date DATE,
                storage_location TEXT,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Products
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                style TEXT,
                abv REAL DEFAULT 0,
                ibu INTEGER DEFAULT 0,
                description TEXT,
                price_per_unit REAL DEFAULT 0,
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Equipment/Tanks
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS equipment (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                equipment_type TEXT NOT NULL,
                capacity REAL,
                capacity_unit TEXT DEFAULT 'L',
                status TEXT DEFAULT 'available',
                current_batch_id INTEGER,
                last_cleaned TIMESTAMP,
                next_cleaning_due TIMESTAMP,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (current_batch_id) REFERENCES production_batches(id)
            )
        """)

        # Production Batches
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS production_batches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                batch_number TEXT UNIQUE NOT NULL,
                product_id INTEGER NOT NULL,
                tank_id INTEGER,
                planned_quantity REAL NOT NULL,
                actual_quantity REAL,
                status TEXT DEFAULT 'planned',
                start_date DATE,
                end_date DATE,
                brewer_id INTEGER,
                equipment_used TEXT,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (product_id) REFERENCES products(id),
                FOREIGN KEY (tank_id) REFERENCES equipment(id),
                FOREIGN KEY (brewer_id) REFERENCES staff(id)
            )
        """)

        # Batch Ingredients
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS batch_ingredients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                batch_id INTEGER NOT NULL,
                material_id INTEGER NOT NULL,
                quantity_used REAL NOT NULL,
                cost_at_time REAL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (batch_id) REFERENCES production_batches(id),
                FOREIGN KEY (material_id) REFERENCES raw_materials(id)
            )
        """)

        # Quality Records
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS quality_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                batch_id INTEGER NOT NULL,
                check_type TEXT NOT NULL,
                value REAL,
                unit TEXT,
                passed INTEGER DEFAULT 1,
                inspector TEXT,
                notes TEXT,
                check_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (batch_id) REFERENCES production_batches(id)
            )
        """)

        # Customers
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS customers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                type TEXT DEFAULT 'retail',
                contact_person TEXT,
                phone TEXT,
                email TEXT,
                address TEXT,
                city TEXT,
                province TEXT,
                tax_id TEXT,
                credit_limit REAL DEFAULT 0,
                payment_terms TEXT DEFAULT 'COD',
                notes TEXT,
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Sales Orders
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sales_orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_number TEXT UNIQUE NOT NULL,
                customer_id INTEGER NOT NULL,
                order_date DATE NOT NULL,
                delivery_date DATE,
                status TEXT DEFAULT 'pending',
                total_amount REAL DEFAULT 0,
                payment_status TEXT DEFAULT 'unpaid',
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (customer_id) REFERENCES customers(id)
            )
        """)

        # Order Items
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS order_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER NOT NULL,
                product_id INTEGER NOT NULL,
                quantity REAL NOT NULL,
                unit_price REAL NOT NULL,
                discount REAL DEFAULT 0,
                subtotal REAL NOT NULL,
                FOREIGN KEY (order_id) REFERENCES sales_orders(id),
                FOREIGN KEY (product_id) REFERENCES products(id)
            )
        """)

        # Financial Transactions
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS financial_transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                transaction_date DATE NOT NULL,
                type TEXT NOT NULL,
                category TEXT,
                amount REAL NOT NULL,
                description TEXT,
                payment_method TEXT,
                reference_id INTEGER,
                reference_type TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Staff
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS staff (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                position TEXT NOT NULL,
                department TEXT,
                phone TEXT,
                email TEXT,
                hire_date DATE,
                salary REAL DEFAULT 0,
                emergency_contact TEXT,
                notes TEXT,
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Staff Schedule
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS staff_schedule (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                staff_id INTEGER NOT NULL,
                schedule_date DATE NOT NULL,
                shift TEXT NOT NULL,
                start_time TIME,
                end_time TIME,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (staff_id) REFERENCES staff(id)
            )
        """)

        # Maintenance Schedule
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS maintenance_schedule (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                equipment_id INTEGER NOT NULL,
                task_type TEXT NOT NULL,
                task_name TEXT NOT NULL,
                description TEXT,
                frequency_days INTEGER DEFAULT 7,
                last_completed TIMESTAMP,
                next_due TIMESTAMP,
                assigned_to INTEGER,
                status TEXT DEFAULT 'scheduled',
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (equipment_id) REFERENCES equipment(id),
                FOREIGN KEY (assigned_to) REFERENCES staff(id)
            )
        """)

        # Daily Tasks/Briefings
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS daily_tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_date DATE NOT NULL,
                task_type TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                assigned_to INTEGER,
                priority TEXT DEFAULT 'normal',
                status TEXT DEFAULT 'pending',
                completed_at TIMESTAMP,
                completed_by INTEGER,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (assigned_to) REFERENCES staff(id),
                FOREIGN KEY (completed_by) REFERENCES staff(id)
            )
        """)

        # Production Schedule
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS production_schedule (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                schedule_date DATE NOT NULL,
                product_id INTEGER NOT NULL,
                tank_id INTEGER,
                planned_quantity REAL NOT NULL,
                status TEXT DEFAULT 'planned',
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (product_id) REFERENCES products(id),
                FOREIGN KEY (tank_id) REFERENCES equipment(id)
            )
        """)

        # Briefing Log
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS briefing_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                briefing_date DATE NOT NULL,
                briefing_type TEXT NOT NULL,
                content TEXT NOT NULL,
                sent_via TEXT DEFAULT 'zalo',
                sent_to TEXT,
                sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                acknowledged INTEGER DEFAULT 0
            )
        """)

        # Invoices
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS invoices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                invoice_number TEXT UNIQUE NOT NULL,
                customer_id INTEGER NOT NULL,
                invoice_date DATE NOT NULL,
                payment_method TEXT DEFAULT 'cash',
                subtotal REAL DEFAULT 0,
                sct_amount REAL DEFAULT 0,
                vat_amount REAL DEFAULT 0,
                environmental_tax REAL DEFAULT 0,
                total REAL DEFAULT 0,
                status TEXT DEFAULT 'draft',
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (customer_id) REFERENCES customers(id)
            )
        """)

        # Invoice Items
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS invoice_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                invoice_id INTEGER NOT NULL,
                product_id INTEGER NOT NULL,
                quantity REAL NOT NULL,
                unit_price REAL NOT NULL,
                line_total REAL NOT NULL,
                FOREIGN KEY (invoice_id) REFERENCES invoices(id),
                FOREIGN KEY (product_id) REFERENCES products(id)
            )
        """)

        # Zalo Messages
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS zalo_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                recipient TEXT NOT NULL,
                message TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Zalo Templates
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS zalo_templates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                content TEXT NOT NULL,
                category TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Chat History (persistent conversation storage)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chat_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # ==================== RECIPE MANAGEMENT ====================
        
        # Recipes
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS recipes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                product_id INTEGER,
                style TEXT,
                batch_size REAL NOT NULL,
                batch_size_unit TEXT DEFAULT 'L',
                boil_time INTEGER DEFAULT 60,
                efficiency REAL DEFAULT 75,
                og REAL,
                fg REAL,
                abv REAL,
                ibu REAL,
                srm REAL,
                description TEXT,
                notes TEXT,
                version INTEGER DEFAULT 1,
                is_active INTEGER DEFAULT 1,
                created_by INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (product_id) REFERENCES products(id),
                FOREIGN KEY (created_by) REFERENCES staff(id)
            )
        """)

        # Recipe Fermentables
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS recipe_fermentables (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                recipe_id INTEGER NOT NULL,
                material_id INTEGER,
                name TEXT NOT NULL,
                amount REAL NOT NULL,
                unit TEXT DEFAULT 'kg',
                percentage REAL DEFAULT 0,
                potential REAL DEFAULT 0,
                color REAL DEFAULT 0,
                notes TEXT,
                FOREIGN KEY (recipe_id) REFERENCES recipes(id) ON DELETE CASCADE,
                FOREIGN KEY (material_id) REFERENCES raw_materials(id)
            )
        """)

        # Recipe Hops
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS recipe_hops (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                recipe_id INTEGER NOT NULL,
                material_id INTEGER,
                name TEXT NOT NULL,
                amount REAL NOT NULL,
                unit TEXT DEFAULT 'g',
                alpha_acid REAL DEFAULT 0,
                boil_time INTEGER DEFAULT 60,
                use_type TEXT DEFAULT 'boil',
                ibu_contribution REAL DEFAULT 0,
                notes TEXT,
                FOREIGN KEY (recipe_id) REFERENCES recipes(id) ON DELETE CASCADE,
                FOREIGN KEY (material_id) REFERENCES raw_materials(id)
            )
        """)

        # Recipe Yeast
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS recipe_yeast (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                recipe_id INTEGER NOT NULL,
                yeast_id INTEGER,
                name TEXT NOT NULL,
                lab TEXT,
                product_id TEXT,
                form TEXT DEFAULT 'liquid',
                attenuation REAL DEFAULT 75,
                min_temp REAL DEFAULT 18,
                max_temp REAL DEFAULT 22,
                notes TEXT,
                FOREIGN KEY (recipe_id) REFERENCES recipes(id) ON DELETE CASCADE,
                FOREIGN KEY (yeast_id) REFERENCES yeast_strains(id)
            )
        """)

        # Recipe Mash Steps
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS recipe_mash_steps (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                recipe_id INTEGER NOT NULL,
                step_number INTEGER NOT NULL,
                name TEXT NOT NULL,
                step_type TEXT DEFAULT 'temperature',
                temperature REAL NOT NULL,
                duration INTEGER NOT NULL,
                notes TEXT,
                FOREIGN KEY (recipe_id) REFERENCES recipes(id) ON DELETE CASCADE
            )
        """)

        # Recipe Other Ingredients
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS recipe_other_ingredients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                recipe_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                ingredient_type TEXT,
                amount REAL NOT NULL,
                unit TEXT DEFAULT 'g',
                add_time TEXT,
                notes TEXT,
                FOREIGN KEY (recipe_id) REFERENCES recipes(id) ON DELETE CASCADE
            )
        """)

        # ==================== YEAST MANAGEMENT ====================
        
        # Yeast Strains
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS yeast_strains (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                lab TEXT,
                product_id TEXT,
                yeast_type TEXT DEFAULT 'ale',
                form TEXT DEFAULT 'liquid',
                attenuation_min REAL DEFAULT 70,
                attenuation_max REAL DEFAULT 80,
                flocculation TEXT DEFAULT 'medium',
                min_temp REAL DEFAULT 18,
                max_temp REAL DEFAULT 22,
                alcohol_tolerance REAL DEFAULT 10,
                description TEXT,
                notes TEXT,
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Yeast Inventory
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS yeast_inventory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                yeast_id INTEGER NOT NULL,
                lot_number TEXT,
                quantity REAL DEFAULT 0,
                unit TEXT DEFAULT 'packs',
                viability REAL DEFAULT 100,
                manufacture_date DATE,
                expiry_date DATE,
                storage_location TEXT,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (yeast_id) REFERENCES yeast_strains(id)
            )
        """)

        # Yeast Propagations
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS yeast_propagations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                yeast_id INTEGER NOT NULL,
                batch_id INTEGER,
                propagation_date DATE NOT NULL,
                starter_size REAL,
                starter_size_unit TEXT DEFAULT 'L',
                starter_gravity REAL,
                stir_plate INTEGER DEFAULT 0,
                temperature REAL,
                duration_hours INTEGER,
                cell_count_start REAL,
                cell_count_end REAL,
                viability REAL,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (yeast_id) REFERENCES yeast_strains(id),
                FOREIGN KEY (batch_id) REFERENCES production_batches(id)
            )
        """)

        # Yeast Usage Log
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS yeast_usage_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                yeast_id INTEGER NOT NULL,
                batch_id INTEGER,
                generation INTEGER DEFAULT 1,
                quantity_used REAL,
                unit TEXT DEFAULT 'mL',
                source TEXT DEFAULT 'new',
                repitched_from INTEGER,
                viability REAL,
                notes TEXT,
                used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (yeast_id) REFERENCES yeast_strains(id),
                FOREIGN KEY (batch_id) REFERENCES production_batches(id),
                FOREIGN KEY (repitched_from) REFERENCES yeast_usage_log(id)
            )
        """)

        # Yeast Viability Tests
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS yeast_viability_tests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                yeast_usage_id INTEGER NOT NULL,
                test_date DATE NOT NULL,
                test_method TEXT DEFAULT 'methylene_blue',
                viability REAL NOT NULL,
                cell_count REAL,
                cell_count_unit TEXT DEFAULT 'cells/mL',
                notes TEXT,
                tested_by INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (yeast_usage_id) REFERENCES yeast_usage_log(id),
                FOREIGN KEY (tested_by) REFERENCES staff(id)
            )
        """)

        # Insert default Zalo templates
        cursor.execute("SELECT COUNT(*) FROM zalo_templates")
        if cursor.fetchone()[0] == 0:
            templates = [
                ('Order Confirmation', 'Cảm ơn bạn đã đặt hàng! Đơn hàng #{order_number} đã được xác nhận. Tổng cộng: {total} VND. Chúng tôi sẽ giao hàng trong thời gian sớm nhất.', 'sales'),
                ('Delivery Notification', 'Đơn hàng #{order_number} của bạn đang được giao. Dự kiến giao trong ngày hôm nay. Vui lòng chuẩn bị nhận hàng.', 'delivery'),
                ('Payment Reminder', 'Xin chào! Đây là thông báo nhắc thanh toán cho đơn hàng #{order_number}. Số tiền cần thanh toán: {amount} VND. Cảm ơn bạn!', 'payment'),
                ('Promotion', '🍺 Khuyến mãi đặc biệt từ Brewery! Giảm {discount}% cho tất cả sản phẩm trong tuần này. Liên hệ ngay để đặt hàng!', 'promotion'),
                ('Daily Briefing', '📋 BÁO CÁO HÀNG NGÀY - {date}\n\nSản xuất: {production_summary}\nĐơn hàng: {orders_summary}\nCảnh báo tồn kho: {stock_alerts}', 'briefing'),
            ]
            for name, content, category in templates:
                cursor.execute("""
                    INSERT INTO zalo_templates (name, content, category)
                    VALUES (?, ?, ?)
                """, (name, content, category))

        # Shift Handovers
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS shift_handovers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                shift_date DATE NOT NULL,
                shift_type TEXT NOT NULL,
                from_staff_id INTEGER NOT NULL,
                to_staff_id INTEGER,
                production_status TEXT,
                quality_notes TEXT,
                equipment_status TEXT,
                pending_tasks TEXT,
                safety_notes TEXT,
                notes TEXT,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (from_staff_id) REFERENCES staff(id),
                FOREIGN KEY (to_staff_id) REFERENCES staff(id)
            )
        """)

        # SOPs (Standard Operating Procedures)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sops (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                category TEXT NOT NULL,
                content TEXT NOT NULL,
                version TEXT DEFAULT '1.0',
                created_by INTEGER,
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (created_by) REFERENCES staff(id)
            )
        """)

        # Performance Metrics
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS performance_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                metric_date DATE NOT NULL,
                category TEXT NOT NULL,
                metric_name TEXT NOT NULL,
                value REAL NOT NULL,
                unit TEXT,
                target REAL,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Training Records
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS training_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                staff_id INTEGER NOT NULL,
                training_date DATE NOT NULL,
                topic TEXT NOT NULL,
                trainer TEXT,
                duration_hours REAL DEFAULT 0,
                result TEXT,
                certificate_number TEXT,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (staff_id) REFERENCES staff(id)
            )
        """)

        # Users (Authentication)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                full_name TEXT,
                role TEXT DEFAULT 'viewer',
                email TEXT,
                is_active INTEGER DEFAULT 1,
                last_login TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Audit Log
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                action TEXT NOT NULL,
                table_name TEXT,
                record_id INTEGER,
                old_values TEXT,
                new_values TEXT,
                ip_address TEXT,
                user_agent TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)

        # Deliveries
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS deliveries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER NOT NULL,
                delivery_date DATE NOT NULL,
                delivery_time TEXT,
                driver_name TEXT,
                driver_phone TEXT,
                vehicle_info TEXT,
                status TEXT DEFAULT 'scheduled',
                notes TEXT,
                delivered_at TIMESTAMP,
                signature_data TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (order_id) REFERENCES sales_orders(id)
            )
        """)

        # Packaging Materials
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS packaging_materials (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                type TEXT NOT NULL,
                quantity INTEGER DEFAULT 0,
                unit TEXT NOT NULL,
                cost_per_unit REAL DEFAULT 0,
                supplier TEXT,
                reorder_level INTEGER DEFAULT 100,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Notifications
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                title TEXT NOT NULL,
                message TEXT NOT NULL,
                type TEXT DEFAULT 'info',
                is_read INTEGER DEFAULT 0,
                link TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)

        # Settings (key-value store)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Goals
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS goals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                target_value REAL DEFAULT 0,
                current_value REAL DEFAULT 0,
                unit TEXT DEFAULT '',
                priority TEXT DEFAULT 'normal',
                category TEXT DEFAULT 'general',
                status TEXT DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Agent Activity Log
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS agent_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                rule_name TEXT NOT NULL,
                category TEXT NOT NULL,
                trigger_data TEXT,
                action_taken TEXT,
                result TEXT,
                status TEXT DEFAULT 'completed',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Agent Rules Configuration
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS agent_rules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                category TEXT NOT NULL,
                description TEXT,
                trigger_condition TEXT NOT NULL,
                action_type TEXT NOT NULL,
                action_config TEXT NOT NULL,
                is_enabled INTEGER DEFAULT 1,
                autonomy_level TEXT DEFAULT 'semi',
                last_triggered TIMESTAMP,
                trigger_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Insert default agent rules
        cursor.execute("SELECT COUNT(*) FROM agent_rules")
        if cursor.fetchone()[0] == 0:
            default_rules = [
                ('low_stock_alert', 'inventory', 'Alert when materials are below minimum',
                 '{"field": "quantity", "operator": "<", "compare_field": "min_quantity"}',
                 'create_task', '{"title": "Reorder: {name}", "priority": "high", "type": "inventory"}',
                 1, 'semi'),
                ('critical_stock_alert', 'inventory', 'Urgent alert for critical stock levels',
                 '{"field": "quantity", "operator": "<", "value_multiplier": 0.5, "compare_field": "min_quantity"}',
                 'create_task_and_notify', '{"title": "URGENT Reorder: {name}", "priority": "urgent", "type": "inventory"}',
                 1, 'semi'),
                ('expiring_materials', 'inventory', 'Alert for materials expiring soon',
                 '{"field": "expiry_date", "operator": "<", "days_ahead": 7}',
                 'create_task', '{"title": "Use soon: {name} expires {expiry_date}", "priority": "normal", "type": "inventory"}',
                 1, 'semi'),
                ('cleaning_due', 'maintenance', 'Create task when equipment cleaning is due',
                 '{"field": "next_cleaning_due", "operator": "<", "hours_ahead": 24}',
                 'create_task', '{"title": "Clean {name}", "priority": "normal", "type": "maintenance"}',
                 1, 'auto'),
                ('batch_completed', 'production', 'Update inventory when batch completes',
                 '{"field": "status", "operator": "=", "value": "completed"}',
                 'update_inventory', '{"action": "add_product_stock"}',
                 1, 'auto'),
                ('quality_failed', 'quality', 'Halt production on quality failure',
                 '{"field": "passed", "operator": "=", "value": 0}',
                 'halt_and_notify', '{"title": "Quality Alert: Batch {batch_id}", "priority": "urgent"}',
                 1, 'semi'),
                ('daily_revenue_report', 'finance', 'Generate daily revenue summary',
                 '{"schedule": "daily", "time": "18:00"}',
                 'generate_report', '{"type": "daily_revenue"}',
                 1, 'auto'),
                ('low_profit_margin', 'finance', 'Alert when profit margin drops',
                 '{"field": "profit_margin", "operator": "<", "value": 20}',
                 'notify', '{"title": "Low Profit Margin Alert", "priority": "warning"}',
                 1, 'semi'),
            ]
            for rule in default_rules:
                cursor.execute("""
                    INSERT INTO agent_rules (name, category, description, trigger_condition,
                                           action_type, action_config, is_enabled, autonomy_level)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, rule)

        # Create default admin user
        cursor.execute("SELECT COUNT(*) FROM users")
        if cursor.fetchone()[0] == 0:
            import bcrypt
            default_password = bcrypt.hashpw('admin123'.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            cursor.execute("""
                INSERT INTO users (username, password_hash, full_name, role, email)
                VALUES (?, ?, ?, ?, ?)
            """, ('admin', default_password, 'System Administrator', 'admin', 'admin@brewery.vn'))

        # Performance Indices
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_batches_status ON production_batches(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_raw_materials_category ON raw_materials(category)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_sales_status ON sales_orders(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_equip_status ON equipment(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_equip_type ON equipment(equipment_type)")

        conn.commit()
        conn.close()

        # Initialize default equipment
        self._init_default_equipment()

    def _init_default_equipment(self):
        """Initialize default brewery equipment"""
        conn = self.get_connection()
        cursor = conn.cursor()

        # Check if equipment already exists
        cursor.execute("SELECT COUNT(*) FROM equipment")
        if cursor.fetchone()[0] > 0:
            conn.close()
            return

        # Fermenters - 2000L
        for i in range(1, 6):
            cursor.execute("""
                INSERT INTO equipment (name, equipment_type, capacity, capacity_unit, status)
                VALUES (?, 'fermenter', 2000, 'L', 'available')
            """, (f'Fermenter 2000L #{i}',))

        # Fermenters - 800L
        for i in range(1, 5):
            cursor.execute("""
                INSERT INTO equipment (name, equipment_type, capacity, capacity_unit, status)
                VALUES (?, 'fermenter', 800, 'L', 'available')
            """, (f'Fermenter 800L #{i}',))

        # Pilot Fermenters - 100L
        for i in range(1, 4):
            cursor.execute("""
                INSERT INTO equipment (name, equipment_type, capacity, capacity_unit, status)
                VALUES (?, 'fermenter', 100, 'L', 'available')
            """, (f'Pilot Fermenter 100L #{i}',))

        # Brewhouse
        cursor.execute("""
            INSERT INTO equipment (name, equipment_type, capacity, capacity_unit, status)
            VALUES ('Brewhouse', 'brewhouse', 1000, 'L', 'available')
        """)

        # Other equipment
        equipment_list = [
            ('Lime Juicer', 'processing', None, None),
            ('Canning Line', 'packaging', None, None),
            ('Glycol Chiller', 'cooling', None, None),
            ('Keg Washer', 'cleaning', None, None),
            ('Water Filter', 'filtration', None, None),
        ]

        for name, eq_type, capacity, unit in equipment_list:
            cursor.execute("""
                INSERT INTO equipment (name, equipment_type, capacity, capacity_unit, status)
                VALUES (?, ?, ?, ?, 'available')
            """, (name, eq_type, capacity, unit))

        conn.commit()
        conn.close()

        # Initialize maintenance schedules
        self._init_maintenance_schedules()

    def _init_maintenance_schedules(self):
        """Initialize default maintenance schedules"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM maintenance_schedule")
        if cursor.fetchone()[0] > 0:
            conn.close()
            return

        # Get equipment IDs
        cursor.execute("SELECT id, name, equipment_type FROM equipment")
        equipment = {row['name']: row['id'] for row in cursor.fetchall()}

        # Maintenance tasks
        maintenance_tasks = [
            # Fermenters
            ('Fermenter 2000L #1', 'cleaning', 'CIP Clean', 'Clean-in-place sanitation', 7),
            ('Fermenter 2000L #1', 'inspection', 'Gasket Inspection', 'Check and replace gaskets if needed', 30),
            ('Fermenter 800L #1', 'cleaning', 'CIP Clean', 'Clean-in-place sanitation', 7),
            ('Pilot Fermenter 100L #1', 'cleaning', 'Manual Clean', 'Manual cleaning and sanitization', 7),

            # Brewhouse
            ('Brewhouse', 'cleaning', 'Boil Kettle Clean', 'Clean boil kettle and heat exchanger', 3),
            ('Brewhouse', 'maintenance', 'Burner Check', 'Inspect and clean gas burners', 30),

            # Lime Juicer
            ('Lime Juicer', 'cleaning', 'Daily Clean', 'Clean juicer components', 1),
            ('Lime Juicer', 'maintenance', 'Blade Inspection', 'Check juicer blades for wear', 14),

            # Canning Line
            ('Canning Line', 'cleaning', 'Line Flush', 'Flush canning line with sanitizer', 1),
            ('Canning Line', 'maintenance', 'Seamer Check', 'Inspect and adjust seaming heads', 7),

            # Glycol Chiller
            ('Glycol Chiller', 'maintenance', 'Glycol Level Check', 'Check glycol concentration and level', 7),
            ('Glycol Chiller', 'maintenance', 'Compressor Service', 'Full compressor inspection', 90),

            # Keg Washer
            ('Keg Washer', 'cleaning', 'Nozzle Clean', 'Clean washing nozzles', 3),
            ('Keg Washer', 'maintenance', 'Pump Check', 'Inspect washing pumps', 30),

            # Water Filter
            ('Water Filter', 'maintenance', 'Filter Replacement', 'Replace filter cartridges', 30),
            ('Water Filter', 'cleaning', 'System Flush', 'Backflush filter system', 7),
        ]

        for eq_name, task_type, task_name, desc, freq_days in maintenance_tasks:
            if eq_name in equipment:
                next_due = datetime.now() + timedelta(days=freq_days)
                cursor.execute("""
                    INSERT INTO maintenance_schedule 
                    (equipment_id, task_type, task_name, description, frequency_days, next_due, status)
                    VALUES (?, ?, ?, ?, ?, ?, 'scheduled')
                """, (equipment[eq_name], task_type, task_name, desc, freq_days, next_due))

        conn.commit()
        conn.close()

    # ==================== EQUIPMENT ====================

    def get_equipment(self, equipment_type: str = None, status: str = None) -> List[Dict]:
        conn = self.get_connection()
        cursor = conn.cursor()
        query = "SELECT * FROM equipment WHERE 1=1"
        params = []

        if equipment_type:
            query += " AND equipment_type = ?"
            params.append(equipment_type)
        if status:
            query += " AND status = ?"
            params.append(status)

        query += " ORDER BY equipment_type, name"
        cursor.execute(query, params)
        result = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return result

    def get_tank_assignments(self) -> List[Dict]:
        """Get current tank assignments with batch and product info"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                e.id, e.name, e.equipment_type, e.capacity, e.capacity_unit,
                e.status, e.last_cleaned, e.next_cleaning_due,
                pb.id as batch_id, pb.batch_number, pb.status as batch_status,
                pb.planned_quantity, pb.actual_quantity, pb.start_date,
                p.name as product_name, p.style as product_style
            FROM equipment e
            LEFT JOIN (
                SELECT pb1.*, ROW_NUMBER() OVER (PARTITION BY pb1.tank_id ORDER BY pb1.start_date DESC) as rn
                FROM production_batches pb1
                WHERE pb1.status IN ('brewing', 'fermenting', 'conditioning')
            ) pb ON e.id = pb.tank_id AND pb.rn = 1
            LEFT JOIN products p ON pb.product_id = p.id
            WHERE e.equipment_type = 'fermenter'
            ORDER BY e.capacity DESC, e.name
        """)
        result = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return result

    def update_equipment_status(self, equipment_id: int, status: str, batch_id: int = None) -> bool:
        conn = self.get_connection()
        cursor = conn.cursor()
        if batch_id:
            cursor.execute("""
                UPDATE equipment SET status = ?, current_batch_id = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (status, batch_id, equipment_id))
        else:
            cursor.execute("""
                UPDATE equipment SET status = ?, current_batch_id = NULL, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (status, equipment_id))
        conn.commit()
        result = cursor.rowcount > 0
        conn.close()
        return result

    def mark_tank_cleaned(self, equipment_id: int) -> bool:
        conn = self.get_connection()
        cursor = conn.cursor()
        next_cleaning = datetime.now() + timedelta(days=7)
        cursor.execute("""
            UPDATE equipment 
            SET last_cleaned = CURRENT_TIMESTAMP, next_cleaning_due = ?, status = 'available'
            WHERE id = ?
        """, (next_cleaning, equipment_id))
        conn.commit()
        result = cursor.rowcount > 0
        conn.close()
        return result

    # ==================== MAINTENANCE ====================

    def get_maintenance_schedule(self, equipment_id: int = None, status: str = None) -> List[Dict]:
        conn = self.get_connection()
        cursor = conn.cursor()
        query = """
            SELECT ms.*, e.name as equipment_name, e.equipment_type,
                   s.name as assigned_to_name
            FROM maintenance_schedule ms
            JOIN equipment e ON ms.equipment_id = e.id
            LEFT JOIN staff s ON ms.assigned_to = s.id
            WHERE 1=1
        """
        params = []

        if equipment_id:
            query += " AND ms.equipment_id = ?"
            params.append(equipment_id)
        if status:
            query += " AND ms.status = ?"
            params.append(status)

        query += " ORDER BY ms.next_due ASC"
        cursor.execute(query, params)
        result = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return result

    def get_overdue_maintenance(self) -> List[Dict]:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT ms.*, e.name as equipment_name, e.equipment_type,
                   s.name as assigned_to_name
            FROM maintenance_schedule ms
            JOIN equipment e ON ms.equipment_id = e.id
            LEFT JOIN staff s ON ms.assigned_to = s.id
            WHERE ms.next_due < CURRENT_TIMESTAMP AND ms.status != 'completed'
            ORDER BY ms.next_due ASC
        """)
        result = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return result

    def complete_maintenance(self, maintenance_id: int, notes: str = None) -> bool:
        conn = self.get_connection()
        cursor = conn.cursor()

        # Get maintenance task details
        cursor.execute("SELECT * FROM maintenance_schedule WHERE id = ?", (maintenance_id,))
        task = cursor.fetchone()
        if not task:
            conn.close()
            return False

        # Calculate next due date
        next_due = datetime.now() + timedelta(days=task['frequency_days'])

        cursor.execute("""
            UPDATE maintenance_schedule 
            SET last_completed = CURRENT_TIMESTAMP, next_due = ?, status = 'scheduled', notes = ?
            WHERE id = ?
        """, (next_due, notes, maintenance_id))

        conn.commit()
        result = cursor.rowcount > 0
        conn.close()
        return result

    # ==================== DAILY TASKS ====================

    def create_daily_task(self, data: Dict) -> int:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO daily_tasks (task_date, task_type, title, description, 
                                     assigned_to, priority, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            data['task_date'], data['task_type'], data['title'],
            data.get('description'), data.get('assigned_to'),
            data.get('priority', 'normal'), data.get('notes')
        ))
        conn.commit()
        lastrowid = cursor.lastrowid
        conn.close()
        return lastrowid

    def get_daily_tasks(self, task_date: str = None, status: str = None, assigned_to: int = None) -> List[Dict]:
        conn = self.get_connection()
        cursor = conn.cursor()
        query = """
            SELECT dt.*, s.name as assigned_to_name, 
                   c.name as completed_by_name
            FROM daily_tasks dt
            LEFT JOIN staff s ON dt.assigned_to = s.id
            LEFT JOIN staff c ON dt.completed_by = c.id
            WHERE 1=1
        """
        params = []

        if task_date:
            query += " AND dt.task_date = ?"
            params.append(task_date)
        if status:
            query += " AND dt.status = ?"
            params.append(status)
        if assigned_to:
            query += " AND dt.assigned_to = ?"
            params.append(assigned_to)

        query += " ORDER BY dt.priority DESC, dt.created_at ASC"
        cursor.execute(query, params)
        result = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return result

    def complete_daily_task(self, task_id: int, completed_by: int, notes: str = None) -> bool:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE daily_tasks 
            SET status = 'completed', completed_at = CURRENT_TIMESTAMP, 
                completed_by = ?, notes = COALESCE(?, notes)
            WHERE id = ?
        """, (completed_by, notes, task_id))
        conn.commit()
        result = cursor.rowcount > 0
        conn.close()
        return result

    def generate_daily_briefing(self, task_date: str) -> Dict:
        """Generate daily briefing content"""
        tasks = self.get_daily_tasks(task_date=task_date)
        overdue_maintenance = self.get_overdue_maintenance()
        tank_assignments = self.get_tank_assignments()
        low_stock = self.get_low_stock_alerts()

        briefing = {
            'date': task_date,
            'tasks': tasks,
            'overdue_maintenance': overdue_maintenance,
            'tank_status': tank_assignments,
            'low_stock_alerts': low_stock,
            'summary': {
                'total_tasks': len(tasks),
                'pending_tasks': len([t for t in tasks if t['status'] == 'pending']),
                'completed_tasks': len([t for t in tasks if t['status'] == 'completed']),
                'overdue_maintenance_count': len(overdue_maintenance),
                'tanks_in_use': len([t for t in tank_assignments if t['batch_id']]),
                'low_stock_count': len(low_stock)
            }
        }
        return briefing

    def log_briefing(self, task_date: str, briefing_type: str, content: str, sent_to: str = None) -> int:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO briefing_log (briefing_date, briefing_type, content, sent_to)
            VALUES (?, ?, ?, ?)
        """, (task_date, briefing_type, content, sent_to))
        conn.commit()
        lastrowid = cursor.lastrowid
        conn.close()
        return lastrowid

    # ==================== RAW MATERIALS ====================

    def add_raw_material(self, data: Dict) -> int:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO raw_materials (name, category, unit, quantity, min_quantity,
                cost_per_unit, supplier, origin, expiry_date, storage_location, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data['name'], data['category'], data['unit'],
            data.get('quantity', 0), data.get('min_quantity', 0),
            data.get('cost_per_unit', 0), data.get('supplier'),
            data.get('origin'), data.get('expiry_date'),
            data.get('storage_location'), data.get('notes')
        ))
        conn.commit()
        lastrowid = cursor.lastrowid
        conn.close()
        return lastrowid

    def get_raw_materials(self, category: str = None, low_stock: bool = False) -> List[Dict]:
        conn = self.get_connection()
        cursor = conn.cursor()
        query = "SELECT * FROM raw_materials WHERE 1=1"
        params = []

        if category:
            query += " AND category = ?"
            params.append(category)
        if low_stock:
            query += " AND quantity <= min_quantity"

        query += " ORDER BY name"
        cursor.execute(query, params)
        result = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return result

    def update_raw_material(self, material_id: int, data: Dict) -> bool:
        conn = self.get_connection()
        cursor = conn.cursor()
        fields = []
        values = []
        for key, value in data.items():
            if key != 'id':
                fields.append(f"{key} = ?")
                values.append(value)
        values.append(material_id)
        cursor.execute(f"UPDATE raw_materials SET {', '.join(fields)}, updated_at = CURRENT_TIMESTAMP WHERE id = ?", values)
        conn.commit()
        result = cursor.rowcount > 0
        conn.close()
        return result

    def adjust_inventory(self, material_id: int, change: float, reason: str = '') -> bool:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE raw_materials SET quantity = quantity + ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (change, material_id))
        conn.commit()
        result = cursor.rowcount > 0
        conn.close()
        return result

    def get_low_stock_alerts(self) -> List[Dict]:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT *, (min_quantity - quantity) as shortage
            FROM raw_materials
            WHERE quantity <= min_quantity
            ORDER BY (min_quantity - quantity) DESC
        """)
        result = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return result

    def get_expiring_materials(self, days: int = 30) -> List[Dict]:
        conn = self.get_connection()
        cursor = conn.cursor()
        future_date = (datetime.now() + timedelta(days=days)).strftime('%Y-%m-%d')
        cursor.execute("""
            SELECT *, julianday(expiry_date) - julianday('now') as days_remaining
            FROM raw_materials
            WHERE expiry_date IS NOT NULL AND expiry_date <= ?
            ORDER BY expiry_date ASC
        """, (future_date,))
        result = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return result

    # ==================== PRODUCTS ====================

    def add_product(self, data: Dict) -> int:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO products (name, style, abv, ibu, description, price_per_unit)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            data['name'], data.get('style'), data.get('abv', 0),
            data.get('ibu', 0), data.get('description'),
            data.get('price_per_unit', 0)
        ))
        conn.commit()
        lastrowid = cursor.lastrowid
        conn.close()
        return lastrowid

    def get_products(self, active_only: bool = True) -> List[Dict]:
        conn = self.get_connection()
        cursor = conn.cursor()
        query = "SELECT * FROM products"
        if active_only:
            query += " WHERE is_active = 1"
        query += " ORDER BY name"
        cursor.execute(query)
        result = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return result

    def update_product(self, product_id: int, data: Dict) -> bool:
        conn = self.get_connection()
        cursor = conn.cursor()
        fields = []
        values = []
        for key, value in data.items():
            if key != 'id':
                fields.append(f"{key} = ?")
                values.append(value)
        values.append(product_id)
        cursor.execute(f"UPDATE products SET {', '.join(fields)} WHERE id = ?", values)
        conn.commit()
        result = cursor.rowcount > 0
        conn.close()
        return result

    # ==================== PRODUCTION BATCHES ====================

    def create_batch(self, data: Dict) -> int:
        conn = self.get_connection()
        cursor = conn.cursor()
        batch_number = data.get('batch_number') or self._generate_batch_number(cursor)
        cursor.execute("""
            INSERT INTO production_batches (batch_number, product_id, tank_id, planned_quantity,
                status, start_date, brewer_id, equipment_used, notes)
            VALUES (?, ?, ?, ?, 'planned', ?, ?, ?, ?)
        """, (
            batch_number, data['product_id'], data.get('tank_id'),
            data['planned_quantity'], data.get('start_date'),
            data.get('brewer_id'), data.get('equipment_used'),
            data.get('notes')
        ))
        batch_id = cursor.lastrowid

        # Update tank status if assigned
        if data.get('tank_id'):
            cursor.execute("""
                UPDATE equipment SET status = 'in_use', current_batch_id = ?
                WHERE id = ?
            """, (batch_id, data['tank_id']))

        conn.commit()
        conn.close()
        return batch_id

    def _generate_batch_number(self, cursor) -> str:
        cursor.execute("SELECT COUNT(*) FROM production_batches")
        count = cursor.fetchone()[0]
        today = datetime.now().strftime("%Y%m%d")
        return f"BTH-{today}-{count + 1:04d}"

    def get_batches(self, status: str = None, product_id: int = None) -> List[Dict]:
        conn = self.get_connection()
        cursor = conn.cursor()
        query = """
            SELECT pb.*, p.name as product_name, p.style as product_style,
                   s.name as brewer_name, e.name as tank_name, e.capacity as tank_capacity
            FROM production_batches pb
            JOIN products p ON pb.product_id = p.id
            LEFT JOIN staff s ON pb.brewer_id = s.id
            LEFT JOIN equipment e ON pb.tank_id = e.id
            WHERE 1=1
        """
        params = []

        if status:
            query += " AND pb.status = ?"
            params.append(status)
        if product_id:
            query += " AND pb.product_id = ?"
            params.append(product_id)

        query += " ORDER BY pb.created_at DESC"
        cursor.execute(query, params)
        result = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return result

    def update_batch_status(self, batch_id: int, status: str, actual_qty: float = None) -> bool:
        conn = self.get_connection()
        cursor = conn.cursor()

        if actual_qty is not None:
            cursor.execute("""
                UPDATE production_batches SET status = ?, actual_quantity = ?
                WHERE id = ?
            """, (status, actual_qty, batch_id))
        else:
            cursor.execute("""
                UPDATE production_batches SET status = ?
                WHERE id = ?
            """, (status, batch_id))

        # If batch is completed or cancelled, free up the tank
        if status in ('completed', 'cancelled'):
            cursor.execute("""
                UPDATE equipment SET status = 'available', current_batch_id = NULL
                WHERE current_batch_id = ?
            """, (batch_id,))

        conn.commit()
        result = cursor.rowcount > 0
        conn.close()
        return result

    def add_batch_ingredients(self, batch_id: int, ingredients: List[Dict]) -> bool:
        conn = self.get_connection()
        cursor = conn.cursor()
        for ing in ingredients:
            cursor.execute("""
                INSERT INTO batch_ingredients (batch_id, material_id, quantity_used, cost_at_time)
                VALUES (?, ?, ?, ?)
            """, (batch_id, ing['material_id'], ing['quantity_used'], ing.get('cost_at_time', 0)))
            # Deduct from inventory
            cursor.execute("""
                UPDATE raw_materials SET quantity = quantity - ?
                WHERE id = ?
            """, (ing['quantity_used'], ing['material_id']))
        conn.commit()
        conn.close()
        return True

    # ==================== QUALITY ====================

    def add_quality_record(self, data: Dict) -> int:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO quality_records (batch_id, check_type, value, unit, passed, inspector, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            data['batch_id'], data['check_type'], data.get('value'),
            data.get('unit'), data.get('passed', 1),
            data.get('inspector'), data.get('notes')
        ))
        conn.commit()
        lastrowid = cursor.lastrowid
        conn.close()
        return lastrowid

    def get_quality_records(self, batch_id: int = None) -> List[Dict]:
        conn = self.get_connection()
        cursor = conn.cursor()
        query = """
            SELECT qr.*, pb.batch_number, p.name as product_name
            FROM quality_records qr
            JOIN production_batches pb ON qr.batch_id = pb.id
            JOIN products p ON pb.product_id = p.id
            WHERE 1=1
        """
        params = []
        if batch_id:
            query += " AND qr.batch_id = ?"
            params.append(batch_id)
        query += " ORDER BY qr.check_date DESC"
        cursor.execute(query, params)
        result = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return result

    # ==================== CUSTOMERS ====================

    def add_customer(self, data: Dict) -> int:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO customers (name, type, contact_person, phone, email,
                address, city, province, tax_id, credit_limit, payment_terms, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data['name'], data.get('type', 'retail'), data.get('contact_person'),
            data.get('phone'), data.get('email'), data.get('address'),
            data.get('city'), data.get('province'), data.get('tax_id'),
            data.get('credit_limit', 0), data.get('payment_terms', 'COD'),
            data.get('notes')
        ))
        conn.commit()
        lastrowid = cursor.lastrowid
        conn.close()
        return lastrowid

    def get_customers(self, active_only: bool = True) -> List[Dict]:
        conn = self.get_connection()
        cursor = conn.cursor()
        query = "SELECT * FROM customers"
        if active_only:
            query += " WHERE is_active = 1"
        query += " ORDER BY name"
        cursor.execute(query)
        result = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return result

    def update_customer(self, customer_id: int, data: Dict) -> bool:
        conn = self.get_connection()
        cursor = conn.cursor()
        fields = []
        values = []
        for key, value in data.items():
            if key != 'id':
                fields.append(f"{key} = ?")
                values.append(value)
        values.append(customer_id)
        cursor.execute(f"UPDATE customers SET {', '.join(fields)} WHERE id = ?", values)
        conn.commit()
        result = cursor.rowcount > 0
        conn.close()
        return result

    def get_top_customers(self, limit: int = 10) -> List[Dict]:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT c.*, COALESCE(SUM(so.total_amount), 0) as total_spent,
                   COUNT(so.id) as order_count
            FROM customers c
            LEFT JOIN sales_orders so ON c.id = so.customer_id
            GROUP BY c.id
            ORDER BY total_spent DESC
            LIMIT ?
        """, (limit,))
        result = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return result

    # ==================== SALES ====================

    def _generate_order_number(self, cursor) -> str:
        cursor.execute("SELECT COUNT(*) FROM sales_orders")
        count = cursor.fetchone()[0]
        today = datetime.now().strftime("%Y%m%d")
        return f"ORD-{today}-{count + 1:04d}"

    def create_sales_order(self, data: Dict) -> int:
        conn = self.get_connection()
        cursor = conn.cursor()
        order_number = self._generate_order_number(cursor)

        # Calculate total
        total = sum(
            item['quantity'] * item['unit_price'] * (1 - item.get('discount', 0) / 100)
            for item in data['items']
        )

        cursor.execute("""
            INSERT INTO sales_orders (order_number, customer_id, order_date,
                delivery_date, total_amount, notes)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            order_number, data['customer_id'], data['order_date'],
            data.get('delivery_date'), total, data.get('notes')
        ))
        order_id = cursor.lastrowid

        # Add items
        for item in data['items']:
            subtotal = item['quantity'] * item['unit_price'] * (1 - item.get('discount', 0) / 100)
            cursor.execute("""
                INSERT INTO order_items (order_id, product_id, quantity, unit_price, discount, subtotal)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (order_id, item['product_id'], item['quantity'],
                  item['unit_price'], item.get('discount', 0), subtotal))

        conn.commit()
        conn.close()
        return order_id

    def get_sales_orders(self, status: str = None) -> List[Dict]:
        conn = self.get_connection()
        cursor = conn.cursor()
        query = """
            SELECT so.*, c.name as customer_name, c.city as customer_city
            FROM sales_orders so
            JOIN customers c ON so.customer_id = c.id
            WHERE 1=1
        """
        params = []
        if status:
            query += " AND so.status = ?"
            params.append(status)
        query += " ORDER BY so.created_at DESC"
        cursor.execute(query, params)
        result = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return result

    def get_order_details(self, order_id: int) -> Dict:
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT so.*, c.name as customer_name, c.phone as customer_phone,
                   c.address as customer_address
            FROM sales_orders so
            JOIN customers c ON so.customer_id = c.id
            WHERE so.id = ?
        """, (order_id,))
        order = dict(cursor.fetchone())

        cursor.execute("""
            SELECT oi.*, p.name as product_name, p.style as product_style
            FROM order_items oi
            JOIN products p ON oi.product_id = p.id
            WHERE oi.order_id = ?
        """, (order_id,))
        order['items'] = [dict(row) for row in cursor.fetchall()]

        conn.close()
        return order

    def update_order_status(self, order_id: int, status: str) -> bool:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE sales_orders SET status = ? WHERE id = ?", (status, order_id))
        conn.commit()
        result = cursor.rowcount > 0
        conn.close()
        return result

    def update_payment_status(self, order_id: int, status: str) -> bool:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE sales_orders SET payment_status = ? WHERE id = ?", (status, order_id))
        conn.commit()
        result = cursor.rowcount > 0
        conn.close()
        return result

    # ==================== FINANCE ====================

    def add_transaction(self, data: Dict) -> int:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO financial_transactions (transaction_date, type, category,
                amount, description, payment_method, reference_id, reference_type)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data['transaction_date'], data['type'], data.get('category'),
            data['amount'], data.get('description'), data.get('payment_method'),
            data.get('reference_id'), data.get('reference_type')
        ))
        conn.commit()
        lastrowid = cursor.lastrowid
        conn.close()
        return lastrowid

    def get_transactions(self, start_date: str = None, end_date: str = None,
                         type_filter: str = None, category: str = None) -> List[Dict]:
        conn = self.get_connection()
        cursor = conn.cursor()
        query = "SELECT * FROM financial_transactions WHERE 1=1"
        params = []

        if start_date:
            query += " AND transaction_date >= ?"
            params.append(start_date)
        if end_date:
            query += " AND transaction_date <= ?"
            params.append(end_date)
        if type_filter:
            query += " AND type = ?"
            params.append(type_filter)
        if category:
            query += " AND category = ?"
            params.append(category)

        query += " ORDER BY transaction_date DESC, created_at DESC"
        cursor.execute(query, params)
        result = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return result

    def get_financial_summary(self, start_date: str = None, end_date: str = None) -> Dict:
        conn = self.get_connection()
        cursor = conn.cursor()

        query_income = "SELECT COALESCE(SUM(amount), 0) FROM financial_transactions WHERE type = 'income'"
        query_expense = "SELECT COALESCE(SUM(amount), 0) FROM financial_transactions WHERE type = 'expense'"
        params = []

        if start_date:
            query_income += " AND transaction_date >= ?"
            query_expense += " AND transaction_date >= ?"
            params.append(start_date)
        if end_date:
            query_income += " AND transaction_date <= ?"
            query_expense += " AND transaction_date <= ?"
            params.append(end_date)

        cursor.execute(query_income, params)
        total_income = cursor.fetchone()[0]

        cursor.execute(query_expense, params)
        total_expense = cursor.fetchone()[0]

        conn.close()
        return {
            'total_income': total_income,
            'total_expense': total_expense,
            'net_profit': total_income - total_expense
        }

    def get_production_report(self, start_date: str = None, end_date: str = None) -> List[Dict]:
        conn = self.get_connection()
        cursor = conn.cursor()
        query = """
            SELECT p.name, p.style, COUNT(pb.id) as batch_count,
                   SUM(pb.planned_quantity) as total_planned,
                   SUM(pb.actual_quantity) as total_actual
            FROM products p
            LEFT JOIN production_batches pb ON p.id = pb.product_id
            WHERE 1=1
        """
        params = []
        if start_date:
            query += " AND pb.start_date >= ?"
            params.append(start_date)
        if end_date:
            query += " AND pb.start_date <= ?"
            params.append(end_date)
        query += " GROUP BY p.id ORDER BY total_actual DESC"
        cursor.execute(query, params)
        result = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return result

    def get_sales_report(self, start_date: str = None, end_date: str = None) -> List[Dict]:
        conn = self.get_connection()
        cursor = conn.cursor()
        query = """
            SELECT p.name, p.style, SUM(oi.quantity) as total_sold,
                   SUM(oi.subtotal) as total_revenue
            FROM products p
            LEFT JOIN order_items oi ON p.id = oi.product_id
            LEFT JOIN sales_orders so ON oi.order_id = so.id
            WHERE 1=1
        """
        params = []
        if start_date:
            query += " AND so.order_date >= ?"
            params.append(start_date)
        if end_date:
            query += " AND so.order_date <= ?"
            params.append(end_date)
        query += " GROUP BY p.id ORDER BY total_revenue DESC"
        cursor.execute(query, params)
        result = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return result

    # ==================== STAFF ====================

    def add_staff(self, data: Dict) -> int:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO staff (name, position, department, phone, email,
                hire_date, salary, emergency_contact, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data['name'], data['position'], data.get('department'),
            data.get('phone'), data.get('email'), data.get('hire_date'),
            data.get('salary', 0), data.get('emergency_contact'),
            data.get('notes')
        ))
        conn.commit()
        lastrowid = cursor.lastrowid
        conn.close()
        return lastrowid

    def get_staff(self, department: str = None, active_only: bool = True) -> List[Dict]:
        conn = self.get_connection()
        cursor = conn.cursor()
        query = "SELECT * FROM staff WHERE 1=1"
        params = []
        if department:
            query += " AND department = ?"
            params.append(department)
        if active_only:
            query += " AND is_active = 1"
        query += " ORDER BY name"
        cursor.execute(query, params)
        result = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return result

    def update_staff(self, staff_id: int, data: Dict) -> bool:
        conn = self.get_connection()
        cursor = conn.cursor()
        fields = []
        values = []
        for key, value in data.items():
            if key != 'id':
                fields.append(f"{key} = ?")
                values.append(value)
        values.append(staff_id)
        cursor.execute(f"UPDATE staff SET {', '.join(fields)} WHERE id = ?", values)
        conn.commit()
        result = cursor.rowcount > 0
        conn.close()
        return result

    def get_schedule(self, date: str = None, staff_id: int = None) -> List[Dict]:
        conn = self.get_connection()
        cursor = conn.cursor()
        query = """
            SELECT ss.*, s.name as staff_name, s.position, s.department
            FROM staff_schedule ss
            JOIN staff s ON ss.staff_id = s.id
            WHERE 1=1
        """
        params = []
        if date:
            query += " AND ss.schedule_date = ?"
            params.append(date)
        if staff_id:
            query += " AND ss.staff_id = ?"
            params.append(staff_id)
        query += " ORDER BY ss.shift, s.name"
        cursor.execute(query, params)
        result = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return result

    def add_schedule(self, data: Dict) -> int:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO staff_schedule (staff_id, schedule_date, shift, start_time, end_time, notes)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            data['staff_id'], data['schedule_date'], data['shift'],
            data.get('start_time'), data.get('end_time'), data.get('notes')
        ))
        conn.commit()
        lastrowid = cursor.lastrowid
        conn.close()
        return lastrowid

    # ==================== DASHBOARD ====================

    @cached(ttl=30)  # Cache for 30 seconds
    def get_dashboard_data(self) -> Dict:
        conn = self.get_connection()
        cursor = conn.cursor()

        # Active batches
        cursor.execute("SELECT COUNT(*) FROM production_batches WHERE status IN ('brewing', 'fermenting', 'conditioning')")
        active_batches = cursor.fetchone()[0]

        # Pending orders
        cursor.execute("SELECT COUNT(*) FROM sales_orders WHERE status = 'pending'")
        pending_orders = cursor.fetchone()[0]

        # Total customers
        cursor.execute("SELECT COUNT(*) FROM customers WHERE is_active = 1")
        total_customers = cursor.fetchone()[0]

        # Total products
        cursor.execute("SELECT COUNT(*) FROM products WHERE is_active = 1")
        total_products = cursor.fetchone()[0]

        # Total staff
        cursor.execute("SELECT COUNT(*) FROM staff WHERE is_active = 1")
        total_staff = cursor.fetchone()[0]

        # Monthly revenue
        first_of_month = datetime.now().strftime('%Y-%m-01')
        cursor.execute("""
            SELECT COALESCE(SUM(amount), 0) FROM financial_transactions
            WHERE type = 'income' AND transaction_date >= ?
        """, (first_of_month,))
        monthly_revenue = cursor.fetchone()[0]

        # Monthly expenses
        cursor.execute("""
            SELECT COALESCE(SUM(amount), 0) FROM financial_transactions
            WHERE type = 'expense' AND transaction_date >= ?
        """, (first_of_month,))
        monthly_expenses = cursor.fetchone()[0]

        # Batch status counts for production chart
        cursor.execute("SELECT COUNT(*) FROM production_batches WHERE status = 'planned'")
        planned_batches = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM production_batches WHERE status = 'brewing'")
        brewing_batches = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM production_batches WHERE status = 'fermenting'")
        fermenting_batches = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM production_batches WHERE status = 'completed'")
        completed_batches = cursor.fetchone()[0]

        conn.close()

        return {
            'active_batches': active_batches,
            'pending_orders': pending_orders,
            'total_customers': total_customers,
            'total_products': total_products,
            'total_staff': total_staff,
            'monthly_revenue': monthly_revenue,
            'monthly_expenses': monthly_expenses,
            'monthly_profit': monthly_revenue - monthly_expenses,
            'planned_batches': planned_batches,
            'brewing_batches': brewing_batches,
            'fermenting_batches': fermenting_batches,
            'completed_batches': completed_batches
        }

    # ==================== INVOICES ====================

    def get_invoices(self) -> List[Dict]:
        """Get all invoices"""
        conn = self.get_connection()
        cursor = conn.execute('''
            SELECT i.*, c.name as customer_name
            FROM invoices i
            LEFT JOIN customers c ON i.customer_id = c.id
            ORDER BY i.invoice_date DESC
        ''')
        result = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return result

    def get_next_invoice_number(self) -> str:
        """Get next invoice number"""
        conn = self.get_connection()
        cursor = conn.execute('SELECT COUNT(*) as count FROM invoices')
        count = cursor.fetchone()['count']
        from datetime import date
        today = date.today()
        conn.close()
        return f"HĐ-{today.strftime('%Y%m')}-{count + 1:04d}"

    def create_invoice(self, data: Dict) -> int:
        """Create invoice"""
        conn = self.get_connection()
        cursor = conn.execute('''
            INSERT INTO invoices (invoice_number, customer_id, invoice_date, payment_method,
                                subtotal, sct_amount, vat_amount, environmental_tax, total, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            self.get_next_invoice_number(),
            data['customer_id'],
            data['invoice_date'],
            data.get('payment_method', 'cash'),
            data['subtotal'],
            data['sct_amount'],
            data['vat_amount'],
            data['environmental_tax'],
            data['total'],
            data.get('notes')
        ))
        invoice_id = cursor.lastrowid

        # Insert invoice items
        for item in data['items']:
            conn.execute('''
                INSERT INTO invoice_items (invoice_id, product_id, quantity, unit_price, line_total)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                invoice_id,
                item['product_id'],
                item['quantity'],
                item['unit_price'],
                item['quantity'] * item['unit_price']
            ))

        conn.commit()
        conn.close()
        return invoice_id

    def get_invoice_details(self, invoice_id: int) -> Dict:
        """Get invoice details"""
        conn = self.get_connection()
        cursor = conn.execute('''
            SELECT i.*, c.name as customer_name, c.address as customer_address, c.tax_id as customer_tax_id
            FROM invoices i
            LEFT JOIN customers c ON i.customer_id = c.id
            WHERE i.id = ?
        ''', (invoice_id,))
        invoice = dict(cursor.fetchone())

        # Get items
        cursor = conn.execute('''
            SELECT ii.*, p.name as product_name
            FROM invoice_items ii
            LEFT JOIN products p ON ii.product_id = p.id
            WHERE ii.invoice_id = ?
        ''', (invoice_id,))
        invoice['items'] = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return invoice

    def get_tax_report(self, start_date: str = None, end_date: str = None) -> Dict:
        """Get tax report"""
        conn = self.get_connection()
        query = '''
            SELECT
                SUM(subtotal) as total_subtotal,
                SUM(sct_amount) as total_sct,
                SUM(vat_amount) as total_vat,
                SUM(environmental_tax) as total_env_tax,
                SUM(total) as grand_total,
                COUNT(*) as invoice_count
            FROM invoices
        '''
        params = []
        if start_date and end_date:
            query += ' WHERE invoice_date BETWEEN ? AND ?'
            params = [start_date, end_date]

        cursor = conn.execute(query, params)
        result = dict(cursor.fetchone())
        conn.close()
        return result

    # ==================== ZALO MESSAGING ====================

    def get_zalo_messages(self, limit: int = 50) -> List[Dict]:
        """Get Zalo messages"""
        conn = self.get_connection()
        cursor = conn.execute('''
            SELECT * FROM zalo_messages ORDER BY sent_at DESC LIMIT ?
        ''', (limit,))
        result = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return result

    def get_zalo_templates(self) -> List[Dict]:
        """Get Zalo templates"""
        conn = self.get_connection()
        cursor = conn.execute('SELECT * FROM zalo_templates ORDER BY name')
        result = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return result

    def log_zalo_message(self, recipient: str, message: str, status: str = 'demo'):
        """Log Zalo message"""
        conn = self.get_connection()
        conn.execute('''
            INSERT INTO zalo_messages (recipient, message, status, sent_at)
            VALUES (?, ?, ?, ?)
        ''', (recipient, message, status, datetime.now().isoformat()))
        conn.commit()
        conn.close()

    # ==================== SHIFT HANDOVERS ====================

    def get_shift_handovers(self, limit: int = 10) -> List[Dict]:
        """Get shift handovers"""
        conn = self.get_connection()
        cursor = conn.execute('''
            SELECT h.*,
                   s1.name as from_staff_name,
                   s2.name as to_staff_name
            FROM shift_handovers h
            LEFT JOIN staff s1 ON h.from_staff_id = s1.id
            LEFT JOIN staff s2 ON h.to_staff_id = s2.id
            ORDER BY h.shift_date DESC, h.created_at DESC
            LIMIT ?
        ''', (limit,))
        result = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return result

    def create_shift_handover(self, data: Dict) -> int:
        """Create shift handover"""
        conn = self.get_connection()
        cursor = conn.execute('''
            INSERT INTO shift_handovers (shift_date, shift_type, from_staff_id, to_staff_id,
                                        production_status, quality_notes, equipment_status,
                                        pending_tasks, safety_notes, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            data['shift_date'],
            data['shift_type'],
            data['from_staff_id'],
            data.get('to_staff_id'),
            data.get('production_status'),
            data.get('quality_notes'),
            data.get('equipment_status'),
            data.get('pending_tasks'),
            data.get('safety_notes'),
            data.get('notes')
        ))
        conn.commit()
        lastrowid = cursor.lastrowid
        conn.close()
        return lastrowid

    # ==================== SOPs ====================

    def get_sops(self) -> List[Dict]:
        """Get SOPs"""
        conn = self.get_connection()
        cursor = conn.execute('SELECT * FROM sops ORDER BY category, title')
        result = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return result

    def create_sop(self, data: Dict) -> int:
        """Create SOP"""
        conn = self.get_connection()
        cursor = conn.execute('''
            INSERT INTO sops (title, category, content, version, created_by)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            data['title'],
            data['category'],
            data['content'],
            data.get('version', '1.0'),
            data.get('created_by', 1)
        ))
        conn.commit()
        lastrowid = cursor.lastrowid
        conn.close()
        return lastrowid

    # ==================== PERFORMANCE METRICS ====================

    def get_performance_metrics(self, limit: int = 20) -> List[Dict]:
        """Get performance metrics"""
        conn = self.get_connection()
        cursor = conn.execute('''
            SELECT * FROM performance_metrics ORDER BY metric_date DESC LIMIT ?
        ''', (limit,))
        result = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return result

    def add_performance_metric(self, data: Dict) -> int:
        """Add performance metric"""
        conn = self.get_connection()
        cursor = conn.execute('''
            INSERT INTO performance_metrics (metric_date, category, metric_name, value, unit, target, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            data['metric_date'],
            data['category'],
            data['metric_name'],
            data['value'],
            data.get('unit'),
            data.get('target'),
            data.get('notes')
        ))
        conn.commit()
        lastrowid = cursor.lastrowid
        conn.close()
        return lastrowid

    # ==================== TRAINING RECORDS ====================

    def get_training_records(self, limit: int = 20) -> List[Dict]:
        """Get training records"""
        conn = self.get_connection()
        cursor = conn.execute('''
            SELECT t.*, s.name as staff_name
            FROM training_records t
            LEFT JOIN staff s ON t.staff_id = s.id
            ORDER BY t.training_date DESC
            LIMIT ?
        ''', (limit,))
        result = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return result

    def add_training_record(self, data: Dict) -> int:
        """Add training record"""
        conn = self.get_connection()
        cursor = conn.execute('''
            INSERT INTO training_records (staff_id, training_date, topic, trainer,
                                        duration_hours, result, certificate_number, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            data['staff_id'],
            data['training_date'],
            data['topic'],
            data.get('trainer'),
            data.get('duration_hours', 0),
            data.get('result'),
            data.get('certificate_number'),
            data.get('notes')
        ))
        conn.commit()
        lastrowid = cursor.lastrowid
        conn.close()
        return lastrowid

    # ==================== USER AUTHENTICATION ====================

    def get_user_by_username(self, username: str) -> Optional[Dict]:
        """Get user by username"""
        conn = self.get_connection()
        cursor = conn.execute('''
            SELECT * FROM users WHERE username = ? AND is_active = 1
        ''', (username,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

    def get_user_by_id(self, user_id: int) -> Optional[Dict]:
        """Get user by ID"""
        conn = self.get_connection()
        cursor = conn.execute('''
            SELECT * FROM users WHERE id = ? AND is_active = 1
        ''', (user_id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

    def get_all_users(self) -> List[Dict]:
        """Get all users"""
        conn = self.get_connection()
        cursor = conn.execute('''
            SELECT id, username, full_name, role, email, is_active, last_login, created_at
            FROM users ORDER BY username
        ''')
        result = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return result

    def create_user(self, data: Dict) -> int:
        """Create new user"""
        conn = self.get_connection()
        cursor = conn.execute('''
            INSERT INTO users (username, password_hash, full_name, role, email)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            data['username'],
            data['password_hash'],
            data.get('full_name'),
            data.get('role', 'viewer'),
            data.get('email')
        ))
        conn.commit()
        lastrowid = cursor.lastrowid
        conn.close()
        return lastrowid

    def update_user(self, user_id: int, data: Dict) -> bool:
        """Update user"""
        conn = self.get_connection()
        fields = []
        values = []
        for key, value in data.items():
            if key != 'id':
                fields.append(f"{key} = ?")
                values.append(value)
        values.append(user_id)
        cursor = conn.execute(f'''
            UPDATE users SET {', '.join(fields)}, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', values)
        conn.commit()
        result = cursor.rowcount > 0
        conn.close()
        return result

    def update_user_password(self, user_id: int, password_hash: str) -> bool:
        """Update user password"""
        conn = self.get_connection()
        cursor = conn.execute('''
            UPDATE users SET password_hash = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (password_hash, user_id))
        conn.commit()
        result = cursor.rowcount > 0
        conn.close()
        return result

    def update_user_last_login(self, user_id: int) -> bool:
        """Update user last login timestamp"""
        conn = self.get_connection()
        cursor = conn.execute('''
            UPDATE users SET last_login = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (user_id,))
        conn.commit()
        result = cursor.rowcount > 0
        conn.close()
        return result

    def deactivate_user(self, user_id: int) -> bool:
        """Deactivate user (soft delete)"""
        conn = self.get_connection()
        cursor = conn.execute('''
            UPDATE users SET is_active = 0, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (user_id,))
        conn.commit()
        result = cursor.rowcount > 0
        conn.close()
        return result

    # ==================== AUDIT LOG ====================

    def log_audit(self, user_id: int, action: str, table_name: str = None,
                  record_id: int = None, old_values: str = None,
                  new_values: str = None, ip_address: str = None,
                  user_agent: str = None) -> int:
        """Log audit entry"""
        conn = self.get_connection()
        cursor = conn.execute('''
            INSERT INTO audit_log (user_id, action, table_name, record_id,
                                  old_values, new_values, ip_address, user_agent)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, action, table_name, record_id,
              old_values, new_values, ip_address, user_agent))
        conn.commit()
        lastrowid = cursor.lastrowid
        conn.close()
        return lastrowid

    def get_audit_log(self, limit: int = 100, user_id: int = None,
                      table_name: str = None, action: str = None) -> List[Dict]:
        """Get audit log entries"""
        conn = self.get_connection()
        query = '''
            SELECT al.*, u.username, u.full_name as user_full_name
            FROM audit_log al
            LEFT JOIN users u ON al.user_id = u.id
            WHERE 1=1
        '''
        params = []

        if user_id:
            query += ' AND al.user_id = ?'
            params.append(user_id)
        if table_name:
            query += ' AND al.table_name = ?'
            params.append(table_name)
        if action:
            query += ' AND al.action = ?'
            params.append(action)

        query += ' ORDER BY al.created_at DESC LIMIT ?'
        params.append(limit)

        cursor = conn.execute(query, params)
        result = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return result

    # ==================== RECIPES ====================

    def create_recipe(self, data: Dict) -> int:
        """Create new recipe with new table structure"""
        conn = self.get_connection()
        cursor = conn.execute('''
            INSERT INTO recipes (name, product_id, style, batch_size, batch_size_unit, boil_time,
                                efficiency, og, fg, abv, ibu, srm, description, notes, created_by)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            data['name'],
            data.get('product_id'),
            data.get('style'),
            data.get('batch_size', 20),
            data.get('batch_size_unit', 'L'),
            data.get('boil_time', 60),
            data.get('efficiency', 75),
            data.get('og'),
            data.get('fg'),
            data.get('abv'),
            data.get('ibu'),
            data.get('srm'),
            data.get('description'),
            data.get('notes'),
            data.get('created_by')
        ))
        conn.commit()
        lastrowid = cursor.lastrowid
        conn.close()
        return lastrowid

    def get_recipes(self, active_only: bool = True) -> List[Dict]:
        """Get all recipes"""
        conn = self.get_connection()
        query = '''
            SELECT r.*, p.name as product_name, s.name as created_by_name
            FROM recipes r
            LEFT JOIN products p ON r.product_id = p.id
            LEFT JOIN staff s ON r.created_by = s.id
            WHERE 1=1
        '''
        if active_only:
            query += ' AND r.is_active = 1'
        query += ' ORDER BY r.name'

        cursor = conn.execute(query)
        result = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return result

    def get_recipe_details(self, recipe_id: int) -> Optional[Dict]:
        """Get recipe with all ingredients"""
        conn = self.get_connection()
        cursor = conn.execute('''
            SELECT r.*, p.name as product_name, s.name as created_by_name
            FROM recipes r
            LEFT JOIN products p ON r.product_id = p.id
            LEFT JOIN staff s ON r.created_by = s.id
            WHERE r.id = ?
        ''', (recipe_id,))
        row = cursor.fetchone()
        if not row:
            conn.close()
            return None

        recipe = dict(row)

        # Get fermentables
        cursor = conn.execute('''
            SELECT * FROM recipe_fermentables WHERE recipe_id = ? ORDER BY id
        ''', (recipe_id,))
        recipe['fermentables'] = [dict(row) for row in cursor.fetchall()]

        # Get hops
        cursor = conn.execute('''
            SELECT * FROM recipe_hops WHERE recipe_id = ? ORDER BY boil_time DESC
        ''', (recipe_id,))
        recipe['hops'] = [dict(row) for row in cursor.fetchall()]

        # Get yeast
        cursor = conn.execute('''
            SELECT * FROM recipe_yeast WHERE recipe_id = ? LIMIT 1
        ''', (recipe_id,))
        yeast_row = cursor.fetchone()
        recipe['yeast'] = dict(yeast_row) if yeast_row else None

        # Get mash steps
        cursor = conn.execute('''
            SELECT * FROM recipe_mash_steps WHERE recipe_id = ? ORDER BY step_number
        ''', (recipe_id,))
        recipe['mash_steps'] = [dict(row) for row in cursor.fetchall()]

        # Get other ingredients
        cursor = conn.execute('''
            SELECT * FROM recipe_other_ingredients WHERE recipe_id = ? ORDER BY ingredient_type
        ''', (recipe_id,))
        recipe['other_ingredients'] = [dict(row) for row in cursor.fetchall()]

        conn.close()
        return recipe

    def update_recipe(self, recipe_id: int, data: Dict) -> bool:
        """Update recipe"""
        conn = self.get_connection()
        fields = []
        values = []
        for key, value in data.items():
            if key not in ('id', 'fermentables', 'hops', 'yeast', 'mash_steps', 'other_ingredients'):
                fields.append(f"{key} = ?")
                values.append(value)
        values.append(recipe_id)
        cursor = conn.execute(f'''
            UPDATE recipes SET {', '.join(fields)}, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', values)
        conn.commit()
        result = cursor.rowcount > 0
        conn.close()
        return result

    def add_recipe_fermentable(self, data: Dict) -> int:
        """Add fermentable to recipe"""
        conn = self.get_connection()
        cursor = conn.execute('''
            INSERT INTO recipe_fermentables (recipe_id, material_id, name, amount, unit,
                                            percentage, potential, color, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            data['recipe_id'],
            data.get('material_id'),
            data['name'],
            data['amount'],
            data.get('unit', 'kg'),
            data.get('percentage', 0),
            data.get('potential', 0),
            data.get('color', 0),
            data.get('notes')
        ))
        conn.commit()
        lastrowid = cursor.lastrowid
        conn.close()
        return lastrowid

    def add_recipe_hop(self, data: Dict) -> int:
        """Add hop to recipe"""
        conn = self.get_connection()
        cursor = conn.execute('''
            INSERT INTO recipe_hops (recipe_id, material_id, name, amount, unit,
                                    alpha_acid, boil_time, use_type, ibu_contribution, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            data['recipe_id'],
            data.get('material_id'),
            data['name'],
            data['amount'],
            data.get('unit', 'g'),
            data.get('alpha_acid', 0),
            data.get('boil_time', 60),
            data.get('use_type', 'boil'),
            data.get('ibu_contribution', 0),
            data.get('notes')
        ))
        conn.commit()
        lastrowid = cursor.lastrowid
        conn.close()
        return lastrowid

    def add_recipe_yeast(self, data: Dict) -> int:
        """Add yeast to recipe"""
        conn = self.get_connection()
        cursor = conn.execute('''
            INSERT INTO recipe_yeast (recipe_id, yeast_id, name, lab, product_id,
                                     form, attenuation, min_temp, max_temp, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            data['recipe_id'],
            data.get('yeast_id'),
            data['name'],
            data.get('lab'),
            data.get('product_id'),
            data.get('form', 'liquid'),
            data.get('attenuation', 75),
            data.get('min_temp', 18),
            data.get('max_temp', 22),
            data.get('notes')
        ))
        conn.commit()
        lastrowid = cursor.lastrowid
        conn.close()
        return lastrowid

    def add_recipe_mash_step(self, data: Dict) -> int:
        """Add mash step to recipe"""
        conn = self.get_connection()
        cursor = conn.execute('''
            INSERT INTO recipe_mash_steps (recipe_id, step_number, name, step_type,
                                          temperature, duration, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            data['recipe_id'],
            data['step_number'],
            data['name'],
            data.get('step_type', 'temperature'),
            data['temperature'],
            data['duration'],
            data.get('notes')
        ))
        conn.commit()
        lastrowid = cursor.lastrowid
        conn.close()
        return lastrowid

    def add_recipe_other_ingredient(self, data: Dict) -> int:
        """Add other ingredient to recipe"""
        conn = self.get_connection()
        cursor = conn.execute('''
            INSERT INTO recipe_other_ingredients (recipe_id, name, ingredient_type,
                                                 amount, unit, add_time, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            data['recipe_id'],
            data['name'],
            data.get('ingredient_type'),
            data['amount'],
            data.get('unit', 'g'),
            data.get('add_time'),
            data.get('notes')
        ))
        conn.commit()
        lastrowid = cursor.lastrowid
        conn.close()
        return lastrowid

    def delete_recipe_ingredients(self, recipe_id: int) -> bool:
        """Delete all ingredients for a recipe"""
        conn = self.get_connection()
        conn.execute('DELETE FROM recipe_fermentables WHERE recipe_id = ?', (recipe_id,))
        conn.execute('DELETE FROM recipe_hops WHERE recipe_id = ?', (recipe_id,))
        conn.execute('DELETE FROM recipe_yeast WHERE recipe_id = ?', (recipe_id,))
        conn.execute('DELETE FROM recipe_mash_steps WHERE recipe_id = ?', (recipe_id,))
        conn.execute('DELETE FROM recipe_other_ingredients WHERE recipe_id = ?', (recipe_id,))
        conn.commit()
        conn.close()
        return True

    def delete_recipe(self, recipe_id: int) -> bool:
        """Delete a recipe and all its ingredients"""
        conn = self.get_connection()
        try:
            # First delete all ingredients
            conn.execute('DELETE FROM recipe_fermentables WHERE recipe_id = ?', (recipe_id,))
            conn.execute('DELETE FROM recipe_hops WHERE recipe_id = ?', (recipe_id,))
            conn.execute('DELETE FROM recipe_yeast WHERE recipe_id = ?', (recipe_id,))
            conn.execute('DELETE FROM recipe_mash_steps WHERE recipe_id = ?', (recipe_id,))
            conn.execute('DELETE FROM recipe_other_ingredients WHERE recipe_id = ?', (recipe_id,))
            # Then delete the recipe itself
            conn.execute('DELETE FROM recipes WHERE id = ?', (recipe_id,))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            conn.close()
            return False

    def import_beersmith_recipe(self, recipe_data: Dict) -> int:
        """Import a recipe from BeerSmith format"""
        conn = self.get_connection()
        
        # Insert main recipe
        cursor = conn.execute('''
            INSERT INTO recipes (name, product_id, style, batch_size, batch_size_unit,
                               boil_time, efficiency, og, fg, abv, ibu, srm,
                               description, notes, is_active)
            VALUES (?, NULL, ?, ?, 'L', ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
        ''', (
            recipe_data['name'],
            recipe_data.get('style', 'Unknown'),
            recipe_data.get('batch_size', 20),
            recipe_data.get('boil_time', 60),
            recipe_data.get('efficiency', 75),
            recipe_data.get('target_og'),
            recipe_data.get('target_fg'),
            recipe_data.get('target_abv'),
            recipe_data.get('target_ibu'),
            recipe_data.get('target_srm'),
            f"Imported from BeerSmith - {recipe_data.get('style', 'Unknown')}",
            recipe_data.get('notes', '')
        ))
        recipe_id = cursor.lastrowid
        
        # Insert fermentables
        for fermentable in recipe_data.get('fermentables', []):
            conn.execute('''
                INSERT INTO recipe_fermentables (recipe_id, name, amount, unit,
                                               percentage, potential, color, notes)
                VALUES (?, ?, ?, 'kg', ?, ?, ?, ?)
            ''', (
                recipe_id,
                fermentable['name'],
                fermentable['amount_kg'],
                fermentable.get('percentage', 0),
                fermentable.get('yield_pct', 75),
                fermentable.get('color_srm', 0),
                fermentable.get('notes', '')
            ))
        
        # Insert hops
        for hop in recipe_data.get('hops', []):
            conn.execute('''
                INSERT INTO recipe_hops (recipe_id, name, amount, unit,
                                       alpha_acid, boil_time, use_type, notes)
                VALUES (?, ?, ?, 'g', ?, ?, ?, ?)
            ''', (
                recipe_id,
                hop['name'],
                hop['amount_kg'] * 1000,  # Convert kg to g
                hop.get('alpha_acid', 0),
                hop.get('boil_time_min', 60),
                hop.get('use_type', 'boil'),
                hop.get('notes', '')
            ))
        
        # Insert yeast
        for yeast in recipe_data.get('yeasts', []):
            conn.execute('''
                INSERT INTO recipe_yeast (recipe_id, name, lab, product_id,
                                        form, attenuation, min_temp, max_temp, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                recipe_id,
                yeast['name'],
                yeast.get('lab', ''),
                yeast.get('product_id', ''),
                'liquid',
                yeast.get('attenuation', 75),
                yeast.get('min_temp', 18),
                yeast.get('max_temp', 22),
                yeast.get('notes', '')
            ))
        
        # Insert mash steps
        for i, step in enumerate(recipe_data.get('mash_steps', []), 1):
            conn.execute('''
                INSERT INTO recipe_mash_steps (recipe_id, step_number, name, step_type,
                                             temperature, duration, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                recipe_id,
                i,
                step['step_name'],
                step.get('step_type', 'temperature'),
                step['temperature'],
                step['duration_min'],
                step.get('notes', '')
            ))
        
        # Insert other ingredients
        for ingredient in recipe_data.get('other_ingredients', []):
            conn.execute('''
                INSERT INTO recipe_other_ingredients (recipe_id, name, ingredient_type,
                                                    amount, unit, add_time, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                recipe_id,
                ingredient['name'],
                ingredient.get('ingredient_type', 'other'),
                ingredient['amount'],
                ingredient.get('unit', 'g'),
                ingredient.get('use_time', 0),
                ingredient.get('notes', '')
            ))
        
        conn.commit()
        conn.close()
        return recipe_id

    def import_beersmith_file(self, file_path: str) -> List[Dict]:
        """Import recipes from BeerSmith .bsmx file"""
        from brewery_manager.utils.beersmith_import import BeerSmithParser, validate_recipe
        
        parser = BeerSmithParser()
        recipes = parser.parse_file(file_path)
        
        results = []
        for recipe_data in recipes:
            warnings = validate_recipe(recipe_data)
            if not warnings:  # Only import valid recipes
                recipe_id = self.import_beersmith_recipe(recipe_data)
                results.append({
                    'success': True,
                    'recipe_id': recipe_id,
                    'name': recipe_data['name']
                })
            else:
                results.append({
                    'success': False,
                    'name': recipe_data.get('name', 'Unknown'),
                    'warnings': warnings
                })
        
        return results

    # ==================== YEAST MANAGEMENT ====================

    def add_yeast_strain(self, data: Dict) -> int:
        """Add yeast strain"""
        conn = self.get_connection()
        cursor = conn.execute('''
            INSERT INTO yeast_strains (name, lab, product_id, yeast_type, form,
                                      attenuation_min, attenuation_max, flocculation,
                                      min_temp, max_temp, alcohol_tolerance, description, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            data['name'],
            data.get('lab'),
            data.get('product_id'),
            data.get('yeast_type', 'ale'),
            data.get('form', 'liquid'),
            data.get('attenuation_min', 70),
            data.get('attenuation_max', 80),
            data.get('flocculation', 'medium'),
            data.get('min_temp', 18),
            data.get('max_temp', 22),
            data.get('alcohol_tolerance', 10),
            data.get('description'),
            data.get('notes')
        ))
        conn.commit()
        lastrowid = cursor.lastrowid
        conn.close()
        return lastrowid

    def get_yeast_strains(self, active_only: bool = True) -> List[Dict]:
        """Get all yeast strains"""
        conn = self.get_connection()
        query = 'SELECT * FROM yeast_strains WHERE 1=1'
        if active_only:
            query += ' AND is_active = 1'
        query += ' ORDER BY name'
        cursor = conn.execute(query)
        result = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return result

    def get_yeast_inventory(self, yeast_id: int = None) -> List[Dict]:
        """Get yeast inventory"""
        conn = self.get_connection()
        query = '''
            SELECT yi.*, ys.name as yeast_name, ys.lab, ys.product_id
            FROM yeast_inventory yi
            JOIN yeast_strains ys ON yi.yeast_id = ys.id
            WHERE 1=1
        '''
        params = []
        if yeast_id:
            query += ' AND yi.yeast_id = ?'
            params.append(yeast_id)
        query += ' ORDER BY yi.expiry_date ASC'
        cursor = conn.execute(query, params)
        result = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return result

    def add_yeast_inventory(self, data: Dict) -> int:
        """Add yeast to inventory"""
        conn = self.get_connection()
        cursor = conn.execute('''
            INSERT INTO yeast_inventory (yeast_id, lot_number, quantity, unit, viability,
                                        manufacture_date, expiry_date, storage_location, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            data['yeast_id'],
            data.get('lot_number'),
            data.get('quantity', 0),
            data.get('unit', 'packs'),
            data.get('viability', 100),
            data.get('manufacture_date'),
            data.get('expiry_date'),
            data.get('storage_location'),
            data.get('notes')
        ))
        conn.commit()
        lastrowid = cursor.lastrowid
        conn.close()
        return lastrowid

    def log_yeast_usage(self, data: Dict) -> int:
        """Log yeast usage"""
        conn = self.get_connection()
        cursor = conn.execute('''
            INSERT INTO yeast_usage_log (yeast_id, batch_id, generation, quantity_used,
                                        unit, source, repitched_from, viability, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            data['yeast_id'],
            data.get('batch_id'),
            data.get('generation', 1),
            data.get('quantity_used'),
            data.get('unit', 'mL'),
            data.get('source', 'new'),
            data.get('repitched_from'),
            data.get('viability'),
            data.get('notes')
        ))
        conn.commit()
        lastrowid = cursor.lastrowid
        conn.close()
        return lastrowid

    def get_yeast_usage_log(self, yeast_id: int = None, batch_id: int = None) -> List[Dict]:
        """Get yeast usage log"""
        conn = self.get_connection()
        query = '''
            SELECT yul.*, ys.name as yeast_name, pb.batch_number
            FROM yeast_usage_log yul
            JOIN yeast_strains ys ON yul.yeast_id = ys.id
            LEFT JOIN production_batches pb ON yul.batch_id = pb.id
            WHERE 1=1
        '''
        params = []
        if yeast_id:
            query += ' AND yul.yeast_id = ?'
            params.append(yeast_id)
        if batch_id:
            query += ' AND yul.batch_id = ?'
            params.append(batch_id)
        query += ' ORDER BY yul.used_at DESC'
        cursor = conn.execute(query, params)
        result = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return result

    def add_yeast_viability_test(self, data: Dict) -> int:
        """Add yeast viability test"""
        conn = self.get_connection()
        cursor = conn.execute('''
            INSERT INTO yeast_viability_tests (yeast_usage_id, test_date, test_method,
                                              viability, cell_count, cell_count_unit, notes, tested_by)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            data['yeast_usage_id'],
            data['test_date'],
            data.get('test_method', 'methylene_blue'),
            data['viability'],
            data.get('cell_count'),
            data.get('cell_count_unit', 'cells/mL'),
            data.get('notes'),
            data.get('tested_by')
        ))
        conn.commit()
        lastrowid = cursor.lastrowid
        conn.close()
        return lastrowid

    def add_yeast_propagation(self, data: Dict) -> int:
        """Add yeast propagation record"""
        conn = self.get_connection()
        cursor = conn.execute('''
            INSERT INTO yeast_propagations (yeast_id, batch_id, propagation_date, starter_size,
                                          starter_size_unit, starter_gravity, stir_plate,
                                          temperature, duration_hours, cell_count_start,
                                          cell_count_end, viability, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            data['yeast_id'],
            data.get('batch_id'),
            data['propagation_date'],
            data.get('starter_size'),
            data.get('starter_size_unit', 'L'),
            data.get('starter_gravity'),
            data.get('stir_plate', 0),
            data.get('temperature'),
            data.get('duration_hours'),
            data.get('cell_count_start'),
            data.get('cell_count_end'),
            data.get('viability'),
            data.get('notes')
        ))
        conn.commit()
        lastrowid = cursor.lastrowid
        conn.close()
        return lastrowid

    # ==================== DELIVERIES ====================

    def create_delivery(self, data: Dict) -> int:
        """Create delivery"""
        conn = self.get_connection()
        cursor = conn.execute('''
            INSERT INTO deliveries (order_id, delivery_date, delivery_time, driver_name,
                                   driver_phone, vehicle_info, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            data['order_id'],
            data['delivery_date'],
            data.get('delivery_time'),
            data.get('driver_name'),
            data.get('driver_phone'),
            data.get('vehicle_info'),
            data.get('notes')
        ))
        conn.commit()
        lastrowid = cursor.lastrowid
        conn.close()
        return lastrowid

    def get_deliveries(self, status: str = None, delivery_date: str = None) -> List[Dict]:
        """Get deliveries"""
        conn = self.get_connection()
        query = '''
            SELECT d.*, so.order_number, c.name as customer_name, c.address as customer_address,
                   c.phone as customer_phone
            FROM deliveries d
            JOIN sales_orders so ON d.order_id = so.id
            JOIN customers c ON so.customer_id = c.id
            WHERE 1=1
        '''
        params = []

        if status:
            query += ' AND d.status = ?'
            params.append(status)
        if delivery_date:
            query += ' AND d.delivery_date = ?'
            params.append(delivery_date)

        query += ' ORDER BY d.delivery_date DESC, d.delivery_time'

        cursor = conn.execute(query, params)
        result = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return result

    def update_delivery_status(self, delivery_id: int, status: str) -> bool:
        """Update delivery status"""
        conn = self.get_connection()
        if status == 'delivered':
            cursor = conn.execute('''
                UPDATE deliveries SET status = ?, delivered_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (status, delivery_id))
        else:
            cursor = conn.execute('''
                UPDATE deliveries SET status = ?
                WHERE id = ?
            ''', (status, delivery_id))
        conn.commit()
        result = cursor.rowcount > 0
        conn.close()
        return result

    # ==================== PACKAGING MATERIALS ====================

    def add_packaging_material(self, data: Dict) -> int:
        """Add packaging material"""
        conn = self.get_connection()
        cursor = conn.execute('''
            INSERT INTO packaging_materials (name, type, quantity, unit, cost_per_unit,
                                           supplier, reorder_level, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            data['name'],
            data['type'],
            data.get('quantity', 0),
            data['unit'],
            data.get('cost_per_unit', 0),
            data.get('supplier'),
            data.get('reorder_level', 100),
            data.get('notes')
        ))
        conn.commit()
        lastrowid = cursor.lastrowid
        conn.close()
        return lastrowid

    def get_packaging_materials(self, material_type: str = None) -> List[Dict]:
        """Get packaging materials"""
        conn = self.get_connection()
        query = 'SELECT * FROM packaging_materials WHERE 1=1'
        params = []

        if material_type:
            query += ' AND type = ?'
            params.append(material_type)

        query += ' ORDER BY type, name'

        cursor = conn.execute(query, params)
        result = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return result

    def update_packaging_material(self, material_id: int, data: Dict) -> bool:
        """Update packaging material"""
        conn = self.get_connection()
        fields = []
        values = []
        for key, value in data.items():
            if key != 'id':
                fields.append(f"{key} = ?")
                values.append(value)
        values.append(material_id)
        cursor = conn.execute(f'''
            UPDATE packaging_materials SET {', '.join(fields)}, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', values)
        conn.commit()
        result = cursor.rowcount > 0
        conn.close()
        return result

    # ==================== NOTIFICATIONS ====================

    def create_notification(self, data: Dict) -> int:
        """Create notification"""
        conn = self.get_connection()
        cursor = conn.execute('''
            INSERT INTO notifications (user_id, title, message, type, link)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            data.get('user_id'),
            data['title'],
            data['message'],
            data.get('type', 'info'),
            data.get('link')
        ))
        conn.commit()
        lastrowid = cursor.lastrowid
        conn.close()
        return lastrowid

    def get_notifications(self, user_id: int, unread_only: bool = False) -> List[Dict]:
        """Get notifications for user"""
        conn = self.get_connection()
        query = 'SELECT * FROM notifications WHERE user_id = ?'
        params = [user_id]

        if unread_only:
            query += ' AND is_read = 0'

        query += ' ORDER BY created_at DESC LIMIT 50'

        cursor = conn.execute(query, params)
        result = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return result

    def mark_notification_read(self, notification_id: int) -> bool:
        """Mark notification as read"""
        conn = self.get_connection()
        cursor = conn.execute('''
            UPDATE notifications SET is_read = 1 WHERE id = ?
        ''', (notification_id,))
        conn.commit()
        result = cursor.rowcount > 0
        conn.close()
        return result

    def mark_all_notifications_read(self, user_id: int) -> bool:
        """Mark all notifications as read for user"""
        conn = self.get_connection()
        cursor = conn.execute('''
            UPDATE notifications SET is_read = 1 WHERE user_id = ? AND is_read = 0
        ''', (user_id,))
        conn.commit()
        result = cursor.rowcount > 0
        conn.close()
        return result

    # ==================== AGENT LOGS ====================

    def create_agent_log(self, data: Dict) -> int:
        """Create agent activity log entry"""
        conn = self.get_connection()
        cursor = conn.execute('''
            INSERT INTO agent_logs (rule_name, category, trigger_data, action_taken, result, status)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            data['rule_name'],
            data['category'],
            data.get('trigger_data'),
            data.get('action_taken'),
            data.get('result'),
            data.get('status', 'completed')
        ))
        conn.commit()
        lastrowid = cursor.lastrowid
        conn.close()
        return lastrowid

    def get_agent_logs(self, limit: int = 100, category: str = None) -> List[Dict]:
        """Get agent activity logs"""
        conn = self.get_connection()
        query = 'SELECT * FROM agent_logs WHERE 1=1'
        params = []

        if category:
            query += ' AND category = ?'
            params.append(category)

        query += ' ORDER BY created_at DESC LIMIT ?'
        params.append(limit)

        cursor = conn.execute(query, params)
        result = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return result

    # ==================== AGENT RULES ====================

    def get_agent_rules(self, category: str = None, enabled_only: bool = False) -> List[Dict]:
        """Get agent rules"""
        conn = self.get_connection()
        query = 'SELECT * FROM agent_rules WHERE 1=1'
        params = []

        if category:
            query += ' AND category = ?'
            params.append(category)
        if enabled_only:
            query += ' AND is_enabled = 1'

        query += ' ORDER BY category, name'

        cursor = conn.execute(query, params)
        result = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return result

    def get_agent_rule(self, rule_id: int) -> Optional[Dict]:
        """Get single agent rule"""
        conn = self.get_connection()
        cursor = conn.execute('SELECT * FROM agent_rules WHERE id = ?', (rule_id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

    def update_agent_rule(self, rule_id: int, data: Dict) -> bool:
        """Update agent rule"""
        conn = self.get_connection()
        fields = []
        values = []
        for key, value in data.items():
            if key != 'id':
                fields.append(f"{key} = ?")
                values.append(value)
        values.append(rule_id)
        cursor = conn.execute(f'''
            UPDATE agent_rules SET {', '.join(fields)}, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', values)
        conn.commit()
        result = cursor.rowcount > 0
        conn.close()
        return result

    def toggle_agent_rule(self, rule_id: int) -> bool:
        """Toggle agent rule enabled/disabled"""
        conn = self.get_connection()
        cursor = conn.execute('''
            UPDATE agent_rules SET is_enabled = CASE WHEN is_enabled = 1 THEN 0 ELSE 1 END,
                                  updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (rule_id,))
        conn.commit()
        result = cursor.rowcount > 0
        conn.close()
        return result

    def increment_rule_trigger(self, rule_id: int) -> bool:
        """Increment rule trigger count"""
        conn = self.get_connection()
        cursor = conn.execute('''
            UPDATE agent_rules SET trigger_count = trigger_count + 1,
                                  last_triggered = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (rule_id,))
        conn.commit()
        result = cursor.rowcount > 0
        conn.close()
        return result

    # ==================== LOT TRACKING ====================

    def generate_lot_number(self, item_type: str = 'RM') -> str:
        """Generate unique lot number"""
        prefix = 'RM' if item_type == 'raw_material' else 'FG'
        today = datetime.now().strftime('%Y%m%d')
        conn = self.get_connection()
        cursor = conn.execute('SELECT COUNT(*) FROM lot_tracking WHERE DATE(created_at) = DATE("now")')
        count = cursor.fetchone()[0]
        conn.close()
        return f"{prefix}-{today}-{count + 1:04d}"

    def create_lot(self, data: Dict) -> int:
        """Create new lot for tracking"""
        conn = self.get_connection()
        lot_number = data.get('lot_number') or self.generate_lot_number(data['item_type'])
        cursor = conn.execute('''
            INSERT INTO lot_tracking (lot_number, material_id, product_id, item_type,
                                     quantity, unit, received_date, expiry_date,
                                     supplier, supplier_lot, storage_location, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            lot_number,
            data.get('material_id'),
            data.get('product_id'),
            data['item_type'],
            data['quantity'],
            data['unit'],
            data['received_date'],
            data.get('expiry_date'),
            data.get('supplier'),
            data.get('supplier_lot'),
            data.get('storage_location'),
            data.get('notes')
        ))
        conn.commit()
        lastrowid = cursor.lastrowid
        conn.close()
        return lastrowid

    def get_lots(self, item_type: str = None, status: str = None, material_id: int = None) -> List[Dict]:
        """Get lots with optional filters"""
        conn = self.get_connection()
        query = '''
            SELECT lt.*, rm.name as material_name, p.name as product_name
            FROM lot_tracking lt
            LEFT JOIN raw_materials rm ON lt.material_id = rm.id
            LEFT JOIN products p ON lt.product_id = p.id
            WHERE 1=1
        '''
        params = []
        
        if item_type:
            query += ' AND lt.item_type = ?'
            params.append(item_type)
        if status:
            query += ' AND lt.status = ?'
            params.append(status)
        if material_id:
            query += ' AND lt.material_id = ?'
            params.append(material_id)
        
        query += ' ORDER BY lt.created_at DESC'
        cursor = conn.execute(query, params)
        result = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return result

    def get_lot_by_id(self, lot_id: int) -> Optional[Dict]:
        """Get lot by ID"""
        conn = self.get_connection()
        cursor = conn.execute('''
            SELECT lt.*, rm.name as material_name, p.name as product_name
            FROM lot_tracking lt
            LEFT JOIN raw_materials rm ON lt.material_id = rm.id
            LEFT JOIN products p ON lt.product_id = p.id
            WHERE lt.id = ?
        ''', (lot_id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

    def update_lot_status(self, lot_id: int, status: str) -> bool:
        """Update lot status"""
        conn = self.get_connection()
        cursor = conn.execute('UPDATE lot_tracking SET status = ? WHERE id = ?', (status, lot_id))
        conn.commit()
        result = cursor.rowcount > 0
        conn.close()
        return result

    def update_lot_quantity(self, lot_id: int, quantity_change: float) -> bool:
        """Update lot quantity (negative for usage)"""
        conn = self.get_connection()
        cursor = conn.execute('''
            UPDATE lot_tracking 
            SET quantity = quantity + ?,
                status = CASE WHEN quantity + ? <= 0 THEN 'depleted' ELSE status END
            WHERE id = ?
        ''', (quantity_change, quantity_change, lot_id))
        conn.commit()
        result = cursor.rowcount > 0
        conn.close()
        return result

    # ==================== BATCH COGS ====================

    def add_batch_cogs_item(self, data: Dict) -> int:
        """Add COGS item to batch"""
        conn = self.get_connection()
        variance = data.get('actual_cost', 0) - data.get('planned_cost', 0)
        cursor = conn.execute('''
            INSERT INTO batch_cogs (batch_id, category, item_name, planned_cost, actual_cost, variance, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            data['batch_id'],
            data['category'],
            data['item_name'],
            data.get('planned_cost', 0),
            data.get('actual_cost', 0),
            variance,
            data.get('notes')
        ))
        conn.commit()
        lastrowid = cursor.lastrowid
        conn.close()
        return lastrowid

    def get_batch_cogs(self, batch_id: int) -> List[Dict]:
        """Get COGS items for a batch"""
        conn = self.get_connection()
        cursor = conn.execute('''
            SELECT * FROM batch_cogs WHERE batch_id = ? ORDER BY category, item_name
        ''', (batch_id,))
        result = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return result

    def get_batch_cogs_summary(self, batch_id: int) -> Dict:
        """Get COGS summary for a batch"""
        conn = self.get_connection()
        cursor = conn.execute('''
            SELECT 
                category,
                SUM(planned_cost) as planned_total,
                SUM(actual_cost) as actual_total,
                SUM(variance) as variance_total
            FROM batch_cogs 
            WHERE batch_id = ?
            GROUP BY category
        ''', (batch_id,))
        categories = [dict(row) for row in cursor.fetchall()]
        
        cursor = conn.execute('''
            SELECT 
                SUM(planned_cost) as total_planned,
                SUM(actual_cost) as total_actual,
                SUM(variance) as total_variance
            FROM batch_cogs 
            WHERE batch_id = ?
        ''', (batch_id,))
        totals = dict(cursor.fetchone())
        conn.close()
        
        return {
            'categories': categories,
            'totals': totals
        }

    def calculate_batch_cogs_from_ingredients(self, batch_id: int) -> bool:
        """Auto-calculate COGS from batch ingredients"""
        conn = self.get_connection()
        
        # Get batch ingredients with costs
        cursor = conn.execute('''
            SELECT bi.*, rm.name as material_name, rm.category
            FROM batch_ingredients bi
            JOIN raw_materials rm ON bi.material_id = rm.id
            WHERE bi.batch_id = ?
        ''', (batch_id,))
        ingredients = [dict(row) for row in cursor.fetchall()]
        
        # Clear existing COGS items
        conn.execute('DELETE FROM batch_cogs WHERE batch_id = ? AND category = "ingredients"', (batch_id,))
        
        # Add COGS items from ingredients
        for ing in ingredients:
            actual_cost = ing['quantity_used'] * ing['cost_at_time']
            conn.execute('''
                INSERT INTO batch_cogs (batch_id, category, item_name, planned_cost, actual_cost, variance)
                VALUES (?, 'ingredients', ?, ?, ?, ?)
            ''', (batch_id, ing['material_name'], actual_cost, actual_cost, 0))
        
        conn.commit()
        conn.close()
        return True

    # ==================== TRACEABILITY ====================

    def add_traceability_link(self, data: Dict) -> int:
        """Add traceability link"""
        conn = self.get_connection()
        cursor = conn.execute('''
            INSERT INTO traceability_chain (batch_id, source_type, source_id, 
                                           destination_type, destination_id, quantity, unit)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            data['batch_id'],
            data['source_type'],
            data['source_id'],
            data['destination_type'],
            data.get('destination_id'),
            data['quantity'],
            data['unit']
        ))
        conn.commit()
        lastrowid = cursor.lastrowid
        conn.close()
        return lastrowid

    def get_traceability_chain(self, batch_id: int) -> List[Dict]:
        """Get full traceability chain for a batch"""
        conn = self.get_connection()
        cursor = conn.execute('''
            SELECT tc.*, 
                   CASE 
                       WHEN tc.source_type = 'raw_material_lot' THEN rm.name
                       WHEN tc.source_type = 'finished_good_lot' THEN p.name
                   END as source_name,
                   lt.lot_number as source_lot
            FROM traceability_chain tc
            LEFT JOIN lot_tracking lt ON tc.source_id = lt.id
            LEFT JOIN raw_materials rm ON lt.material_id = rm.id AND tc.source_type = 'raw_material_lot'
            LEFT JOIN products p ON lt.product_id = p.id AND tc.source_type = 'finished_good_lot'
            WHERE tc.batch_id = ?
            ORDER BY tc.traced_at
        ''', (batch_id,))
        result = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return result

    def trace_lot_forward(self, lot_id: int) -> List[Dict]:
        """Trace a lot forward through the supply chain"""
        conn = self.get_connection()
        cursor = conn.execute('''
            SELECT tc.*, pb.batch_number, p.name as product_name
            FROM traceability_chain tc
            JOIN production_batches pb ON tc.batch_id = pb.id
            LEFT JOIN products p ON pb.product_id = p.id
            WHERE tc.source_id = ?
            ORDER BY tc.traced_at DESC
        ''', (lot_id,))
        result = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return result

    def trace_lot_backward(self, lot_id: int) -> List[Dict]:
        """Trace a lot backward to its sources"""
        conn = self.get_connection()
        cursor = conn.execute('''
            SELECT tc.*, lt.lot_number, rm.name as material_name
            FROM traceability_chain tc
            JOIN lot_tracking lt ON tc.source_id = lt.id
            LEFT JOIN raw_materials rm ON lt.material_id = rm.id
            WHERE tc.destination_type = 'finished_good_lot' AND tc.destination_id = ?
            ORDER BY tc.traced_at
        ''', (lot_id,))
        result = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return result

    # ==================== FINISHED GOODS LOTS ====================

    def generate_fg_lot_number(self) -> str:
        """Generate finished goods lot number"""
        today = datetime.now().strftime('%Y%m%d')
        conn = self.get_connection()
        cursor = conn.execute('SELECT COUNT(*) FROM finished_goods_lots WHERE DATE(created_at) = DATE("now")')
        count = cursor.fetchone()[0]
        conn.close()
        return f"FG-{today}-{count + 1:04d}"

    def create_finished_goods_lot(self, data: Dict) -> int:
        """Create finished goods lot from completed batch"""
        conn = self.get_connection()
        lot_number = data.get('lot_number') or self.generate_fg_lot_number()
        cursor = conn.execute('''
            INSERT INTO finished_goods_lots (lot_number, batch_id, product_id, 
                                            quantity_produced, quantity_remaining, unit,
                                            production_date, expiry_date, abv, ibu, ph, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            lot_number,
            data['batch_id'],
            data['product_id'],
            data['quantity_produced'],
            data['quantity_produced'],  # Initially remaining = produced
            data.get('unit', 'L'),
            data['production_date'],
            data.get('expiry_date'),
            data.get('abv'),
            data.get('ibu'),
            data.get('ph'),
            data.get('notes')
        ))
        lot_id = cursor.lastrowid
        
        # Also create lot tracking entry
        self.create_lot({
            'lot_number': lot_number,
            'product_id': data['product_id'],
            'item_type': 'finished_good',
            'quantity': data['quantity_produced'],
            'unit': data.get('unit', 'L'),
            'received_date': data['production_date'],
            'expiry_date': data.get('expiry_date'),
            'notes': data.get('notes')
        })
        
        conn.commit()
        conn.close()
        return lot_id

    def get_finished_goods_lots(self, product_id: int = None, status: str = None) -> List[Dict]:
        """Get finished goods lots"""
        conn = self.get_connection()
        query = '''
            SELECT fgl.*, p.name as product_name, p.style as product_style, pb.batch_number
            FROM finished_goods_lots fgl
            JOIN products p ON fgl.product_id = p.id
            JOIN production_batches pb ON fgl.batch_id = pb.id
            WHERE 1=1
        '''
        params = []
        
        if product_id:
            query += ' AND fgl.product_id = ?'
            params.append(product_id)
        if status:
            query += ' AND fgl.status = ?'
            params.append(status)
        
        query += ' ORDER BY fgl.production_date DESC'
        cursor = conn.execute(query, params)
        result = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return result

    def update_fg_lot_quantity(self, lot_id: int, quantity_shipped: float) -> bool:
        """Update finished goods lot quantity after shipment"""
        conn = self.get_connection()
        cursor = conn.execute('''
            UPDATE finished_goods_lots 
            SET quantity_remaining = quantity_remaining - ?,
                status = CASE WHEN quantity_remaining - ? <= 0 THEN 'shipped' ELSE status END
            WHERE id = ?
        ''', (quantity_shipped, quantity_shipped, lot_id))
        conn.commit()
        result = cursor.rowcount > 0
        conn.close()
        return result

    def get_inventory_value_report(self) -> Dict:
        """Get inventory value report with lot details"""
        conn = self.get_connection()
        
        # Raw materials by lot
        cursor = conn.execute('''
            SELECT lt.*, rm.name as material_name, rm.cost_per_unit,
                   (lt.quantity * rm.cost_per_unit) as total_value
            FROM lot_tracking lt
            JOIN raw_materials rm ON lt.material_id = rm.id
            WHERE lt.item_type = 'raw_material' AND lt.status = 'active' AND lt.quantity > 0
            ORDER BY rm.category, rm.name
        ''')
        raw_material_lots = [dict(row) for row in cursor.fetchall()]
        
        # Finished goods by lot
        cursor = conn.execute('''
            SELECT fgl.*, p.name as product_name, p.price_per_unit,
                   (fgl.quantity_remaining * p.price_per_unit) as total_value
            FROM finished_goods_lots fgl
            JOIN products p ON fgl.product_id = p.id
            WHERE fgl.status = 'available' AND fgl.quantity_remaining > 0
            ORDER BY p.name
        ''')
        finished_goods_lots = [dict(row) for row in cursor.fetchall()]
        
        # Totals
        rm_total = sum(lot['total_value'] for lot in raw_material_lots)
        fg_total = sum(lot['total_value'] for lot in finished_goods_lots)
        
        conn.close()
        
        return {
            'raw_material_lots': raw_material_lots,
            'finished_goods_lots': finished_goods_lots,
            'raw_material_total': rm_total,
            'finished_goods_total': fg_total,
            'grand_total': rm_total + fg_total
        }


    # ==================== SPRINT 3: PACKAGING MODULE ====================
    
    def create_packaging_material(self, data: Dict) -> int:
        """Create packaging material"""
        query = """
            INSERT INTO packaging_materials 
            (name, material_type, unit, quantity, min_quantity, cost_per_unit, supplier, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
        return self._execute_insert(query, (
            data['name'], data.get('material_type'), data.get('unit', 'pcs'),
            data.get('quantity', 0), data.get('min_quantity', 0),
            data.get('cost_per_unit', 0), data.get('supplier'), data.get('notes')
        ))

    def get_packaging_materials(self, material_type: str = None) -> List[Dict]:
        """Get packaging materials"""
        query = "SELECT * FROM packaging_materials WHERE 1=1"
        params = []
        if material_type:
            query += " AND material_type = ?"
            params.append(material_type)
        query += " ORDER BY name"
        return self._execute_query(query, tuple(params))

    def update_packaging_material(self, material_id: int, data: Dict):
        """Update packaging material"""
        fields = []
        values = []
        for key, value in data.items():
            fields.append(f"{key} = ?")
            values.append(value)
        values.append(material_id)
        query = f"UPDATE packaging_materials SET {', '.join(fields)} WHERE id = ?"
        self._execute_query(query, tuple(values))

    def create_packaging_run(self, data: Dict) -> int:
        """Create packaging run record"""
        query = """
            INSERT INTO packaging_runs 
            (batch_id, package_type, quantity_filled, quantity_wasted, run_date, staff_id, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        return self._execute_insert(query, (
            data['batch_id'], data.get('package_type'), data.get('quantity_filled', 0),
            data.get('quantity_wasted', 0), data.get('run_date', date.today().isoformat()),
            data.get('staff_id'), data.get('notes')
        ))

    def get_packaging_runs(self, batch_id: int = None) -> List[Dict]:
        """Get packaging runs"""
        query = """
            SELECT pr.*, b.batch_number, p.name as product_name
            FROM packaging_runs pr
            LEFT JOIN batches b ON pr.batch_id = b.id
            LEFT JOIN products p ON b.product_id = p.id
            WHERE 1=1
        """
        params = []
        if batch_id:
            query += " AND pr.batch_id = ?"
            params.append(batch_id)
        query += " ORDER BY pr.run_date DESC"
        return self._execute_query(query, tuple(params))

    # ==================== SPRINT 3: SUPPLIER MANAGEMENT ====================
    
    def create_supplier(self, data: Dict) -> int:
        """Create supplier"""
        query = """
            INSERT INTO suppliers 
            (name, contact_person, phone, email, address, city, province, 
             tax_id, payment_terms, lead_time_days, rating, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        return self._execute_insert(query, (
            data['name'], data.get('contact_person'), data.get('phone'),
            data.get('email'), data.get('address'), data.get('city'),
            data.get('province'), data.get('tax_id'), data.get('payment_terms', 'NET30'),
            data.get('lead_time_days', 7), data.get('rating', 5), data.get('notes')
        ))

    def get_suppliers(self, active_only: bool = True) -> List[Dict]:
        """Get suppliers"""
        query = "SELECT * FROM suppliers WHERE 1=1"
        if active_only:
            query += " AND is_active = 1"
        query += " ORDER BY name"
        return self._execute_query(query)

    def update_supplier(self, supplier_id: int, data: Dict):
        """Update supplier"""
        fields = []
        values = []
        for key, value in data.items():
            fields.append(f"{key} = ?")
            values.append(value)
        values.append(supplier_id)
        query = f"UPDATE suppliers SET {', '.join(fields)} WHERE id = ?"
        self._execute_query(query, tuple(values))

    def create_purchase_order(self, data: Dict) -> int:
        """Create purchase order"""
        query = """
            INSERT INTO purchase_orders 
            (supplier_id, order_date, expected_delivery, status, total_amount, notes, created_by)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        return self._execute_insert(query, (
            data['supplier_id'], data.get('order_date', date.today().isoformat()),
            data.get('expected_delivery'), data.get('status', 'pending'),
            data.get('total_amount', 0), data.get('notes'), data.get('created_by')
        ))

    def get_purchase_orders(self, status: str = None) -> List[Dict]:
        """Get purchase orders"""
        query = """
            SELECT po.*, s.name as supplier_name
            FROM purchase_orders po
            LEFT JOIN suppliers s ON po.supplier_id = s.id
            WHERE 1=1
        """
        params = []
        if status:
            query += " AND po.status = ?"
            params.append(status)
        query += " ORDER BY po.order_date DESC"
        return self._execute_query(query, tuple(params))

    def add_purchase_order_item(self, data: Dict) -> int:
        """Add item to purchase order"""
        query = """
            INSERT INTO purchase_order_items 
            (po_id, material_id, quantity, unit_price, total_price)
            VALUES (?, ?, ?, ?, ?)
        """
        return self._execute_insert(query, (
            data['po_id'], data.get('material_id'), data['quantity'],
            data['unit_price'], data.get('total_price', data['quantity'] * data['unit_price'])
        ))

    def get_purchase_order_items(self, po_id: int) -> List[Dict]:
        """Get purchase order items"""
        query = """
            SELECT poi.*, rm.name as material_name, rm.unit
            FROM purchase_order_items poi
            LEFT JOIN raw_materials rm ON poi.material_id = rm.id
            WHERE poi.po_id = ?
        """
        return self._execute_query(query, (po_id,))

    def update_purchase_order_status(self, po_id: int, status: str):
        """Update purchase order status"""
        self._execute_query("UPDATE purchase_orders SET status = ? WHERE id = ?", (status, po_id))

    # ==================== SPRINT 3: TEMPERATURE MONITORING ====================
    
    def log_temperature(self, data: Dict) -> int:
        """Log temperature reading"""
        query = """
            INSERT INTO temperature_logs 
            (tank_id, batch_id, temperature, logged_at, logged_by, notes)
            VALUES (?, ?, ?, ?, ?, ?)
        """
        return self._execute_insert(query, (
            data['tank_id'], data.get('batch_id'), data['temperature'],
            data.get('logged_at', datetime.now().isoformat()), data.get('logged_by'), data.get('notes')
        ))

    def get_temperature_logs(self, tank_id: int = None, batch_id: int = None, 
                            start_date: str = None, end_date: str = None, limit: int = 100) -> List[Dict]:
        """Get temperature logs"""
        query = """
            SELECT tl.*, e.name as tank_name, b.batch_number
            FROM temperature_logs tl
            LEFT JOIN equipment e ON tl.tank_id = e.id
            LEFT JOIN batches b ON tl.batch_id = b.id
            WHERE 1=1
        """
        params = []
        if tank_id:
            query += " AND tl.tank_id = ?"
            params.append(tank_id)
        if batch_id:
            query += " AND tl.batch_id = ?"
            params.append(batch_id)
        if start_date:
            query += " AND tl.logged_at >= ?"
            params.append(start_date)
        if end_date:
            query += " AND tl.logged_at <= ?"
            params.append(end_date)
        query += f" ORDER BY tl.logged_at DESC LIMIT {limit}"
        return self._execute_query(query, tuple(params))

    def get_temperature_alerts(self) -> List[Dict]:
        """Get temperature alerts (readings outside normal range)"""
        query = """
            SELECT tl.*, e.name as tank_name, e.temp_min, e.temp_max
            FROM temperature_logs tl
            LEFT JOIN equipment e ON tl.tank_id = e.id
            WHERE tl.temperature < e.temp_min OR tl.temperature > e.temp_max
            ORDER BY tl.logged_at DESC
            LIMIT 50
        """
        return self._execute_query(query)

    # ==================== SPRINT 3: DISTRIBUTION TRACKING ====================
    
    def create_delivery_route(self, data: Dict) -> int:
        """Create delivery route"""
        query = """
            INSERT INTO delivery_routes 
            (route_name, driver_id, vehicle, scheduled_date, status, notes)
            VALUES (?, ?, ?, ?, ?, ?)
        """
        return self._execute_insert(query, (
            data['route_name'], data.get('driver_id'), data.get('vehicle'),
            data.get('scheduled_date', date.today().isoformat()), data.get('status', 'planned'), data.get('notes')
        ))

    def get_delivery_routes(self, status: str = None, route_date: str = None) -> List[Dict]:
        """Get delivery routes"""
        query = """
            SELECT dr.*, s.name as driver_name
            FROM delivery_routes dr
            LEFT JOIN staff s ON dr.driver_id = s.id
            WHERE 1=1
        """
        params = []
        if status:
            query += " AND dr.status = ?"
            params.append(status)
        if route_date:
            query += " AND dr.scheduled_date = ?"
            params.append(route_date)
        query += " ORDER BY dr.scheduled_date DESC"
        return self._execute_query(query, tuple(params))

    def add_delivery_stop(self, data: Dict) -> int:
        """Add stop to delivery route"""
        query = """
            INSERT INTO delivery_stops 
            (route_id, order_id, customer_id, address, stop_sequence, status, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        return self._execute_insert(query, (
            data['route_id'], data.get('order_id'), data.get('customer_id'),
            data.get('address'), data.get('stop_sequence', 1), data.get('status', 'pending'), data.get('notes')
        ))

    def get_delivery_stops(self, route_id: int) -> List[Dict]:
        """Get delivery stops for route"""
        query = """
            SELECT ds.*, c.name as customer_name, so.order_number
            FROM delivery_stops ds
            LEFT JOIN customers c ON ds.customer_id = c.id
            LEFT JOIN sales_orders so ON ds.order_id = so.id
            WHERE ds.route_id = ?
            ORDER BY ds.stop_sequence
        """
        return self._execute_query(query, (route_id,))

    def update_delivery_stop_status(self, stop_id: int, status: str):
        """Update delivery stop status"""
        self._execute_query("UPDATE delivery_stops SET status = ? WHERE id = ?", (status, stop_id))

    # ==================== SPRINT 3: WASTE TRACKING ====================
    
    def log_waste(self, data: Dict) -> int:
        """Log waste/spillage"""
        query = """
            INSERT INTO waste_log 
            (batch_id, waste_type, quantity, unit, reason, cost_impact, logged_by, logged_at, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        return self._execute_insert(query, (
            data.get('batch_id'), data['waste_type'], data['quantity'], data.get('unit', 'L'),
            data.get('reason'), data.get('cost_impact', 0), data.get('logged_by'),
            data.get('logged_at', datetime.now().isoformat()), data.get('notes')
        ))

    def get_waste_log(self, start_date: str = None, end_date: str = None, 
                     waste_type: str = None) -> List[Dict]:
        """Get waste log"""
        query = """
            SELECT wl.*, b.batch_number, p.name as product_name
            FROM waste_log wl
            LEFT JOIN batches b ON wl.batch_id = b.id
            LEFT JOIN products p ON b.product_id = p.id
            WHERE 1=1
        """
        params = []
        if start_date:
            query += " AND wl.logged_at >= ?"
            params.append(start_date)
        if end_date:
            query += " AND wl.logged_at <= ?"
            params.append(end_date)
        if waste_type:
            query += " AND wl.waste_type = ?"
            params.append(waste_type)
        query += " ORDER BY wl.logged_at DESC"
        return self._execute_query(query, tuple(params))

    def get_waste_summary(self, start_date: str = None, end_date: str = None) -> Dict:
        """Get waste summary"""
        query = """
            SELECT 
                waste_type,
                COUNT(*) as count,
                SUM(quantity) as total_quantity,
                SUM(cost_impact) as total_cost
            FROM waste_log
            WHERE 1=1
        """
        params = []
        if start_date:
            query += " AND logged_at >= ?"
            params.append(start_date)
        if end_date:
            query += " AND logged_at <= ?"
            params.append(end_date)
        query += " GROUP BY waste_type"
        return self._execute_query(query, tuple(params))

    # ==================== SPRINT 3: ADVANCED REPORTS ====================
    
    def get_product_profitability(self, start_date: str = None, end_date: str = None) -> List[Dict]:
        """Get product profitability report"""
        query = """
            SELECT 
                p.id,
                p.name,
                p.style,
                COUNT(DISTINCT b.id) as batch_count,
                SUM(b.actual_quantity) as total_volume,
                AVG(b.actual_quantity) as avg_batch_size,
                SUM(bc.total_actual) as total_cogs,
                SUM(soi.quantity * soi.unit_price) as total_revenue,
                CASE 
                    WHEN SUM(soi.quantity * soi.unit_price) > 0 
                    THEN (SUM(soi.quantity * soi.unit_price) - SUM(bc.total_actual)) / SUM(soi.quantity * soi.unit_price) * 100
                    ELSE 0 
                END as profit_margin
            FROM products p
            LEFT JOIN batches b ON p.id = b.product_id
            LEFT JOIN (
                SELECT batch_id, SUM(actual_cost) as total_actual
                FROM batch_cogs
                GROUP BY batch_id
            ) bc ON b.id = bc.batch_id
            LEFT JOIN sales_order_items soi ON p.id = soi.product_id
            LEFT JOIN sales_orders so ON soi.order_id = so.id
            WHERE 1=1
        """
        params = []
        if start_date:
            query += " AND so.order_date >= ?"
            params.append(start_date)
        if end_date:
            query += " AND so.order_date <= ?"
            params.append(end_date)
        query += " GROUP BY p.id ORDER BY profit_margin DESC"
        return self._execute_query(query, tuple(params))

    def get_customer_lifetime_value(self, limit: int = 20) -> List[Dict]:
        """Get customer lifetime value report"""
        query = """
            SELECT 
                c.id,
                c.name,
                c.type,
                c.city,
                COUNT(DISTINCT so.id) as total_orders,
                SUM(so.total_amount) as total_spent,
                AVG(so.total_amount) as avg_order_value,
                MIN(so.order_date) as first_order,
                MAX(so.order_date) as last_order,
                JULIANDAY(MAX(so.order_date)) - JULIANDAY(MIN(so.order_date)) as customer_days,
                CASE 
                    WHEN JULIANDAY(MAX(so.order_date)) - JULIANDAY(MIN(so.order_date)) > 0
                    THEN SUM(so.total_amount) / ((JULIANDAY(MAX(so.order_date)) - JULIANDAY(MIN(so.order_date))) / 30)
                    ELSE SUM(so.total_amount)
                END as monthly_value
            FROM customers c
            LEFT JOIN sales_orders so ON c.id = so.customer_id
            GROUP BY c.id
            ORDER BY total_spent DESC
            LIMIT ?
        """
        return self._execute_query(query, (limit,))

    def get_production_efficiency(self, start_date: str = None, end_date: str = None) -> List[Dict]:
        """Get production efficiency report"""
        query = """
            SELECT 
                b.id,
                b.batch_number,
                p.name as product_name,
                b.planned_quantity,
                b.actual_quantity,
                CASE 
                    WHEN b.planned_quantity > 0 
                    THEN (b.actual_quantity / b.planned_quantity) * 100
                    ELSE 0 
                END as yield_percentage,
                bc.planned_cost,
                bc.actual_cost,
                CASE 
                    WHEN bc.planned_cost > 0 
                    THEN ((bc.planned_cost - bc.actual_cost) / bc.planned_cost) * 100
                    ELSE 0 
                END as cost_variance
            FROM batches b
            LEFT JOIN products p ON b.product_id = p.id
            LEFT JOIN (
                SELECT batch_id, 
                       SUM(planned_cost) as planned_cost,
                       SUM(actual_cost) as actual_cost
                FROM batch_cogs
                GROUP BY batch_id
            ) bc ON b.id = bc.batch_id
            WHERE b.status = 'completed'
        """
        params = []
        if start_date:
            query += " AND b.end_date >= ?"
            params.append(start_date)
        if end_date:
            query += " AND b.end_date <= ?"
            params.append(end_date)
        query += " ORDER BY yield_percentage DESC"
        return self._execute_query(query, tuple(params))
    
    # ==================== QUERY HELPER METHODS ====================
    
    def _execute_query(self, query: str, params: tuple = None) -> List[Dict]:
        """Execute a SELECT query and return results as list of dicts"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Query execution error: {e}")
            return []
    
    def _execute_insert(self, query: str, params: tuple = None) -> int:
        """Execute an INSERT query and return the last row ID"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            conn.commit()
            return cursor.lastrowid
        except Exception as e:
            conn.rollback()
            logger.error(f"Insert execution error: {e}")
            raise

    # ==================== CHAT HISTORY METHODS ====================
    
    def save_chat_message(self, session_id: str, role: str, content: str) -> int:
        """Save a chat message to persistent storage"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO chat_history (session_id, role, content)
            VALUES (?, ?, ?)
        """, (session_id, role, content))
        conn.commit()
        lastrowid = cursor.lastrowid
        conn.close()
        return lastrowid

    def get_chat_history(self, session_id: str, limit: int = 50) -> List[Dict]:
        """Get chat history for a session"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT role, content, timestamp FROM chat_history
            WHERE session_id = ?
            ORDER BY timestamp ASC
            LIMIT ?
        """, (session_id, limit))
        result = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return result

    def clear_chat_history(self, session_id: str) -> bool:
        """Clear chat history for a session"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM chat_history WHERE session_id = ?", (session_id,))
        conn.commit()
        result = cursor.rowcount > 0
        conn.close()
        return result

    def get_all_chat_sessions(self, limit: int = 20) -> List[Dict]:
        """Get all chat sessions with last message"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT session_id, 
                   MAX(timestamp) as last_message_at,
                   COUNT(*) as message_count,
                   (SELECT content FROM chat_history ch2 
                    WHERE ch2.session_id = ch1.session_id 
                    ORDER BY ch2.timestamp DESC LIMIT 1) as last_message
            FROM chat_history ch1
            GROUP BY session_id
            ORDER BY last_message_at DESC
            LIMIT ?
        """, (limit,))
        result = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return result

    # ==================== GOAL TRACKING METHODS ====================
    
    def create_goal(self, data: Dict) -> int:
        """Create a new goal"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO goals (goal_type, description, target_value, current_value,
                             start_date, end_date, status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            data['goal_type'], data.get('description', ''),
            data.get('target_value'), data.get('current_value', 0),
            data.get('start_date', datetime.now().strftime('%Y-%m-%d')),
            data.get('end_date'), data.get('status', 'active')
        ))
        conn.commit()
        return cursor.lastrowid
    
    def update_goal(self, goal_id: int, data: Dict) -> bool:
        """Update a goal"""
        conn = self.get_connection()
        cursor = conn.cursor()
        fields = []
        values = []
        for key in ['current_value', 'status', 'description', 'end_date']:
            if key in data:
                fields.append(f"{key} = ?")
                values.append(data[key])
        if not fields:
            return False
        values.append(goal_id)
        cursor.execute(f"UPDATE goals SET {', '.join(fields)}, updated_at = CURRENT_TIMESTAMP WHERE id = ?", values)
        conn.commit()
        return cursor.rowcount > 0
    
    def get_goals(self, status: str = None, goal_type: str = None) -> List[Dict]:
        """Get goals with optional filters"""
        query = "SELECT * FROM goals WHERE 1=1"
        params = []
        if status:
            query += " AND status = ?"
            params.append(status)
        if goal_type:
            query += " AND goal_type = ?"
            params.append(goal_type)
        query += " ORDER BY created_at DESC"
        return self._execute_query(query, tuple(params) if params else None)
    
    def get_goal(self, goal_id: int) -> Optional[Dict]:
        """Get a single goal by ID"""
        results = self._execute_query("SELECT * FROM goals WHERE id = ?", (goal_id,))
        return results[0] if results else None

