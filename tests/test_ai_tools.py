"""
Tests for AI Tools Module
"""
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, date


class TestAITools:
    """Test AI Tools functionality"""
    
    def test_get_tools_returns_list(self):
        """Test that get_tools returns a list of tools"""
        from utils.ai_tools import get_tools
        
        tools = get_tools()
        
        assert isinstance(tools, list)
        assert len(tools) > 0
        
        # Check tool structure
        tool = tools[0]
        assert 'type' in tool
        assert tool['type'] == 'function'
        assert 'function' in tool
        assert 'name' in tool['function']
        assert 'description' in tool['function']
        assert 'parameters' in tool['function']
    
    def test_get_tools_has_query_inventory(self):
        """Test that query_inventory tool exists"""
        from utils.ai_tools import get_tools
        
        tools = get_tools()
        tool_names = [t['function']['name'] for t in tools]
        
        assert 'query_inventory' in tool_names
    
    def test_get_tools_has_query_batches(self):
        """Test that query_batches tool exists"""
        from utils.ai_tools import get_tools
        
        tools = get_tools()
        tool_names = [t['function']['name'] for t in tools]
        
        assert 'query_batches' in tool_names
    
    def test_get_tools_has_create_task(self):
        """Test that create_task tool exists"""
        from utils.ai_tools import get_tools
        
        tools = get_tools()
        tool_names = [t['function']['name'] for t in tools]
        
        assert 'create_task' in tool_names
    
    def test_get_tools_has_schedule_batch(self):
        """Test that schedule_batch tool exists"""
        from utils.ai_tools import get_tools
        
        tools = get_tools()
        tool_names = [t['function']['name'] for t in tools]
        
        assert 'schedule_batch' in tool_names
    
    def test_get_tools_has_create_order(self):
        """Test that create_order tool exists"""
        from utils.ai_tools import get_tools
        
        tools = get_tools()
        tool_names = [t['function']['name'] for t in tools]
        
        assert 'create_order' in tool_names
    
    def test_get_tools_has_quality_tools(self):
        """Test that quality-related tools exist"""
        from utils.ai_tools import get_tools
        
        tools = get_tools()
        tool_names = [t['function']['name'] for t in tools]
        
        assert 'log_quality_check' in tool_names
        assert 'query_quality_checks' in tool_names
    
    def test_get_tools_has_temperature_tools(self):
        """Test that temperature-related tools exist"""
        from utils.ai_tools import get_tools
        
        tools = get_tools()
        tool_names = [t['function']['name'] for t in tools]
        
        assert 'log_temperature' in tool_names
        assert 'query_temperature_logs' in tool_names
        assert 'get_temperature_alerts' in tool_names
    
    def test_get_tools_has_tank_tools(self):
        """Test that tank-related tools exist"""
        from utils.ai_tools import get_tools
        
        tools = get_tools()
        tool_names = [t['function']['name'] for t in tools]
        
        assert 'get_tank_availability' in tool_names
        assert 'update_tank_status' in tool_names
        assert 'mark_tank_cleaned' in tool_names
    
    def test_get_tools_has_inventory_tools(self):
        """Test that inventory-related tools exist"""
        from utils.ai_tools import get_tools
        
        tools = get_tools()
        tool_names = [t['function']['name'] for t in tools]
        
        assert 'add_inventory_item' in tool_names
        assert 'update_inventory_quantity' in tool_names
        assert 'check_stock_levels' in tool_names
    
    def test_get_tools_has_customer_tools(self):
        """Test that customer-related tools exist"""
        from utils.ai_tools import get_tools
        
        tools = get_tools()
        tool_names = [t['function']['name'] for t in tools]
        
        assert 'query_customers' in tool_names
        assert 'create_customer' in tool_names
    
    def test_make_json_serializable_dict(self):
        """Test JSON serialization for dicts"""
        from utils.ai_tools import make_json_serializable
        
        data = {
            'date': date(2026, 4, 17),
            'datetime': datetime(2026, 4, 17, 10, 30),
            'string': 'test',
            'number': 42
        }
        
        result = make_json_serializable(data)
        
        assert result['date'] == '2026-04-17'
        assert '2026-04-17' in result['datetime']
        assert result['string'] == 'test'
        assert result['number'] == 42
    
    def test_make_json_serializable_list(self):
        """Test JSON serialization for lists"""
        from utils.ai_tools import make_json_serializable
        
        data = [
            date(2026, 4, 17),
            'test',
            42
        ]
        
        result = make_json_serializable(data)
        
        assert result[0] == '2026-04-17'
        assert result[1] == 'test'
        assert result[2] == 42
    
    def test_make_json_serializable_nested(self):
        """Test JSON serialization for nested structures"""
        from utils.ai_tools import make_json_serializable
        
        data = {
            'items': [
                {'date': date(2026, 4, 17)},
                {'datetime': datetime(2026, 4, 17, 10, 30)}
            ]
        }
        
        result = make_json_serializable(data)
        
        assert result['items'][0]['date'] == '2026-04-17'
        assert '2026-04-17' in result['items'][1]['datetime']
    
    def test_execute_tool_query_inventory(self, temp_db, sample_material):
        """Test executing query_inventory tool"""
        from utils.ai_tools import execute_tool
        
        result = execute_tool('query_inventory', {'filter': 'all'})
        
        # Returns dict with items list and count
        assert isinstance(result, dict)
        assert 'items' in result
        assert 'count' in result
        assert isinstance(result['items'], list)
    
    def test_execute_tool_query_batches(self, temp_db):
        """Test executing query_batches tool"""
        from utils.ai_tools import execute_tool
        
        result = execute_tool('query_batches', {'status': 'all'})
        
        # Returns dict with batches list and count
        assert isinstance(result, dict)
        assert 'batches' in result
        assert 'count' in result
        assert isinstance(result['batches'], list)
    
    def test_execute_tool_query_products(self, temp_db, sample_product):
        """Test executing get_products tool"""
        from utils.ai_tools import execute_tool
        
        result = execute_tool('get_products', {'active_only': True})
        
        # Returns dict with products list and count
        assert isinstance(result, dict)
        assert 'products' in result
        assert 'count' in result
        assert isinstance(result['products'], list)
        assert len(result['products']) > 0
    
    def test_execute_tool_invalid_tool(self):
        """Test executing invalid tool name"""
        from utils.ai_tools import execute_tool
        
        result = execute_tool('invalid_tool_name', {})
        
        # Should return error dict
        assert 'error' in result
    
    def test_execute_tool_get_dashboard_summary(self, temp_db):
        """Test executing get_dashboard_summary tool"""
        from utils.ai_tools import execute_tool
        
        result = execute_tool('get_dashboard_summary', {})
        
        # Should return dashboard data
        assert isinstance(result, dict)