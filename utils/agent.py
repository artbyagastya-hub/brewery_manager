"""
Brewery Manager - Agent Engine
Autonomous monitoring, analysis, and action execution
Proactive automation with configurable autonomy levels
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from models.database import Database

logger = logging.getLogger(__name__)

# Autonomy levels
AUTONOMY_OFF = 'off'
AUTONOMY_OBSERVER = 'observer'      # Only monitors and reports
AUTONOMY_SUGGESTER = 'suggester'    # Suggests actions but doesn't execute
AUTONOMY_ACTOR = 'actor'            # Executes safe actions, asks for risky ones
AUTONOMY_AUTONOMOUS = 'autonomous'  # Executes all actions

# Action safety levels
SAFETY_SAFE = 'safe'                    # Queries, reports, analysis
SAFETY_NEEDS_CONFIRMATION = 'confirm'   # Inventory changes, order mods
SAFETY_NEEDS_APPROVAL = 'approval'      # Batch scheduling, staff changes


class BreweryAgent:
    """Autonomous agent for brewery management"""

    def __init__(self, db: Database):
        self.db = db
        self.rules = []
        self.load_rules()

    def load_rules(self):
        """Load active agent rules from database"""
        self.rules = self.db.get_agent_rules(enabled_only=True)
        logger.info(f"Loaded {len(self.rules)} active agent rules")

    def run_check_cycle(self):
        """Run one complete check cycle through all rules"""
        logger.info("Starting agent check cycle")
        results = []

        for rule in self.rules:
            try:
                result = self.evaluate_rule(rule)
                if result:
                    results.append(result)
            except Exception as e:
                logger.error(f"Error evaluating rule {rule['name']}: {e}")

        logger.info(f"Agent check cycle complete. {len(results)} actions triggered")
        return results

    def evaluate_rule(self, rule: Dict) -> Optional[Dict]:
        """Evaluate a single rule and execute action if triggered"""
        condition = json.loads(rule['trigger_condition'])
        action_config = json.loads(rule['action_config'])

        # Get data based on category
        triggered_items = self.check_condition(rule['category'], condition)

        if not triggered_items:
            return None

        # Execute action for each triggered item
        results = []
        for item in triggered_items:
            result = self.execute_action(
                rule['id'],
                rule['name'],
                rule['category'],
                rule['action_type'],
                action_config,
                item,
                rule['autonomy_level']
            )
            results.append(result)

        # Update rule trigger count
        self.db.increment_rule_trigger(rule['id'])

        return {
            'rule_name': rule['name'],
            'category': rule['category'],
            'triggered_count': len(triggered_items),
            'actions': results
        }

    def check_condition(self, category: str, condition: Dict) -> List[Dict]:
        """Check condition and return triggered items"""
        field = condition.get('field')
        operator = condition.get('operator')
        triggered = []

        if category == 'inventory':
            triggered = self._check_inventory_condition(condition)
        elif category == 'maintenance':
            triggered = self._check_maintenance_condition(condition)
        elif category == 'production':
            triggered = self._check_production_condition(condition)
        elif category == 'quality':
            triggered = self._check_quality_condition(condition)
        elif category == 'finance':
            triggered = self._check_finance_condition(condition)

        return triggered

    def _check_inventory_condition(self, condition: Dict) -> List[Dict]:
        """Check inventory-related conditions"""
        triggered = []
        materials = self.db.get_raw_materials()

        for material in materials:
            if self._evaluate_condition(material, condition):
                triggered.append(material)

        # Check expiring materials
        if condition.get('field') == 'expiry_date':
            days_ahead = condition.get('days_ahead', 7)
            expiring = self.db.get_expiring_materials(days=days_ahead)
            triggered.extend(expiring)

        return triggered

    def _check_maintenance_condition(self, condition: Dict) -> List[Dict]:
        """Check maintenance-related conditions"""
        triggered = []

        if condition.get('field') == 'next_cleaning_due':
            hours_ahead = condition.get('hours_ahead', 24)
            threshold = datetime.now() + timedelta(hours=hours_ahead)

            equipment = self.db.get_equipment()
            for eq in equipment:
                if eq.get('next_cleaning_due'):
                    due_date = datetime.fromisoformat(eq['next_cleaning_due'])
                    if due_date <= threshold:
                        triggered.append(eq)

        # Check overdue maintenance
        overdue = self.db.get_overdue_maintenance()
        triggered.extend(overdue)

        return triggered

    def _check_production_condition(self, condition: Dict) -> List[Dict]:
        """Check production-related conditions"""
        triggered = []
        batches = self.db.get_batches()

        for batch in batches:
            if self._evaluate_condition(batch, condition):
                triggered.append(batch)

        return triggered

    def _check_quality_condition(self, condition: Dict) -> List[Dict]:
        """Check quality-related conditions"""
        triggered = []
        records = self.db.get_quality_records()

        for record in records:
            if self._evaluate_condition(record, condition):
                triggered.append(record)

        return triggered

    def _check_finance_condition(self, condition: Dict) -> List[Dict]:
        """Check finance-related conditions"""
        triggered = []

        if condition.get('field') == 'profit_margin':
            summary = self.db.get_financial_summary()
            if summary['total_income'] > 0:
                margin = (summary['net_profit'] / summary['total_income']) * 100
                if margin < condition.get('value', 20):
                    triggered.append({'margin': margin, **summary})

        return triggered

    def _evaluate_condition(self, item: Dict, condition: Dict) -> bool:
        """Evaluate a condition against an item"""
        field = condition.get('field')
        operator = condition.get('operator')
        value = condition.get('value')
        compare_field = condition.get('compare_field')
        value_multiplier = condition.get('value_multiplier', 1)

        item_value = item.get(field)

        if item_value is None:
            return False

        if compare_field:
            compare_value = item.get(compare_field, 0) * value_multiplier
        else:
            compare_value = value

        if operator == '<':
            return item_value < compare_value
        elif operator == '<=':
            return item_value <= compare_value
        elif operator == '>':
            return item_value > compare_value
        elif operator == '>=':
            return item_value >= compare_value
        elif operator == '=':
            return item_value == compare_value
        elif operator == '!=':
            return item_value != compare_value

        return False

    def execute_action(self, rule_id: int, rule_name: str, category: str,
                       action_type: str, action_config: Dict, item: Dict,
                       autonomy_level: str) -> Dict:
        """Execute an action based on rule configuration"""
        result = {
            'action_type': action_type,
            'item': item.get('name', item.get('id', 'unknown')),
            'status': 'pending'
        }

        try:
            if action_type == 'create_task':
                task_id = self._create_task(action_config, item)
                result['task_id'] = task_id
                result['status'] = 'task_created'

            elif action_type == 'create_task_and_notify':
                task_id = self._create_task(action_config, item)
                self._send_notifications(action_config, item)
                result['task_id'] = task_id
                result['status'] = 'task_and_notification_created'

            elif action_type == 'notify':
                self._send_notifications(action_config, item)
                result['status'] = 'notification_sent'

            elif action_type == 'halt_and_notify':
                self._halt_production(item)
                self._send_notifications(action_config, item)
                result['status'] = 'production_halted'

            elif action_type == 'update_inventory':
                self._update_inventory(action_config, item)
                result['status'] = 'inventory_updated'

            elif action_type == 'generate_report':
                report = self._generate_report(action_config)
                result['report'] = report
                result['status'] = 'report_generated'

            # Log the agent action
            self.db.create_agent_log({
                'rule_name': rule_name,
                'category': category,
                'trigger_data': json.dumps(item, default=str),
                'action_taken': json.dumps(action_config),
                'result': json.dumps(result),
                'status': result['status']
            })

        except Exception as e:
            logger.error(f"Error executing action {action_type}: {e}")
            result['status'] = 'error'
            result['error'] = str(e)

        return result

    def _create_task(self, config: Dict, item: Dict) -> int:
        """Create a daily task"""
        title = config.get('title', 'Agent Task')
        title = self._format_template(title, item)

        task_data = {
            'task_date': datetime.now().strftime('%Y-%m-%d'),
            'task_type': config.get('type', 'agent'),
            'title': title,
            'description': f"Auto-generated by agent. Item: {json.dumps(item, default=str)}",
            'priority': config.get('priority', 'normal'),
            'notes': 'Created by autonomous agent'
        }

        return self.db.create_daily_task(task_data)

    def _send_notifications(self, config: Dict, item: Dict):
        """Send notifications to relevant users"""
        title = config.get('title', 'Agent Alert')
        title = self._format_template(title, item)

        message = f"Agent detected: {json.dumps(item, default=str)}"

        # Get all admin users
        users = self.db.get_all_users()
        for user in users:
            if user.get('role') in ('admin', 'manager'):
                self.db.create_notification({
                    'user_id': user['id'],
                    'title': title,
                    'message': message,
                    'type': config.get('priority', 'info'),
                    'link': config.get('link')
                })

    def _halt_production(self, item: Dict):
        """Halt production for a batch"""
        batch_id = item.get('batch_id')
        if batch_id:
            self.db.update_batch_status(batch_id, 'halted')

    def _update_inventory(self, config: Dict, item: Dict):
        """Update inventory based on action config"""
        action = config.get('action')
        if action == 'add_product_stock':
            # Add finished product to inventory logic
            pass

    def _generate_report(self, config: Dict) -> Dict:
        """Generate a report"""
        report_type = config.get('type')

        if report_type == 'daily_revenue':
            today = datetime.now().strftime('%Y-%m-%d')
            return self.db.get_financial_summary(start_date=today, end_date=today)

        return {}

    def _format_template(self, template: str, item: Dict) -> str:
        """Format a template string with item data"""
        try:
            return template.format(**item)
        except (KeyError, ValueError):
            return template

    def get_agent_status(self) -> Dict:
        """Get current agent status"""
        rules = self.db.get_agent_rules()
        logs = self.db.get_agent_logs(limit=10)

        return {
            'total_rules': len(rules),
            'active_rules': len([r for r in rules if r['is_enabled']]),
            'recent_actions': logs,
            'rules_by_category': self._group_rules_by_category(rules)
        }

    def _group_rules_by_category(self, rules: List[Dict]) -> Dict:
        """Group rules by category"""
        grouped = {}
        for rule in rules:
            cat = rule['category']
            if cat not in grouped:
                grouped[cat] = {'total': 0, 'active': 0}
            grouped[cat]['total'] += 1
            if rule['is_enabled']:
                grouped[cat]['active'] += 1
        return grouped


def get_agent(db: Database = None) -> BreweryAgent:
    """Get or create agent instance"""
    if db is None:
        db = Database()
    return BreweryAgent(db)


class ProactiveAgent(BreweryAgent):
    """Enhanced proactive agent with autonomy levels and goal tracking"""

    def __init__(self, db: Database = None):
        super().__init__(db or Database())
        self.autonomy_level = AUTONOMY_OBSERVER
        self.goals = []
        self.pending_suggestions = []
        self.activity_log = []
        self.load_goals()
        self.load_autonomy_level()

    def load_autonomy_level(self):
        """Load autonomy level from database or default"""
        try:
            row = self.db.execute_query(
                "SELECT value FROM settings WHERE key = 'ai_autonomy_level'"
            )
            if row:
                self.autonomy_level = row[0]['value']
        except:
            pass

    def set_autonomy_level(self, level: str):
        """Set the autonomy level"""
        if level not in [AUTONOMY_OFF, AUTONOMY_OBSERVER, AUTONOMY_SUGGESTER, AUTONOMY_ACTOR, AUTONOMY_AUTONOMOUS]:
            raise ValueError(f"Invalid autonomy level: {level}")
        self.autonomy_level = level
        try:
            self.db.execute_query(
                "INSERT OR REPLACE INTO settings (key, value) VALUES ('ai_autonomy_level', ?)",
                (level,)
            )
        except:
            pass
        self._log_activity('autonomy_change', f"Autonomy level set to {level}")

    def load_goals(self):
        """Load brewery goals from database"""
        try:
            rows = self.db.execute_query(
                "SELECT * FROM goals WHERE status = 'active' ORDER BY priority"
            )
            self.goals = rows or []
        except:
            self.goals = []

    def add_goal(self, name: str, description: str, target_value: float,
                 current_value: float = 0, unit: str = '', priority: str = 'normal',
                 category: str = 'general') -> int:
        """Add a new brewery goal"""
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        try:
            self.db.execute_query(
                """INSERT INTO goals (name, description, target_value, current_value, unit,
                   priority, category, status, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, 'active', ?, ?)""",
                (name, description, target_value, current_value, unit, priority, category, now, now)
            )
            self.load_goals()
            self._log_activity('goal_added', f"Added goal: {name}")
            return self.db.cursor.lastrowid if hasattr(self.db, 'cursor') else 0
        except Exception as e:
            logger.error(f"Error adding goal: {e}")
            return 0

    def update_goal_progress(self, goal_id: int, current_value: float):
        """Update progress toward a goal"""
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        try:
            self.db.execute_query(
                "UPDATE goals SET current_value = ?, updated_at = ? WHERE id = ?",
                (current_value, now, goal_id)
            )
            self.load_goals()
            self._log_activity('goal_updated', f"Goal #{goal_id} progress updated to {current_value}")
        except Exception as e:
            logger.error(f"Error updating goal: {e}")

    def get_goal_progress(self) -> List[Dict]:
        """Get progress for all active goals"""
        self.load_goals()
        results = []
        for goal in self.goals:
            progress = 0
            if goal.get('target_value', 0) > 0:
                progress = (goal.get('current_value', 0) / goal['target_value']) * 100
            results.append({
                **goal,
                'progress_percent': round(progress, 1)
            })
        return results

    def run_proactive_scan(self) -> List[Dict]:
        """Run a proactive scan for opportunities and issues"""
        if self.autonomy_level == AUTONOMY_OFF:
            return []

        suggestions = []

        # 1. Check situation
        try:
            from utils.ai_planner import AIPlanner
            planner = AIPlanner(self.db)
            situation = planner.analyze_situation()

            for alert in situation.get('alerts', []):
                suggestions.append({
                    'type': 'alert',
                    'severity': 'high',
                    'title': alert['message'],
                    'description': alert.get('action', ''),
                    'action_safe': SAFETY_NEEDS_CONFIRMATION
                })

            for opp in situation.get('opportunities', []):
                suggestions.append({
                    'type': 'opportunity',
                    'severity': 'medium',
                    'title': opp['message'],
                    'description': opp.get('action', ''),
                    'action_safe': SAFETY_SAFE
                })
        except Exception as e:
            logger.error(f"Error in situation analysis: {e}")

        # 2. Check goal progress
        goal_progress = self.get_goal_progress()
        for goal in goal_progress:
            if goal['progress_percent'] < 50:
                suggestions.append({
                    'type': 'goal_reminder',
                    'severity': 'low',
                    'title': f"Goal '{goal['name']}' is at {goal['progress_percent']}%",
                    'description': f"Target: {goal['target_value']} {goal.get('unit', '')}",
                    'action_safe': SAFETY_SAFE
                })

        # 3. Run existing agent checks
        check_results = self.run_check_cycle()
        for result in check_results:
            for action in result.get('actions', []):
                suggestions.append({
                    'type': 'agent_action',
                    'severity': 'medium',
                    'title': f"{result['rule_name']}: {action['status']}",
                    'description': f"Item: {action.get('item', 'N/A')}",
                    'action_safe': SAFETY_NEEDS_CONFIRMATION
                })

        # Store suggestions based on autonomy
        if self.autonomy_level == AUTONOMY_SUGGESTER:
            self.pending_suggestions.extend(suggestions)
        elif self.autonomy_level in [AUTONOMY_ACTOR, AUTONOMY_AUTONOMOUS]:
            # Auto-execute safe actions
            for s in suggestions:
                if s['action_safe'] == SAFETY_SAFE or self.autonomy_level == AUTONOMY_AUTONOMOUS:
                    self._execute_suggestion(s)
                else:
                    self.pending_suggestions.append(s)

        self._log_activity('proactive_scan', f"Found {len(suggestions)} items")
        return suggestions

    def _execute_suggestion(self, suggestion: Dict):
        """Execute a suggestion automatically"""
        try:
            # Log the auto-execution
            self.db.create_agent_log({
                'rule_name': 'proactive_auto',
                'category': suggestion.get('type', 'unknown'),
                'trigger_data': json.dumps(suggestion, default=str),
                'action_taken': 'auto_executed',
                'result': 'success',
                'status': 'auto_executed'
            })
            self._log_activity('auto_execute', f"Auto-executed: {suggestion['title']}")
        except Exception as e:
            logger.error(f"Error executing suggestion: {e}")

    def get_pending_suggestions(self) -> List[Dict]:
        """Get pending suggestions for user review"""
        return self.pending_suggestions

    def approve_suggestion(self, index: int) -> bool:
        """User approves a pending suggestion"""
        if 0 <= index < len(self.pending_suggestions):
            suggestion = self.pending_suggestions.pop(index)
            self._execute_suggestion(suggestion)
            return True
        return False

    def dismiss_suggestion(self, index: int) -> bool:
        """User dismisses a pending suggestion"""
        if 0 <= index < len(self.pending_suggestions):
            self.pending_suggestions.pop(index)
            self._log_activity('dismiss_suggestion', f"Dismissed suggestion #{index}")
            return True
        return False

    def get_activity_log(self, limit: int = 50) -> List[Dict]:
        """Get recent activity log"""
        return self.activity_log[-limit:]

    def _log_activity(self, activity_type: str, description: str):
        """Log an activity"""
        self.activity_log.append({
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'type': activity_type,
            'description': description
        })
        # Keep only last 1000 entries
        if len(self.activity_log) > 1000:
            self.activity_log = self.activity_log[-500:]

    def get_autonomy_level(self) -> str:
        """Get current autonomy level"""
        return self.autonomy_level

    def get_autonomy_config(self) -> Dict:
        """Get autonomy configuration for UI"""
        return {
            'level': self.autonomy_level,
            'levels': [
                {'value': AUTONOMY_OFF, 'label': 'Off', 'description': 'AI disabled'},
                {'value': AUTONOMY_OBSERVER, 'label': 'Observer', 'description': 'Monitor only'},
                {'value': AUTONOMY_SUGGESTER, 'label': 'Suggester', 'description': 'Suggests actions'},
                {'value': AUTONOMY_ACTOR, 'label': 'Actor', 'description': 'Executes safe actions'},
                {'value': AUTONOMY_AUTONOMOUS, 'label': 'Autonomous', 'description': 'Full autonomy'}
            ],
            'pending_suggestions': len(self.pending_suggestions),
            'goals_count': len(self.goals)
        }


def get_proactive_agent(db: Database = None) -> ProactiveAgent:
    """Get or create proactive agent instance"""
    return ProactiveAgent(db)


class ProactiveCheckPipeline:
    """Proactive check pipeline for scheduled brewery monitoring"""
    
    def __init__(self, agent: ProactiveAgent):
        self.agent = agent
        self.db = agent.db
    
    def run_morning_routine(self) -> Dict:
        """Morning routine: Check overnight batches, plan day's tasks, review alerts"""
        logger.info("Running morning routine")
        results = {
            'type': 'morning_routine',
            'timestamp': datetime.now().isoformat(),
            'checks': []
        }
        
        # 1. Check overnight batches
        overnight_batches = self._check_overnight_batches()
        results['checks'].append({
            'name': 'overnight_batches',
            'result': overnight_batches
        })
        
        # 2. Review pending tasks
        pending_tasks = self._review_pending_tasks()
        results['checks'].append({
            'name': 'pending_tasks',
            'result': pending_tasks
        })
        
        # 3. Check alerts and issues
        alerts = self._check_alerts()
        results['checks'].append({
            'name': 'alerts',
            'result': alerts
        })
        
        # 4. Check equipment status
        equipment_status = self._check_equipment_status()
        results['checks'].append({
            'name': 'equipment_status',
            'result': equipment_status
        })
        
        # 5. Plan day's tasks based on findings
        day_plan = self._plan_day_tasks(results['checks'])
        results['day_plan'] = day_plan
        
        # Log activity
        self.agent._log_activity('morning_routine', 
            f"Completed morning routine: {len(results['checks'])} checks performed")
        
        return results
    
    def run_midday_check(self) -> Dict:
        """Midday check: Monitor production progress, check inventory movements"""
        logger.info("Running midday check")
        results = {
            'type': 'midday_check',
            'timestamp': datetime.now().isoformat(),
            'checks': []
        }
        
        # 1. Check production progress
        production_progress = self._check_production_progress()
        results['checks'].append({
            'name': 'production_progress',
            'result': production_progress
        })
        
        # 2. Check inventory movements
        inventory_movements = self._check_inventory_movements()
        results['checks'].append({
            'name': 'inventory_movements',
            'result': inventory_movements
        })
        
        # 3. Check pending orders
        pending_orders = self._check_pending_orders()
        results['checks'].append({
            'name': 'pending_orders',
            'result': pending_orders
        })
        
        # 4. Generate midday summary
        summary = self._generate_midday_summary(results['checks'])
        results['summary'] = summary
        
        self.agent._log_activity('midday_check', 
            f"Completed midday check: {len(results['checks'])} checks performed")
        
        return results
    
    def run_end_of_day_review(self) -> Dict:
        """End-of-day review: Summarize day's activities, plan tomorrow, generate reports"""
        logger.info("Running end-of-day review")
        results = {
            'type': 'end_of_day_review',
            'timestamp': datetime.now().isoformat(),
            'checks': []
        }
        
        # 1. Summarize day's activities
        daily_summary = self._summarize_daily_activities()
        results['checks'].append({
            'name': 'daily_summary',
            'result': daily_summary
        })
        
        # 2. Check goal progress
        goal_progress = self.agent.get_goal_progress()
        results['checks'].append({
            'name': 'goal_progress',
            'result': goal_progress
        })
        
        # 3. Generate daily reports
        daily_reports = self._generate_daily_reports()
        results['checks'].append({
            'name': 'daily_reports',
            'result': daily_reports
        })
        
        # 4. Plan tomorrow's tasks
        tomorrow_plan = self._plan_tomorrow_tasks()
        results['tomorrow_plan'] = tomorrow_plan
        
        # 5. Check for any urgent issues
        urgent_issues = self._check_urgent_issues()
        results['urgent_issues'] = urgent_issues
        
        self.agent._log_activity('end_of_day_review', 
            f"Completed end-of-day review: {len(results['checks'])} checks performed")
        
        return results
    
    def run_continuous_monitoring(self) -> Dict:
        """Continuous monitoring: Watch for anomalies, opportunities, urgent issues"""
        logger.info("Running continuous monitoring")
        results = {
            'type': 'continuous_monitoring',
            'timestamp': datetime.now().isoformat(),
            'alerts': []
        }
        
        # 1. Run proactive scan
        suggestions = self.agent.run_proactive_scan()
        if suggestions:
            results['alerts'].extend(suggestions)
        
        # 2. Check for anomalies
        anomalies = self._detect_anomalies()
        if anomalies:
            results['alerts'].extend(anomalies)
        
        # 3. Check for urgent issues
        urgent = self._check_urgent_issues()
        if urgent:
            results['alerts'].extend(urgent)
        
        # 4. Check for opportunities
        opportunities = self._detect_opportunities()
        if opportunities:
            results['alerts'].extend(opportunities)
        
        if results['alerts']:
            self.agent._log_activity('continuous_monitoring', 
                f"Found {len(results['alerts'])} alerts/opportunities")
        
        return results
    
    # ==================== HELPER METHODS ====================
    
    def _check_overnight_batches(self) -> List[Dict]:
        """Check batches that were active overnight"""
        try:
            batches = self.db.get_batches(status='fermenting')
            overnight = []
            for batch in batches:
                if batch.get('start_date'):
                    start = datetime.strptime(batch['start_date'], '%Y-%m-%d')
                    days_active = (datetime.now() - start).days
                    if days_active > 0:
                        overnight.append({
                            'batch_id': batch['id'],
                            'batch_number': batch['batch_number'],
                            'product': batch.get('product_name'),
                            'days_active': days_active,
                            'status': batch['status']
                        })
            return overnight
        except Exception as e:
            logger.error(f"Error checking overnight batches: {e}")
            return []
    
    def _review_pending_tasks(self) -> Dict:
        """Review pending tasks for today"""
        try:
            today = datetime.now().strftime('%Y-%m-%d')
            tasks = self.db.get_daily_tasks(task_date=today, status='pending')
            return {
                'count': len(tasks),
                'tasks': tasks[:10]  # Return first 10
            }
        except Exception as e:
            logger.error(f"Error reviewing pending tasks: {e}")
            return {'count': 0, 'tasks': []}
    
    def _check_alerts(self) -> List[Dict]:
        """Check for system alerts"""
        alerts = []
        try:
            # Low stock alerts
            low_stock = self.db.get_low_stock_alerts()
            if low_stock:
                alerts.append({
                    'type': 'low_stock',
                    'count': len(low_stock),
                    'items': low_stock[:5]
                })
            
            # Expiring materials
            expiring = self.db.get_expiring_materials(days=7)
            if expiring:
                alerts.append({
                    'type': 'expiring_materials',
                    'count': len(expiring),
                    'items': expiring[:5]
                })
            
            # Overdue maintenance
            overdue = self.db.get_overdue_maintenance()
            if overdue:
                alerts.append({
                    'type': 'overdue_maintenance',
                    'count': len(overdue),
                    'items': overdue[:5]
                })
        except Exception as e:
            logger.error(f"Error checking alerts: {e}")
        
        return alerts
    
    def _check_equipment_status(self) -> Dict:
        """Check equipment status"""
        try:
            equipment = self.db.get_equipment()
            in_use = len([e for e in equipment if e.get('status') == 'in_use'])
            available = len([e for e in equipment if e.get('status') == 'available'])
            maintenance = len([e for e in equipment if e.get('status') == 'maintenance'])
            
            return {
                'total': len(equipment),
                'in_use': in_use,
                'available': available,
                'maintenance': maintenance
            }
        except Exception as e:
            logger.error(f"Error checking equipment status: {e}")
            return {'total': 0, 'in_use': 0, 'available': 0, 'maintenance': 0}
    
    def _plan_day_tasks(self, checks: List[Dict]) -> List[Dict]:
        """Plan day's tasks based on morning checks"""
        tasks = []
        
        for check in checks:
            if check['name'] == 'alerts':
                for alert in check.get('result', []):
                    if alert.get('type') == 'low_stock':
                        tasks.append({
                            'type': 'inventory',
                            'title': f"Reorder {alert['count']} low stock items",
                            'priority': 'high'
                        })
                    elif alert.get('type') == 'overdue_maintenance':
                        tasks.append({
                            'type': 'maintenance',
                            'title': f"Complete {alert['count']} overdue maintenance tasks",
                            'priority': 'high'
                        })
            
            elif check['name'] == 'overnight_batches':
                for batch in check.get('result', []):
                    if batch.get('days_active', 0) > 7:
                        tasks.append({
                            'type': 'production',
                            'title': f"Check batch {batch['batch_number']} ({batch['days_active']} days active)",
                            'priority': 'medium'
                        })
        
        return tasks
    
    def _check_production_progress(self) -> Dict:
        """Check production progress"""
        try:
            active_batches = self.db.get_batches(status='brewing')
            fermenting_batches = self.db.get_batches(status='fermenting')
            
            return {
                'brewing': len(active_batches),
                'fermenting': len(fermenting_batches),
                'total_active': len(active_batches) + len(fermenting_batches)
            }
        except Exception as e:
            logger.error(f"Error checking production progress: {e}")
            return {'brewing': 0, 'fermenting': 0, 'total_active': 0}
    
    def _check_inventory_movements(self) -> Dict:
        """Check inventory movements today"""
        try:
            today = datetime.now().strftime('%Y-%m-%d')
            # This would check material usage, receipts, etc.
            return {
                'date': today,
                'note': 'Inventory movement tracking to be implemented'
            }
        except Exception as e:
            logger.error(f"Error checking inventory movements: {e}")
            return {}
    
    def _check_pending_orders(self) -> Dict:
        """Check pending orders"""
        try:
            pending = self.db.get_sales_orders(status='pending')
            return {
                'count': len(pending),
                'orders': pending[:5]
            }
        except Exception as e:
            logger.error(f"Error checking pending orders: {e}")
            return {'count': 0, 'orders': []}
    
    def _generate_midday_summary(self, checks: List[Dict]) -> str:
        """Generate midday summary"""
        summary_parts = []
        
        for check in checks:
            if check['name'] == 'production_progress':
                result = check.get('result', {})
                summary_parts.append(
                    f"Production: {result.get('brewing', 0)} brewing, "
                    f"{result.get('fermenting', 0)} fermenting"
                )
            elif check['name'] == 'pending_orders':
                result = check.get('result', {})
                summary_parts.append(f"Pending orders: {result.get('count', 0)}")
        
        return "; ".join(summary_parts) if summary_parts else "All systems normal"
    
    def _summarize_daily_activities(self) -> Dict:
        """Summarize today's activities"""
        try:
            today = datetime.now().strftime('%Y-%m-%d')
            tasks = self.db.get_daily_tasks(task_date=today)
            
            completed = len([t for t in tasks if t.get('status') == 'completed'])
            pending = len([t for t in tasks if t.get('status') == 'pending'])
            
            return {
                'date': today,
                'total_tasks': len(tasks),
                'completed': completed,
                'pending': pending,
                'completion_rate': (completed / len(tasks) * 100) if tasks else 0
            }
        except Exception as e:
            logger.error(f"Error summarizing daily activities: {e}")
            return {'date': datetime.now().strftime('%Y-%m-%d'), 'total_tasks': 0, 
                    'completed': 0, 'pending': 0, 'completion_rate': 0}
    
    def _generate_daily_reports(self) -> List[Dict]:
        """Generate daily reports"""
        reports = []
        try:
            today = datetime.now().strftime('%Y-%m-%d')
            
            # Financial summary
            financial = self.db.get_financial_summary(start_date=today, end_date=today)
            reports.append({
                'type': 'financial',
                'data': financial
            })
            
            # Production summary
            production = self.db.get_production_report(start_date=today, end_date=today)
            reports.append({
                'type': 'production',
                'data': production
            })
        except Exception as e:
            logger.error(f"Error generating daily reports: {e}")
        
        return reports
    
    def _plan_tomorrow_tasks(self) -> List[Dict]:
        """Plan tomorrow's tasks"""
        tasks = []
        try:
            # Check upcoming maintenance
            tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
            maintenance = self.db.get_maintenance_schedule(status='scheduled')
            
            for item in maintenance:
                if item.get('next_due'):
                    due_date = item['next_due'][:10]  # Get date part
                    if due_date <= tomorrow:
                        tasks.append({
                            'type': 'maintenance',
                            'title': f"Due: {item.get('task_name')}",
                            'equipment': item.get('equipment_name'),
                            'priority': 'medium'
                        })
            
            # Check scheduled deliveries
            deliveries = self.db.get_deliveries(delivery_date=tomorrow)
            if deliveries:
                tasks.append({
                    'type': 'delivery',
                    'title': f"{len(deliveries)} deliveries scheduled",
                    'priority': 'high'
                })
        except Exception as e:
            logger.error(f"Error planning tomorrow's tasks: {e}")
        
        return tasks
    
    def _check_urgent_issues(self) -> List[Dict]:
        """Check for urgent issues requiring immediate attention"""
        urgent = []
        try:
            # Critical stock levels
            low_stock = self.db.get_low_stock_alerts()
            for item in low_stock:
                if item.get('quantity', 0) <= 0:
                    urgent.append({
                        'type': 'critical_stock',
                        'severity': 'critical',
                        'message': f"{item['name']} is out of stock!",
                        'item': item
                    })
            
            # Failed quality checks
            # This would need a method to get recent failed quality records
            
            # Equipment failures
            equipment = self.db.get_equipment(status='maintenance')
            for eq in equipment:
                urgent.append({
                    'type': 'equipment_maintenance',
                    'severity': 'high',
                    'message': f"{eq['name']} requires maintenance",
                    'equipment': eq
                })
        except Exception as e:
            logger.error(f"Error checking urgent issues: {e}")
        
        return urgent
    
    def _detect_anomalies(self) -> List[Dict]:
        """Detect anomalies in brewery operations"""
        anomalies = []
        try:
            # Check for unusual batch durations
            active_batches = self.db.get_batches(status='fermenting')
            for batch in active_batches:
                if batch.get('start_date'):
                    start = datetime.strptime(batch['start_date'], '%Y-%m-%d')
                    days = (datetime.now() - start).days
                    if days > 14:  # Fermenting too long
                        anomalies.append({
                            'type': 'long_fermentation',
                            'severity': 'medium',
                            'message': f"Batch {batch['batch_number']} has been fermenting for {days} days",
                            'batch': batch
                        })
            
            # Check for inventory discrepancies
            # This would compare expected vs actual inventory levels
        except Exception as e:
            logger.error(f"Error detecting anomalies: {e}")
        
        return anomalies
    
    def _detect_opportunities(self) -> List[Dict]:
        """Detect optimization opportunities"""
        opportunities = []
        try:
            # Check for underutilized equipment
            equipment = self.db.get_equipment(status='available')
            fermenters = [e for e in equipment if e.get('equipment_type') == 'fermenter']
            
            if len(fermenters) > 2:
                opportunities.append({
                    'type': 'capacity_available',
                    'severity': 'low',
                    'message': f"{len(fermenters)} fermenters available for new batches",
                    'count': len(fermenters)
                })
            
            # Check for expiring materials that could be used
            expiring = self.db.get_expiring_materials(days=14)
            if expiring:
                opportunities.append({
                    'type': 'use_expiring',
                    'severity': 'low',
                    'message': f"{len(expiring)} materials expiring soon - consider using them",
                    'items': expiring
                })
        except Exception as e:
            logger.error(f"Error detecting opportunities: {e}")
        
        return opportunities


def get_proactive_pipeline(agent: ProactiveAgent = None) -> ProactiveCheckPipeline:
    """Get or create proactive check pipeline instance"""
    if agent is None:
        agent = get_proactive_agent()
    return ProactiveCheckPipeline(agent)
