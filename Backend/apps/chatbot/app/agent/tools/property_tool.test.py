"""
Unit tests for property search and details tools.

Tests the property_tool module which provides tools for searching properties
and retrieving property details through the sync bridge.
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from app.agent.tools.property_tool import (
    search_properties_tool,
    get_property_details_tool,
    get_owner_properties_tool,
    PROPERTY_TOOLS
)


@pytest.mark.asyncio
class TestSearchPropertiesTool:
    """Tests for search_properties_tool function"""
    
    async def test_search_properties_success(self):
        """Test successful property search"""
        mock_result = {
            'success': True,
            'data': {
                'items': [
                    {
                        'id': 1,
                        'name': 'Downtown Sports Center',
                        'city': 'New York',
                        'state': 'NY',
                        'address': '123 Main St',
                        'amenities': ['parking', 'wifi'],
                        'maps_link': 'https://maps.example.com/1'
                    },
                    {
                        'id': 2,
                        'name': 'Westside Arena',
                        'city': 'New York',
                        'state': 'NY',
                        'address': '456 West Ave',
                        'amenities': ['parking'],
                        'maps_link': 'https://maps.example.com/2'
                    }
                ],
                'total': 2,
                'page': 1,
                'limit': 10
            }
        }
        
        with patch('app.agent.tools.property_tool.call_sync_service', new_callable=AsyncMock) as mock_call:
            mock_call.return_value = mock_result
            
            result = await search_properties_tool(
                owner_id="123",
                city="New York",
                sport_type="tennis"
            )
            
            assert len(result) == 2
            assert result[0]['name'] == 'Downtown Sports Center'
            assert result[1]['name'] == 'Westside Arena'
            
            # Verify call was made with correct parameters
            mock_call.assert_called_once()
            call_kwargs = mock_call.call_args[1]
            assert call_kwargs['city'] == 'New York'
            assert call_kwargs['sport_type'] == 'tennis'
    
    async def test_search_properties_no_results(self):
        """Test property search with no results"""
        mock_result = {
            'success': True,
            'data': {
                'items': [],
                'total': 0,
                'page': 1,
                'limit': 10
            }
        }
        
        with patch('app.agent.tools.property_tool.call_sync_service', new_callable=AsyncMock) as mock_call:
            mock_call.return_value = mock_result
            
            result = await search_properties_tool(
                owner_id="123",
                city="NonExistentCity"
            )
            
            assert len(result) == 0
    
    async def test_search_properties_service_failure(self):
        """Test property search when service returns failure"""
        mock_result = {
            'success': False,
            'message': 'Database error'
        }
        
        with patch('app.agent.tools.property_tool.call_sync_service', new_callable=AsyncMock) as mock_call:
            mock_call.return_value = mock_result
            
            result = await search_properties_tool(owner_id="123")
            
            assert len(result) == 0
    
    async def test_search_properties_exception(self):
        """Test property search when exception occurs"""
        with patch('app.agent.tools.property_tool.call_sync_service', new_callable=AsyncMock) as mock_call:
            mock_call.side_effect = Exception("Connection error")
            
            result = await search_properties_tool(owner_id="123")
            
            assert len(result) == 0
    
    async def test_search_properties_with_filters(self):
        """Test property search with multiple filters"""
        mock_result = {
            'success': True,
            'data': {
                'items': [{'id': 1, 'name': 'Test Property'}],
                'total': 1
            }
        }
        
        with patch('app.agent.tools.property_tool.call_sync_service', new_callable=AsyncMock) as mock_call:
            mock_call.return_value = mock_result
            
            result = await search_properties_tool(
                owner_id="123",
                city="Boston",
                sport_type="basketball",
                min_price=30.0,
                max_price=100.0,
                limit=5
            )
            
            assert len(result) == 1
            
            # Verify all filters were passed
            call_kwargs = mock_call.call_args[1]
            assert call_kwargs['city'] == 'Boston'
            assert call_kwargs['sport_type'] == 'basketball'
            assert call_kwargs['min_price'] == 30.0
            assert call_kwargs['max_price'] == 100.0
            assert call_kwargs['limit'] == 5


@pytest.mark.asyncio
class TestGetPropertyDetailsTool:
    """Tests for get_property_details_tool function"""
    
    async def test_get_property_details_with_owner(self):
        """Test getting property details with owner verification"""
        mock_result = {
            'success': True,
            'data': {
                'id': 1,
                'name': 'Downtown Sports Center',
                'description': 'Premier sports facility',
                'address': '123 Main St',
                'city': 'New York',
                'state': 'NY',
                'country': 'USA',
                'phone': '555-1234',
                'email': 'info@downtown.com',
                'amenities': ['parking', 'wifi', 'locker rooms'],
                'is_active': True,
                'courts': [
                    {
                        'id': 1,
                        'name': 'Court A',
                        'sport_type': 'tennis',
                        'is_active': True
                    }
                ]
            }
        }
        
        with patch('app.agent.tools.property_tool.call_sync_service', new_callable=AsyncMock) as mock_call:
            mock_call.return_value = mock_result
            
            result = await get_property_details_tool(
                property_id=1,
                owner_id="123"
            )
            
            assert result is not None
            assert result['name'] == 'Downtown Sports Center'
            assert len(result['courts']) == 1
            assert result['courts'][0]['sport_type'] == 'tennis'
    
    async def test_get_property_details_public(self):
        """Test getting property details without owner (public access)"""
        mock_result = {
            'success': True,
            'data': {
                'id': 1,
                'name': 'Public Property',
                'city': 'Boston',
                'courts': []
            }
        }
        
        with patch('app.agent.tools.property_tool.call_sync_service', new_callable=AsyncMock) as mock_call:
            mock_call.return_value = mock_result
            
            result = await get_property_details_tool(property_id=1)
            
            assert result is not None
            assert result['name'] == 'Public Property'
    
    async def test_get_property_details_not_found(self):
        """Test getting property details when property doesn't exist"""
        mock_result = {
            'success': False,
            'message': 'Property not found'
        }
        
        with patch('app.agent.tools.property_tool.call_sync_service', new_callable=AsyncMock) as mock_call:
            mock_call.return_value = mock_result
            
            result = await get_property_details_tool(property_id=999)
            
            assert result is None
    
    async def test_get_property_details_exception(self):
        """Test getting property details when exception occurs"""
        with patch('app.agent.tools.property_tool.call_sync_service', new_callable=AsyncMock) as mock_call:
            mock_call.side_effect = Exception("Database error")
            
            result = await get_property_details_tool(property_id=1)
            
            assert result is None


@pytest.mark.asyncio
class TestGetOwnerPropertiesTool:
    """Tests for get_owner_properties_tool function"""
    
    async def test_get_owner_properties_success(self):
        """Test successfully getting owner's properties"""
        mock_result = {
            'success': True,
            'data': [
                {
                    'id': 1,
                    'name': 'Property 1',
                    'city': 'New York',
                    'state': 'NY',
                    'is_active': True
                },
                {
                    'id': 2,
                    'name': 'Property 2',
                    'city': 'Boston',
                    'state': 'MA',
                    'is_active': True
                }
            ]
        }
        
        with patch('app.agent.tools.property_tool.call_sync_service', new_callable=AsyncMock) as mock_call:
            mock_call.return_value = mock_result
            
            result = await get_owner_properties_tool(owner_id="123")
            
            assert len(result) == 2
            assert result[0]['name'] == 'Property 1'
            assert result[1]['name'] == 'Property 2'
    
    async def test_get_owner_properties_no_properties(self):
        """Test getting properties for owner with no properties"""
        mock_result = {
            'success': True,
            'data': []
        }
        
        with patch('app.agent.tools.property_tool.call_sync_service', new_callable=AsyncMock) as mock_call:
            mock_call.return_value = mock_result
            
            result = await get_owner_properties_tool(owner_id="123")
            
            assert len(result) == 0
    
    async def test_get_owner_properties_service_failure(self):
        """Test getting owner properties when service fails"""
        mock_result = {
            'success': False,
            'message': 'Owner not found'
        }
        
        with patch('app.agent.tools.property_tool.call_sync_service', new_callable=AsyncMock) as mock_call:
            mock_call.return_value = mock_result
            
            result = await get_owner_properties_tool(owner_id="999")
            
            assert len(result) == 0
    
    async def test_get_owner_properties_exception(self):
        """Test getting owner properties when exception occurs"""
        with patch('app.agent.tools.property_tool.call_sync_service', new_callable=AsyncMock) as mock_call:
            mock_call.side_effect = Exception("Connection error")
            
            result = await get_owner_properties_tool(owner_id="123")
            
            assert len(result) == 0


class TestPropertyToolsRegistry:
    """Tests for PROPERTY_TOOLS registry"""
    
    def test_property_tools_registry_contains_all_tools(self):
        """Test that registry contains all expected tools"""
        assert 'search_properties' in PROPERTY_TOOLS
        assert 'get_property_details' in PROPERTY_TOOLS
        assert 'get_owner_properties' in PROPERTY_TOOLS
    
    def test_property_tools_registry_functions_are_callable(self):
        """Test that all registered tools are callable"""
        for tool_name, tool_func in PROPERTY_TOOLS.items():
            assert callable(tool_func), f"{tool_name} should be callable"
