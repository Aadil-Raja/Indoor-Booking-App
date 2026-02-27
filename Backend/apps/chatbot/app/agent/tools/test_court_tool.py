"""
Unit tests for court tool functions.

These tests verify that the court search and details tools correctly
integrate with the sync services through the sync bridge.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.agent.tools.court_tool import (
    search_courts_tool,
    get_court_details_tool,
    get_property_courts_tool,
    COURT_TOOLS
)


@pytest.mark.asyncio
class TestSearchCourtsTool:
    """Tests for search_courts_tool function"""
    
    async def test_search_courts_by_sport_type(self):
        """Test searching courts by sport type"""
        # Mock response data
        mock_properties = {
            'success': True,
            'data': {
                'items': [
                    {'id': 1, 'name': 'Sports Center A'},
                    {'id': 2, 'name': 'Sports Center B'}
                ]
            }
        }
        
        mock_property_details_1 = {
            'success': True,
            'data': {
                'id': 1,
                'name': 'Sports Center A',
                'city': 'New York',
                'address': '123 Main St',
                'courts': [
                    {
                        'id': 101,
                        'name': 'Tennis Court 1',
                        'sport_type': 'tennis',
                        'description': 'Professional tennis court'
                    },
                    {
                        'id': 102,
                        'name': 'Basketball Court',
                        'sport_type': 'basketball',
                        'description': 'Indoor basketball court'
                    }
                ]
            }
        }
        
        mock_property_details_2 = {
            'success': True,
            'data': {
                'id': 2,
                'name': 'Sports Center B',
                'city': 'New York',
                'address': '456 Oak Ave',
                'courts': [
                    {
                        'id': 201,
                        'name': 'Tennis Court 2',
                        'sport_type': 'tennis',
                        'description': 'Outdoor tennis court'
                    }
                ]
            }
        }
        
        with patch('app.agent.tools.court_tool._get_management_services') as mock_services, \
             patch('app.agent.tools.court_tool.call_sync_service') as mock_call:
            # Mock the services
            mock_services.return_value = (MagicMock(), MagicMock())
            
            # Setup mock to return different values based on call
            mock_call.side_effect = [
                mock_properties,
                mock_property_details_1,
                mock_property_details_2
            ]
            
            # Execute
            result = await search_courts_tool(sport_type='tennis', city='New York')
            
            # Verify
            assert len(result) == 2
            assert result[0]['id'] == 101
            assert result[0]['sport_type'] == 'tennis'
            assert result[0]['property_name'] == 'Sports Center A'
            assert result[1]['id'] == 201
            assert result[1]['sport_type'] == 'tennis'
            assert result[1]['property_name'] == 'Sports Center B'
    
    async def test_search_courts_by_property_id(self):
        """Test searching courts for a specific property"""
        mock_property_details = {
            'success': True,
            'data': {
                'id': 1,
                'name': 'Sports Center',
                'courts': [
                    {
                        'id': 101,
                        'name': 'Tennis Court',
                        'sport_type': 'tennis'
                    },
                    {
                        'id': 102,
                        'name': 'Basketball Court',
                        'sport_type': 'basketball'
                    }
                ]
            }
        }
        
        with patch('app.agent.tools.court_tool._get_management_services') as mock_services, \
             patch('app.agent.tools.court_tool.call_sync_service') as mock_call:
            mock_services.return_value = (MagicMock(), MagicMock())
            mock_call.return_value = mock_property_details
            
            # Execute
            result = await search_courts_tool(property_id=1)
            
            # Verify
            assert len(result) == 2
            assert result[0]['id'] == 101
            assert result[1]['id'] == 102
    
    async def test_search_courts_with_sport_type_filter_on_property(self):
        """Test filtering courts by sport type for a specific property"""
        mock_property_details = {
            'success': True,
            'data': {
                'id': 1,
                'name': 'Sports Center',
                'courts': [
                    {
                        'id': 101,
                        'name': 'Tennis Court',
                        'sport_type': 'tennis'
                    },
                    {
                        'id': 102,
                        'name': 'Basketball Court',
                        'sport_type': 'basketball'
                    }
                ]
            }
        }
        
        with patch('app.agent.tools.court_tool._get_management_services') as mock_services, \
             patch('app.agent.tools.court_tool.call_sync_service') as mock_call:
            mock_services.return_value = (MagicMock(), MagicMock())
            mock_call.return_value = mock_property_details
            
            # Execute
            result = await search_courts_tool(property_id=1, sport_type='tennis')
            
            # Verify - should only return tennis court
            assert len(result) == 1
            assert result[0]['id'] == 101
            assert result[0]['sport_type'] == 'tennis'
    
    async def test_search_courts_no_results(self):
        """Test searching courts with no results"""
        mock_response = {
            'success': True,
            'data': {'items': []}
        }
        
        with patch('app.agent.tools.court_tool.call_sync_service') as mock_call:
            mock_call.return_value = mock_response
            
            # Execute
            result = await search_courts_tool(sport_type='squash')
            
            # Verify
            assert result == []
    
    async def test_search_courts_service_error(self):
        """Test handling service errors gracefully"""
        mock_response = {
            'success': False,
            'message': 'Database error'
        }
        
        with patch('app.agent.tools.court_tool.call_sync_service') as mock_call:
            mock_call.return_value = mock_response
            
            # Execute
            result = await search_courts_tool(sport_type='tennis')
            
            # Verify - should return empty list on error
            assert result == []
    
    async def test_search_courts_exception_handling(self):
        """Test exception handling in search_courts_tool"""
        with patch('app.agent.tools.court_tool.call_sync_service') as mock_call:
            mock_call.side_effect = Exception('Connection error')
            
            # Execute
            result = await search_courts_tool(sport_type='tennis')
            
            # Verify - should return empty list on exception
            assert result == []


@pytest.mark.asyncio
class TestGetCourtDetailsTool:
    """Tests for get_court_details_tool function"""
    
    async def test_get_court_details_success(self):
        """Test getting court details successfully"""
        mock_response = {
            'success': True,
            'data': {
                'id': 101,
                'name': 'Tennis Court 1',
                'sport_type': 'tennis',
                'description': 'Professional tennis court',
                'property': {
                    'id': 1,
                    'name': 'Sports Center',
                    'city': 'New York'
                },
                'pricing_rules': [
                    {
                        'id': 1,
                        'days': 'weekday',
                        'price_per_hour': 50.0
                    }
                ]
            }
        }
        
        with patch('app.agent.tools.court_tool._get_management_services') as mock_services, \
             patch('app.agent.tools.court_tool.call_sync_service') as mock_call:
            mock_services.return_value = (MagicMock(), MagicMock())
            mock_call.return_value = mock_response
            
            # Execute
            result = await get_court_details_tool(court_id=101)
            
            # Verify
            assert result is not None
            assert result['id'] == 101
            assert result['name'] == 'Tennis Court 1'
            assert result['sport_type'] == 'tennis'
            assert 'property' in result
            assert 'pricing_rules' in result
    
    async def test_get_court_details_not_found(self):
        """Test getting details for non-existent court"""
        mock_response = {
            'success': False,
            'message': 'Court not found'
        }
        
        with patch('app.agent.tools.court_tool.call_sync_service') as mock_call:
            mock_call.return_value = mock_response
            
            # Execute
            result = await get_court_details_tool(court_id=999)
            
            # Verify
            assert result is None
    
    async def test_get_court_details_exception(self):
        """Test exception handling in get_court_details_tool"""
        with patch('app.agent.tools.court_tool.call_sync_service') as mock_call:
            mock_call.side_effect = Exception('Database error')
            
            # Execute
            result = await get_court_details_tool(court_id=101)
            
            # Verify
            assert result is None


@pytest.mark.asyncio
class TestGetPropertyCourtsTool:
    """Tests for get_property_courts_tool function"""
    
    async def test_get_property_courts_with_owner(self):
        """Test getting property courts with owner verification"""
        mock_response = {
            'success': True,
            'data': [
                {
                    'id': 101,
                    'name': 'Tennis Court',
                    'sport_type': 'tennis'
                },
                {
                    'id': 102,
                    'name': 'Basketball Court',
                    'sport_type': 'basketball'
                }
            ]
        }
        
        with patch('app.agent.tools.court_tool._get_management_services') as mock_services, \
             patch('app.agent.tools.court_tool.call_sync_service') as mock_call:
            mock_services.return_value = (MagicMock(), MagicMock())
            mock_call.return_value = mock_response
            
            # Execute
            result = await get_property_courts_tool(property_id=1, owner_id=456)
            
            # Verify
            assert len(result) == 2
            assert result[0]['id'] == 101
            assert result[1]['id'] == 102
    
    async def test_get_property_courts_public_access(self):
        """Test getting property courts without owner (public access)"""
        mock_response = {
            'success': True,
            'data': {
                'id': 1,
                'name': 'Sports Center',
                'courts': [
                    {
                        'id': 101,
                        'name': 'Tennis Court',
                        'sport_type': 'tennis'
                    }
                ]
            }
        }
        
        with patch('app.agent.tools.court_tool._get_management_services') as mock_services, \
             patch('app.agent.tools.court_tool.call_sync_service') as mock_call:
            mock_services.return_value = (MagicMock(), MagicMock())
            mock_call.return_value = mock_response
            
            # Execute
            result = await get_property_courts_tool(property_id=1)
            
            # Verify
            assert len(result) == 1
            assert result[0]['id'] == 101
    
    async def test_get_property_courts_not_found(self):
        """Test getting courts for non-existent property"""
        mock_response = {
            'success': False,
            'message': 'Property not found'
        }
        
        with patch('app.agent.tools.court_tool.call_sync_service') as mock_call:
            mock_call.return_value = mock_response
            
            # Execute
            result = await get_property_courts_tool(property_id=999)
            
            # Verify
            assert result == []
    
    async def test_get_property_courts_exception(self):
        """Test exception handling in get_property_courts_tool"""
        with patch('app.agent.tools.court_tool.call_sync_service') as mock_call:
            mock_call.side_effect = Exception('Connection error')
            
            # Execute
            result = await get_property_courts_tool(property_id=1)
            
            # Verify
            assert result == []


class TestCourtToolsRegistry:
    """Tests for COURT_TOOLS registry"""
    
    def test_court_tools_registry_contains_all_tools(self):
        """Test that COURT_TOOLS registry contains all expected tools"""
        assert 'search_courts' in COURT_TOOLS
        assert 'get_court_details' in COURT_TOOLS
        assert 'get_property_courts' in COURT_TOOLS
    
    def test_court_tools_registry_functions_are_callable(self):
        """Test that all tools in registry are callable"""
        for tool_name, tool_func in COURT_TOOLS.items():
            assert callable(tool_func), f"{tool_name} should be callable"
