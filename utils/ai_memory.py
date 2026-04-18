"""
AI Memory System - Persistent memory for autonomous brewery management
Stores decisions, observations, patterns, and learning for the AI
"""

import os
import sys
import json
from datetime import datetime, date, timedelta
from typing import Dict, List, Any, Optional
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from models.database import Database

db = Database()

class AIMemory:
    """Persistent memory system for the AI assistant"""
    
    def __init__(self):
        self.memory_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'ai_memory.json')
        self.memory = self._load_memory()
    
    def _load_memory(self) -> Dict:
        """Load memory from file"""
        if os.path.exists(self.memory_file):
            try:
                with open(self.memory_file, 'r') as f:
                    return json.load(f)
            except:
                pass
        return self._initialize_memory()
    
    def _initialize_memory(self) -> Dict:
        """Initialize empty memory structure"""
        return {
            'decisions': [],           # Past decisions and reasoning
            'observations': [],        # Notable observations about operations
            'patterns': {},            # Learned patterns (sales, production, etc.)
            'alerts_history': [],      # Past alerts and their resolutions
            'planning_history': [],    # Past plans and outcomes
            'user_preferences': {},    # Learned user preferences
            'context': {},             # Current operational context
            'last_updated': datetime.now().isoformat()
        }
    
    def _save_memory(self):
        """Save memory to file"""
        os.makedirs(os.path.dirname(self.memory_file), exist_ok=True)
        self.memory['last_updated'] = datetime.now().isoformat()
        with open(self.memory_file, 'w') as f:
            json.dump(self.memory, f, indent=2, default=str)
    
    def remember_decision(self, decision_type: str, description: str, 
                         reasoning: str, outcome: str = None):
        """Record a decision made by the AI"""
        decision = {
            'type': decision_type,
            'description': description,
            'reasoning': reasoning,
            'outcome': outcome,
            'timestamp': datetime.now().isoformat()
        }
        self.memory['decisions'].append(decision)
        # Keep only last 100 decisions
        self.memory['decisions'] = self.memory['decisions'][-100:]
        self._save_memory()
    
    def remember_observation(self, category: str, observation: str, 
                            importance: str = 'normal'):
        """Record an observation about operations"""
        obs = {
            'category': category,
            'observation': observation,
            'importance': importance,
            'timestamp': datetime.now().isoformat()
        }
        self.memory['observations'].append(obs)
        # Keep only last 200 observations
        self.memory['observations'] = self.memory['observations'][-200:]
        self._save_memory()
    
    def learn_pattern(self, pattern_type: str, pattern_data: Dict):
        """Learn and store a pattern"""
        if pattern_type not in self.memory['patterns']:
            self.memory['patterns'][pattern_type] = []
        
        pattern_data['learned_at'] = datetime.now().isoformat()
        self.memory['patterns'][pattern_type].append(pattern_data)
        # Keep only last 50 patterns per type
        self.memory['patterns'][pattern_type] = self.memory['patterns'][pattern_type][-50:]
        self._save_memory()
    
    def record_alert(self, alert_type: str, description: str, 
                    severity: str, resolution: str = None):
        """Record an alert and its resolution"""
        alert = {
            'type': alert_type,
            'description': description,
            'severity': severity,
            'resolution': resolution,
            'timestamp': datetime.now().isoformat(),
            'resolved': resolution is not None
        }
        self.memory['alerts_history'].append(alert)
        self.memory['alerts_history'] = self.memory['alerts_history'][-100:]
        self._save_memory()
    
    def record_plan(self, plan_type: str, objectives: List[str], 
                   actions: List[Dict], outcome: str = None):
        """Record a plan and its outcome"""
        plan = {
            'type': plan_type,
            'objectives': objectives,
            'actions': actions,
            'outcome': outcome,
            'timestamp': datetime.now().isoformat()
        }
        self.memory['planning_history'].append(plan)
        self.memory['planning_history'] = self.memory['planning_history'][-50:]
        self._save_memory()
    
    def update_context(self, context_key: str, context_value: Any):
        """Update current operational context"""
        self.memory['context'][context_key] = {
            'value': context_value,
            'updated_at': datetime.now().isoformat()
        }
        self._save_memory()
    
    def get_context(self, context_key: str = None) -> Any:
        """Get current context"""
        if context_key:
            ctx = self.memory['context'].get(context_key)
            return ctx['value'] if ctx else None
        return {k: v['value'] for k, v in self.memory['context'].items()}
    
    def get_recent_decisions(self, limit: int = 10) -> List[Dict]:
        """Get recent decisions"""
        return self.memory['decisions'][-limit:]
    
    def get_recent_observations(self, limit: int = 10, 
                               category: str = None) -> List[Dict]:
        """Get recent observations, optionally filtered by category"""
        obs = self.memory['observations']
        if category:
            obs = [o for o in obs if o['category'] == category]
        return obs[-limit:]
    
    def get_patterns(self, pattern_type: str = None) -> Dict:
        """Get learned patterns"""
        if pattern_type:
            return self.memory['patterns'].get(pattern_type, [])
        return self.memory['patterns']
    
    def get_unresolved_alerts(self) -> List[Dict]:
        """Get unresolved alerts"""
        return [a for a in self.memory['alerts_history'] if not a['resolved']]
    
    def get_memory_summary(self) -> Dict:
        """Get a summary of current memory state"""
        return {
            'total_decisions': len(self.memory['decisions']),
            'total_observations': len(self.memory['observations']),
            'pattern_types': list(self.memory['patterns'].keys()),
            'unresolved_alerts': len(self.get_unresolved_alerts()),
            'total_plans': len(self.memory['planning_history']),
            'last_updated': self.memory['last_updated']
        }
    
    def clear_old_data(self, days: int = 30):
        """Clear data older than specified days"""
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        
        self.memory['decisions'] = [
            d for d in self.memory['decisions'] 
            if d['timestamp'] > cutoff
        ]
        self.memory['observations'] = [
            o for o in self.memory['observations']
            if o['timestamp'] > cutoff
        ]
        self.memory['alerts_history'] = [
            a for a in self.memory['alerts_history']
            if a['timestamp'] > cutoff
        ]
        self._save_memory()

# Singleton instance
_memory = None

def get_memory() -> AIMemory:
    """Get singleton memory instance"""
    global _memory
    if _memory is None:
        _memory = AIMemory()
    return _memory