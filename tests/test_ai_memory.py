"""
Tests for AI Memory System
"""
import pytest
import os
import json
import tempfile
from datetime import datetime, timedelta


class TestAIMemory:
    """Test AI Memory functionality"""
    
    def test_memory_initialization(self, temp_memory):
        """Test memory initializes with correct structure"""
        memory = temp_memory
        assert 'decisions' in memory.memory
        assert 'observations' in memory.memory
        assert 'patterns' in memory.memory
        assert 'alerts_history' in memory.memory
        assert 'planning_history' in memory.memory
        assert 'context' in memory.memory
    
    def test_remember_decision(self, temp_memory):
        """Test recording decisions"""
        memory = temp_memory
        memory.remember_decision(
            'production',
            'Scheduled new batch',
            'Tank was available and demand was high',
            'Batch created successfully'
        )
        
        decisions = memory.get_recent_decisions(limit=1)
        assert len(decisions) == 1
        assert decisions[0]['type'] == 'production'
        assert decisions[0]['description'] == 'Scheduled new batch'
        assert decisions[0]['reasoning'] == 'Tank was available and demand was high'
        assert decisions[0]['outcome'] == 'Batch created successfully'
    
    def test_remember_observation(self, temp_memory):
        """Test recording observations"""
        memory = temp_memory
        memory.remember_observation(
            'inventory',
            'Low stock on Pale Malt',
            'high'
        )
        
        obs = memory.get_recent_observations(limit=1, category='inventory')
        assert len(obs) == 1
        assert obs[0]['category'] == 'inventory'
        assert obs[0]['observation'] == 'Low stock on Pale Malt'
        assert obs[0]['importance'] == 'high'
    
    def test_learn_pattern(self, temp_memory):
        """Test learning patterns"""
        memory = temp_memory
        pattern_data = {
            'peak_hours': ['17:00', '18:00', '19:00'],
            'avg_orders': 15
        }
        memory.learn_pattern('sales', pattern_data)
        
        patterns = memory.get_patterns('sales')
        assert len(patterns) == 1
        assert patterns[0]['peak_hours'] == ['17:00', '18:00', '19:00']
        assert 'learned_at' in patterns[0]
    
    def test_record_alert(self, temp_memory):
        """Test recording alerts"""
        memory = temp_memory
        memory.record_alert(
            'inventory',
            'Pale Malt below minimum',
            'high',
            'Ordered more from supplier'
        )
        
        alerts = memory.memory['alerts_history']
        assert len(alerts) == 1
        assert alerts[0]['type'] == 'inventory'
        assert alerts[0]['resolved'] is True
        
        # Test unresolved alerts
        unresolved = memory.get_unresolved_alerts()
        assert len(unresolved) == 0
        
        # Add unresolved alert
        memory.record_alert('quality', 'Batch overdue', 'medium')
        unresolved = memory.get_unresolved_alerts()
        assert len(unresolved) == 1
    
    def test_record_plan(self, temp_memory):
        """Test recording plans"""
        memory = temp_memory
        memory.record_plan(
            'production',
            ['Increase IPA production', 'Schedule tank cleaning'],
            [{'action': 'Create batch', 'priority': 'high'}],
            'Plan executed successfully'
        )
        
        plans = memory.memory['planning_history']
        assert len(plans) == 1
        assert plans[0]['type'] == 'production'
        assert 'Increase IPA production' in plans[0]['objectives']
    
    def test_update_context(self, temp_memory):
        """Test updating and retrieving context"""
        memory = temp_memory
        memory.update_context('current_batch', 123)
        memory.update_context('active_tanks', 5)
        
        assert memory.get_context('current_batch') == 123
        assert memory.get_context('active_tanks') == 5
        
        # Get all context
        all_context = memory.get_context()
        assert all_context['current_batch'] == 123
        assert all_context['active_tanks'] == 5
    
    def test_memory_summary(self, temp_memory):
        """Test memory summary generation"""
        memory = temp_memory
        memory.remember_decision('test', 'Test decision', 'Testing')
        memory.remember_observation('test', 'Test observation')
        memory.learn_pattern('test', {'data': 'test'})
        
        summary = memory.get_memory_summary()
        assert summary['total_decisions'] == 1
        assert summary['total_observations'] == 1
        assert 'test' in summary['pattern_types']
    
    def test_clear_old_data(self, temp_memory):
        """Test clearing old data"""
        memory = temp_memory
        
        # Add old decision
        old_decision = {
            'type': 'test',
            'description': 'Old decision',
            'reasoning': 'Test',
            'timestamp': (datetime.now() - timedelta(days=40)).isoformat()
        }
        memory.memory['decisions'].append(old_decision)
        
        # Add recent decision
        memory.remember_decision('test', 'Recent decision', 'Test')
        
        assert len(memory.memory['decisions']) == 2
        
        # Clear data older than 30 days
        memory.clear_old_data(days=30)
        
        assert len(memory.memory['decisions']) == 1
        assert memory.memory['decisions'][0]['description'] == 'Recent decision'
    
    def test_max_items_limit(self, temp_memory):
        """Test that memory limits are enforced"""
        memory = temp_memory
        
        # Add more than 100 decisions
        for i in range(110):
            memory.remember_decision('test', f'Decision {i}', 'Test')
        
        # Should only keep last 100
        assert len(memory.memory['decisions']) == 100
        assert memory.memory['decisions'][0]['description'] == 'Decision 10'
    
    def test_memory_persistence(self):
        """Test that memory persists to file"""
        fd, path = tempfile.mkstemp(suffix='.json')
        os.close(fd)
        
        try:
            # Create memory with custom path
            from utils.ai_memory import AIMemory
            memory = AIMemory()
            memory.memory_file = path
            memory.memory = memory._initialize_memory()
            
            # Save some data
            memory.remember_decision('test', 'Test decision', 'Testing')
            memory._save_memory()
            
            # Create new instance and load
            memory2 = AIMemory()
            memory2.memory_file = path
            memory2.memory = memory2._load_memory()
            
            # Verify data persisted
            assert len(memory2.memory['decisions']) == 1
            assert memory2.memory['decisions'][0]['description'] == 'Test decision'
        finally:
            if os.path.exists(path):
                os.unlink(path)