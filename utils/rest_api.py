"""
Brewery Manager - REST API Module
Provides RESTful API endpoints for external integrations
"""

import json
import hashlib
import secrets
from datetime import datetime, date
from functools import wraps
from typing import Dict, List, Optional, Any
from flask import request, jsonify, current_app


class RestAPI:
    """REST API manager for brewery operations"""
    
    def __init__(self, db):
        self.db = db
        self.api_version = "v1"
        self.rate_limits = {}
    
    def generate_api_key(self, user_id: int, name: str, permissions: List[str] = None) -> Dict:
        """Generate a new API key"""
        api_key = f"brw_{secrets.token_hex(32)}"
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        
        self.db.create_api_key({
            'user_id': user_id,
            'name': name,
            'key_hash': key_hash,
            'permissions': json.dumps(permissions or ['read']),
            'created_at': datetime.now().isoformat(),
            'is_active': 1
        })
        
        return {
            'api_key': api_key,
            'name': name,
            'permissions': permissions or ['read']
        }
    
    def validate_api_key(self, api_key: str) -> Optional[Dict]:
        """Validate API key and return key info"""
        if not api_key:
            return None
        
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        key_info = self.db.get_api_key_by_hash(key_hash)
        
        if key_info and key_info.get('is_active'):
            self.db.update_api_key_last_used(key_info['id'])
            return key_info
        
        return None
    
    def check_permission(self, key_info: Dict, required_permission: str) -> bool:
        """Check if API key has required permission"""
        permissions = json.loads(key_info.get('permissions', '[]'))
        return 'admin' in permissions or required_permission in permissions
    
    def check_rate_limit(self, api_key: str, limit: int = 100, window: int = 3600) -> bool:
        """Check rate limit (requests per window)"""
        now = datetime.now().timestamp()
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()[:16]
        
        if key_hash not in self.rate_limits:
            self.rate_limits[key_hash] = []
        
        self.rate_limits[key_hash] = [
            t for t in self.rate_limits[key_hash] if now - t < window
        ]
        
        if len(self.rate_limits[key_hash]) >= limit:
            return False
        
        self.rate_limits[key_hash].append(now)
        return True
    
    def paginate(self, items: List, page: int = 1, per_page: int = 20) -> Dict:
        """Paginate results"""
        total = len(items)
        start = (page - 1) * per_page
        end = start + per_page
        
        return {
            'items': items[start:end],
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total,
                'pages': (total + per_page - 1) // per_page
            }
        }
    
    def get_materials(self, params: Dict) -> Dict:
        """GET /api/v1/materials"""
        category = params.get('category')
        low_stock = params.get('low_stock', 'false').lower() == 'true'
        page = int(params.get('page', 1))
        per_page = int(params.get('per_page', 20))
        
        materials = self.db.get_raw_materials(category=category, low_stock=low_stock)
        
        items = []
        for m in materials:
            items.append({
                'id': m['id'],
                'name': m['name'],
                'category': m['category'],
                'unit': m['unit'],
                'quantity': m['quantity'],
                'min_quantity': m['min_quantity'],
                'cost_per_unit': m['cost_per_unit'],
                'total_value': m['quantity'] * m['cost_per_unit'],
                'supplier': m.get('supplier'),
                'origin': m.get('origin'),
                'expiry_date': m.get('expiry_date'),
                'storage_location': m.get('storage_location'),
                'status': 'out_of_stock' if m['quantity'] <= 0 else 'low_stock' if m['quantity'] <= m['min_quantity'] else 'ok'
            })
        
        return self.paginate(items, page, per_page)
    
    def get_material(self, material_id: int) -> Optional[Dict]:
        """GET /api/v1/materials/:id"""
        materials = self.db.get_raw_materials()
        material = next((m for m in materials if m['id'] == material_id), None)
        
        if not material:
            return None
        
        return {
            'id': material['id'],
            'name': material['name'],
            'category': material['category'],
            'unit': material['unit'],
            'quantity': material['quantity'],
            'min_quantity': material['min_quantity'],
            'cost_per_unit': material['cost_per_unit'],
            'total_value': material['quantity'] * material['cost_per_unit'],
            'supplier': material.get('supplier'),
            'origin': material.get('origin'),
            'expiry_date': material.get('expiry_date'),
            'storage_location': material.get('storage_location'),
            'notes': material.get('notes'),
            'created_at': material.get('created_at'),
            'updated_at': material.get('updated_at')
        }
    
    def create_material(self, data: Dict) -> Dict:
        """POST /api/v1/materials"""
        material_data = {
            'name': data['name'],
            'category': data.get('category', 'other'),
            'unit': data.get('unit', 'kg'),
            'quantity': float(data.get('quantity', 0)),
            'min_quantity': float(data.get('min_quantity', 0)),
            'cost_per_unit': float(data.get('cost_per_unit', 0)),
            'supplier': data.get('supplier'),
            'origin': data.get('origin'),
            'expiry_date': data.get('expiry_date'),
            'storage_location': data.get('storage_location'),
            'notes': data.get('notes')
        }
        
        material_id = self.db.add_raw_material(material_data)
        material_data['id'] = material_id
        return material_data
    
    def update_material(self, material_id: int, data: Dict) -> bool:
        """PUT /api/v1/materials/:id"""
        return self.db.update_raw_material(material_id, data)
    
    def get_products(self, params: Dict) -> Dict:
        """GET /api/v1/products"""
        active_only = params.get('active', 'true').lower() == 'true'
        page = int(params.get('page', 1))
        per_page = int(params.get('per_page', 20))
        
        products = self.db.get_products(active_only=active_only)
        
        items = []
        for p in products:
            items.append({
                'id': p['id'],
                'name': p['name'],
                'style': p.get('style'),
                'abv': p.get('abv'),
                'ibu': p.get('ibu'),
                'price_per_unit': p.get('price_per_unit'),
                'description': p.get('description'),
                'is_active': p.get('is_active', 1)
            })
        
        return self.paginate(items, page, per_page)
    
    def get_product(self, product_id: int) -> Optional[Dict]:
        """GET /api/v1/products/:id"""
        products = self.db.get_products(active_only=False)
        product = next((p for p in products if p['id'] == product_id), None)
        
        if not product:
            return None
        
        return {
            'id': product['id'],
            'name': product['name'],
            'style': product.get('style'),
            'abv': product.get('abv'),
            'ibu': product.get('ibu'),
            'price_per_unit': product.get('price_per_unit'),
            'description': product.get('description'),
            'is_active': product.get('is_active', 1),
            'created_at': product.get('created_at')
        }
    
    def create_product(self, data: Dict) -> Dict:
        """POST /api/v1/products"""
        product_data = {
            'name': data['name'],
            'style': data.get('style'),
            'abv': float(data.get('abv', 0)),
            'ibu': int(data.get('ibu', 0)),
            'price_per_unit': float(data.get('price_per_unit', 0)),
            'description': data.get('description')
        }
        
        product_id = self.db.add_product(product_data)
        product_data['id'] = product_id
        return product_data
    
    def get_batches(self, params: Dict) -> Dict:
        """GET /api/v1/batches"""
        status = params.get('status')
        page = int(params.get('page', 1))
        per_page = int(params.get('per_page', 20))
        
        batches = self.db.get_batches(status=status)
        
        items = []
        for b in batches:
            items.append({
                'id': b['id'],
                'product_id': b['product_id'],
                'product_name': b.get('product_name'),
                'tank_id': b.get('tank_id'),
                'tank_name': b.get('tank_name'),
                'planned_quantity': b['planned_quantity'],
                'actual_quantity': b.get('actual_quantity'),
                'status': b['status'],
                'start_date': b.get('start_date'),
                'end_date': b.get('end_date'),
                'actual_abv': b.get('actual_abv'),
                'actual_ibu': b.get('actual_ibu')
            })
        
        return self.paginate(items, page, per_page)
    
    def get_batch(self, batch_id: int) -> Optional[Dict]:
        """GET /api/v1/batches/:id"""
        batches = self.db.get_batches()
        batch = next((b for b in batches if b['id'] == batch_id), None)
        
        if not batch:
            return None
        
        return {
            'id': batch['id'],
            'product_id': batch['product_id'],
            'product_name': batch.get('product_name'),
            'tank_id': batch.get('tank_id'),
            'tank_name': batch.get('tank_name'),
            'recipe_id': batch.get('recipe_id'),
            'planned_quantity': batch['planned_quantity'],
            'actual_quantity': batch.get('actual_quantity'),
            'status': batch['status'],
            'start_date': batch.get('start_date'),
            'end_date': batch.get('end_date'),
            'actual_abv': batch.get('actual_abv'),
            'actual_ibu': batch.get('actual_ibu'),
            'notes': batch.get('notes'),
            'created_at': batch.get('created_at')
        }
    
    def create_batch(self, data: Dict) -> Dict:
        """POST /api/v1/batches"""
        batch_data = {
            'product_id': int(data['product_id']),
            'tank_id': int(data['tank_id']) if data.get('tank_id') else None,
            'recipe_id': int(data['recipe_id']) if data.get('recipe_id') else None,
            'planned_quantity': float(data.get('planned_quantity', 0)),
            'start_date': data.get('start_date'),
            'end_date': data.get('end_date'),
            'status': data.get('status', 'planned'),
            'notes': data.get('notes')
        }
        
        batch_id = self.db.create_batch(batch_data)
        batch_data['id'] = batch_id
        return batch_data
    
    def update_batch_status(self, batch_id: int, data: Dict) -> bool:
        """PUT /api/v1/batches/:id/status"""
        status = data.get('status')
        actual_qty = data.get('actual_quantity')
        return self.db.update_batch_status(batch_id, status, actual_qty)
    
    def get_customers(self, params: Dict) -> Dict:
        """GET /api/v1/customers"""
        active_only = params.get('active', 'true').lower() == 'true'
        page = int(params.get('page', 1))
        per_page = int(params.get('per_page', 20))
        
        customers = self.db.get_customers(active_only=active_only)
        
        items = []
        for c in customers:
            items.append({
                'id': c['id'],
                'name': c['name'],
                'type': c.get('type'),
                'contact_person': c.get('contact_person'),
                'phone': c.get('phone'),
                'email': c.get('email'),
                'address': c.get('address'),
                'city': c.get('city'),
                'province': c.get('province'),
                'tax_id': c.get('tax_id'),
                'credit_limit': c.get('credit_limit'),
                'payment_terms': c.get('payment_terms'),
                'is_active': c.get('is_active', 1)
            })
        
        return self.paginate(items, page, per_page)
    
    def get_customer(self, customer_id: int) -> Optional[Dict]:
        """GET /api/v1/customers/:id"""
        customers = self.db.get_customers(active_only=False)
        customer = next((c for c in customers if c['id'] == customer_id), None)
        
        if not customer:
            return None
        
        return {
            'id': customer['id'],
            'name': customer['name'],
            'type': customer.get('type'),
            'contact_person': customer.get('contact_person'),
            'phone': customer.get('phone'),
            'email': customer.get('email'),
            'address': customer.get('address'),
            'city': customer.get('city'),
            'province': customer.get('province'),
            'tax_id': customer.get('tax_id'),
            'credit_limit': customer.get('credit_limit'),
            'payment_terms': customer.get('payment_terms'),
            'notes': customer.get('notes'),
            'is_active': customer.get('is_active', 1),
            'created_at': customer.get('created_at')
        }
    
    def create_customer(self, data: Dict) -> Dict:
        """POST /api/v1/customers"""
        customer_data = {
            'name': data['name'],
            'type': data.get('type', 'retail'),
            'contact_person': data.get('contact_person'),
            'phone': data.get('phone'),
            'email': data.get('email'),
            'address': data.get('address'),
            'city': data.get('city'),
            'province': data.get('province'),
            'tax_id': data.get('tax_id'),
            'credit_limit': float(data.get('credit_limit', 0)),
            'payment_terms': data.get('payment_terms', 'COD'),
            'notes': data.get('notes')
        }
        
        customer_id = self.db.add_customer(customer_data)
        customer_data['id'] = customer_id
        return customer_data
    
    def get_orders(self, params: Dict) -> Dict:
        """GET /api/v1/orders"""
        status = params.get('status')
        page = int(params.get('page', 1))
        per_page = int(params.get('per_page', 20))
        
        orders = self.db.get_sales_orders(status=status)
        
        items = []
        for o in orders:
            items.append({
                'id': o['id'],
                'order_number': o.get('order_number'),
                'customer_id': o['customer_id'],
                'customer_name': o.get('customer_name'),
                'order_date': o.get('order_date'),
                'delivery_date': o.get('delivery_date'),
                'total_amount': o.get('total_amount', 0),
                'status': o['status'],
                'payment_status': o.get('payment_status')
            })
        
        return self.paginate(items, page, per_page)
    
    def get_order(self, order_id: int) -> Optional[Dict]:
        """GET /api/v1/orders/:id"""
        order = self.db.get_order_details(order_id)
        
        if not order:
            return None
        
        items = []
        for item in order.get('items', []):
            items.append({
                'product_id': item['product_id'],
                'product_name': item.get('product_name'),
                'quantity': item['quantity'],
                'unit_price': item['unit_price'],
                'discount': item.get('discount', 0),
                'subtotal': item['quantity'] * item['unit_price'] * (1 - item.get('discount', 0) / 100)
            })
        
        return {
            'id': order['id'],
            'order_number': order.get('order_number'),
            'customer_id': order['customer_id'],
            'customer_name': order.get('customer_name'),
            'order_date': order.get('order_date'),
            'delivery_date': order.get('delivery_date'),
            'total_amount': order.get('total_amount', 0),
            'status': order['status'],
            'payment_status': order.get('payment_status'),
            'notes': order.get('notes'),
            'items': items,
            'created_at': order.get('created_at')
        }
    
    def create_order(self, data: Dict) -> Dict:
        """POST /api/v1/orders"""
        items = []
        for item in data.get('items', []):
            items.append({
                'product_id': int(item['product_id']),
                'quantity': float(item['quantity']),
                'unit_price': float(item['unit_price']),
                'discount': float(item.get('discount', 0))
            })
        
        order_data = {
            'customer_id': int(data['customer_id']),
            'order_date': data.get('order_date', date.today().isoformat()),
            'delivery_date': data.get('delivery_date'),
            'notes': data.get('notes'),
            'items': items
        }
        
        order_id = self.db.create_sales_order(order_data)
        order_data['id'] = order_id
        return order_data
    
    def get_transactions(self, params: Dict) -> Dict:
        """GET /api/v1/transactions"""
        start_date = params.get('start_date')
        end_date = params.get('end_date')
        ttype = params.get('type')
        page = int(params.get('page', 1))
        per_page = int(params.get('per_page', 50))
        
        transactions = self.db.get_transactions(start_date, end_date, ttype)
        
        items = []
        for t in transactions:
            items.append({
                'id': t['id'],
                'transaction_date': t['transaction_date'],
                'type': t['type'],
                'category': t['category'],
                'amount': t['amount'],
                'description': t.get('description'),
                'payment_method': t.get('payment_method')
            })
        
        return self.paginate(items, page, per_page)
    
    def create_transaction(self, data: Dict) -> Dict:
        """POST /api/v1/transactions"""
        transaction_data = {
            'transaction_date': data.get('transaction_date', date.today().isoformat()),
            'type': data['type'],
            'category': data['category'],
            'amount': float(data['amount']),
            'description': data.get('description'),
            'payment_method': data.get('payment_method')
        }
        
        self.db.add_transaction(transaction_data)
        return transaction_data
    
    def get_financial_summary(self, params: Dict) -> Dict:
        """GET /api/v1/finance/summary"""
        start_date = params.get('start_date')
        end_date = params.get('end_date')
        
        summary = self.db.get_financial_summary(start_date, end_date)
        
        return {
            'period': {
                'start_date': start_date,
                'end_date': end_date
            },
            'total_income': summary.get('total_income', 0),
            'total_expense': summary.get('total_expense', 0),
            'net_profit': summary.get('total_income', 0) - summary.get('total_expense', 0),
            'transaction_count': summary.get('transaction_count', 0)
        }
    
    def get_dashboard(self) -> Dict:
        """GET /api/v1/dashboard"""
        data = self.db.get_dashboard_data()
        low_stock = self.db.get_low_stock_alerts()
        
        return {
            'summary': {
                'total_products': data.get('total_products', 0),
                'active_batches': data.get('active_batches', 0),
                'pending_orders': data.get('pending_orders', 0),
                'total_customers': data.get('total_customers', 0),
                'monthly_revenue': data.get('monthly_revenue', 0),
                'monthly_expenses': data.get('monthly_expenses', 0)
            },
            'alerts': {
                'low_stock_count': len(low_stock),
                'low_stock_items': [
                    {
                        'id': item['id'],
                        'name': item['name'],
                        'quantity': item['quantity'],
                        'min_quantity': item['min_quantity']
                    }
                    for item in low_stock[:10]
                ]
            },
            'timestamp': datetime.now().isoformat()
        }
    
    def get_recipes(self, params: Dict) -> Dict:
        """GET /api/v1/recipes"""
        active_only = params.get('active', 'true').lower() == 'true'
        page = int(params.get('page', 1))
        per_page = int(params.get('per_page', 20))
        
        recipes = self.db.get_recipes(active_only=active_only)
        
        items = []
        for r in recipes:
            items.append({
                'id': r['id'],
                'name': r['name'],
                'style': r.get('style'),
                'batch_size': r.get('batch_size'),
                'abv': r.get('abv'),
                'ibu': r.get('ibu'),
                'srm': r.get('srm'),
                'is_active': r.get('is_active', 1)
            })
        
        return self.paginate(items, page, per_page)
    
    def get_recipe(self, recipe_id: int) -> Optional[Dict]:
        """GET /api/v1/recipes/:id"""
        recipe = self.db.get_recipe_details(recipe_id)
        
        if not recipe:
            return None
        
        return {
            'id': recipe['id'],
            'name': recipe['name'],
            'style': recipe.get('style'),
            'batch_size': recipe.get('batch_size'),
            'batch_size_unit': recipe.get('batch_size_unit', 'L'),
            'boil_time': recipe.get('boil_time'),
            'efficiency': recipe.get('efficiency'),
            'og': recipe.get('og'),
            'fg': recipe.get('fg'),
            'abv': recipe.get('abv'),
            'ibu': recipe.get('ibu'),
            'srm': recipe.get('srm'),
            'description': recipe.get('description'),
            'notes': recipe.get('notes'),
            'fermentables': recipe.get('fermentables', []),
            'hops': recipe.get('hops', []),
            'yeasts': recipe.get('yeasts', []),
            'mash_steps': recipe.get('mash_steps', []),
            'is_active': recipe.get('is_active', 1)
        }
    
    def get_equipment(self, params: Dict) -> Dict:
        """GET /api/v1/equipment"""
        eq_type = params.get('type')
        page = int(params.get('page', 1))
        per_page = int(params.get('per_page', 20))
        
        equipment = self.db.get_equipment(equipment_type=eq_type)
        
        items = []
        for e in equipment:
            items.append({
                'id': e['id'],
                'name': e['name'],
                'type': e['equipment_type'],
                'capacity': e.get('capacity'),
                'capacity_unit': e.get('capacity_unit', 'L'),
                'status': e['status'],
                'location': e.get('location'),
                'last_cleaned': e.get('last_cleaned'),
                'next_maintenance': e.get('next_maintenance')
            })
        
        return self.paginate(items, page, per_page)
    
    def get_tanks(self, params: Dict) -> Dict:
        """GET /api/v1/tanks"""
        tank_assignments = self.db.get_tank_assignments()
        
        items = []
        for t in tank_assignments:
            items.append({
                'id': t['id'],
                'name': t['name'],
                'capacity': t.get('capacity'),
                'status': t['status'],
                'batch_id': t.get('batch_id'),
                'product_name': t.get('product_name'),
                'batch_status': t.get('batch_status'),
                'days_in_tank': t.get('days_in_tank'),
                'last_cleaned': t.get('last_cleaned')
            })
        
        return {'tanks': items}
    
    def get_staff(self, params: Dict) -> Dict:
        """GET /api/v1/staff"""
        department = params.get('department')
        active_only = params.get('active', 'true').lower() == 'true'
        page = int(params.get('page', 1))
        per_page = int(params.get('per_page', 20))
        
        staff = self.db.get_staff(department=department, active_only=active_only)
        
        items = []
        for s in staff:
            items.append({
                'id': s['id'],
                'name': s['name'],
                'position': s['position'],
                'department': s.get('department'),
                'phone': s.get('phone'),
                'email': s.get('email'),
                'hire_date': s.get('hire_date'),
                'is_active': s.get('is_active', 1)
            })
        
        return self.paginate(items, page, per_page)


def get_rest_api(db):
    """Get REST API instance"""
    return RestAPI(db)


def api_auth_required(permission='read'):
    """Decorator for API authentication"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            from flask import g
            
            api_key = request.headers.get('X-API-Key') or request.args.get('api_key')
            
            if not api_key:
                return jsonify({
                    'error': 'Missing API key',
                    'message': 'Please provide API key in X-API-Key header or api_key query parameter'
                }), 401
            
            api = get_rest_api(g.db)
            key_info = api.validate_api_key(api_key)
            
            if not key_info:
                return jsonify({
                    'error': 'Invalid API key',
                    'message': 'The provided API key is invalid or inactive'
                }), 401
            
            if not api.check_permission(key_info, permission):
                return jsonify({
                    'error': 'Insufficient permissions',
                    'message': f'This endpoint requires {permission} permission'
                }), 403
            
            if not api.check_rate_limit(api_key):
                return jsonify({
                    'error': 'Rate limit exceeded',
                    'message': 'Too many requests. Please try again later.'
                }), 429
            
            g.api_key_info = key_info
            g.api = api
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator