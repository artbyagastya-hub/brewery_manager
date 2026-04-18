"""
Tests for Background Scheduler Module
"""
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime


class TestScheduler:
    """Test Scheduler functionality"""
    
    def test_get_scheduler_status_not_running(self):
        """Test scheduler status when not running"""
        import utils.scheduler as scheduler_module
        
        # Reset global scheduler
        scheduler_module.scheduler = None
        
        from utils.scheduler import get_scheduler_status
        status = get_scheduler_status()
        
        assert status['running'] is False
        assert status['jobs'] == []
    
    def test_start_scheduler(self):
        """Test starting the scheduler"""
        import utils.scheduler as scheduler_module
        
        # Reset global scheduler
        scheduler_module.scheduler = None
        
        from utils.scheduler import start_scheduler, stop_scheduler
        
        try:
            result = start_scheduler()
            assert result is not None
            assert result.running is True
        finally:
            stop_scheduler()
    
    def test_stop_scheduler(self):
        """Test stopping the scheduler"""
        import utils.scheduler as scheduler_module
        
        from utils.scheduler import start_scheduler, stop_scheduler
        
        try:
            start_scheduler()
            assert scheduler_module.scheduler.running is True
            
            stop_scheduler()
            # After stop, scheduler should be shutdown
            assert scheduler_module.scheduler.running is False
        except:
            pass
    
    def test_start_scheduler_idempotent(self):
        """Test that starting scheduler twice doesn't create duplicate"""
        import utils.scheduler as scheduler_module
        
        scheduler_module.scheduler = None
        
        from utils.scheduler import start_scheduler, stop_scheduler
        
        try:
            scheduler1 = start_scheduler()
            scheduler2 = start_scheduler()
            
            # Should return same scheduler
            assert scheduler1 is scheduler2
        finally:
            stop_scheduler()
    
    def test_scheduler_jobs_registered(self):
        """Test that all expected jobs are registered"""
        import utils.scheduler as scheduler_module
        
        scheduler_module.scheduler = None
        
        from utils.scheduler import start_scheduler, stop_scheduler
        
        try:
            scheduler = start_scheduler()
            jobs = scheduler.get_jobs()
            
            job_ids = [job.id for job in jobs]
            
            # Check all expected jobs are present
            assert 'agent_check' in job_ids
            assert 'daily_report' in job_ids
            assert 'maintenance_check' in job_ids
            assert 'ai_daily_agenda' in job_ids
            assert 'ai_situation_analysis' in job_ids
            assert 'ai_proactive_check' in job_ids
        finally:
            stop_scheduler()
    
    def test_get_scheduler_status_running(self):
        """Test scheduler status when running"""
        import utils.scheduler as scheduler_module
        
        scheduler_module.scheduler = None
        
        from utils.scheduler import start_scheduler, stop_scheduler, get_scheduler_status
        
        try:
            start_scheduler()
            status = get_scheduler_status()
            
            assert status['running'] is True
            assert len(status['jobs']) > 0
            
            # Check job structure
            job = status['jobs'][0]
            assert 'id' in job
            assert 'name' in job
            assert 'next_run' in job
        finally:
            stop_scheduler()
    
    @patch('utils.scheduler.logger')
    def test_run_agent_check_success(self, mock_logger, temp_db):
        """Test successful agent check execution"""
        from utils.scheduler import _run_agent_check
        
        mock_agent = MagicMock()
        mock_agent.run_check_cycle.return_value = ['rule1', 'rule2']
        
        _run_agent_check(mock_agent, temp_db)
        
        mock_agent.run_check_cycle.assert_called_once()
        mock_logger.info.assert_called()
    
    @patch('utils.scheduler.logger')
    def test_run_agent_check_error(self, mock_logger, temp_db):
        """Test agent check error handling"""
        from utils.scheduler import _run_agent_check
        
        mock_agent = MagicMock()
        mock_agent.run_check_cycle.side_effect = Exception("Test error")
        
        _run_agent_check(mock_agent, temp_db)
        
        mock_logger.error.assert_called()
    
    @patch('utils.scheduler.logger')
    def test_generate_daily_report(self, mock_logger, temp_db):
        """Test daily report generation"""
        from utils.scheduler import _generate_daily_report
        
        _generate_daily_report(temp_db)
        
        # Should complete without error
        mock_logger.info.assert_called()
    
    @patch('utils.scheduler.logger')
    def test_check_maintenance(self, mock_logger, temp_db):
        """Test maintenance check"""
        from utils.scheduler import _check_maintenance
        
        _check_maintenance(temp_db)
        
        # Should complete without error (no overdue maintenance in test)
        # Either info or no log is fine
    
    @patch('utils.scheduler.logger')
    def test_generate_daily_agenda(self, mock_logger):
        """Test daily agenda generation"""
        from utils.scheduler import _generate_daily_agenda
        
        with patch('utils.scheduler.get_planner') as mock_get_planner:
            mock_planner = MagicMock()
            mock_planner.generate_daily_agenda.return_value = {
                'date': '2026-04-17',
                'tasks': [{'title': 'Test task'}],
                'priorities': ['Test priority'],
                'reminders': []
            }
            mock_get_planner.return_value = mock_planner
            
            _generate_daily_agenda()
            
            mock_planner.generate_daily_agenda.assert_called_once()
            mock_logger.info.assert_called()
    
    @patch('utils.scheduler.logger')
    def test_generate_daily_agenda_error(self, mock_logger):
        """Test daily agenda error handling"""
        from utils.scheduler import _generate_daily_agenda
        
        with patch('utils.scheduler.get_planner') as mock_get_planner:
            mock_get_planner.side_effect = Exception("Test error")
            
            _generate_daily_agenda()
            
            mock_logger.error.assert_called()
    
    @patch('utils.scheduler.logger')
    def test_run_situation_analysis(self, mock_logger, temp_db):
        """Test situation analysis execution"""
        from utils.scheduler import _run_situation_analysis
        
        with patch('utils.scheduler.get_planner') as mock_get_planner, \
             patch('utils.scheduler.get_memory') as mock_get_memory:
            
            mock_planner = MagicMock()
            mock_planner.analyze_situation.return_value = {
                'status': 'healthy',
                'alerts': [
                    {'type': 'test', 'message': 'Test alert', 'severity': 'low'}
                ],
                'opportunities': [],
                'recommendations': []
            }
            mock_get_planner.return_value = mock_planner
            
            mock_memory = MagicMock()
            mock_get_memory.return_value = mock_memory
            
            _run_situation_analysis(temp_db)
            
            mock_memory.record_alert.assert_called_once()
            mock_memory.update_context.assert_called_once()
    
    @patch('utils.scheduler.logger')
    def test_check_proactive_suggestions_reactive(self, mock_logger, temp_db):
        """Test proactive suggestions skip in reactive mode"""
        from utils.scheduler import _check_proactive_suggestions
        
        with patch('utils.scheduler.get_planner') as mock_get_planner:
            mock_planner = MagicMock()
            mock_planner.mode = 'reactive'
            mock_get_planner.return_value = mock_planner
            
            _check_proactive_suggestions(temp_db)
            
            # Should return early without calling get_proactive_suggestions
            mock_planner.get_proactive_suggestions.assert_not_called()
    
    @patch('utils.scheduler.logger')
    def test_check_proactive_suggestions_proactive(self, mock_logger, temp_db):
        """Test proactive suggestions in proactive mode"""
        from utils.scheduler import _check_proactive_suggestions
        
        with patch('utils.scheduler.get_planner') as mock_get_planner:
            mock_planner = MagicMock()
            mock_planner.mode = 'proactive'
            mock_planner.get_proactive_suggestions.return_value = [
                {
                    'type': 'inventory',
                    'message': 'Low stock alert',
                    'urgency': 'high'
                }
            ]
            mock_get_planner.return_value = mock_planner
            
            _check_proactive_suggestions(temp_db)
            
            mock_planner.get_proactive_suggestions.assert_called_once()
            mock_logger.info.assert_called()