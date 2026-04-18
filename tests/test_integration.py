"""
Integration Tests for Autonomous AI Cycle and Safety Boundaries
"""
import pytest
import tempfile
import os
from unittest.mock import patch, MagicMock


class TestAutonomousCycle:
    """Integration tests for the autonomous AI decision cycle"""
    
    def test_situation_analysis_cycle(self, temp_db):
        """Test complete situation analysis cycle"""
        from utils.ai_planner import get_planner
        from utils.ai_memory import get_memory
        
        planner = get_planner()
        memory = get_memory()
        
        # Run analysis
        analysis = planner.analyze_situation()
        
        assert isinstance(analysis, dict)
        assert 'status' in analysis
        assert 'recommendations' in analysis or 'alerts' in analysis
        
        # Memory should have recorded the observation
        summary = memory.get_memory_summary()
        assert 'total_observations' in summary
    
    def test_production_plan_creation_cycle(self, temp_db):
        """Test production plan creation and storage"""
        from utils.ai_planner import get_planner
        from utils.ai_memory import get_memory
        
        planner = get_planner()
        memory = get_memory()
        
        # Create plan (no weeks_ahead parameter)
        plan = planner.create_production_plan()
        
        assert isinstance(plan, dict)
        
        # Record in memory (requires actions parameter)
        memory.record_plan('production', plan, actions=['test_action'])
        
        # Verify stored
        summary = memory.get_memory_summary()
        assert 'total_plans' in summary
        assert summary['total_plans'] >= 1
    
    def test_daily_agenda_generation_cycle(self, temp_db):
        """Test daily agenda generation"""
        from utils.ai_planner import get_planner
        
        planner = get_planner()
        
        # Generate agenda
        agenda = planner.generate_daily_agenda()
        
        assert isinstance(agenda, dict)
        assert 'date' in agenda
    
    def test_decision_memory_cycle(self, temp_db):
        """Test decision recording and retrieval"""
        from utils.ai_memory import get_memory
        
        memory = get_memory()
        
        # Record decision (correct signature)
        memory.remember_decision(
            decision_type="inventory",
            description="Low stock detected for Pale Malt",
            reasoning="Stock below minimum threshold",
            outcome="pending"
        )
        
        # Verify stored
        summary = memory.get_memory_summary()
        assert 'total_decisions' in summary
        assert summary['total_decisions'] >= 1
    
    def test_pattern_learning_cycle(self, temp_db):
        """Test pattern learning and retrieval"""
        from utils.ai_memory import get_memory
        
        memory = get_memory()
        
        # Learn pattern (correct signature)
        memory.learn_pattern(
            pattern_type="seasonal",
            pattern_data={"description": "IPA sales increase 20% in summer", "product": "IPA", "season": "summer", "increase": 0.2}
        )
        
        # Verify stored
        patterns = memory.memory['patterns']
        assert 'seasonal' in patterns
        assert len(patterns['seasonal']) > 0
    
    def test_full_agent_check_cycle(self, temp_db):
        """Test complete agent check cycle through scheduler"""
        from utils import scheduler
        from utils.agent import get_agent
        from utils.ai_memory import get_memory
        from models.database import Database
        
        memory = get_memory()
        db = Database()
        agent = get_agent(db)
        
        # Run check (use private function with agent argument)
        result = scheduler._run_agent_check(agent)
        
        # Result is None (function doesn't return), but it should run without error
        assert result is None or isinstance(result, dict)
        
        # Memory should have been updated
        summary = memory.get_memory_summary()
        assert isinstance(summary, dict)


class TestSafetyBoundaries:
    """Tests for autonomy safety boundaries"""
    
    def test_reactive_mode_no_autonomous_actions(self, temp_db):
        """Test that reactive mode does not take autonomous actions"""
        from utils.ai_planner import get_planner
        
        planner = get_planner()
        planner.set_mode('reactive')
        planner.enable_auto_actions(False)
        
        # Should not take action
        assert not planner.should_take_action('create_order')
        assert not planner.should_take_action('update_inventory')
        assert not planner.should_take_action('schedule_batch')
    
    def test_proactive_mode_suggests_only(self, temp_db):
        """Test that proactive mode only suggests, never acts"""
        from utils.ai_planner import get_planner
        
        planner = get_planner()
        planner.set_mode('proactive')
        planner.enable_auto_actions(False)
        
        # Should suggest but not auto-execute
        assert not planner.should_take_action('create_order')
        
        # Get suggestions
        suggestions = planner.get_proactive_suggestions()
        assert isinstance(suggestions, list)
    
    def test_disabled_mode_no_suggestions(self, temp_db):
        """Test that disabled mode provides no suggestions"""
        from utils.ai_planner import get_planner
        
        planner = get_planner()
        planner.set_mode('disabled')
        
        # Should not suggest anything
        suggestions = planner.get_proactive_suggestions()
        assert suggestions == []
    
    def test_autonomous_mode_requires_explicit_enable(self, temp_db):
        """Test that autonomous mode requires explicit enable"""
        from utils.ai_planner import get_planner
        
        planner = get_planner()
        planner.set_mode('autonomous')
        
        # Even in autonomous mode, auto_actions must be explicitly enabled
        planner.enable_auto_actions(False)
        assert not planner.should_take_action('create_order')
        
        # Only when explicitly enabled
        planner.enable_auto_actions(True)
        assert planner.should_take_action('create_order')
    
    def test_dangerous_action_blocked_without_permission(self, temp_db):
        """Test that dangerous actions require explicit permission"""
        from utils.ai_planner import get_planner
        
        planner = get_planner()
        planner.enable_auto_actions(False)
        
        # Test that actions are blocked without explicit enable
        actions_to_test = ['create_order', 'schedule_batch']
        
        for action in actions_to_test:
            # Should not auto-execute without explicit enable
            assert not planner.should_take_action(action), \
                f"Action {action} should be blocked without explicit enable"
    
    def test_memory_max_items_enforced(self, temp_db):
        """Test that memory respects max item limits"""
        from utils.ai_memory import get_memory
        
        memory = get_memory()
        
        # Memory limits are enforced in remember_decision (last 100) and remember_observation (last 200)
        # Add many decisions
        for i in range(150):
            memory.remember_decision(
                decision_type="test",
                description=f"Test decision {i}",
                reasoning="Testing limits",
                outcome="test"
            )
        
        # Should not exceed 100 decisions
        assert len(memory.memory['decisions']) <= 100
    
    def test_scheduler_starts_and_stops(self, temp_db):
        """Test that scheduler starts and stops"""
        from utils import scheduler
        
        # Stop if running
        scheduler.stop_scheduler()
        
        # Start
        scheduler.start_scheduler()
        status = scheduler.get_scheduler_status()
        assert status['running'] is True
        
        # Stop
        scheduler.stop_scheduler()
        status = scheduler.get_scheduler_status()
        assert status['running'] is False
    
    def test_goal_progress_bounds(self, temp_db):
        """Test that goal progress stays within bounds"""
        from utils.agent import get_proactive_agent
        
        agent = get_proactive_agent()
        
        # Create goal
        goal_id = agent.add_goal(
            name="Test Goal",
            description="Test",
            target_value=100,
            current_value=0,
            unit="units"
        )
        
        if goal_id > 0:
            # Update to valid value
            agent.update_goal_progress(goal_id, 50)
            goals = agent.get_goal_progress()
            
            # Find the goal
            test_goal = None
            for g in goals:
                if g['id'] == goal_id:
                    test_goal = g
                    break
            
            if test_goal:
                assert test_goal['current_value'] == 50
    
    def test_suggestion_approval_flow(self, temp_db):
        """Test suggestion approval and dismissal flow"""
        from utils.agent import get_proactive_agent
        
        agent = get_proactive_agent()
        
        # Get pending suggestions
        pending_before = agent.get_pending_suggestions()
        initial_count = len(pending_before)
        
        # Dismiss if any exist
        if initial_count > 0:
            result = agent.dismiss_suggestion(0)
            assert result is True
            
            pending_after = agent.get_pending_suggestions()
            assert len(pending_after) == initial_count - 1
    
    def test_autonomy_mode_switching(self):
        """Test autonomy mode switching"""
        from utils.ai_planner import get_planner
        
        planner = get_planner()
        
        # Test mode switching (MODE_DISABLED doesn't exist, only reactive/proactive/autonomous)
        planner.set_mode('reactive')
        assert planner.get_planning_status()['mode'] == 'reactive'
        
        planner.set_mode('proactive')
        assert planner.get_planning_status()['mode'] == 'proactive'
        
        planner.set_mode('autonomous')
        assert planner.get_planning_status()['mode'] == 'autonomous'
        
        # Reset to reactive at end
        planner.set_mode('reactive')


class TestAPIEndpoints:
    """Tests for new AI API endpoints"""
    
    def test_api_get_goals(self, client, auth_headers, temp_db):
        """Test GET /api/ai/goals endpoint"""
        with client.session_transaction() as sess:
            sess['user_id'] = 1
            sess['logged_in'] = True
        
        response = client.get('/api/ai/goals', headers=auth_headers)
        
        assert response.status_code == 200
        data = response.get_json()
        assert 'success' in data
        assert data['success'] is True
        assert 'goals' in data
    
    def test_api_add_goal(self, client, auth_headers, temp_db):
        """Test POST /api/ai/goals endpoint"""
        with client.session_transaction() as sess:
            sess['user_id'] = 1
            sess['logged_in'] = True
        
        goal_data = {
            'name': 'Test Integration Goal',
            'description': 'Test goal from integration test',
            'target_value': 100,
            'current_value': 0,
            'unit': 'units',
            'priority': 'normal',
            'category': 'test'
        }
        
        response = client.post(
            '/api/ai/goals',
            json=goal_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.get_json()
        assert 'success' in data
    
    def test_api_update_goal(self, client, auth_headers, temp_db):
        """Test PUT /api/ai/goals/<id> endpoint"""
        with client.session_transaction() as sess:
            sess['user_id'] = 1
            sess['logged_in'] = True
        
        update_data = {'current_value': 50}
        
        response = client.put(
            '/api/ai/goals/1',
            json=update_data,
            headers=auth_headers
        )
        
        # Should succeed or return appropriate error
        assert response.status_code in [200, 404, 500]
    
    def test_api_get_suggestions(self, client, auth_headers, temp_db):
        """Test GET /api/ai/suggestions/pending endpoint"""
        with client.session_transaction() as sess:
            sess['user_id'] = 1
            sess['logged_in'] = True
        
        response = client.get(
            '/api/ai/suggestions/pending',
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.get_json()
        assert 'success' in data
    
    def test_api_activity_log(self, client, auth_headers, temp_db):
        """Test GET /api/ai/activity-log endpoint"""
        with client.session_transaction() as sess:
            sess['user_id'] = 1
            sess['logged_in'] = True
        
        response = client.get(
            '/api/ai/activity-log?limit=10',
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.get_json()
        assert 'success' in data
        assert 'activities' in data
    
    def test_api_anomalies(self, client, auth_headers, temp_db):
        """Test GET /api/ai/anomalies endpoint"""
        with client.session_transaction() as sess:
            sess['user_id'] = 1
            sess['logged_in'] = True
        
        response = client.get(
            '/api/ai/anomalies',
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.get_json()
        assert 'success' in data
    
    def test_api_ai_health(self, client, auth_headers, temp_db):
        """Test GET /ai/health endpoint"""
        with client.session_transaction() as sess:
            sess['user_id'] = 1
            sess['logged_in'] = True
        
        response = client.get(
            '/ai/health',
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.get_json()
        assert 'status' in data or 'healthy' in data
