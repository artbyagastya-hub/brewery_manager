"""
Brewery Manager - Traceability & Costing Module
Lot tracking, COGS calculation, and traceability reports for Vietnamese craft breweries
"""

import sqlite3
import os
import sys
import csv
import io
from datetime import datetime, date, timedelta
from typing import List, Dict, Optional, Tuple
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from models.database import Database


class TraceabilityManager:
    """Manages lot tracking, COGS calculation, and traceability"""
    
    def __init__(self, db: Database):
        self.db = db
        self.init_traceability_tables()
    
    def init_traceability_tables(self):
        """Initialize traceability-specific tables"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        # Lots table - tracks incoming material lots
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS lots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lot_number TEXT UNIQUE NOT NULL,
                material_id INTEGER NOT NULL,
                supplier TEXT,
                quantity_received REAL NOT NULL,
                quantity_remaining REAL NOT NULL,
                unit TEXT NOT NULL,
                cost_per_unit REAL DEFAULT 0,
                total_cost REAL DEFAULT 0,
                received_date DATE NOT NULL,
                expiry_date DATE,
                certificate_of_analysis TEXT,
                storage_location TEXT,
                status TEXT DEFAULT 'active',
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (material_id) REFERENCES raw_materials(id)
            )
        """)
        
        # Lot Usage - tracks which lots are used in which batches
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS lot_usage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lot_id INTEGER NOT NULL,
                batch_id INTEGER NOT NULL,
                quantity_used REAL NOT NULL,
                cost_at_time REAL DEFAULT 0,
                used_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                used_by INTEGER,
                notes TEXT,
                FOREIGN KEY (lot_id) REFERENCES lots(id),
                FOREIGN KEY (batch_id) REFERENCES production_batches(id),
                FOREIGN KEY (used_by) REFERENCES staff(id)
            )
        """)
        
        # Batch Costs - detailed COGS breakdown per batch
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS batch_costs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                batch_id INTEGER NOT NULL,
                cost_type TEXT NOT NULL,
                category TEXT,
                planned_cost REAL DEFAULT 0,
                actual_cost REAL DEFAULT 0,
                variance REAL DEFAULT 0,
                notes TEXT,
                calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (batch_id) REFERENCES production_batches(id)
            )
        """)
        
        # Finished Goods Lots - track成品 lots
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS finished_goods_lots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lot_number TEXT UNIQUE NOT NULL,
                batch_id INTEGER NOT NULL,
                product_id INTEGER NOT NULL,
                quantity REAL NOT NULL,
                unit TEXT DEFAULT 'L',
                production_date DATE NOT NULL,
                expiry_date DATE,
                status TEXT DEFAULT 'available',
                location TEXT,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (batch_id) REFERENCES production_batches(id),
                FOREIGN KEY (product_id) REFERENCES products(id)
            )
        """)
        
        # Order Lot Allocation - link orders to finished goods lots
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS order_lot_allocation (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_item_id INTEGER NOT NULL,
                finished_lot_id INTEGER NOT NULL,
                quantity REAL NOT NULL,
                allocated_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (order_item_id) REFERENCES order_items(id),
                FOREIGN KEY (finished_lot_id) REFERENCES finished_goods_lots(id)
            )
        """)
        
        conn.commit()
        conn.close()
    
    # ==================== LOT MANAGEMENT ====================
    
    def create_lot(self, lot_data: Dict) -> int:
        """Create a new material lot"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        # Generate lot number if not provided
        if 'lot_number' not in lot_data or not lot_data['lot_number']:
            lot_data['lot_number'] = self._generate_lot_number(
                lot_data.get('material_id'),
                lot_data.get('received_date', date.today())
            )
        
        # Calculate total cost
        if 'total_cost' not in lot_data:
            lot_data['total_cost'] = lot_data.get('quantity_received', 0) * lot_data.get('cost_per_unit', 0)
        
        # Set quantity_remaining to quantity_received initially
        lot_data['quantity_remaining'] = lot_data.get('quantity_received', 0)
        
        cursor.execute("""
            INSERT INTO lots (lot_number, material_id, supplier, quantity_received, 
                            quantity_remaining, unit, cost_per_unit, total_cost,
                            received_date, expiry_date, certificate_of_analysis,
                            storage_location, status, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            lot_data['lot_number'],
            lot_data['material_id'],
            lot_data.get('supplier'),
            lot_data['quantity_received'],
            lot_data['quantity_remaining'],
            lot_data['unit'],
            lot_data.get('cost_per_unit', 0),
            lot_data['total_cost'],
            lot_data['received_date'],
            lot_data.get('expiry_date'),
            lot_data.get('certificate_of_analysis'),
            lot_data.get('storage_location'),
            lot_data.get('status', 'active'),
            lot_data.get('notes')
        ))
        
        lot_id = cursor.lastrowid
        
        # Update raw_materials quantity
        cursor.execute("""
            UPDATE raw_materials 
            SET quantity = quantity + ?, 
                cost_per_unit = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (lot_data['quantity_received'], lot_data.get('cost_per_unit', 0), lot_data['material_id']))
        
        conn.commit()
        conn.close()
        
        return lot_id
    
    def _generate_lot_number(self, material_id: int, received_date: date) -> str:
        """Generate a unique lot number"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        # Get material category prefix
        cursor.execute("SELECT category FROM raw_materials WHERE id = ?", (material_id,))
        result = cursor.fetchone()
        category = result[0] if result else 'UNK'
        
        # Category prefixes
        prefixes = {
            'malt': 'MLT',
            'hops': 'HPS',
            'yeast': 'YST',
            'adjunct': 'ADJ',
            'packaging': 'PKG',
            'chemical': 'CHM'
        }
        prefix = prefixes.get(category.lower(), 'MAT')
        
        # Format: PREFIX-YYYYMMDD-XXXX
        date_str = received_date.strftime('%Y%m%d')
        
        # Get next sequence number for today
        cursor.execute("""
            SELECT COUNT(*) FROM lots 
            WHERE lot_number LIKE ?
        """, (f"{prefix}-{date_str}-%",))
        count = cursor.fetchone()[0] + 1
        
        conn.close()
        
        return f"{prefix}-{date_str}-{count:04d}"
    
    def use_lot(self, lot_id: int, batch_id: int, quantity: float, 
                used_by: int = None, notes: str = None) -> int:
        """Record usage of a lot in a batch"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        # Get lot details
        cursor.execute("SELECT * FROM lots WHERE id = ?", (lot_id,))
        lot = cursor.fetchone()
        
        if not lot:
            conn.close()
            raise ValueError(f"Lot {lot_id} not found")
        
        if lot['quantity_remaining'] < quantity:
            conn.close()
            raise ValueError(f"Insufficient quantity in lot {lot['lot_number']}. "
                           f"Available: {lot['quantity_remaining']}, Requested: {quantity}")
        
        # Calculate cost at time of use
        cost_at_time = quantity * lot['cost_per_unit']
        
        # Record usage
        cursor.execute("""
            INSERT INTO lot_usage (lot_id, batch_id, quantity_used, cost_at_time, used_by, notes)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (lot_id, batch_id, quantity, cost_at_time, used_by, notes))
        
        usage_id = cursor.lastrowid
        
        # Update lot remaining quantity
        cursor.execute("""
            UPDATE lots 
            SET quantity_remaining = quantity_remaining - ?,
                status = CASE WHEN quantity_remaining - ? <= 0 THEN 'depleted' ELSE status END
            WHERE id = ?
        """, (quantity, quantity, lot_id))
        
        # Update raw_materials quantity
        cursor.execute("""
            UPDATE raw_materials 
            SET quantity = quantity - ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (quantity, lot['material_id']))
        
        conn.commit()
        conn.close()
        
        return usage_id
    
    # ==================== COGS CALCULATION ====================
    
    def calculate_batch_cogs(self, batch_id: int) -> Dict:
        """Calculate Cost of Goods Sold for a batch"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        # Get batch details
        cursor.execute("""
            SELECT pb.*, p.name as product_name, p.price_per_unit
            FROM production_batches pb
            JOIN products p ON pb.product_id = p.id
            WHERE pb.id = ?
        """, (batch_id,))
        batch = cursor.fetchone()
        
        if not batch:
            conn.close()
            raise ValueError(f"Batch {batch_id} not found")
        
        # Get ingredient costs from lot usage
        cursor.execute("""
            SELECT 
                rm.name as material_name,
                rm.category,
                lu.quantity_used,
                lu.cost_at_time,
                l.lot_number,
                l.cost_per_unit
            FROM lot_usage lu
            JOIN lots l ON lu.lot_id = l.id
            JOIN raw_materials rm ON l.material_id = rm.id
            WHERE lu.batch_id = ?
        """, (batch_id,))
        
        ingredients = cursor.fetchall()
        
        # Calculate ingredient costs by category
        ingredient_costs = defaultdict(float)
        ingredient_details = []
        total_ingredient_cost = 0
        
        for ing in ingredients:
            category = ing['category'] or 'other'
            ingredient_costs[category] += ing['cost_at_time']
            total_ingredient_cost += ing['cost_at_time']
            ingredient_details.append({
                'material': ing['material_name'],
                'lot': ing['lot_number'],
                'quantity': ing['quantity_used'],
                'unit_cost': ing['cost_per_unit'],
                'total_cost': ing['cost_at_time']
            })
        
        # Get labor costs (estimated based on brewer salary)
        labor_cost = 0
        if batch['brewer_id']:
            cursor.execute("SELECT salary FROM staff WHERE id = ?", (batch['brewer_id'],))
            brewer = cursor.fetchone()
            if brewer and brewer['salary']:
                # Estimate 8 hours per batch
                hourly_rate = brewer['salary'] / (22 * 8)  # 22 working days per month
                labor_cost = hourly_rate * 8
        
        # Get overhead costs (equipment depreciation, utilities, etc.)
        # Estimate 10% of ingredient cost as overhead
        overhead_cost = total_ingredient_cost * 0.10
        
        # Total COGS
        total_cogs = total_ingredient_cost + labor_cost + overhead_cost
        
        # Calculate per-unit cost
        actual_quantity = batch['actual_quantity'] or batch['planned_quantity']
        cost_per_unit = total_cogs / actual_quantity if actual_quantity > 0 else 0
        
        # Calculate variance (planned vs actual)
        planned_cost = batch['planned_quantity'] * cost_per_unit
        variance = total_cogs - planned_cost
        
        # Store batch costs
        cursor.execute("DELETE FROM batch_costs WHERE batch_id = ?", (batch_id,))
        
        # Ingredient costs by category
        for category, cost in ingredient_costs.items():
            cursor.execute("""
                INSERT INTO batch_costs (batch_id, cost_type, category, actual_cost, notes)
                VALUES (?, 'ingredient', ?, ?, ?)
            """, (batch_id, category, cost, f"Ingredients: {category}"))
        
        # Labor cost
        cursor.execute("""
            INSERT INTO batch_costs (batch_id, cost_type, category, actual_cost, notes)
            VALUES (?, 'labor', 'direct_labor', ?, 'Estimated labor cost')
        """, (batch_id, labor_cost))
        
        # Overhead cost
        cursor.execute("""
            INSERT INTO batch_costs (batch_id, cost_type, category, actual_cost, notes)
            VALUES (?, 'overhead', 'production_overhead', ?, 'Estimated overhead (10%)')
        """, (batch_id, overhead_cost))
        
        conn.commit()
        conn.close()
        
        return {
            'batch_id': batch_id,
            'batch_number': batch['batch_number'],
            'product_name': batch['product_name'],
            'planned_quantity': batch['planned_quantity'],
            'actual_quantity': actual_quantity,
            'ingredient_costs': dict(ingredient_costs),
            'total_ingredient_cost': total_ingredient_cost,
            'labor_cost': labor_cost,
            'overhead_cost': overhead_cost,
            'total_cogs': total_cogs,
            'cost_per_unit': cost_per_unit,
            'selling_price': batch['price_per_unit'],
            'gross_margin': batch['price_per_unit'] - cost_per_unit if batch['price_per_unit'] else 0,
            'gross_margin_pct': ((batch['price_per_unit'] - cost_per_unit) / batch['price_per_unit'] * 100) if batch['price_per_unit'] else 0,
            'variance': variance,
            'ingredient_details': ingredient_details
        }
    
    # ==================== TRACEABILITY ====================
    
    def forward_trace(self, lot_number: str) -> Dict:
        """Forward traceability: Lot → Batches → Orders → Customers"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        # Get lot details
        cursor.execute("""
            SELECT l.*, rm.name as material_name, rm.category
            FROM lots l
            JOIN raw_materials rm ON l.material_id = rm.id
            WHERE l.lot_number = ?
        """, (lot_number,))
        lot = cursor.fetchone()
        
        if not lot:
            conn.close()
            raise ValueError(f"Lot {lot_number} not found")
        
        # Get batches using this lot
        cursor.execute("""
            SELECT 
                pb.id as batch_id,
                pb.batch_number,
                pb.status as batch_status,
                p.name as product_name,
                lu.quantity_used,
                lu.used_date
            FROM lot_usage lu
            JOIN production_batches pb ON lu.batch_id = pb.id
            JOIN products p ON pb.product_id = p.id
            WHERE lu.lot_id = ?
            ORDER BY lu.used_date
        """, (lot['id'],))
        
        batches = cursor.fetchall()
        
        # Get orders for these batches (through finished goods lots)
        batch_ids = [b['batch_id'] for b in batches]
        orders = []
        
        if batch_ids:
            placeholders = ','.join('?' * len(batch_ids))
            cursor.execute(f"""
                SELECT DISTINCT
                    so.order_number,
                    so.order_date,
                    c.name as customer_name,
                    c.phone as customer_phone,
                    p.name as product_name,
                    oi.quantity,
                    fgl.lot_number as finished_lot
                FROM finished_goods_lots fgl
                JOIN order_lot_allocation ola ON fgl.id = ola.finished_lot_id
                JOIN order_items oi ON ola.order_item_id = oi.id
                JOIN sales_orders so ON oi.order_id = so.id
                JOIN customers c ON so.customer_id = c.id
                JOIN products p ON oi.product_id = p.id
                WHERE fgl.batch_id IN ({placeholders})
                ORDER BY so.order_date DESC
            """, batch_ids)
            
            orders = cursor.fetchall()
        
        conn.close()
        
        return {
            'lot': dict(lot),
            'batches': [dict(b) for b in batches],
            'orders': [dict(o) for o in orders],
            'trace_type': 'forward'
        }
    
    def backward_trace(self, order_number: str) -> Dict:
        """Backward traceability: Customer → Order → Batches → Lots"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        # Get order details
        cursor.execute("""
            SELECT 
                so.*,
                c.name as customer_name,
                c.phone as customer_phone,
                c.address as customer_address
            FROM sales_orders so
            JOIN customers c ON so.customer_id = c.id
            WHERE so.order_number = ?
        """, (order_number,))
        
        order = cursor.fetchone()
        if not order:
            conn.close()
            raise ValueError(f"Order {order_number} not found")
        
        # Get order items with batch and lot info
        cursor.execute("""
            SELECT 
                oi.id as item_id,
                p.name as product_name,
                oi.quantity,
                oi.unit_price,
                oi.subtotal,
                fgl.lot_number as finished_lot,
                fgl.batch_id,
                pb.batch_number
            FROM order_items oi
            JOIN products p ON oi.product_id = p.id
            LEFT JOIN order_lot_allocation ola ON oi.id = ola.order_item_id
            LEFT JOIN finished_goods_lots fgl ON ola.finished_lot_id = fgl.id
            LEFT JOIN production_batches pb ON fgl.batch_id = pb.id
            WHERE oi.order_id = ?
        """, (order['id'],))
        
        items = cursor.fetchall()
        
        # Get raw material lots for each batch
        batch_ids = [item['batch_id'] for item in items if item['batch_id']]
        raw_lots = []
        
        if batch_ids:
            placeholders = ','.join('?' * len(batch_ids))
            cursor.execute(f"""
                SELECT DISTINCT
                    l.lot_number,
                    rm.name as material_name,
                    rm.category,
                    l.supplier,
                    l.received_date,
                    l.expiry_date,
                    lu.quantity_used,
                    pb.batch_number
                FROM lot_usage lu
                JOIN lots l ON lu.lot_id = l.id
                JOIN raw_materials rm ON l.material_id = rm.id
                JOIN production_batches pb ON lu.batch_id = pb.id
                WHERE lu.batch_id IN ({placeholders})
                ORDER BY rm.category, rm.name
            """, batch_ids)
            
            raw_lots = cursor.fetchall()
        
        conn.close()
        
        return {
            'order': dict(order),
            'items': [dict(i) for i in items],
            'raw_material_lots': [dict(l) for l in raw_lots],
            'trace_type': 'backward'
        }
    
    # ==================== REPORTS ====================
    
    def get_lot_inventory_report(self) -> List[Dict]:
        """Get current lot inventory status"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                l.lot_number,
                rm.name as material_name,
                rm.category,
                l.supplier,
                l.quantity_received,
                l.quantity_remaining,
                l.unit,
                l.cost_per_unit,
                l.received_date,
                l.expiry_date,
                l.storage_location,
                l.status,
                CASE 
                    WHEN l.expiry_date <= date('now', '+30 days') THEN 'expiring_soon'
                    WHEN l.expiry_date <= date('now') THEN 'expired'
                    ELSE 'ok'
                END as expiry_status
            FROM lots l
            JOIN raw_materials rm ON l.material_id = rm.id
            WHERE l.status = 'active' AND l.quantity_remaining > 0
            ORDER BY l.expiry_date, rm.category, rm.name
        """)
        
        lots = cursor.fetchall()
        conn.close()
        
        return [dict(lot) for lot in lots]
    
    def get_cogs_summary(self, start_date: date = None, end_date: date = None) -> Dict:
        """Get COGS summary for a period"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        if not start_date:
            start_date = date.today() - timedelta(days=30)
        if not end_date:
            end_date = date.today()
        
        cursor.execute("""
            SELECT 
                p.name as product_name,
                COUNT(pb.id) as batch_count,
                SUM(pb.actual_quantity) as total_volume,
                SUM(COALESCE(bc.actual_cost, 0)) as total_cost,
                AVG(COALESCE(bc.actual_cost, 0) / NULLIF(pb.actual_quantity, 0)) as avg_cost_per_unit
            FROM production_batches pb
            JOIN products p ON pb.product_id = p.id
            LEFT JOIN batch_costs bc ON pb.id = bc.batch_id
            WHERE pb.status = 'completed'
                AND pb.end_date BETWEEN ? AND ?
            GROUP BY p.id, p.name
            ORDER BY total_cost DESC
        """, (start_date, end_date))
        
        products = cursor.fetchall()
        
        # Get cost breakdown
        cursor.execute("""
            SELECT 
                bc.cost_type,
                SUM(bc.actual_cost) as total_cost
            FROM batch_costs bc
            JOIN production_batches pb ON bc.batch_id = pb.id
            WHERE pb.status = 'completed'
                AND pb.end_date BETWEEN ? AND ?
            GROUP BY bc.cost_type
        """, (start_date, end_date))
        
        cost_breakdown = cursor.fetchall()
        
        conn.close()
        
        return {
            'period': {'start': start_date.isoformat(), 'end': end_date.isoformat()},
            'products': [dict(p) for p in products],
            'cost_breakdown': {cb['cost_type']: cb['total_cost'] for cb in cost_breakdown}
        }
    
    def get_variance_report(self, batch_id: int = None) -> List[Dict]:
        """Get variance analysis report"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        query = """
            SELECT 
                pb.batch_number,
                p.name as product_name,
                pb.planned_quantity,
                pb.actual_quantity,
                SUM(CASE WHEN bc.cost_type = 'ingredient' THEN bc.actual_cost ELSE 0 END) as ingredient_cost,
                SUM(CASE WHEN bc.cost_type = 'labor' THEN bc.actual_cost ELSE 0 END) as labor_cost,
                SUM(CASE WHEN bc.cost_type = 'overhead' THEN bc.actual_cost ELSE 0 END) as overhead_cost,
                SUM(bc.actual_cost) as total_actual_cost,
                pb.planned_quantity * p.price_per_unit as planned_revenue,
                (pb.actual_quantity * p.price_per_unit) - SUM(bc.actual_cost) as gross_profit
            FROM production_batches pb
            JOIN products p ON pb.product_id = p.id
            LEFT JOIN batch_costs bc ON pb.id = bc.batch_id
            WHERE pb.status = 'completed'
        """
        
        params = []
        if batch_id:
            query += " AND pb.id = ?"
            params.append(batch_id)
        
        query += " GROUP BY pb.id ORDER BY pb.end_date DESC"
        
        cursor.execute(query, params)
        results = cursor.fetchall()
        conn.close()
        
        return [dict(r) for r in results]
    
    # ==================== EXPORT FUNCTIONS ====================
    
    def export_lot_inventory_csv(self) -> str:
        """Export lot inventory to CSV format"""
        lots = self.get_lot_inventory_report()
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Header
        writer.writerow([
            'Lot Number', 'Material', 'Category', 'Supplier', 
            'Quantity Received', 'Quantity Remaining', 'Unit',
            'Cost/Unit', 'Received Date', 'Expiry Date', 
            'Storage Location', 'Status', 'Expiry Status'
        ])
        
        # Data rows
        for lot in lots:
            writer.writerow([
                lot['lot_number'],
                lot['material_name'],
                lot['category'],
                lot.get('supplier', ''),
                lot['quantity_received'],
                lot['quantity_remaining'],
                lot['unit'],
                lot['cost_per_unit'],
                lot['received_date'],
                lot.get('expiry_date', ''),
                lot.get('storage_location', ''),
                lot['status'],
                lot['expiry_status']
            ])
        
        content = output.getvalue()
        output.close()
        return content
    
    def export_cogs_summary_csv(self, start_date: date = None, end_date: date = None) -> str:
        """Export COGS summary to CSV format"""
        summary = self.get_cogs_summary(start_date, end_date)
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Header
        writer.writerow(['Product', 'Batch Count', 'Total Volume (L)', 'Total Cost', 'Avg Cost/Unit'])
        
        # Data rows
        for product in summary['products']:
            writer.writerow([
                product['product_name'],
                product['batch_count'],
                product['total_volume'],
                product['total_cost'],
                product['avg_cost_per_unit']
            ])
        
        # Cost breakdown section
        writer.writerow([])
        writer.writerow(['Cost Breakdown'])
        writer.writerow(['Cost Type', 'Total'])
        for cost_type, total in summary['cost_breakdown'].items():
            writer.writerow([cost_type, total])
        
        content = output.getvalue()
        output.close()
        return content
    
    def export_variance_report_csv(self, batch_id: int = None) -> str:
        """Export variance report to CSV format"""
        report = self.get_variance_report(batch_id)
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Header
        writer.writerow([
            'Batch Number', 'Product', 'Planned Qty', 'Actual Qty',
            'Ingredient Cost', 'Labor Cost', 'Overhead Cost',
            'Total Actual Cost', 'Planned Revenue', 'Gross Profit'
        ])
        
        # Data rows
        for row in report:
            writer.writerow([
                row['batch_number'],
                row['product_name'],
                row['planned_quantity'],
                row['actual_quantity'],
                row['ingredient_cost'],
                row['labor_cost'],
                row['overhead_cost'],
                row['total_actual_cost'],
                row['planned_revenue'],
                row['gross_profit']
            ])
        
        content = output.getvalue()
        output.close()
        return content
    
    def export_forward_trace_csv(self, lot_number: str) -> str:
        """Export forward traceability to CSV format"""
        trace_data = self.forward_trace(lot_number)
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Lot info
        lot = trace_data['lot']
        writer.writerow(['Forward Traceability Report'])
        writer.writerow(['Lot Number', lot['lot_number']])
        writer.writerow(['Material', lot['material_name']])
        writer.writerow(['Category', lot['category']])
        writer.writerow(['Supplier', lot.get('supplier', '')])
        writer.writerow([])
        
        # Batches section
        writer.writerow(['Batches Using This Lot'])
        writer.writerow(['Batch Number', 'Product', 'Status', 'Quantity Used', 'Used Date'])
        for batch in trace_data['batches']:
            writer.writerow([
                batch['batch_number'],
                batch['product_name'],
                batch['batch_status'],
                batch['quantity_used'],
                batch['used_date']
            ])
        
        writer.writerow([])
        
        # Orders section
        writer.writerow(['Orders From These Batches'])
        writer.writerow(['Order Number', 'Order Date', 'Customer', 'Product', 'Quantity', 'Finished Lot'])
        for order in trace_data['orders']:
            writer.writerow([
                order['order_number'],
                order['order_date'],
                order['customer_name'],
                order['product_name'],
                order['quantity'],
                order['finished_lot']
            ])
        
        content = output.getvalue()
        output.close()
        return content
    
    def export_backward_trace_csv(self, order_number: str) -> str:
        """Export backward traceability to CSV format"""
        trace_data = self.backward_trace(order_number)
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Order info
        order = trace_data['order']
        writer.writerow(['Backward Traceability Report'])
        writer.writerow(['Order Number', order['order_number']])
        writer.writerow(['Order Date', order['order_date']])
        writer.writerow(['Customer', order['customer_name']])
        writer.writerow(['Customer Phone', order.get('customer_phone', '')])
        writer.writerow([])
        
        # Items section
        writer.writerow(['Order Items'])
        writer.writerow(['Product', 'Quantity', 'Unit Price', 'Subtotal', 'Finished Lot', 'Batch Number'])
        for item in trace_data['items']:
            writer.writerow([
                item['product_name'],
                item['quantity'],
                item['unit_price'],
                item['subtotal'],
                item.get('finished_lot', ''),
                item.get('batch_number', '')
            ])
        
        writer.writerow([])
        
        # Raw materials section
        writer.writerow(['Raw Material Lots'])
        writer.writerow(['Lot Number', 'Material', 'Category', 'Supplier', 'Received Date', 'Expiry Date', 'Quantity Used', 'Batch'])
        for lot in trace_data['raw_material_lots']:
            writer.writerow([
                lot['lot_number'],
                lot['material_name'],
                lot['category'],
                lot.get('supplier', ''),
                lot['received_date'],
                lot.get('expiry_date', ''),
                lot['quantity_used'],
                lot['batch_number']
            ])
        
        content = output.getvalue()
        output.close()
        return content


def get_traceability_manager(db: Database = None) -> TraceabilityManager:
    """Get traceability manager instance"""
    if db is None:
        db = Database()
    return TraceabilityManager(db)
