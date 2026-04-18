"""
Tests for AI Planner Module
"""
import pytest
from datetime import datetime, date
from unittest.mock import patch, MagicMock


class TestAIPlanner:
    """Test AI Planner functionality"""
    
    def test_planner_initialization(self, temp_planner):
        """Test planner initializes with correct mode"""
        planner = temp_planner
        assert planner.mode in ['reactive', 'proactive', 'autonomous']
        assert hasattr(planner, 'memory')
    
    def test_set_mode(self, temp_planner):
        """Test setting planning mode"""
        planner = temp_planner
        
        planner.set_mode('reactive')
        assert planner.mode == 'reactive'
        
        planner.set_mode('proactive')
        assert planner.mode == 'proactive'
        
        planner.set_mode('autonomous')
        assert planner.mode == 'autonomous'
        
        # Invalid mode should not change
        planner.set_mode('invalid')
        assert planner.mode == 'autonomous'
    
    def test_enable_auto_actions(self, temp_planner):
        """Test enabling/disabling auto actions"""
        planner = temp_planner
        
        planner.enable_auto_actions(True)
        assert planner.auto_actions_enabled is True
        
        planner.enable_auto_actions(False)
        assert planner.auto_actions_enabled is False
    
    def test_analyze_situation(self, temp_planner, temp_db):
        """Test situation analysis"""
        planner = temp_planner
        
        analysis = planner.analyze_situation()
        
        assert 'timestamp' in analysis
        assert 'alerts' in analysis
        assert 'opportunities' in analysis
        assert 'recommendations' in analysis
        assert 'status' in analysis
        assert analysis['status'] in ['healthy', 'minor_issues', 'attention_needed']
    
    def test_create_production_plan(self, temp_planner, temp_db, sample_product, sample_tank):
        """Test production plan creation"""
        planner = temp_planner
        
        plan = planner.create_production_plan(['Increase IPA production'])
        
        assert plan['type'] == 'production'
        assert 'created_at' in plan
        assert 'steps' in plan
        assert 'Increase IPA production' in plan['objectives']
    
    def test_create_inventory_plan(self, temp_planner, temp_db, sample_material):
        """Test inventory plan creation"""
        planner = temp_planner
        
        plan = planner.create_inventory_plan()
        
        assert plan['type'] == 'inventory'
        assert 'created_at' in plan
        assert 'actions' in plan
        assert 'Maintain optimal stock levels' in plan['objectives']
    
    def test_create_sales_plan(self, temp_planner, temp_db):
        """Test sales plan creation"""
        planner = temp_planner
        
        plan = planner.create_sales_plan()
        
        assert plan['type'] == 'sales'
        assert 'created_at' in plan
        assert 'actions' in plan
        assert 'Increase revenue' in plan['objectives']
    
    def test_generate_daily_agenda(self, temp_planner, temp_db):
        """Test daily agenda generation"""
        planner = temp_planner
        
        agenda = planner.generate_daily_agenda()
        
        assert 'date' in agenda
        assert agenda['date'] == date.today().isoformat()
        assert 'priorities' in agenda
        assert 'tasks' in agenda
        assert 'reminders' in agenda
    
    def test_should_take_action_reactive(self, temp_planner):
        """Test action decision in reactive mode"""
        planner = temp_planner
        planner.set_mode('reactive')
        planner.enable_auto_actions(True)
        
        # Reactive mode should never auto-execute
        assert planner.should_take_action('observation') is False
        assert planner.should_take_action('create_batch') is False
    
    def test_should_take_action_proactive(self, temp_planner):
        """Test action decision in proactive mode"""
        planner = temp_planner
        planner.set_mode('proactive')
        planner.enable_auto_actions(True)
        
        # Safe actions should be allowed
        assert planner.should_take_action('observation') is True
        assert planner.should_take_action('suggestion') is True
        
        # Destructive actions should not be allowed
        assert planner.should_take_action('delete_data') is False
    
    def test_should_take_action_autonomous(self, temp_planner):
        """Test action decision in autonomous mode"""
        planner = temp_planner
        planner.set_mode('autonomous')
        planner.enable_auto_actions(True)
        
        # All actions should be allowed in autonomous mode
        assert planner.should_take_action('observation') is True
        assert planner.should_take_action('create_batch') is True
    
    def test_should_take_action_disabled(self, temp_planner):
        """Test action decision when auto actions disabled"""
        planner = temp_planner
        planner.set_mode('autonomous')
        planner.enable_auto_actions(False)
        
        # Should not take any action when disabled
        assert planner.should_take_action('observation') is False
    
    def test_get_proactive_suggestions_reactive(self, temp_planner):
        """Test suggestions in reactive mode"""
        planner = temp_planner
        planner.set_mode('reactive')
        
        suggestions = planner.get_proactive_suggestions()
        assert suggestions == []
    
    def test_get_proactive_suggestions_proactive(self, temp_planner, temp_db):
        """Test suggestions in proactive mode"""
        planner = temp_planner
        planner.set_mode('proactive')
        
        suggestions = planner.get_proactive_suggestions()
        assert isinstance(suggestions, list)
    
    def test_get_planning_status(self, temp_planner):
        """Test getting planning status"""
        planner = temp_planner
        planner.set_mode('proactive')
        planner.enable_auto_actions(True)
        
        status = planner.get_planning_status()
        
        assert status['mode'] == 'proactive'
        assert status['auto_actions_enabled'] is True
        assert 'memory_summary' in status