"""
Brewery Manager - Production Planning Module
Calendar, scheduling, and capacity management for brewery operations
"""

from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Tuple
import json


class ProductionPlanner:
    """Production planning and scheduling manager"""
    
    def __init__(self, db):
        self.db = db
    
    # ==================== PRODUCTION SCHEDULE ====================
    
    def get_schedule(self, start_date: date, end_date: date) -> List[Dict]:
        """Get production schedule for date range"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT ps.*, 
                   p.name as product_name, p.style,
                   e.name as tank_name, e.capacity as tank_capacity,
                   s.name as brewer_name,
                   r.name as recipe_name
            FROM production_schedule ps
            LEFT JOIN products p ON ps.product_id = p.id
            LEFT JOIN equipment e ON ps.tank_id = e.id
            LEFT JOIN staff s ON ps.brewer_id = s.id
            LEFT JOIN recipes r ON ps.recipe_id = r.id
            WHERE ps.planned_start_date <= ? AND ps.planned_end_date >= ?
            ORDER BY ps.planned_start_date, ps.priority DESC
        """, (end_date.isoformat(), start_date.isoformat()))
        
        schedule = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return schedule
    
    def get_schedule_by_week(self, year: int, week: int) -> List[Dict]:
        """Get schedule for specific week"""
        # Calculate week start and end
        jan1 = date(year, 1, 1)
        week_start = jan1 + timedelta(days=(week - 1) * 7 - jan1.weekday())
        week_end = week_start + timedelta(days=6)
        
        return self.get_schedule(week_start, week_end)
    
    def get_schedule_by_month(self, year: int, month: int) -> List[Dict]:
        """Get schedule for specific month"""
        month_start = date(year, month, 1)
        if month == 12:
            month_end = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            month_end = date(year, month + 1, 1) - timedelta(days=1)
        
        return self.get_schedule(month_start, month_end)
    
    def create_schedule_entry(self, data: Dict) -> int:
        """Create new production schedule entry"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        # Calculate end date based on recipe fermentation time
        start_date = datetime.fromisoformat(data['planned_start_date'])
        fermentation_days = data.get('fermentation_days', 14)
        end_date = start_date + timedelta(days=fermentation_days)
        
        cursor.execute("""
            INSERT INTO production_schedule 
            (product_id, recipe_id, tank_id, brewer_id, 
             planned_start_date, planned_end_date, planned_volume,
             priority, status, notes, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data['product_id'],
            data.get('recipe_id'),
            data.get('tank_id'),
            data.get('brewer_id'),
            data['planned_start_date'],
            end_date.isoformat(),
            data.get('planned_volume', 0),
            data.get('priority', 'normal'),
            data.get('status', 'draft'),
            data.get('notes'),
            datetime.now().isoformat()
        ))
        
        schedule_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return schedule_id
    
    def update_schedule_entry(self, schedule_id: int, data: Dict) -> bool:
        """Update production schedule entry"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        fields = []
        values = []
        
        for key in ['product_id', 'recipe_id', 'tank_id', 'brewer_id',
                    'planned_start_date', 'planned_end_date', 'planned_volume',
                    'priority', 'status', 'notes']:
            if key in data:
                fields.append(f"{key} = ?")
                values.append(data[key])
        
        if not fields:
            conn.close()
            return False
        
        values.append(schedule_id)
        
        cursor.execute(f"""
            UPDATE production_schedule 
            SET {', '.join(fields)}, updated_at = ?
            WHERE id = ?
        """, (*values, datetime.now().isoformat(), schedule_id))
        
        conn.commit()
        conn.close()
        return True
    
    def delete_schedule_entry(self, schedule_id: int) -> bool:
        """Delete production schedule entry"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM production_schedule WHERE id = ?", (schedule_id,))
        
        conn.commit()
        conn.close()
        return True
    
    def confirm_schedule(self, schedule_id: int) -> int:
        """Convert schedule entry to actual batch"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        # Get schedule entry
        cursor.execute("""
            SELECT * FROM production_schedule WHERE id = ?
        """, (schedule_id,))
        schedule = cursor.fetchone()
        
        if not schedule:
            conn.close()
            raise ValueError("Schedule entry not found")
        
        schedule = dict(schedule)
        
        # Create batch
        cursor.execute("""
            INSERT INTO production_batches 
            (product_id, recipe_id, tank_id, brewer_id,
             planned_quantity, start_date, end_date, status, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'planned', ?)
        """, (
            schedule['product_id'],
            schedule.get('recipe_id'),
            schedule.get('tank_id'),
            schedule.get('brewer_id'),
            schedule.get('planned_volume', 0),
            schedule['planned_start_date'],
            schedule['planned_end_date'],
            schedule.get('notes')
        ))
        
        batch_id = cursor.lastrowid
        
        # Update schedule status
        cursor.execute("""
            UPDATE production_schedule 
            SET status = 'confirmed', batch_id = ?, updated_at = ?
            WHERE id = ?
        """, (batch_id, datetime.now().isoformat(), schedule_id))
        
        conn.commit()
        conn.close()
        
        return batch_id
    
    # ==================== CAPACITY PLANNING ====================
    
    def get_tank_availability(self, start_date: date, end_date: date) -> List[Dict]:
        """Get tank availability for date range"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        # Get all tanks
        cursor.execute("""
            SELECT e.*, 
                   CASE WHEN e.status = 'maintenance' THEN 0 ELSE 1 END as available
            FROM equipment e
            WHERE e.equipment_type IN ('fermenter', 'brite_tank', 'conditioning_tank')
            ORDER BY e.name
        """)
        tanks = [dict(row) for row in cursor.fetchall()]
        
        # Get scheduled usage
        cursor.execute("""
            SELECT tank_id, planned_start_date, planned_end_date, 
                   product_id, status
            FROM production_schedule
            WHERE tank_id IS NOT NULL
              AND status IN ('draft', 'confirmed', 'in_progress')
              AND planned_start_date <= ? AND planned_end_date >= ?
        """, (end_date.isoformat(), start_date.isoformat()))
        
        scheduled = [dict(row) for row in cursor.fetchall()]
        
        # Map usage to tanks
        for tank in tanks:
            tank['scheduled_periods'] = [
                s for s in scheduled if s['tank_id'] == tank['id']
            ]
            tank['utilization'] = self._calculate_tank_utilization(
                tank['id'], start_date, end_date, scheduled
            )
        
        conn.close()
        return tanks
    
    def _calculate_tank_utilization(self, tank_id: int, start_date: date, 
                                     end_date: date, scheduled: List[Dict]) -> float:
        """Calculate tank utilization percentage"""
        total_days = (end_date - start_date).days + 1
        if total_days <= 0:
            return 0
        
        used_days = 0
        for s in scheduled:
            if s['tank_id'] != tank_id:
                continue
            
            s_start = max(date.fromisoformat(s['planned_start_date']), start_date)
            s_end = min(date.fromisoformat(s['planned_end_date']), end_date)
            
            if s_start <= s_end:
                used_days += (s_end - s_start).days + 1
        
        return min(100, (used_days / total_days) * 100)
    
    def get_capacity_forecast(self, weeks_ahead: int = 12) -> Dict:
        """Get capacity forecast for upcoming weeks"""
        today = date.today()
        forecast = []
        
        for week_offset in range(weeks_ahead):
            week_start = today + timedelta(weeks=week_offset)
            week_end = week_start + timedelta(days=6)
            
            schedule = self.get_schedule(week_start, week_end)
            
            total_volume = sum(s.get('planned_volume', 0) for s in schedule)
            batch_count = len(schedule)
            
            # Get available tanks
            tanks = self.get_tank_availability(week_start, week_end)
            available_tanks = len([t for t in tanks if t['available'] and t['utilization'] < 100])
            
            forecast.append({
                'week_start': week_start.isoformat(),
                'week_end': week_end.isoformat(),
                'week_number': week_start.isocalendar()[1],
                'planned_volume': total_volume,
                'batch_count': batch_count,
                'available_tanks': available_tanks,
                'total_tanks': len(tanks)
            })
        
        return {
            'forecast': forecast,
            'total_planned_volume': sum(f['planned_volume'] for f in forecast),
            'total_planned_batches': sum(f['batch_count'] for f in forecast)
        }
    
    def get_brewer_availability(self, start_date: date, end_date: date) -> List[Dict]:
        """Get brewer availability for date range"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        # Get brewing staff
        cursor.execute("""
            SELECT s.* FROM staff s
            WHERE s.department = 'brewing' AND s.active = 1
            ORDER BY s.name
        """)
        brewers = [dict(row) for row in cursor.fetchall()]
        
        # Get scheduled assignments
        cursor.execute("""
            SELECT brewer_id, COUNT(*) as batch_count
            FROM production_schedule
            WHERE brewer_id IS NOT NULL
              AND status IN ('draft', 'confirmed', 'in_progress')
              AND planned_start_date <= ? AND planned_end_date >= ?
            GROUP BY brewer_id
        """, (end_date.isoformat(), start_date.isoformat()))
        
        assignments = {row['brewer_id']: row['batch_count'] for row in cursor.fetchall()}
        
        for brewer in brewers:
            brewer['scheduled_batches'] = assignments.get(brewer['id'], 0)
            brewer['availability'] = 'available' if brewer['scheduled_batches'] < 3 else 'busy'
        
        conn.close()
        return brewers
    
    # ==================== PRODUCTION CALENDAR ====================
    
    def get_calendar_data(self, year: int, month: int) -> Dict:
        """Get calendar data for month view"""
        month_start = date(year, month, 1)
        if month == 12:
            month_end = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            month_end = date(year, month + 1, 1) - timedelta(days=1)
        
        # Get schedule for month
        schedule = self.get_schedule(month_start, month_end)
        
        # Build calendar weeks
        calendar_weeks = []
        current_date = month_start - timedelta(days=month_start.weekday())  # Start from Monday
        
        while current_date <= month_end:
            week = []
            for day_offset in range(7):
                day_date = current_date + timedelta(days=day_offset)
                
                # Find events for this day
                day_events = []
                for event in schedule:
                    event_start = date.fromisoformat(event['planned_start_date'])
                    event_end = date.fromisoformat(event['planned_end_date'])
                    
                    if event_start <= day_date <= event_end:
                        day_events.append({
                            'id': event['id'],
                            'product_name': event.get('product_name', 'Unknown'),
                            'tank_name': event.get('tank_name', 'N/A'),
                            'status': event['status'],
                            'is_start': day_date == event_start,
                            'is_end': day_date == event_end
                        })
                
                week.append({
                    'date': day_date.isoformat(),
                    'day': day_date.day,
                    'is_current_month': day_date.month == month,
                    'is_today': day_date == date.today(),
                    'events': day_events
                })
            
            calendar_weeks.append(week)
            current_date += timedelta(days=7)
        
        return {
            'year': year,
            'month': month,
            'month_name': month_start.strftime('%B'),
            'weeks': calendar_weeks,
            'total_batches': len(schedule),
            'total_volume': sum(s.get('planned_volume', 0) for s in schedule)
        }
    
    # ==================== RESOURCE ALLOCATION ====================
    
    def allocate_resources(self, schedule_id: int) -> Dict:
        """Allocate resources to a schedule entry"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT ps.*, r.id as recipe_id
            FROM production_schedule ps
            LEFT JOIN recipes r ON ps.recipe_id = r.id
            WHERE ps.id = ?
        """, (schedule_id,))
        
        schedule = cursor.fetchone()
        if not schedule:
            conn.close()
            raise ValueError("Schedule entry not found")
        
        schedule = dict(schedule)
        
        # Get recipe ingredients if available
        ingredients = []
        if schedule.get('recipe_id'):
            cursor.execute("""
                SELECT ri.*, rm.name as material_name, rm.quantity as available_qty
                FROM recipe_ingredients ri
                JOIN raw_materials rm ON ri.material_id = rm.id
                WHERE ri.recipe_id = ?
            """, (schedule['recipe_id'],))
            ingredients = [dict(row) for row in cursor.fetchall()]
        
        # Check resource availability
        resource_status = {
            'tank_available': True,
            'brewer_available': True,
            'ingredients_available': True,
            'ingredients': []
        }
        
        # Check tank availability
        if schedule.get('tank_id'):
            cursor.execute("""
                SELECT COUNT(*) as conflict_count
                FROM production_schedule
                WHERE tank_id = ?
                  AND id != ?
                  AND status IN ('confirmed', 'in_progress')
                  AND planned_start_date <= ? AND planned_end_date >= ?
            """, (
                schedule['tank_id'], schedule_id,
                schedule['planned_end_date'], schedule['planned_start_date']
            ))
            conflict = cursor.fetchone()
            resource_status['tank_available'] = conflict['conflict_count'] == 0
        
        # Check brewer availability
        if schedule.get('brewer_id'):
            cursor.execute("""
                SELECT COUNT(*) as batch_count
                FROM production_schedule
                WHERE brewer_id = ?
                  AND id != ?
                  AND status IN ('confirmed', 'in_progress')
                  AND planned_start_date <= ? AND planned_end_date >= ?
            """, (
                schedule['brewer_id'], schedule_id,
                schedule['planned_end_date'], schedule['planned_start_date']
            ))
            brewer = cursor.fetchone()
            resource_status['brewer_available'] = brewer['batch_count'] < 3
        
        # Check ingredient availability
        for ingredient in ingredients:
            needed = ingredient.get('quantity', 0) * (schedule.get('planned_volume', 20) / 20)
            available = ingredient.get('available_qty', 0)
            
            resource_status['ingredients'].append({
                'name': ingredient.get('material_name'),
                'needed': needed,
                'available': available,
                'sufficient': available >= needed
            })
            
            if available < needed:
                resource_status['ingredients_available'] = False
        
        conn.close()
        return resource_status
    
    # ==================== PRODUCTION METRICS ====================
    
    def get_production_metrics(self, days: int = 30) -> Dict:
        """Get production planning metrics"""
        end_date = date.today()
        start_date = end_date - timedelta(days=days)
        
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        # Schedule metrics
        cursor.execute("""
            SELECT 
                COUNT(*) as total_scheduled,
                SUM(CASE WHEN status = 'draft' THEN 1 ELSE 0 END) as draft_count,
                SUM(CASE WHEN status = 'confirmed' THEN 1 ELSE 0 END) as confirmed_count,
                SUM(CASE WHEN status = 'in_progress' THEN 1 ELSE 0 END) as in_progress_count,
                SUM(planned_volume) as total_planned_volume
            FROM production_schedule
            WHERE planned_start_date >= ? AND planned_start_date <= ?
        """, (start_date.isoformat(), end_date.isoformat()))
        
        schedule_metrics = dict(cursor.fetchone())
        
        # Batch metrics
        cursor.execute("""
            SELECT 
                COUNT(*) as total_batches,
                SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed_count,
                SUM(CASE WHEN status = 'fermenting' THEN 1 ELSE 0 END) as fermenting_count,
                SUM(actual_quantity) as total_actual_volume
            FROM production_batches
            WHERE start_date >= ? AND start_date <= ?
        """, (start_date.isoformat(), end_date.isoformat()))
        
        batch_metrics = dict(cursor.fetchone())
        
        # Tank utilization
        cursor.execute("""
            SELECT 
                COUNT(DISTINCT tank_id) as tanks_used,
                (SELECT COUNT(*) FROM equipment WHERE equipment_type IN ('fermenter', 'brite_tank')) as total_tanks
            FROM production_batches
            WHERE status IN ('brewing', 'fermenting', 'conditioning')
              AND tank_id IS NOT NULL
        """)
        
        tank_metrics = dict(cursor.fetchone())
        
        conn.close()
        
        return {
            'period': {
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat(),
                'days': days
            },
            'schedule': schedule_metrics,
            'batches': batch_metrics,
            'tanks': {
                'used': tank_metrics['tanks_used'] or 0,
                'total': tank_metrics['total_tanks'] or 0,
                'utilization': (tank_metrics['tanks_used'] or 0) / max(tank_metrics['total_tanks'] or 1, 1) * 100
            }
        }


def get_production_planner(db) -> ProductionPlanner:
    """Get production planner instance"""
    return ProductionPlanner(db)


# ==================== ALIAS METHODS FOR WEB ROUTES ====================

# Add these methods to ProductionPlanner class
def _add_alias_methods():
    """Add alias methods for backward compatibility"""
    
    def get_monthly_schedule(self, year: int, month: int) -> List[Dict]:
        """Get schedule for specific month (alias for get_schedule_by_month)"""
        return self.get_schedule_by_month(year, month)
    
    def get_capacity_utilization(self) -> Dict:
        """Get current capacity utilization"""
        today = date.today()
        month_start = date(today.year, today.month, 1)
        if today.month == 12:
            month_end = date(today.year + 1, 1, 1) - timedelta(days=1)
        else:
            month_end = date(today.year, today.month + 1, 1) - timedelta(days=1)
        
        # Get tank availability
        tanks = self.get_tank_availability(month_start, month_end)
        
        # Calculate capacity
        total_capacity = sum(t.get('capacity', 0) or 0 for t in tanks)
        used_capacity = sum(
            (t.get('capacity', 0) or 0) * (t.get('utilization', 0) or 0) / 100 
            for t in tanks
        )
        available_capacity = total_capacity - used_capacity
        
        # Calculate utilization
        total_tanks = len(tanks)
        if total_tanks == 0:
            avg_utilization = 0
        else:
            avg_utilization = sum(t.get('utilization', 0) or 0 for t in tanks) / total_tanks
        
        available_tanks = len([t for t in tanks if t.get('available') and (t.get('utilization', 0) or 0) < 100])
        
        return {
            'total_capacity': total_capacity,
            'available_capacity': available_capacity,
            'used_capacity': used_capacity,
            'utilization_percent': round(avg_utilization, 1),
            'total_tanks': total_tanks,
            'available_tanks': available_tanks,
            'tanks': tanks
        }
    
    def detect_conflicts(self) -> List[Dict]:
        """Detect scheduling conflicts"""
        today = date.today()
        end_date = today + timedelta(days=30)  # Check next 30 days
        
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        # Find overlapping schedules for same tank
        cursor.execute("""
            SELECT 
                ps1.id as schedule_id_1,
                ps1.planned_start_date as start_1,
                ps1.planned_end_date as end_1,
                ps1.tank_id,
                ps2.id as schedule_id_2,
                ps2.planned_start_date as start_2,
                ps2.planned_end_date as end_2,
                e.name as tank_name,
                p1.name as product_1,
                p2.name as product_2
            FROM production_schedule ps1
            JOIN production_schedule ps2 ON ps1.tank_id = ps2.tank_id AND ps1.id < ps2.id
            LEFT JOIN equipment e ON ps1.tank_id = e.id
            LEFT JOIN products p1 ON ps1.product_id = p1.id
            LEFT JOIN products p2 ON ps2.product_id = p2.id
            WHERE ps1.status IN ('draft', 'confirmed', 'in_progress')
              AND ps2.status IN ('draft', 'confirmed', 'in_progress')
              AND ps1.planned_start_date <= ?
              AND ps1.planned_end_date >= ?
              AND ps2.planned_start_date <= ps1.planned_end_date
              AND ps2.planned_end_date >= ps1.planned_start_date
        """, (end_date.isoformat(), today.isoformat()))
        
        conflicts = []
        for row in cursor.fetchall():
            conflicts.append({
                'type': 'tank_overlap',
                'tank_name': row['tank_name'],
                'schedule_1': {
                    'id': row['schedule_id_1'],
                    'product': row['product_1'],
                    'start': row['start_1'],
                    'end': row['end_1']
                },
                'schedule_2': {
                    'id': row['schedule_id_2'],
                    'product': row['product_2'],
                    'start': row['start_2'],
                    'end': row['end_2']
                },
                'message': f"Tank {row['tank_name']} has overlapping schedules"
            })
        
        # Find brewer overallocation
        cursor.execute("""
            SELECT 
                ps.brewer_id,
                s.name as brewer_name,
                COUNT(*) as batch_count,
                GROUP_CONCAT(ps.id) as schedule_ids
            FROM production_schedule ps
            LEFT JOIN staff s ON ps.brewer_id = s.id
            WHERE ps.brewer_id IS NOT NULL
              AND ps.status IN ('draft', 'confirmed', 'in_progress')
              AND ps.planned_start_date <= ?
              AND ps.planned_end_date >= ?
            GROUP BY ps.brewer_id
            HAVING COUNT(*) > 3
        """, (end_date.isoformat(), today.isoformat()))
        
        for row in cursor.fetchall():
            conflicts.append({
                'type': 'brewer_overload',
                'brewer_name': row['brewer_name'],
                'batch_count': row['batch_count'],
                'message': f"Brewer {row['brewer_name']} has {row['batch_count']} batches scheduled (max recommended: 3)"
            })
        
        conn.close()
        return conflicts
    
    # Add methods to class
    ProductionPlanner.get_monthly_schedule = get_monthly_schedule
    ProductionPlanner.get_capacity_utilization = get_capacity_utilization
    ProductionPlanner.detect_conflicts = detect_conflicts

# Apply alias methods
_add_alias_methods()
