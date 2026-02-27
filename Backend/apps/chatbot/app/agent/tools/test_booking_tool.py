"""
Unit tests for booking tools.

Tests the booking_tool module which provides tools for creating and managing
bookings through the sync bridge.
"""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from datetime import date, time
from app.agent.tools.booking_tool import (
    create_booking_tool,
    get_booking_details_tool,
    cancel_booking_tool,
    BOOKING_TOOLS
)


@pytest.mark.asyncio
class TestCreateBookingTool:
    """Tests for create_booking_tool function"""
    
    async def test_create_booking_success(self):
        """Test successful booking creation"""
        mock_result = {
            'success': True,
            'message': 'Booking created successfully',
            'data': {
                'id': 789,
                'booking_date': '2024-01-15',
                'start_time': '14:00:00',
                'end_time': '15:30:00',
                'total_price': 75.0,
                'status': 'pending',
                'payment_status': 'pending'
            }
        }
        
        with patch('app.agent.tools.booking_tool._get_management_services') as mock_get_services, \
             patch('app.agent.tools.booking_tool._get_booking_schema') as mock_get_schema, \
             patch('app.agent.tools.booking_tool.call_sync_service', new_callable=AsyncMock) as mock_call:
            mock_get_services.return_value = MagicMock()
            mock_get_schema.return_value = MagicMock()
            mock_call.return_value = mock_result
            
            result = await create_booking_tool(
                customer_id=123,
                court_id=456,
                booking_date=date(2024, 1, 15),
                start_time=time(14, 0),
                end_time=time(15, 30),
                notes="Birthday party booking"
            )
            
            assert result is not None
            assert result['success'] is True
            assert result['data']['id'] == 789
            assert result['data']['total_price'] == 75.0
            assert result['data']['status'] == 'pending'
            
            # Verify call was made
            mock_call.assert_called_once()
    
    async def test_create_booking_without_notes(self):
        """Test booking creation without optional notes"""
        mock_result = {
            'success': True,
            'message': 'Booking created successfully',
            'data': {
                'id': 790,
                'booking_date': '2024-01-16',
                'start_time': '10:00:00',
                'end_time': '11:00:00',
                'total_price': 50.0,
                'status': 'pending',
                'payment_status': 'pending'
            }
        }
        
        with patch('app.agent.tools.booking_tool._get_management_services') as mock_get_services, \
             patch('app.agent.tools.booking_tool._get_booking_schema') as mock_get_schema, \
             patch('app.agent.tools.booking_tool.call_sync_service', new_callable=AsyncMock) as mock_call:
            mock_get_services.return_value = MagicMock()
            mock_get_schema.return_value = MagicMock()
            mock_call.return_value = mock_result
            
            result = await create_booking_tool(
                customer_id=123,
                court_id=456,
                booking_date=date(2024, 1, 16),
                start_time=time(10, 0),
                end_time=time(11, 0)
            )
            
            assert result is not None
            assert result['success'] is True
    
    async def test_create_booking_court_not_found(self):
        """Test booking creation when court doesn't exist"""
        mock_result = {
            'success': False,
            'message': 'Court not found or inactive'
        }
        
        with patch('app.agent.tools.booking_tool._get_management_services') as mock_get_services, \
             patch('app.agent.tools.booking_tool._get_booking_schema') as mock_get_schema, \
             patch('app.agent.tools.booking_tool.call_sync_service', new_callable=AsyncMock) as mock_call:
            mock_get_services.return_value = MagicMock()
            mock_get_schema.return_value = MagicMock()
            mock_call.return_value = mock_result
            
            result = await create_booking_tool(
                customer_id=123,
                court_id=999,
                booking_date=date(2024, 1, 15),
                start_time=time(14, 0),
                end_time=time(15, 30)
            )
            
            assert result is not None
            assert result['success'] is False
            assert 'Court not found' in result['message']
    
    async def test_create_booking_time_slot_conflict(self):
        """Test booking creation when time slot is already booked"""
        mock_result = {
            'success': False,
            'message': 'This time slot is already booked'
        }
        
        with patch('app.agent.tools.booking_tool._get_management_services') as mock_get_services, \
             patch('app.agent.tools.booking_tool._get_booking_schema') as mock_get_schema, \
             patch('app.agent.tools.booking_tool.call_sync_service', new_callable=AsyncMock) as mock_call:
            mock_get_services.return_value = MagicMock()
            mock_get_schema.return_value = MagicMock()
            mock_call.return_value = mock_result
            
            result = await create_booking_tool(
                customer_id=123,
                court_id=456,
                booking_date=date(2024, 1, 15),
                start_time=time(14, 0),
                end_time=time(15, 30)
            )
            
            assert result is not None
            assert result['success'] is False
            assert 'already booked' in result['message']
    
    async def test_create_booking_court_blocked(self):
        """Test booking creation when court is blocked"""
        mock_result = {
            'success': False,
            'message': 'Court is not available during this time. Reason: Maintenance'
        }
        
        with patch('app.agent.tools.booking_tool._get_management_services') as mock_get_services, \
             patch('app.agent.tools.booking_tool._get_booking_schema') as mock_get_schema, \
             patch('app.agent.tools.booking_tool.call_sync_service', new_callable=AsyncMock) as mock_call:
            mock_get_services.return_value = MagicMock()
            mock_get_schema.return_value = MagicMock()
            mock_call.return_value = mock_result
            
            result = await create_booking_tool(
                customer_id=123,
                court_id=456,
                booking_date=date(2024, 1, 15),
                start_time=time(14, 0),
                end_time=time(15, 30)
            )
            
            assert result is not None
            assert result['success'] is False
            assert 'not available' in result['message']
    
    async def test_create_booking_no_pricing(self):
        """Test booking creation when no pricing available"""
        mock_result = {
            'success': False,
            'message': 'No pricing available for this time slot'
        }
        
        with patch('app.agent.tools.booking_tool._get_management_services') as mock_get_services, \
             patch('app.agent.tools.booking_tool._get_booking_schema') as mock_get_schema, \
             patch('app.agent.tools.booking_tool.call_sync_service', new_callable=AsyncMock) as mock_call:
            mock_get_services.return_value = MagicMock()
            mock_get_schema.return_value = MagicMock()
            mock_call.return_value = mock_result
            
            result = await create_booking_tool(
                customer_id=123,
                court_id=456,
                booking_date=date(2024, 1, 15),
                start_time=time(14, 0),
                end_time=time(15, 30)
            )
            
            assert result is not None
            assert result['success'] is False
            assert 'No pricing available' in result['message']
    
    async def test_create_booking_validation_error(self):
        """Test booking creation with invalid data (validation error)"""
        with patch('app.agent.tools.booking_tool._get_management_services') as mock_get_services, \
             patch('app.agent.tools.booking_tool._get_booking_schema') as mock_get_schema:
            mock_get_services.return_value = MagicMock()
            mock_schema = MagicMock()
            mock_schema.side_effect = ValueError("end_time must be after start_time")
            mock_get_schema.return_value = mock_schema
            
            result = await create_booking_tool(
                customer_id=123,
                court_id=456,
                booking_date=date(2024, 1, 15),
                start_time=time(15, 30),
                end_time=time(14, 0)  # Invalid: end before start
            )
            
            assert result is not None
            assert result['success'] is False
            assert 'Invalid booking data' in result['message']
    
    async def test_create_booking_exception(self):
        """Test booking creation when exception occurs"""
        with patch('app.agent.tools.booking_tool._get_management_services') as mock_get_services, \
             patch('app.agent.tools.booking_tool._get_booking_schema') as mock_get_schema, \
             patch('app.agent.tools.booking_tool.call_sync_service', new_callable=AsyncMock) as mock_call:
            mock_get_services.return_value = MagicMock()
            mock_get_schema.return_value = MagicMock()
            mock_call.side_effect = Exception("Database error")
            
            result = await create_booking_tool(
                customer_id=123,
                court_id=456,
                booking_date=date(2024, 1, 15),
                start_time=time(14, 0),
                end_time=time(15, 30)
            )
            
            assert result is not None
            assert result['success'] is False
            assert 'unexpected error' in result['message']


@pytest.mark.asyncio
class TestGetBookingDetailsTool:
    """Tests for get_booking_details_tool function"""
    
    async def test_get_booking_details_success(self):
        """Test successful booking details retrieval"""
        mock_result = {
            'success': True,
            'message': 'Booking details retrieved successfully',
            'data': {
                'id': 789,
                'booking_date': '2024-01-15',
                'start_time': '14:00:00',
                'end_time': '15:30:00',
                'total_hours': 1.5,
                'price_per_hour': 50.0,
                'total_price': 75.0,
                'status': 'pending',
                'payment_status': 'pending',
                'notes': 'Birthday party booking',
                'court': {
                    'id': 456,
                    'name': 'Tennis Court A',
                    'sport_type': 'tennis'
                },
                'property': {
                    'id': 123,
                    'name': 'Downtown Sports Center',
                    'address': '123 Main St',
                    'phone': '555-0100'
                }
            }
        }
        
        with patch('app.agent.tools.booking_tool._get_management_services') as mock_get_services, \
             patch('app.agent.tools.booking_tool.call_sync_service', new_callable=AsyncMock) as mock_call:
            mock_get_services.return_value = MagicMock()
            mock_call.return_value = mock_result
            
            result = await get_booking_details_tool(
                booking_id=789,
                user_id=123
            )
            
            assert result is not None
            assert result['success'] is True
            assert result['data']['id'] == 789
            assert result['data']['court']['name'] == 'Tennis Court A'
            assert result['data']['property']['name'] == 'Downtown Sports Center'
            
            # Verify call was made with correct parameters
            mock_call.assert_called_once()
            call_kwargs = mock_call.call_args[1]
            assert call_kwargs['booking_id'] == 789
            assert call_kwargs['user_id'] == 123
    
    async def test_get_booking_details_not_found(self):
        """Test booking details retrieval when booking doesn't exist"""
        mock_result = {
            'success': False,
            'message': 'Booking not found'
        }
        
        with patch('app.agent.tools.booking_tool._get_management_services') as mock_get_services, \
             patch('app.agent.tools.booking_tool.call_sync_service', new_callable=AsyncMock) as mock_call:
            mock_get_services.return_value = MagicMock()
            mock_call.return_value = mock_result
            
            result = await get_booking_details_tool(
                booking_id=999,
                user_id=123
            )
            
            assert result is not None
            assert result['success'] is False
            assert 'not found' in result['message']
    
    async def test_get_booking_details_access_denied(self):
        """Test booking details retrieval with access denied"""
        mock_result = {
            'success': False,
            'message': 'Access denied'
        }
        
        with patch('app.agent.tools.booking_tool._get_management_services') as mock_get_services, \
             patch('app.agent.tools.booking_tool.call_sync_service', new_callable=AsyncMock) as mock_call:
            mock_get_services.return_value = MagicMock()
            mock_call.return_value = mock_result
            
            result = await get_booking_details_tool(
                booking_id=789,
                user_id=999  # Different user
            )
            
            assert result is not None
            assert result['success'] is False
            assert 'Access denied' in result['message']
    
    async def test_get_booking_details_exception(self):
        """Test booking details retrieval when exception occurs"""
        with patch('app.agent.tools.booking_tool._get_management_services') as mock_get_services, \
             patch('app.agent.tools.booking_tool.call_sync_service', new_callable=AsyncMock) as mock_call:
            mock_get_services.return_value = MagicMock()
            mock_call.side_effect = Exception("Database error")
            
            result = await get_booking_details_tool(
                booking_id=789,
                user_id=123
            )
            
            assert result is not None
            assert result['success'] is False
            assert 'unexpected error' in result['message']


@pytest.mark.asyncio
class TestCancelBookingTool:
    """Tests for cancel_booking_tool function"""
    
    async def test_cancel_booking_success(self):
        """Test successful booking cancellation"""
        mock_result = {
            'success': True,
            'message': 'Booking cancelled successfully'
        }
        
        with patch('app.agent.tools.booking_tool._get_management_services') as mock_get_services, \
             patch('app.agent.tools.booking_tool.call_sync_service', new_callable=AsyncMock) as mock_call:
            mock_get_services.return_value = MagicMock()
            mock_call.return_value = mock_result
            
            result = await cancel_booking_tool(
                booking_id=789,
                user_id=123
            )
            
            assert result is not None
            assert result['success'] is True
            assert 'cancelled successfully' in result['message']
            
            # Verify call was made with correct parameters
            mock_call.assert_called_once()
            call_kwargs = mock_call.call_args[1]
            assert call_kwargs['booking_id'] == 789
            assert call_kwargs['user_id'] == 123
    
    async def test_cancel_booking_not_found(self):
        """Test booking cancellation when booking doesn't exist"""
        mock_result = {
            'success': False,
            'message': 'Booking not found'
        }
        
        with patch('app.agent.tools.booking_tool._get_management_services') as mock_get_services, \
             patch('app.agent.tools.booking_tool.call_sync_service', new_callable=AsyncMock) as mock_call:
            mock_get_services.return_value = MagicMock()
            mock_call.return_value = mock_result
            
            result = await cancel_booking_tool(
                booking_id=999,
                user_id=123
            )
            
            assert result is not None
            assert result['success'] is False
            assert 'not found' in result['message']
    
    async def test_cancel_booking_not_customer(self):
        """Test booking cancellation by non-customer"""
        mock_result = {
            'success': False,
            'message': 'Only the customer can cancel their booking'
        }
        
        with patch('app.agent.tools.booking_tool._get_management_services') as mock_get_services, \
             patch('app.agent.tools.booking_tool.call_sync_service', new_callable=AsyncMock) as mock_call:
            mock_get_services.return_value = MagicMock()
            mock_call.return_value = mock_result
            
            result = await cancel_booking_tool(
                booking_id=789,
                user_id=999  # Different user
            )
            
            assert result is not None
            assert result['success'] is False
            assert 'Only the customer' in result['message']
    
    async def test_cancel_booking_already_cancelled(self):
        """Test cancellation of already cancelled booking"""
        mock_result = {
            'success': False,
            'message': 'Booking is already cancelled'
        }
        
        with patch('app.agent.tools.booking_tool._get_management_services') as mock_get_services, \
             patch('app.agent.tools.booking_tool.call_sync_service', new_callable=AsyncMock) as mock_call:
            mock_get_services.return_value = MagicMock()
            mock_call.return_value = mock_result
            
            result = await cancel_booking_tool(
                booking_id=789,
                user_id=123
            )
            
            assert result is not None
            assert result['success'] is False
            assert 'already cancelled' in result['message']
    
    async def test_cancel_booking_completed(self):
        """Test cancellation of completed booking"""
        mock_result = {
            'success': False,
            'message': 'Cannot cancel completed booking'
        }
        
        with patch('app.agent.tools.booking_tool._get_management_services') as mock_get_services, \
             patch('app.agent.tools.booking_tool.call_sync_service', new_callable=AsyncMock) as mock_call:
            mock_get_services.return_value = MagicMock()
            mock_call.return_value = mock_result
            
            result = await cancel_booking_tool(
                booking_id=789,
                user_id=123
            )
            
            assert result is not None
            assert result['success'] is False
            assert 'Cannot cancel completed' in result['message']
    
    async def test_cancel_booking_exception(self):
        """Test booking cancellation when exception occurs"""
        with patch('app.agent.tools.booking_tool._get_management_services') as mock_get_services, \
             patch('app.agent.tools.booking_tool.call_sync_service', new_callable=AsyncMock) as mock_call:
            mock_get_services.return_value = MagicMock()
            mock_call.side_effect = Exception("Database error")
            
            result = await cancel_booking_tool(
                booking_id=789,
                user_id=123
            )
            
            assert result is not None
            assert result['success'] is False
            assert 'unexpected error' in result['message']


class TestBookingToolsRegistry:
    """Tests for BOOKING_TOOLS registry"""
    
    def test_booking_tools_registry_contains_all_tools(self):
        """Test that registry contains all expected tools"""
        assert 'create_booking' in BOOKING_TOOLS
        assert 'get_booking_details' in BOOKING_TOOLS
        assert 'cancel_booking' in BOOKING_TOOLS
    
    def test_booking_tools_registry_functions_are_callable(self):
        """Test that all registered tools are callable"""
        for tool_name, tool_func in BOOKING_TOOLS.items():
            assert callable(tool_func), f"{tool_name} should be callable"
    
    def test_booking_tools_registry_has_correct_functions(self):
        """Test that registry maps to correct functions"""
        assert BOOKING_TOOLS['create_booking'] == create_booking_tool
        assert BOOKING_TOOLS['get_booking_details'] == get_booking_details_tool
        assert BOOKING_TOOLS['cancel_booking'] == cancel_booking_tool
