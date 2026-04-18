"""
Database Migration: Add Indexes for Performance
Run this script to add indexes to frequently queried columns
"""
import sqlite3
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'brewery.db')


def add_indexes():
    """Add indexes to improve query performance"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    indexes = [
        # Raw Materials
        "CREATE INDEX IF NOT EXISTS idx_raw_materials_category ON raw_materials(category)",
        "CREATE INDEX IF NOT EXISTS idx_raw_materials_name ON raw_materials(name)",
        "CREATE INDEX IF NOT EXISTS idx_raw_materials_expiry ON raw_materials(expiry_date)",
        
        # Products
        "CREATE INDEX IF NOT EXISTS idx_products_name ON products(name)",
        "CREATE INDEX IF NOT EXISTS idx_products_style ON products(style)",
        "CREATE INDEX IF NOT EXISTS idx_products_active ON products(is_active)",
        
        # Equipment
        "CREATE INDEX IF NOT EXISTS idx_equipment_type ON equipment(equipment_type)",
        "CREATE INDEX IF NOT EXISTS idx_equipment_status ON equipment(status)",
        
        # Production Batches
        "CREATE INDEX IF NOT EXISTS idx_batches_number ON production_batches(batch_number)",
        "CREATE INDEX IF NOT EXISTS idx_batches_product ON production_batches(product_id)",
        "CREATE INDEX IF NOT EXISTS idx_batches_status ON production_batches(status)",
        "CREATE INDEX IF NOT EXISTS idx_batches_dates ON production_batches(start_date, end_date)",
        
        # Batch Ingredients
        "CREATE INDEX IF NOT EXISTS idx_batch_ingredients_batch ON batch_ingredients(batch_id)",
        "CREATE INDEX IF NOT EXISTS idx_batch_ingredients_material ON batch_ingredients(material_id)",
        
        # Quality Records
        "CREATE INDEX IF NOT EXISTS idx_quality_batch ON quality_records(batch_id)",
        "CREATE INDEX IF NOT EXISTS idx_quality_type ON quality_records(check_type)",
        "CREATE INDEX IF NOT EXISTS idx_quality_date ON quality_records(check_date)",
        
        # Customers
        "CREATE INDEX IF NOT EXISTS idx_customers_name ON customers(name)",
        "CREATE INDEX IF NOT EXISTS idx_customers_type ON customers(type)",
        "CREATE INDEX IF NOT EXISTS idx_customers_city ON customers(city)",
        "CREATE INDEX IF NOT EXISTS idx_customers_active ON customers(is_active)",
        
        # Sales Orders
        "CREATE INDEX IF NOT EXISTS idx_orders_number ON sales_orders(order_number)",
        "CREATE INDEX IF NOT EXISTS idx_orders_customer ON sales_orders(customer_id)",
        "CREATE INDEX IF NOT EXISTS idx_orders_status ON sales_orders(status)",
        "CREATE INDEX IF NOT EXISTS idx_orders_date ON sales_orders(order_date)",
        "CREATE INDEX IF NOT EXISTS idx_orders_payment ON sales_orders(payment_status)",
        
        # Order Items
        "CREATE INDEX IF NOT EXISTS idx_order_items_order ON order_items(order_id)",
        "CREATE INDEX IF NOT EXISTS idx_order_items_product ON order_items(product_id)",
        
        # Financial Transactions
        "CREATE INDEX IF NOT EXISTS idx_transactions_date ON financial_transactions(transaction_date)",
        "CREATE INDEX IF NOT EXISTS idx_transactions_type ON financial_transactions(type)",
        "CREATE INDEX IF NOT EXISTS idx_transactions_category ON financial_transactions(category)",
        
        # Staff
        "CREATE INDEX IF NOT EXISTS idx_staff_name ON staff(name)",
        "CREATE INDEX IF NOT EXISTS idx_staff_department ON staff(department)",
        "CREATE INDEX IF NOT EXISTS idx_staff_active ON staff(is_active)",
        
        # Staff Schedule
        "CREATE INDEX IF NOT EXISTS idx_schedule_staff ON staff_schedule(staff_id)",
        "CREATE INDEX IF NOT EXISTS idx_schedule_date ON staff_schedule(schedule_date)",
        
        # Maintenance
        "CREATE INDEX IF NOT EXISTS idx_maintenance_equipment ON maintenance_schedule(equipment_id)",
        "CREATE INDEX IF NOT EXISTS idx_maintenance_status ON maintenance_schedule(status)",
        "CREATE INDEX IF NOT EXISTS idx_maintenance_due ON maintenance_schedule(next_due)",
        
        # Daily Tasks
        "CREATE INDEX IF NOT EXISTS idx_tasks_date ON daily_tasks(task_date)",
        "CREATE INDEX IF NOT EXISTS idx_tasks_status ON daily_tasks(status)",
        "CREATE INDEX IF NOT EXISTS idx_tasks_assigned ON daily_tasks(assigned_to)",
        
        # Invoices
        "CREATE INDEX IF NOT EXISTS idx_invoices_number ON invoices(invoice_number)",
        "CREATE INDEX IF NOT EXISTS idx_invoices_customer ON invoices(customer_id)",
        "CREATE INDEX IF NOT EXISTS idx_invoices_date ON invoices(invoice_date)",
        "CREATE INDEX IF NOT EXISTS idx_invoices_status ON invoices(status)",
        
        # Recipes
        "CREATE INDEX IF NOT EXISTS idx_recipes_name ON recipes(name)",
        "CREATE INDEX IF NOT EXISTS idx_recipes_style ON recipes(style)",
        
        # Yeast
        "CREATE INDEX IF NOT EXISTS idx_yeast_strains_name ON yeast_strains(name)",
        "CREATE INDEX IF NOT EXISTS idx_yeast_inventory_strain ON yeast_inventory(strain_id)",
        "CREATE INDEX IF NOT EXISTS idx_yeast_usage_batch ON yeast_usage_log(batch_id)",
        
        # Users
        "CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)",
        "CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)",
        
        # Audit Log
        "CREATE INDEX IF NOT EXISTS idx_audit_user ON audit_log(user_id)",
        "CREATE INDEX IF NOT EXISTS idx_audit_date ON audit_log(timestamp)",
        "CREATE INDEX IF NOT EXISTS idx_audit_action ON audit_log(action)",
        
        # Notifications
        "CREATE INDEX IF NOT EXISTS idx_notifications_user ON notifications(user_id)",
        "CREATE INDEX IF NOT EXISTS idx_notifications_read ON notifications(is_read)",
        "CREATE INDEX IF NOT EXISTS idx_notifications_date ON notifications(created_at)",
        
        # Deliveries
        "CREATE INDEX IF NOT EXISTS idx_deliveries_order ON deliveries(order_id)",
        "CREATE INDEX IF NOT EXISTS idx_deliveries_date ON deliveries(delivery_date)",
        "CREATE INDEX IF NOT EXISTS idx_deliveries_status ON deliveries(status)",
    ]
    
    success_count = 0
    error_count = 0
    
    for index_sql in indexes:
        try:
            cursor.execute(index_sql)
            success_count += 1
            print(f"✓ {index_sql.split('idx_')[1].split(' ON')[0]}")
        except Exception as e:
            error_count += 1
            print(f"✗ Error: {e}")
    
    conn.commit()
    conn.close()
    
    print(f"\n{'='*50}")
    print(f"Migration Complete!")
    print(f"Indexes created: {success_count}")
    print(f"Errors: {error_count}")
    print(f"{'='*50}")


if __name__ == '__main__':
    print("Adding database indexes for performance optimization...")
    print("="*50)
    add_indexes()