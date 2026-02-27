"""
Unit tests for availability checking tools.

Tests the availability_tool module which provides tools for checking court
availability and retrieving available time slots through the sync bridge.
"""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from datetime import date
from app.agent.tools.availability_tool import (
    check_availability_tool,
    get_available_slots_tool,
    AVAILABILITY_TOOLS
)


@pytest.mark.asyncio
class TestCheckAvailabilityTool:
    """Tests for check_availability_tool function"""
    
    async def test_check_availability_success(self):
        """Test successful availability check with blocked slots"""
        mock_result = {
            'success': True,
            'data': [
                {
                    'id': 1,
                    'date': '2024-01-15',
                    'start_time': '09:00:00',
                    'end_time': '11:00:00',
                    'reason': 'Maintenance'
                },
                {
                    'id': 2,
                    'date': '2024-01-16',
                    'start_time': '14:00:00',
                    'end_time': '16:00:00',
                    'reason': 'Private event'
                }
            ]
        }
        
        with patch('app.agent.tools.availability_tool._get_management_services') as mock_get_services, \
             patch('app.agent.tools.availability_tool.call_sync_service', new_callable=AsyncMock) as mock_call:
            # Mock _get_management_services to return tuple of mock services
            mock_get_services.return_value = (MagicMock(), MagicMock())
            mock_call.return_value = mock_result
            
            result = await check_availability_tool(
                court_id=123,
                owner_id=456,
                from_date=date(2024, 1, 15)
            )
            
            assert len(result) == 2
            assert result[0]['reason'] == 'Maintenance'
            assert result[1]['reason'] == 'Private event'
            
            # Verify call was made with correct parameters
            mock_call.assert_called_once()
            call_kwargs = mock_call.call_args[1]
            assert call_kwargs['court_id'] == 123
            assert call_kwargs['owner_id'] == 456
            assert call_kwargs['from_date'] == date(2024, 1, 15)
    
    async def test_check_availability_no_blocked_slots(self):
        """Test availability check with no blocked slots"""
        mock_result = {
            'success': True,
            'data': []
        }
        
        with patch('app.agent.tools.availability_tool._get_management_services') as mock_get_services, \
             patch('app.agent.tools.availability_tool.call_sync_service', new_callable=AsyncMock) as mock_call:
            mock_get_services.return_value = (MagicMock(), MagicMock())
            mock_call.return_value = mock_result
            
            result = await check_availability_tool(
                court_id=123,
                owner_id=456
            )
            
            assert len(result) == 0
    
    async def test_check_availability_court_not_found(self):
        """Test availability check when court doesn't exist"""
        mock_result = {
            'success': False,
            'message': 'Court not found'
        }
        
        with patch('app.agent.tools.availability_tool._get_management_services') as mock_get_services, \
             patch('app.agent.tools.availability_tool.call_sync_service', new_callable=AsyncMock) as mock_call:
            mock_get_services.return_value = (MagicMock(), MagicMock())
            mock_call.return_value = mock_result
            
            result = await check_availability_tool(
                court_id=999,
                owner_id=456
            )
            
            assert len(result) == 0
    
    async def test_check_availability_access_denied(self):
        """Test availability check when owner doesn't have access"""
        mock_result = {
            'success': False,
            'message': 'Access denied'
        }
        
        with patch('app.agent.tools.availability_tool._get_management_services') as mock_get_services, \
             patch('app.agent.tools.availability_tool.call_sync_service', new_callable=AsyncMock) as mock_call:
            mock_get_services.return_value = (MagicMock(), MagicMock())
            mock_call.return_value = mock_result
            
            result = await check_availability_tool(
                court_id=123,
                owner_id=999
            )
            
            assert len(result) == 0
    
    async def test_check_availability_exception(self):
        """Test availability check when exception occurs"""
        with patch('app.agent.tools.availability_tool._get_management_services') as mock_get_services, \
             patch('app.agent.tools.availability_tool.call_sync_service', new_callable=AsyncMock) as mock_call:
            mock_get_services.return_value = (MagicMock(), MagicMock())
            mock_call.side_effect = Exception("Database error")
            
            result = await check_availability_tool(
                court_id=123,
                owner_id=456
            )
            
            assert len(result) == 0
    
    async def test_check_availability_default_from_date(self):
        """Test availability check without specifying from_date"""
        mock_result = {
            'success': True,
            'data': []
        }
        
        with patch('app.agent.tools.availability_tool._get_management_services') as mock_get_services, \
             patch('app.agent.tools.availability_tool.call_sync_service', new_callable=AsyncMock) as mock_call:
            mock_get_services.return_value = (MagicMock(), MagicMock())
            mock_call.return_value = mock_result
            
            result = await check_availability_tool(
                court_id=123,
                owner_id=456
            )
            
            # Verify from_date was passed as None (will default to today in service)
            call_kwargs = mock_call.call_args[1]
            assert call_kwargs['from_date'] is None


@pytest.mark.asyncio
class TestGetAvailableSlotsTool:
    """Tests for get_available_slots_tool function"""
    
    async def test_get_available_slots_success(self):
        """Test successful retrieval of available slots"""
        mock_result = {
            'success': True,
            'data': {
                'date': '2024-01-15',
                'court_id': 123,
                'court_name': 'Tennis Court A',
                'available_slots': [
                    {
                        'start_time': '09:00:00',
                        'end_time': '10:00:00',
                        'price_per_hour': 50.0,
                        'label': 'Morning Rate'
                    },
                    {
                        'start_time': '10:00:00',
                        'end_time': '11:00:00',
                        'price_per_hour': 50.0,
                        'label': 'Morning Rate'
                    },
                    {
                        'start_time': '14:00:00',
                        'end_time': '15:00:00',
                        'price_per_hour': 75.0,
                        'label': 'Afternoon Rate'
                    }
                ]
            }
        }
        
        with patch('app.agent.tools.availability_tool._get_management_services') as mock_get_services, \
             patch('app.agent.tools.availability_tool.call_sync_service', new_callable=AsyncMock) as mock_call:
            mock_get_services.return_value = (MagicMock(), MagicMock())
            mock_call.return_value = mock_result
            
            result = await get_available_slots_tool(
                court_id=123,
                date_val=date(2024, 1, 15)
            )
            
            assert result is not None
            assert result['court_id'] == 123
            assert result['court_name'] == 'Tennis Court A'
            assert len(result['available_slots']) == 3
            assert result['available_slots'][0]['price_per_hour'] == 50.0
            assert result['available_slots'][2]['price_per_hour'] == 75.0
            
            # Verify call was made with correct parameters
            mock_call.assert_called_once()
            call_kwargs = mock_call.call_args[1]
            assert call_kwargs['court_id'] == 123
            assert call_kwargs['date_val'] == date(2024, 1, 15)
    
    async def test_get_available_slots_no_slots(self):
        """Test getting available slots when none are available"""
        mock_result = {
            'success': True,
            'data': {
                'date': '2024-01-15',
                'court_id': 123,
                'court_name': 'Tennis Court A',
                'available_slots': []
            }
        }
        
        with patch('app.agent.tools.availability_tool._get_management_services') as mock_get_services, \
             patch('app.agent.tools.availability_tool.call_sync_service', new_callable=AsyncMock) as mock_call:
            mock_get_services.return_value = (MagicMock(), MagicMock())
            mock_call.return_value = mock_result
            
            result = await get_available_slots_tool(
                court_id=123,
                date_val=date(2024, 1, 15)
            )
            
            assert result is not None
            assert len(result['available_slots']) == 0
    
    async def test_get_available_slots_court_not_found(self):
        """Test getting available slots when court doesn't exist"""
        mock_result = {
            'success': False,
            'message': 'Court not found'
        }
        
        with patch('app.agent.tools.availability_tool._get_management_services') as mock_get_services, \
             patch('app.agent.tools.availability_tool.call_sync_service', new_callable=AsyncMock) as mock_call:
            mock_get_services.return_value = (MagicMock(), MagicMock())
            mock_call.return_value = mock_result
            
            result = await get_available_slots_tool(
                court_id=999,
                date_val=date(2024, 1, 15)
            )
            
            assert result is None
    
    async def test_get_available_slots_court_not_available_on_date(self):
        """Test getting available slots when court not available on date"""
        mock_result = {
            'success': False,
            'message': 'Court not available on this date'
        }
        
        with patch('app.agent.tools.availability_tool._get_management_services') as mock_get_services, \
             patch('app.agent.tools.availability_tool.call_sync_service', new_callable=AsyncMock) as mock_call:
            mock_get_services.return_value = (MagicMock(), MagicMock())
            mock_call.return_value = mock_result
            
            result = await get_available_slots_tool(
                court_id=123,
                date_val=date(2024, 1, 15)
            )
            
            assert result is None
    
    async def test_get_available_slots_exception(self):
        """Test getting available slots when exception occurs"""
        with patch('app.agent.tools.availability_tool._get_management_services') as mock_get_services, \
             patch('app.agent.tools.availability_tool.call_sync_service', new_callable=AsyncMock) as mock_call:
            mock_get_services.return_value = (MagicMock(), MagicMock())
            mock_call.side_effect = Exception("Connection error")
            
            result = await get_available_slots_tool(
                court_id=123,
                date_val=date(2024, 1, 15)
            )
            
            assert result is None
    
    async def test_get_available_slots_with_pricing_variations(self):
        """Test getting available slots with different pricing labels"""
        mock_result = {
            'success': True,
            'data': {
                'date': '2024-01-15',
                'court_id': 123,
                'court_name': 'Basketball Court B',
                'available_slots': [
                    {
                        'start_time': '06:00:00',
                        'end_time': '07:00:00',
                        'price_per_hour': 40.0,
                        'label': 'Early Bird'
                    },
                    {
                        'start_time': '18:00:00',
                        'end_time': '19:00:00',
                        'price_per_hour': 80.0,
                        'label': 'Peak Hours'
                    },
                    {
                        'start_time': '21:00:00',
                        'end_time': '22:00:00',
                        'price_per_hour': 60.0,
                        'label': 'Evening Rate'
                    }
                ]
            }
        }
        
        with patch('app.agent.tools.availability_tool._get_management_services') as mock_get_services, \
             patch('app.agent.tools.availability_tool.call_sync_service', new_callable=AsyncMock) as mock_call:
            mock_get_services.return_value = (MagicMock(), MagicMock())
            mock_call.return_value = mock_result
            
            result = await get_available_slots_tool(
                court_id=123,
                date_val=date(2024, 1, 15)
            )
            
            assert result is not None
            assert len(result['available_slots']) == 3
            
            # Verify different pricing labels
            labels = [slot['label'] for slot in result['available_slots']]
            assert 'Early Bird' in labels
            assert 'Peak Hours' in labels
            assert 'Evening Rate' in labels
            
            # Verify pricing varies
            prices = [slot['price_per_hour'] for slot in result['available_slots']]
            assert 40.0 in prices
            assert 80.0 in prices
            assert 60.0 in prices


class TestAvailabilityToolsRegistry:
    """Tests for AVAILABILITY_TOOLS registry"""
    
    def test_availability_tools_registry_contains_all_tools(self):
        """Test that registry contains all expected tools"""
        assert 'check_availability' in AVAILABILITY_TOOLS
        assert 'get_available_slots' in AVAILABILITY_TOOLS
    
    def test_availability_tools_registry_functions_are_callable(self):
        """Test that all registered tools are callable"""
        for tool_name, tool_func in AVAILABILITY_TOOLS.items():
            assert callable(tool_func), f"{tool_name} should be callable"
    
    def test_availability_tools_registry_has_correct_functions(self):
        """Test that registry maps to correct functions"""
        assert AVAILABILITY_TOOLS['check_availability'] == check_availability_tool
        assert AVAILABILITY_TOOLS['get_available_slots'] == get_available_slots_tool
