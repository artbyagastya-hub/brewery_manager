"""
Enhanced Reporting Module for Brewery Manager
Provides comprehensive analytics and reporting capabilities
"""

from datetime import datetime, timedelta
from collections import defaultdict
import json


class BreweryReports:
    """Enhanced reporting class for brewery analytics"""

    def __init__(self, db):
        self.db = db

    def get_executive_summary(self, start_date=None, end_date=None):
        """Get executive summary with key metrics"""
        if not start_date:
            start_date = datetime.now() - timedelta(days=30)
        if not end_date:
            end_date = datetime.now()

        # Revenue
        revenue = self.db.execute_query("""
            SELECT COALESCE(SUM(total_amount), 0) as total
            FROM orders
            WHERE order_date BETWEEN ? AND ?
            AND status != 'cancelled'
        """, (start_date, end_date))

        # Expenses
        expenses = self.db.execute_query("""
            SELECT COALESCE(SUM(amount), 0) as total
            FROM transactions
            WHERE type = 'expense'
            AND date BETWEEN ? AND ?
        """, (start_date, end_date))

        # Production
        production = self.db.execute_query("""
            SELECT COUNT(*) as batches, COALESCE(SUM(actual_quantity), 0) as volume
            FROM production_batches
            WHERE start_date BETWEEN ? AND ?
            AND status = 'completed'
        """, (start_date, end_date))

        # Orders
        orders = self.db.execute_query("""
            SELECT COUNT(*) as count, COALESCE(SUM(total_amount), 0) as value
            FROM orders
            WHERE order_date BETWEEN ? AND ?
        """, (start_date, end_date))

        revenue_total = revenue[0]['total'] if revenue else 0
        expenses_total = expenses[0]['total'] if expenses else 0
        profit = revenue_total - expenses_total

        return {
            'period': {
                'start': start_date.strftime('%Y-%m-%d'),
                'end': end_date.strftime('%Y-%m-%d')
            },
            'revenue': revenue_total,
            'expenses': expenses_total,
            'profit': profit,
            'margin': (profit / revenue_total * 100) if revenue_total > 0 else 0,
            'production': {
                'batches': production[0]['batches'] if production else 0,
                'volume': production[0]['volume'] if production else 0
            },
            'orders': {
                'count': orders[0]['count'] if orders else 0,
                'value': orders[0]['value'] if orders else 0
            }
        }

    def get_sales_analytics(self, days=30):
        """Get detailed sales analytics"""
        start_date = datetime.now() - timedelta(days=days)

        # Sales by product
        by_product = self.db.execute_query("""
            SELECT p.name, p.style,
                   COUNT(DISTINCT oi.order_id) as order_count,
                   SUM(oi.quantity) as total_quantity,
                   SUM(oi.quantity * oi.unit_price) as total_revenue
            FROM order_items oi
            JOIN products p ON oi.product_id = p.id
            JOIN orders o ON oi.order_id = o.id
            WHERE o.order_date >= ?
            AND o.status != 'cancelled'
            GROUP BY p.id
            ORDER BY total_revenue DESC
        """, (start_date,))

        # Sales by customer type
        by_customer_type = self.db.execute_query("""
            SELECT c.type,
                   COUNT(DISTINCT o.id) as order_count,
                   SUM(o.total_amount) as total_revenue
            FROM orders o
            JOIN customers c ON o.customer_id = c.id
            WHERE o.order_date >= ?
            AND o.status != 'cancelled'
            GROUP BY c.type
            ORDER BY total_revenue DESC
        """, (start_date,))

        # Daily sales trend
        daily_trend = self.db.execute_query("""
            SELECT DATE(order_date) as date,
                   COUNT(*) as order_count,
                   SUM(total_amount) as revenue
            FROM orders
            WHERE order_date >= ?
            AND status != 'cancelled'
            GROUP BY DATE(order_date)
            ORDER BY date
        """, (start_date,))

        # Top customers
        top_customers = self.db.execute_query("""
            SELECT c.name, c.type,
                   COUNT(o.id) as order_count,
                   SUM(o.total_amount) as total_spent
            FROM orders o
            JOIN customers c ON o.customer_id = c.id
            WHERE o.order_date >= ?
            AND o.status != 'cancelled'
            GROUP BY c.id
            ORDER BY total_spent DESC
            LIMIT 10
        """, (start_date,))

        return {
            'by_product': by_product or [],
            'by_customer_type': by_customer_type or [],
            'daily_trend': daily_trend or [],
            'top_customers': top_customers or []
        }

    def get_production_analytics(self, days=90):
        """Get production analytics"""
        start_date = datetime.now() - timedelta(days=days)

        # Production by product
        by_product = self.db.execute_query("""
            SELECT p.name, p.style,
                   COUNT(*) as batch_count,
                   SUM(pb.planned_quantity) as planned,
                   SUM(pb.actual_quantity) as actual,
                   AVG(pb.actual_quantity * 100.0 / NULLIF(pb.planned_quantity, 0)) as efficiency
            FROM production_batches pb
            JOIN products p ON pb.product_id = p.id
            WHERE pb.start_date >= ?
            GROUP BY p.id
            ORDER BY batch_count DESC
        """, (start_date,))

        # Production by status
        by_status = self.db.execute_query("""
            SELECT status, COUNT(*) as count
            FROM production_batches
            WHERE start_date >= ?
            GROUP BY status
        """, (start_date,))

        # Monthly production
        monthly = self.db.execute_query("""
            SELECT strftime('%Y-%m', start_date) as month,
                   COUNT(*) as batches,
                   SUM(actual_quantity) as volume
            FROM production_batches
            WHERE start_date >= ?
            AND status = 'completed'
            GROUP BY month
            ORDER BY month
        """, (start_date,))

        # Average batch time
        avg_time = self.db.execute_query("""
            SELECT AVG(JULIANDAY(end_date) - JULIANDAY(start_date)) as avg_days
            FROM production_batches
            WHERE start_date >= ?
            AND status = 'completed'
            AND end_date IS NOT NULL
        """, (start_date,))

        return {
            'by_product': by_product or [],
            'by_status': by_status or [],
            'monthly': monthly or [],
            'avg_batch_days': avg_time[0]['avg_days'] if avg_time and avg_time[0]['avg_days'] else 0
        }

    def get_inventory_analytics(self):
        """Get inventory analytics"""
        # Current inventory value
        inventory_value = self.db.execute_query("""
            SELECT
                COUNT(*) as item_count,
                SUM(quantity * cost_per_unit) as total_value,
                SUM(CASE WHEN quantity <= min_quantity THEN 1 ELSE 0 END) as low_stock_count
            FROM inventory
            WHERE status = 'active'
        """)

        # Value by category
        by_category = self.db.execute_query("""
            SELECT category,
                   COUNT(*) as item_count,
                   SUM(quantity) as total_quantity,
                   SUM(quantity * cost_per_unit) as total_value
            FROM inventory
            WHERE status = 'active'
            GROUP BY category
            ORDER BY total_value DESC
        """)

        # Expiring soon (next 30 days)
        expiring = self.db.execute_query("""
            SELECT name, quantity, unit, expiry_date
            FROM inventory
            WHERE expiry_date IS NOT NULL
            AND expiry_date <= DATE('now', '+30 days')
            AND quantity > 0
            ORDER BY expiry_date
        """)

        # Low stock items
        low_stock = self.db.execute_query("""
            SELECT name, quantity, min_quantity, unit, category
            FROM inventory
            WHERE quantity <= min_quantity
            AND status = 'active'
            ORDER BY (quantity * 1.0 / NULLIF(min_quantity, 0))
        """)

        return {
            'summary': inventory_value[0] if inventory_value else {},
            'by_category': by_category or [],
            'expiring_soon': expiring or [],
            'low_stock': low_stock or []
        }

    def get_financial_analytics(self, days=30):
        """Get financial analytics"""
        start_date = datetime.now() - timedelta(days=days)

        # Income by category
        income_by_category = self.db.execute_query("""
            SELECT category, SUM(amount) as total
            FROM transactions
            WHERE type = 'income'
            AND date >= ?
            GROUP BY category
            ORDER BY total DESC
        """, (start_date,))

        # Expenses by category
        expense_by_category = self.db.execute_query("""
            SELECT category, SUM(amount) as total
            FROM transactions
            WHERE type = 'expense'
            AND date >= ?
            GROUP BY category
            ORDER BY total DESC
        """, (start_date,))

        # Daily cash flow
        daily_flow = self.db.execute_query("""
            SELECT DATE(date) as date,
                   SUM(CASE WHEN type = 'income' THEN amount ELSE 0 END) as income,
                   SUM(CASE WHEN type = 'expense' THEN amount ELSE 0 END) as expense
            FROM transactions
            WHERE date >= ?
            GROUP BY DATE(date)
            ORDER BY date
        """, (start_date,))

        # Accounts receivable (unpaid orders)
        receivable = self.db.execute_query("""
            SELECT SUM(total_amount - COALESCE(paid_amount, 0)) as total
            FROM orders
            WHERE payment_status IN ('unpaid', 'partial')
            AND status != 'cancelled'
        """)

        return {
            'income_by_category': income_by_category or [],
            'expense_by_category': expense_by_category or [],
            'daily_flow': daily_flow or [],
            'accounts_receivable': receivable[0]['total'] if receivable and receivable[0]['total'] else 0
        }

    def get_quality_analytics(self, days=90):
        """Get quality control analytics"""
        start_date = datetime.now() - timedelta(days=days)

        # Pass/fail rate
        pass_rate = self.db.execute_query("""
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN passed = 1 THEN 1 ELSE 0 END) as passed,
                SUM(CASE WHEN passed = 0 THEN 1 ELSE 0 END) as failed
            FROM quality_checks
            WHERE check_date >= ?
        """, (start_date,))

        # By check type
        by_type = self.db.execute_query("""
            SELECT check_type,
                   COUNT(*) as total,
                   SUM(CASE WHEN passed = 1 THEN 1 ELSE 0 END) as passed
            FROM quality_checks
            WHERE check_date >= ?
            GROUP BY check_type
        """, (start_date,))

        # Failed checks detail
        failed_checks = self.db.execute_query("""
            SELECT qc.*, pb.batch_number, p.name as product_name
            FROM quality_checks qc
            LEFT JOIN production_batches pb ON qc.batch_id = pb.id
            LEFT JOIN products p ON pb.product_id = p.id
            WHERE qc.passed = 0
            AND qc.check_date >= ?
            ORDER BY qc.check_date DESC
            LIMIT 20
        """, (start_date,))

        total = pass_rate[0]['total'] if pass_rate else 0
        passed = pass_rate[0]['passed'] if pass_rate else 0

        return {
            'pass_rate': (passed / total * 100) if total > 0 else 0,
            'total_checks': total,
            'passed': passed,
            'failed': pass_rate[0]['failed'] if pass_rate else 0,
            'by_type': by_type or [],
            'failed_checks': failed_checks or []
        }

    def get_customer_analytics(self, days=90):
        """Get customer analytics"""
        start_date = datetime.now() - timedelta(days=days)

        # Customer segments
        segments = self.db.execute_query("""
            SELECT type, COUNT(*) as count
            FROM customers
            WHERE status = 'active'
            GROUP BY type
        """)

        # Customer lifetime value
        ltv = self.db.execute_query("""
            SELECT c.id, c.name, c.type,
                   COUNT(o.id) as order_count,
                   SUM(o.total_amount) as total_spent,
                   MIN(o.order_date) as first_order,
                   MAX(o.order_date) as last_order
            FROM customers c
            LEFT JOIN orders o ON c.id = o.customer_id
            WHERE c.status = 'active'
            GROUP BY c.id
            HAVING order_count > 0
            ORDER BY total_spent DESC
            LIMIT 20
        """)

        # New customers
        new_customers = self.db.execute_query("""
            SELECT COUNT(*) as count
            FROM customers
            WHERE created_at >= ?
        """, (start_date,))

        # Customer retention (ordered in last 90 days)
        active_customers = self.db.execute_query("""
            SELECT COUNT(DISTINCT customer_id) as count
            FROM orders
            WHERE order_date >= ?
            AND status != 'cancelled'
        """, (start_date,))

        return {
            'segments': segments or [],
            'top_by_ltv': ltv or [],
            'new_customers': new_customers[0]['count'] if new_customers else 0,
            'active_customers': active_customers[0]['count'] if active_customers else 0
        }

    def export_report(self, report_type, format='json', **kwargs):
        """Export report in specified format"""
        report_data = None

        if report_type == 'executive':
            report_data = self.get_executive_summary(**kwargs)
        elif report_type == 'sales':
            report_data = self.get_sales_analytics(**kwargs)
        elif report_type == 'production':
            report_data = self.get_production_analytics(**kwargs)
        elif report_type == 'inventory':
            report_data = self.get_inventory_analytics()
        elif report_type == 'financial':
            report_data = self.get_financial_analytics(**kwargs)
        elif report_type == 'quality':
            report_data = self.get_quality_analytics(**kwargs)
        elif report_type == 'customers':
            report_data = self.get_customer_analytics(**kwargs)

        if format == 'json':
            return json.dumps(report_data, default=str, indent=2)
        else:
            return report_data