"""
Unit tests for pricing tools.

Tests the pricing_tool module which provides tools for retrieving pricing
information and calculating total booking costs through the sync bridge.
"""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from datetime import date, time
from app.agent.tools.pricing_tool import (
    get_pricing_tool,
    calculate_total_price,
    PRICING_TOOLS
)


@pytest.mark.asyncio
class TestGetPricingTool:
    """Tests for get_pricing_tool function"""
    
    async def test_get_pricing_success(self):
        """Test successful pricing retrieval"""
        mock_result = {
            'success': True,
            'data': {
                'date': '2024-01-15',
                'day_of_week': 0,  # Monday
                'pricing': [
                    {
                        'start_time': '09:00:00',
                        'end_time': '17:00:00',
                        'price_per_hour': 50.0,
                        'label': 'Daytime Rate'
                    },
                    {
                        'start_time': '17:00:00',
                        'end_time': '22:00:00',
                        'price_per_hour': 75.0,
                        'label': 'Evening Rate'
                    }
                ]
            }
        }
        
        with patch('app.agent.tools.pricing_tool._get_management_services') as mock_get_services, \
             patch('app.agent.tools.pricing_tool.call_sync_service', new_callable=AsyncMock) as mock_call:
            mock_get_services.return_value = MagicMock()
            mock_call.return_value = mock_result
            
            result = await get_pricing_tool(
                court_id=123,
                date_val=date(2024, 1, 15)
            )
            
            assert result is not None
            assert result['date'] == '2024-01-15'
            assert result['day_of_week'] == 0
            assert len(result['pricing']) == 2
            assert result['pricing'][0]['price_per_hour'] == 50.0
            assert result['pricing'][1]['price_per_hour'] == 75.0
            
            # Verify call was made with correct parameters
            mock_call.assert_called_once()
            call_kwargs = mock_call.call_args[1]
            assert call_kwargs['court_id'] == 123
            assert call_kwargs['date_val'] == date(2024, 1, 15)
    
    async def test_get_pricing_single_rate(self):
        """Test pricing retrieval with single rate for entire day"""
        mock_result = {
            'success': True,
            'data': {
                'date': '2024-01-15',
                'day_of_week': 0,
                'pricing': [
                    {
                        'start_time': '08:00:00',
                        'end_time': '22:00:00',
                        'price_per_hour': 60.0,
                        'label': 'Standard Rate'
                    }
                ]
            }
        }
        
        with patch('app.agent.tools.pricing_tool._get_management_services') as mock_get_services, \
             patch('app.agent.tools.pricing_tool.call_sync_service', new_callable=AsyncMock) as mock_call:
            mock_get_services.return_value = MagicMock()
            mock_call.return_value = mock_result
            
            result = await get_pricing_tool(
                court_id=123,
                date_val=date(2024, 1, 15)
            )
            
            assert result is not None
            assert len(result['pricing']) == 1
            assert result['pricing'][0]['label'] == 'Standard Rate'
    
    async def test_get_pricing_court_not_found(self):
        """Test pricing retrieval when court doesn't exist"""
        mock_result = {
            'success': False,
            'message': 'Court not found'
        }
        
        with patch('app.agent.tools.pricing_tool._get_management_services') as mock_get_services, \
             patch('app.agent.tools.pricing_tool.call_sync_service', new_callable=AsyncMock) as mock_call:
            mock_get_services.return_value = MagicMock()
            mock_call.return_value = mock_result
            
            result = await get_pricing_tool(
                court_id=999,
                date_val=date(2024, 1, 15)
            )
            
            assert result is None
    
    async def test_get_pricing_no_pricing_available(self):
        """Test pricing retrieval when no pricing rules exist for date"""
        mock_result = {
            'success': False,
            'message': 'No pricing available for this date'
        }
        
        with patch('app.agent.tools.pricing_tool._get_management_services') as mock_get_services, \
             patch('app.agent.tools.pricing_tool.call_sync_service', new_callable=AsyncMock) as mock_call:
            mock_get_services.return_value = MagicMock()
            mock_call.return_value = mock_result
            
            result = await get_pricing_tool(
                court_id=123,
                date_val=date(2024, 1, 15)
            )
            
            assert result is None
    
    async def test_get_pricing_exception(self):
        """Test pricing retrieval when exception occurs"""
        with patch('app.agent.tools.pricing_tool._get_management_services') as mock_get_services, \
             patch('app.agent.tools.pricing_tool.call_sync_service', new_callable=AsyncMock) as mock_call:
            mock_get_services.return_value = MagicMock()
            mock_call.side_effect = Exception("Database error")
            
            result = await get_pricing_tool(
                court_id=123,
                date_val=date(2024, 1, 15)
            )
            
            assert result is None
    
    async def test_get_pricing_weekend_rates(self):
        """Test pricing retrieval for weekend with different rates"""
        mock_result = {
            'success': True,
            'data': {
                'date': '2024-01-20',
                'day_of_week': 5,  # Saturday
                'pricing': [
                    {
                        'start_time': '08:00:00',
                        'end_time': '12:00:00',
                        'price_per_hour': 80.0,
                        'label': 'Weekend Morning'
                    },
                    {
                        'start_time': '12:00:00',
                        'end_time': '20:00:00',
                        'price_per_hour': 100.0,
                        'label': 'Weekend Peak'
                    }
                ]
            }
        }
        
        with patch('app.agent.tools.pricing_tool._get_management_services') as mock_get_services, \
             patch('app.agent.tools.pricing_tool.call_sync_service', new_callable=AsyncMock) as mock_call:
            mock_get_services.return_value = MagicMock()
            mock_call.return_value = mock_result
            
            result = await get_pricing_tool(
                court_id=123,
                date_val=date(2024, 1, 20)
            )
            
            assert result is not None
            assert result['day_of_week'] == 5
            assert result['pricing'][0]['price_per_hour'] == 80.0
            assert result['pricing'][1]['price_per_hour'] == 100.0


@pytest.mark.asyncio
class TestCalculateTotalPrice:
    """Tests for calculate_total_price function"""
    
    async def test_calculate_total_price_one_hour(self):
        """Test total price calculation for 1 hour booking"""
        mock_pricing_data = {
            'date': '2024-01-15',
            'day_of_week': 0,
            'pricing': [
                {
                    'start_time': '09:00:00',
                    'end_time': '17:00:00',
                    'price_per_hour': 50.0,
                    'label': 'Daytime Rate'
                }
            ]
        }
        
        with patch('app.agent.tools.pricing_tool.get_pricing_tool', new_callable=AsyncMock) as mock_get_pricing:
            mock_get_pricing.return_value = mock_pricing_data
            
            result = await calculate_total_price(
                court_id=123,
                date_val=date(2024, 1, 15),
                start_time=time(10, 0),
                duration_minutes=60
            )
            
            assert result == 50.0
    
    async def test_calculate_total_price_ninety_minutes(self):
        """Test total price calculation for 1.5 hour booking"""
        mock_pricing_data = {
            'date': '2024-01-15',
            'day_of_week': 0,
            'pricing': [
                {
                    'start_time': '09:00:00',
                    'end_time': '17:00:00',
                    'price_per_hour': 50.0,
                    'label': 'Daytime Rate'
                }
            ]
        }
        
        with patch('app.agent.tools.pricing_tool.get_pricing_tool', new_callable=AsyncMock) as mock_get_pricing:
            mock_get_pricing.return_value = mock_pricing_data
            
            result = await calculate_total_price(
                court_id=123,
                date_val=date(2024, 1, 15),
                start_time=time(10, 0),
                duration_minutes=90
            )
            
            assert result == 75.0  # 1.5 hours * $50/hour
    
    async def test_calculate_total_price_thirty_minutes(self):
        """Test total price calculation for 30 minute booking"""
        mock_pricing_data = {
            'date': '2024-01-15',
            'day_of_week': 0,
            'pricing': [
                {
                    'start_time': '09:00:00',
                    'end_time': '17:00:00',
                    'price_per_hour': 60.0,
                    'label': 'Daytime Rate'
                }
            ]
        }
        
        with patch('app.agent.tools.pricing_tool.get_pricing_tool', new_callable=AsyncMock) as mock_get_pricing:
            mock_get_pricing.return_value = mock_pricing_data
            
            result = await calculate_total_price(
                court_id=123,
                date_val=date(2024, 1, 15),
                start_time=time(10, 0),
                duration_minutes=30
            )
            
            assert result == 30.0  # 0.5 hours * $60/hour
    
    async def test_calculate_total_price_evening_rate(self):
        """Test total price calculation with evening rate"""
        mock_pricing_data = {
            'date': '2024-01-15',
            'day_of_week': 0,
            'pricing': [
                {
                    'start_time': '09:00:00',
                    'end_time': '17:00:00',
                    'price_per_hour': 50.0,
                    'label': 'Daytime Rate'
                },
                {
                    'start_time': '17:00:00',
                    'end_time': '22:00:00',
                    'price_per_hour': 75.0,
                    'label': 'Evening Rate'
                }
            ]
        }
        
        with patch('app.agent.tools.pricing_tool.get_pricing_tool', new_callable=AsyncMock) as mock_get_pricing:
            mock_get_pricing.return_value = mock_pricing_data
            
            result = await calculate_total_price(
                court_id=123,
                date_val=date(2024, 1, 15),
                start_time=time(18, 0),  # 6 PM - evening rate
                duration_minutes=60
            )
            
            assert result == 75.0
    
    async def test_calculate_total_price_no_pricing_data(self):
        """Test total price calculation when no pricing data available"""
        with patch('app.agent.tools.pricing_tool.get_pricing_tool', new_callable=AsyncMock) as mock_get_pricing:
            mock_get_pricing.return_value = None
            
            result = await calculate_total_price(
                court_id=123,
                date_val=date(2024, 1, 15),
                start_time=time(10, 0),
                duration_minutes=60
            )
            
            assert result is None
    
    async def test_calculate_total_price_empty_pricing_rules(self):
        """Test total price calculation when pricing data has no rules"""
        mock_pricing_data = {
            'date': '2024-01-15',
            'day_of_week': 0,
            'pricing': []
        }
        
        with patch('app.agent.tools.pricing_tool.get_pricing_tool', new_callable=AsyncMock) as mock_get_pricing:
            mock_get_pricing.return_value = mock_pricing_data
            
            result = await calculate_total_price(
                court_id=123,
                date_val=date(2024, 1, 15),
                start_time=time(10, 0),
                duration_minutes=60
            )
            
            assert result is None
    
    async def test_calculate_total_price_time_not_in_range(self):
        """Test total price calculation when start time not in any pricing rule"""
        mock_pricing_data = {
            'date': '2024-01-15',
            'day_of_week': 0,
            'pricing': [
                {
                    'start_time': '09:00:00',
                    'end_time': '17:00:00',
                    'price_per_hour': 50.0,
                    'label': 'Daytime Rate'
                }
            ]
        }
        
        with patch('app.agent.tools.pricing_tool.get_pricing_tool', new_callable=AsyncMock) as mock_get_pricing:
            mock_get_pricing.return_value = mock_pricing_data
            
            result = await calculate_total_price(
                court_id=123,
                date_val=date(2024, 1, 15),
                start_time=time(20, 0),  # 8 PM - outside pricing range
                duration_minutes=60
            )
            
            assert result is None
    
    async def test_calculate_total_price_two_hours(self):
        """Test total price calculation for 2 hour booking"""
        mock_pricing_data = {
            'date': '2024-01-15',
            'day_of_week': 0,
            'pricing': [
                {
                    'start_time': '09:00:00',
                    'end_time': '17:00:00',
                    'price_per_hour': 50.0,
                    'label': 'Daytime Rate'
                }
            ]
        }
        
        with patch('app.agent.tools.pricing_tool.get_pricing_tool', new_callable=AsyncMock) as mock_get_pricing:
            mock_get_pricing.return_value = mock_pricing_data
            
            result = await calculate_total_price(
                court_id=123,
                date_val=date(2024, 1, 15),
                start_time=time(10, 0),
                duration_minutes=120
            )
            
            assert result == 100.0  # 2 hours * $50/hour
    
    async def test_calculate_total_price_exception(self):
        """Test total price calculation when exception occurs"""
        with patch('app.agent.tools.pricing_tool.get_pricing_tool', new_callable=AsyncMock) as mock_get_pricing:
            mock_get_pricing.side_effect = Exception("Service error")
            
            result = await calculate_total_price(
                court_id=123,
                date_val=date(2024, 1, 15),
                start_time=time(10, 0),
                duration_minutes=60
            )
            
            assert result is None
    
    async def test_calculate_total_price_rounding(self):
        """Test total price calculation rounds to 2 decimal places"""
        mock_pricing_data = {
            'date': '2024-01-15',
            'day_of_week': 0,
            'pricing': [
                {
                    'start_time': '09:00:00',
                    'end_time': '17:00:00',
                    'price_per_hour': 33.33,
                    'label': 'Daytime Rate'
                }
            ]
        }
        
        with patch('app.agent.tools.pricing_tool.get_pricing_tool', new_callable=AsyncMock) as mock_get_pricing:
            mock_get_pricing.return_value = mock_pricing_data
            
            result = await calculate_total_price(
                court_id=123,
                date_val=date(2024, 1, 15),
                start_time=time(10, 0),
                duration_minutes=90
            )
            
            # 1.5 hours * $33.33/hour = $49.995, rounds to $49.99
            assert result == 49.99


class TestPricingToolsRegistry:
    """Tests for PRICING_TOOLS registry"""
    
    def test_pricing_tools_registry_contains_all_tools(self):
        """Test that registry contains all expected tools"""
        assert 'get_pricing' in PRICING_TOOLS
        assert 'calculate_total_price' in PRICING_TOOLS
    
    def test_pricing_tools_registry_functions_are_callable(self):
        """Test that all registered tools are callable"""
        for tool_name, tool_func in PRICING_TOOLS.items():
            assert callable(tool_func), f"{tool_name} should be callable"
    
    def test_pricing_tools_registry_has_correct_functions(self):
        """Test that registry maps to correct functions"""
        assert PRICING_TOOLS['get_pricing'] == get_pricing_tool
        assert PRICING_TOOLS['calculate_total_price'] == calculate_total_price
