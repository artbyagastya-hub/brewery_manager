"""
AI Planner Module - Active planning for autonomous brewery management
Enables the AI to proactively create and execute plans
"""

import os
import sys
import json
from datetime import datetime, date, timedelta
from typing import Dict, List, Any, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from models.database import Database
from utils.ai_memory import get_memory

db = Database()

class AIPlanner:
    """Active planning system for autonomous operations"""
    
    # Planning modes
    MODE_REACTIVE = 'reactive'      # Only responds to user requests
    MODE_PROACTIVE = 'proactive'    # Makes suggestions and observations
    MODE_AUTONOMOUS = 'autonomous'  # Takes actions automatically
    
    def __init__(self):
        self.memory = get_memory()
        self.mode = self.memory.get_context('planning_mode') or self.MODE_PROACTIVE
        self.auto_actions_enabled = self.memory.get_context('auto_actions') or False
    
    def set_mode(self, mode: str):
        """Set planning mode"""
        if mode in [self.MODE_REACTIVE, self.MODE_PROACTIVE, self.MODE_AUTONOMOUS]:
            self.mode = mode
            self.memory.update_context('planning_mode', mode)
    
    def enable_auto_actions(self, enabled: bool = True):
        """Enable/disable automatic action execution"""
        self.auto_actions_enabled = enabled
        self.memory.update_context('auto_actions', enabled)
    
    def analyze_situation(self) -> Dict:
        """Analyze current brewery situation and identify opportunities/issues"""
        analysis = {
            'timestamp': datetime.now().isoformat(),
            'alerts': [],
            'opportunities': [],
            'recommendations': [],
            'goal_progress': [],
            'status': 'healthy'
        }
        
        # Check inventory levels
        try:
            low_stock = db.execute_query(
                "SELECT COUNT(*) as count FROM raw_materials WHERE quantity <= min_quantity "
            )
            if low_stock and low_stock[0]['count'] > 0:
                analysis['alerts'].append({
                    'type': 'inventory',
                    'severity': 'warning',
                    'message': f"{low_stock[0]['count']} items are at or below minimum stock level",
                    'action': 'Review and reorder low stock items'
                })
        except Exception as e:
            import logging
            logging.error(f"AI Planner Error: {str(e)}")
        
        # Check active batches
        try:
            active_batches = db.execute_query(
                "SELECT COUNT(*) as count FROM production_batches WHERE status IN ('in_progress', 'fermenting')"
            )
            if active_batches and active_batches[0]['count'] == 0:
                analysis['opportunities'].append({
                    'type': 'production',
                    'message': 'No active batches - consider scheduling production',
                    'action': 'Schedule new batch'
                })
        except Exception as e:
            import logging
            logging.error(f"AI Planner Error: {str(e)}")
        
        # Check pending orders
        try:
            pending_orders = db.execute_query(
                "SELECT COUNT(*) as count FROM sales_orders WHERE status = 'pending'"
            )
            if pending_orders and pending_orders[0]['count'] > 0:
                analysis['recommendations'].append({
                    'type': 'sales',
                    'message': f"{pending_orders[0]['count']} orders pending confirmation",
                    'action': 'Review and confirm pending orders'
                })
        except Exception as e:
            import logging
            logging.error(f"AI Planner Error: {str(e)}")
        
        # Check tank availability
        try:
            tanks = db.execute_query(
                "SELECT COUNT(*) as count FROM equipment WHERE equipment_type = 'tank' AND status = 'available'"
            )
            if tanks and tanks[0]['count'] > 0:
                analysis['opportunities'].append({
                    'type': 'equipment',
                    'message': f"{tanks[0]['count']} tanks available for new batches",
                    'action': 'Consider scheduling production'
                })
        except Exception as e:
            import logging
            logging.error(f"AI Planner Error: {str(e)}")
        
        # Determine overall status
        if len(analysis['alerts']) > 2:
            analysis['status'] = 'attention_needed'
        elif len(analysis['alerts']) > 0:
            analysis['status'] = 'minor_issues'
        
        # Store observation
        self.memory.remember_observation(
            'situation_analysis',
            f"Status: {analysis['status']}, Alerts: {len(analysis['alerts'])}, Opportunities: {len(analysis['opportunities'])}",
            'normal'
        )
        
        return analysis
    
    def create_production_plan(self, objectives: List[str] = None) -> Dict:
        """Create a production plan based on current state"""
        plan = {
            'type': 'production',
            'created_at': datetime.now().isoformat(),
            'objectives': objectives or ['Optimize production efficiency'],
            'steps': [],
            'estimated_duration': '1 week',
            'status': 'draft'
        }
        
        # Check what's needed
        try:
            # Get low stock items that affect production
            low_stock = db.execute_query("""
                SELECT name, quantity, min_quantity, unit 
                FROM raw_materials 
                WHERE quantity <= min_quantity * 1.2 
                ORDER BY (quantity / NULLIF(min_quantity, 0))
                LIMIT 5
            """)
            
            if low_stock:
                plan['steps'].append({
                    'order': 1,
                    'action': 'Restock materials',
                    'details': [f"Order {item['name']}: {item['quantity']}{item['unit']} remaining" 
                               for item in low_stock],
                    'priority': 'high'
                })
            
            # Check tank availability
            tanks = db.execute_query("""
                SELECT COUNT(*) as available 
                FROM equipment 
                WHERE equipment_type LIKE '%tank%' AND status = 'available'
            """)
            
            if tanks and tanks[0]['available'] > 0:
                plan['steps'].append({
                    'order': len(plan['steps']) + 1,
                    'action': 'Schedule production',
                    'details': [f"{tanks[0]['available']} tanks available"],
                    'priority': 'medium'
                })
            
            # Check active batches needing attention
            fermenting = db.execute_query("""
                SELECT b.id, p.name as product_name, b.start_date
                FROM production_batches b
                JOIN products p ON b.product_id = p.id
                WHERE b.status = 'fermenting'
                ORDER BY b.start_date
                LIMIT 3
            """)
            
            if fermenting:
                plan['steps'].append({
                    'order': len(plan['steps']) + 1,
                    'action': 'Monitor fermentation',
                    'details': [f"Batch #{b['id']} ({b['product_name']}) - started {b['start_date']}" 
                               for b in fermenting],
                    'priority': 'medium'
                })
            
        except Exception as e:
            plan['error'] = str(e)
        
        # Record plan in memory
        self.memory.record_plan(
            'production',
            plan['objectives'],
            plan['steps']
        )
        
        return plan
    
    def create_inventory_plan(self) -> Dict:
        """Create an inventory management plan"""
        plan = {
            'type': 'inventory',
            'created_at': datetime.now().isoformat(),
            'objectives': ['Maintain optimal stock levels', 'Prevent stockouts'],
            'actions': [],
            'status': 'draft'
        }
        
        try:
            # Items needing reorder
            reorder = db.execute_query("""
                SELECT name, quantity, min_quantity, unit, supplier
                FROM raw_materials 
                WHERE quantity <= min_quantity 
                ORDER BY (quantity / NULLIF(min_quantity, 0))
            """)
            
            for item in reorder:
                plan['actions'].append({
                    'action': 'reorder',
                    'item': item['name'],
                    'current': f"{item['quantity']}{item['unit']}",
                    'minimum': f"{item['min_quantity']}{item['unit']}",
                    'supplier': item.get('supplier', 'Unknown'),
                    'priority': 'high' if item['quantity'] <= item['min_quantity'] * 0.5 else 'medium'
                })
            
            # Items expiring soon
            expiring = db.execute_query("""
                SELECT name, quantity, unit, expiry_date
                FROM raw_materials 
                WHERE expiry_date <= date('now', '+7 days') AND quantity > 0 
                ORDER BY expiry_date
            """)
            
            for item in expiring:
                plan['actions'].append({
                    'action': 'use_soon',
                    'item': item['name'],
                    'quantity': f"{item['quantity']}{item['unit']}",
                    'expires': item['expiry_date'],
                    'priority': 'urgent'
                })
                
        except Exception as e:
            plan['error'] = str(e)
        
        # Record plan
        self.memory.record_plan(
            'inventory',
            plan['objectives'],
            plan['actions']
        )
        
        return plan
    
    def create_sales_plan(self) -> Dict:
        """Create a sales optimization plan"""
        plan = {
            'type': 'sales',
            'created_at': datetime.now().isoformat(),
            'objectives': ['Increase revenue', 'Improve customer satisfaction'],
            'actions': [],
            'status': 'draft'
        }
        
        try:
            # Pending orders
            pending = db.execute_query("""
                SELECT COUNT(*) as count, SUM(total_amount) as value
                FROM sales_orders 
                WHERE status = 'pending'
            """)
            
            if pending and pending[0]['count'] > 0:
                plan['actions'].append({
                    'action': 'process_orders',
                    'details': f"{pending[0]['count']} pending orders worth {pending[0]['value'] or 0:,.0f}",
                    'priority': 'high'
                })
            
            # Low stock products
            low_products = db.execute_query("""
                SELECT p.name, SUM(i.quantity) as stock
                FROM products p
                LEFT JOIN inventory i ON p.name LIKE '%' || i.name || '%'
                WHERE p.active = 1
                GROUP BY p.id
                HAVING stock < 10 OR stock IS NULL
                LIMIT 5
            """)
            
            if low_products:
                plan['actions'].append({
                    'action': 'restock_products',
                    'details': [p['name'] for p in low_products],
                    'priority': 'medium'
                })
                
        except Exception as e:
            plan['error'] = str(e)
        
        # Record plan
        self.memory.record_plan(
            'sales',
            plan['objectives'],
            plan['actions']
        )
        
        return plan
    
    def generate_daily_agenda(self) -> Dict:
        """Generate a daily agenda based on current state"""
        agenda = {
            'date': date.today().isoformat(),
            'generated_at': datetime.now().isoformat(),
            'priorities': [],
            'tasks': [],
            'reminders': []
        }
        
        # Analyze situation
        situation = self.analyze_situation()
        
        # Add alerts as priorities
        for alert in situation['alerts']:
            agenda['priorities'].append({
                'priority': 'high',
                'item': alert['message'],
                'action': alert['action']
            })
        
        # Add recommendations as tasks
        for rec in situation['recommendations']:
            agenda['tasks'].append({
                'priority': 'medium',
                'task': rec['message'],
                'action': rec['action']
            })
        
        # Add opportunities as reminders
        for opp in situation['opportunities']:
            agenda['reminders'].append({
                'type': 'opportunity',
                'item': opp['message'],
                'action': opp['action']
            })
        
        # Get today's tasks from database
        try:
            today_tasks = db.execute_query("""
                SELECT title, priority, status, task_type
                FROM daily_tasks
                WHERE task_date = date('now')
                ORDER BY 
                    CASE priority 
                        WHEN 'urgent' THEN 1 
                        WHEN 'high' THEN 2 
                        WHEN 'normal' THEN 3 
                        ELSE 4 
                    END
            """)
            
            for task in today_tasks:
                agenda['tasks'].append({
                    'priority': task['priority'],
                    'task': task['title'],
                    'type': task['task_type'],
                    'status': task['status']
                })
        except Exception as e:
            import logging
            logging.error(f"AI Planner Error: {str(e)}")
        
        # Store in context
        self.memory.update_context('daily_agenda', agenda)
        
        return agenda
    
    def should_take_action(self, action_type: str, context: Dict = None) -> bool:
        """Determine if AI should take automatic action"""
        if not self.auto_actions_enabled:
            return False
        
        if self.mode == self.MODE_REACTIVE:
            return False
        
        # Check if action is safe to auto-execute
        safe_actions = ['observation', 'suggestion', 'reminder', 'analysis']
        if action_type in safe_actions:
            return True
        
        # For destructive actions, require autonomous mode
        if self.mode == self.MODE_AUTONOMOUS:
            return True
        
        return False
    
    def get_proactive_suggestions(self) -> List[Dict]:
        """Get proactive suggestions based on current state"""
        suggestions = []
        
        if self.mode == self.MODE_REACTIVE:
            return suggestions
        
        # Analyze current situation
        situation = self.analyze_situation()
        
        # Convert alerts to suggestions
        for alert in situation['alerts']:
            suggestions.append({
                'type': 'alert',
                'message': alert['message'],
                'suggested_action': alert['action'],
                'urgency': alert['severity']
            })
        
        # Convert opportunities to suggestions
        for opp in situation['opportunities']:
            suggestions.append({
                'type': 'opportunity',
                'message': opp['message'],
                'suggested_action': opp['action'],
                'urgency': 'low'
            })
        
        # Check patterns for proactive suggestions
        patterns = self.memory.get_patterns('sales')
        if patterns:
            # Add pattern-based suggestions
            pass
        
        return suggestions
    
    def get_planning_status(self) -> Dict:
        """Get current planning status"""
        return {
            'mode': self.mode,
            'auto_actions_enabled': self.auto_actions_enabled,
            'memory_summary': self.memory.get_memory_summary(),
            'last_analysis': self.memory.get_context('last_analysis')
        }

# Singleton instance
_planner = None

def get_planner() -> AIPlanner:
    """Get singleton planner instance"""
    global _planner
    if _planner is None:
        _planner = AIPlanner()
    return _planner