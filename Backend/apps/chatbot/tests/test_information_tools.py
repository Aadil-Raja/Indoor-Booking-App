"""
Unit tests for information tools.

This module tests all information tools used by the Information Node,
including property search, property details, court details, availability,
pricing, and media retrieval.

Requirements: 1.1-1.5, 2.1-2.5, 3.1-3.5, 4.1-4.5, 5.1-5.5, 6.1-6.5
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import date, datetime

# Import tools to test
import sys
from pathlib import Path

# Add Backend path for imports
backend_path = Path(__file__).parent.parent.parent.parent
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

from apps.chatbot.app.agent.tools.information_tools import (
    search_properties_tool,
    get_property_details_tool,
    get_court_details_tool,
    get_court_availability_tool,
    get_court_pricing_tool,
    get_property_media_tool,
    get_court_media_tool,
)


# Fixtures for mock data

@pytest.fixture
def mock_properties():
    """Mock property search results."""
    return [
        {
            "id": 6,
            "name": "Downtown Tennis Center",
            "city": "New York",
            "address": "123 Main St",
            "amenities": ["parking", "locker_rooms"]
        },
        {
            "id": 12,
            "name": "Uptown Sports Complex",
            "city": "New York",
            "address": "456 Park Ave",
            "amenities": ["parking", "cafe"]
        }
    ]


@pytest.fixture
def mock_property_details():
    """Mock property details."""
    return {
        "id": 6,
        "name": "Downtown Tennis Center",
        "description": "Premier tennis facility",
        "address": "123 Main St",
        "city": "New York",
        "state": "NY",
        "country": "USA",
        "phone": "555-1234",
        "email": "info@dtc.com",
        "maps_link": "https://maps.google.com/...",
        "amenities": ["parking", "locker_rooms", "pro_shop"],
        "courts": [
            {
                "id": 23,
                "name": "Court 1",
                "sport_type": "tennis"
            }
        ],
        "media": [
            {
                "id": 1,
                "media_type": "photo",
                "url": "https://example.com/photo1.jpg",
                "caption": "Main entrance"
            }
        ]
    }


@pytest.fixture
def mock_court_details():
    """Mock court details."""
    return {
        "id": 23,
        "name": "Court 1",
        "sport_type": "tennis",
        "description": "Professional tennis court",
        "specifications": "Hard court surface",
        "amenities": ["lighting", "net"],
        "property": {
            "id": 6,
            "name": "Downtown Tennis Center"
        },
        "pricing_rules": [
            {
                "id": 1,
                "start_time": "09:00:00",
                "end_time": "17:00:00",
                "price_per_hour": 50.0,
                "label": "Daytime"
            }
        ],
        "media": [
            {
                "id": 2,
                "media_type": "photo",
                "url": "https://example.com/court1.jpg",
                "caption": "Court view"
            }
        ]
    }


@pytest.fixture
def mock_availability():
    """Mock availability data."""
    return {
        "date": "2026-03-10",
        "court_id": 23,
        "court_name": "Court 1",
        "available_slots": [
            {
                "start_time": "09:00:00",
                "end_time": "10:00:00",
                "price_per_hour": 50.0,
                "label": "Daytime"
            },
            {
                "start_time": "10:00:00",
                "end_time": "11:00:00",
                "price_per_hour": 50.0,
                "label": "Daytime"
            }
        ]
    }


@pytest.fixture
def mock_pricing():
    """Mock pricing data."""
    return {
        "date": "2026-03-10",
        "day_of_week": 1,  # Tuesday
        "pricing": [
            {
                "start_time": "09:00:00",
                "end_time": "17:00:00",
                "price_per_hour": 50.0,
                "label": "Daytime"
            },
            {
                "start_time": "17:00:00",
                "end_time": "22:00:00",
                "price_per_hour": 75.0,
                "label": "Evening"
            }
        ]
    }


# Tests for search_properties_tool

@pytest.mark.asyncio
async def test_search_properties_with_sport_type(mock_properties):
    """Test searching properties by sport type."""
    # Mock both _get_public_service and call_sync_service
    mock_service = MagicMock()
    
    with patch('apps.chatbot.app.agent.tools.information_tools._get_public_service', return_value=mock_service):
        with patch('apps.chatbot.app.agent.tools.information_tools.call_sync_service') as mock_call:
            mock_call.return_value = {
                'success': True,
                'data': {
                    'items': mock_properties
                }
            }
            
            result = await search_properties_tool(sport_type="tennis", limit=10)
            
            assert len(result) == 2
            assert result[0]["id"] == 6
            assert result[0]["name"] == "Downtown Tennis Center"
            assert result[1]["id"] == 12
            mock_call.assert_called_once()


@pytest.mark.asyncio
async def test_search_properties_with_city(mock_properties):
    """Test searching properties by city."""
    mock_service = MagicMock()
    
    with patch('apps.chatbot.app.agent.tools.information_tools._get_public_service', return_value=mock_service):
        with patch('apps.chatbot.app.agent.tools.information_tools.call_sync_service') as mock_call:
            mock_call.return_value = {
                'success': True,
                'data': {
                    'items': mock_properties
                }
            }
            
            result = await search_properties_tool(city="New York", limit=10)
            
            assert len(result) == 2
            assert all(p["city"] == "New York" for p in result)
            mock_call.assert_called_once()


@pytest.mark.asyncio
async def test_search_properties_with_price_range(mock_properties):
    """Test searching properties with price range."""
    mock_service = MagicMock()
    
    with patch('apps.chatbot.app.agent.tools.information_tools._get_public_service', return_value=mock_service):
        with patch('apps.chatbot.app.agent.tools.information_tools.call_sync_service') as mock_call:
            mock_call.return_value = {
                'success': True,
                'data': {
                    'items': mock_properties
                }
            }
            
            result = await search_properties_tool(
                min_price=30.0,
                max_price=100.0,
                limit=10
            )
            
            assert len(result) == 2
            mock_call.assert_called_once()


@pytest.mark.asyncio
async def test_search_properties_no_results():
    """Test searching properties with no results."""
    mock_service = MagicMock()
    
    with patch('apps.chatbot.app.agent.tools.information_tools._get_public_service', return_value=mock_service):
        with patch('apps.chatbot.app.agent.tools.information_tools.call_sync_service') as mock_call:
            mock_call.return_value = {
                'success': True,
                'data': {
                    'items': []
                }
            }
            
            result = await search_properties_tool(sport_type="cricket", limit=10)
            
            assert len(result) == 0
            mock_call.assert_called_once()


@pytest.mark.asyncio
async def test_search_properties_service_failure():
    """Test handling of service failure in property search."""
    mock_service = MagicMock()
    
    with patch('apps.chatbot.app.agent.tools.information_tools._get_public_service', return_value=mock_service):
        with patch('apps.chatbot.app.agent.tools.information_tools.call_sync_service') as mock_call:
            mock_call.return_value = {
                'success': False,
                'message': 'Database error'
            }
            
            result = await search_properties_tool(sport_type="tennis", limit=10)
            
            assert len(result) == 0
            mock_call.assert_called_once()


@pytest.mark.asyncio
async def test_search_properties_exception():
    """Test handling of exception in property search."""
    mock_service = MagicMock()
    
    with patch('apps.chatbot.app.agent.tools.information_tools._get_public_service', return_value=mock_service):
        with patch('apps.chatbot.app.agent.tools.information_tools.call_sync_service') as mock_call:
            mock_call.side_effect = Exception("Connection error")
            
            result = await search_properties_tool(sport_type="tennis", limit=10)
            
            assert len(result) == 0
            mock_call.assert_called_once()


# Tests for get_property_details_tool

@pytest.mark.asyncio
async def test_get_property_details_valid_id(mock_property_details):
    """Test getting property details with valid ID."""
    mock_service = MagicMock()
    
    with patch('apps.chatbot.app.agent.tools.information_tools._get_public_service', return_value=mock_service):
        with patch('apps.chatbot.app.agent.tools.information_tools.call_sync_service') as mock_call:
            mock_call.return_value = {
                'success': True,
                'data': mock_property_details
            }
            
            result = await get_property_details_tool(property_id=6)
            
            assert result is not None
            assert result["id"] == 6
            assert result["name"] == "Downtown Tennis Center"
            assert "courts" in result
            assert "media" in result
            assert len(result["courts"]) == 1
            mock_call.assert_called_once()


@pytest.mark.asyncio
async def test_get_property_details_invalid_id():
    """Test getting property details with invalid ID."""
    mock_service = MagicMock()
    
    with patch('apps.chatbot.app.agent.tools.information_tools._get_public_service', return_value=mock_service):
        with patch('apps.chatbot.app.agent.tools.information_tools.call_sync_service') as mock_call:
            mock_call.return_value = {
                'success': False,
                'message': 'Property not found'
            }
            
            result = await get_property_details_tool(property_id=999)
            
            assert result is None
            mock_call.assert_called_once()


@pytest.mark.asyncio
async def test_get_property_details_exception():
    """Test handling of exception in property details."""
    mock_service = MagicMock()
    
    with patch('apps.chatbot.app.agent.tools.information_tools._get_public_service', return_value=mock_service):
        with patch('apps.chatbot.app.agent.tools.information_tools.call_sync_service') as mock_call:
            mock_call.side_effect = Exception("Database error")
            
            result = await get_property_details_tool(property_id=6)
            
            assert result is None
            mock_call.assert_called_once()


# Tests for get_court_details_tool

@pytest.mark.asyncio
async def test_get_court_details_valid_id(mock_court_details):
    """Test getting court details with valid ID."""
    mock_service = MagicMock()
    
    with patch('apps.chatbot.app.agent.tools.information_tools._get_public_service', return_value=mock_service):
        with patch('apps.chatbot.app.agent.tools.information_tools.call_sync_service') as mock_call:
            mock_call.return_value = {
                'success': True,
                'data': mock_court_details
            }
            
            result = await get_court_details_tool(court_id=23)
            
            assert result is not None
            assert result["id"] == 23
            assert result["name"] == "Court 1"
            assert result["sport_type"] == "tennis"
            assert "pricing_rules" in result
            assert "media" in result
            assert len(result["pricing_rules"]) == 1
            mock_call.assert_called_once()


@pytest.mark.asyncio
async def test_get_court_details_invalid_id():
    """Test getting court details with invalid ID."""
    mock_service = MagicMock()
    
    with patch('apps.chatbot.app.agent.tools.information_tools._get_public_service', return_value=mock_service):
        with patch('apps.chatbot.app.agent.tools.information_tools.call_sync_service') as mock_call:
            mock_call.return_value = {
                'success': False,
                'message': 'Court not found'
            }
            
            result = await get_court_details_tool(court_id=999)
            
            assert result is None
            mock_call.assert_called_once()


@pytest.mark.asyncio
async def test_get_court_details_exception():
    """Test handling of exception in court details."""
    mock_service = MagicMock()
    
    with patch('apps.chatbot.app.agent.tools.information_tools._get_public_service', return_value=mock_service):
        with patch('apps.chatbot.app.agent.tools.information_tools.call_sync_service') as mock_call:
            mock_call.side_effect = Exception("Database error")
            
            result = await get_court_details_tool(court_id=23)
            
            assert result is None
            mock_call.assert_called_once()


# Tests for get_court_availability_tool

@pytest.mark.asyncio
async def test_get_court_availability_valid_inputs(mock_availability):
    """Test getting court availability with valid inputs."""
    mock_service = MagicMock()
    
    with patch('apps.chatbot.app.agent.tools.information_tools._get_public_service', return_value=mock_service):
        with patch('apps.chatbot.app.agent.tools.information_tools.call_sync_service') as mock_call:
            mock_call.return_value = {
                'success': True,
                'data': mock_availability
            }
            
            result = await get_court_availability_tool(
                court_id=23,
                date_val="2026-03-10"
            )
            
            assert result is not None
            assert result["court_id"] == 23
            assert result["date"] == "2026-03-10"
            assert "available_slots" in result
            assert len(result["available_slots"]) == 2
            mock_call.assert_called_once()


@pytest.mark.asyncio
async def test_get_court_availability_no_slots():
    """Test getting court availability with no available slots."""
    mock_service = MagicMock()
    
    with patch('apps.chatbot.app.agent.tools.information_tools._get_public_service', return_value=mock_service):
        with patch('apps.chatbot.app.agent.tools.information_tools.call_sync_service') as mock_call:
            mock_call.return_value = {
                'success': True,
                'data': {
                    "date": "2026-03-10",
                    "court_id": 23,
                    "court_name": "Court 1",
                    "available_slots": []
                }
            }
            
            result = await get_court_availability_tool(
                court_id=23,
                date_val="2026-03-10"
            )
            
            assert result is not None
            assert len(result["available_slots"]) == 0
            mock_call.assert_called_once()


@pytest.mark.asyncio
async def test_get_court_availability_invalid_court():
    """Test getting availability for invalid court ID."""
    mock_service = MagicMock()
    
    with patch('apps.chatbot.app.agent.tools.information_tools._get_public_service', return_value=mock_service):
        with patch('apps.chatbot.app.agent.tools.information_tools.call_sync_service') as mock_call:
            mock_call.return_value = {
                'success': False,
                'message': 'Court not found'
            }
            
            result = await get_court_availability_tool(
                court_id=999,
                date_val="2026-03-10"
            )
            
            assert result is None
            mock_call.assert_called_once()


@pytest.mark.asyncio
async def test_get_court_availability_exception():
    """Test handling of exception in availability check."""
    mock_service = MagicMock()
    
    with patch('apps.chatbot.app.agent.tools.information_tools._get_public_service', return_value=mock_service):
        with patch('apps.chatbot.app.agent.tools.information_tools.call_sync_service') as mock_call:
            mock_call.side_effect = Exception("Database error")
            
            result = await get_court_availability_tool(
                court_id=23,
                date_val="2026-03-10"
            )
            
            assert result is None
            mock_call.assert_called_once()


# Tests for get_court_pricing_tool

@pytest.mark.asyncio
async def test_get_court_pricing_valid_inputs(mock_pricing):
    """Test getting court pricing with valid inputs."""
    mock_service = MagicMock()
    
    with patch('apps.chatbot.app.agent.tools.information_tools._get_public_service', return_value=mock_service):
        with patch('apps.chatbot.app.agent.tools.information_tools.call_sync_service') as mock_call:
            mock_call.return_value = {
                'success': True,
                'data': mock_pricing
            }
            
            result = await get_court_pricing_tool(
                court_id=23,
                date_val="2026-03-10"
            )
            
            assert result is not None
            assert result["date"] == "2026-03-10"
            assert result["day_of_week"] == 1
            assert "pricing" in result
            assert len(result["pricing"]) == 2
            assert result["pricing"][0]["price_per_hour"] == 50.0
            mock_call.assert_called_once()


@pytest.mark.asyncio
async def test_get_court_pricing_no_pricing():
    """Test getting pricing when no pricing configured."""
    mock_service = MagicMock()
    
    with patch('apps.chatbot.app.agent.tools.information_tools._get_public_service', return_value=mock_service):
        with patch('apps.chatbot.app.agent.tools.information_tools.call_sync_service') as mock_call:
            mock_call.return_value = {
                'success': False,
                'message': 'No pricing configured'
            }
            
            result = await get_court_pricing_tool(
                court_id=23,
                date_val="2026-03-10"
            )
            
            assert result is None
            mock_call.assert_called_once()


@pytest.mark.asyncio
async def test_get_court_pricing_invalid_court():
    """Test getting pricing for invalid court ID."""
    mock_service = MagicMock()
    
    with patch('apps.chatbot.app.agent.tools.information_tools._get_public_service', return_value=mock_service):
        with patch('apps.chatbot.app.agent.tools.information_tools.call_sync_service') as mock_call:
            mock_call.return_value = {
                'success': False,
                'message': 'Court not found'
            }
            
            result = await get_court_pricing_tool(
                court_id=999,
                date_val="2026-03-10"
            )
            
            assert result is None
            mock_call.assert_called_once()


@pytest.mark.asyncio
async def test_get_court_pricing_exception():
    """Test handling of exception in pricing retrieval."""
    mock_service = MagicMock()
    
    with patch('apps.chatbot.app.agent.tools.information_tools._get_public_service', return_value=mock_service):
        with patch('apps.chatbot.app.agent.tools.information_tools.call_sync_service') as mock_call:
            mock_call.side_effect = Exception("Database error")
            
            result = await get_court_pricing_tool(
                court_id=23,
                date_val="2026-03-10"
            )
            
            assert result is None
            mock_call.assert_called_once()


# Tests for get_property_media_tool

@pytest.mark.asyncio
async def test_get_property_media_valid_id(mock_property_details):
    """Test getting property media with valid ID."""
    with patch('apps.chatbot.app.agent.tools.information_tools.get_property_details_tool') as mock_details:
        mock_details.return_value = mock_property_details
        
        result = await get_property_media_tool(property_id=6, limit=5)
        
        assert len(result) == 1
        assert result[0]["media_type"] == "photo"
        assert result[0]["url"] == "https://example.com/photo1.jpg"
        mock_details.assert_called_once_with(property_id=6)


@pytest.mark.asyncio
async def test_get_property_media_with_limit():
    """Test getting property media with limit."""
    mock_property_with_media = {
        "id": 6,
        "name": "Test Property",
        "media": [
            {"id": i, "media_type": "photo", "url": f"https://example.com/photo{i}.jpg"}
            for i in range(10)
        ]
    }
    
    with patch('apps.chatbot.app.agent.tools.information_tools.get_property_details_tool') as mock_details:
        mock_details.return_value = mock_property_with_media
        
        result = await get_property_media_tool(property_id=6, limit=3)
        
        assert len(result) == 3
        mock_details.assert_called_once_with(property_id=6)


@pytest.mark.asyncio
async def test_get_property_media_no_media():
    """Test getting property media when no media exists."""
    mock_property_no_media = {
        "id": 6,
        "name": "Test Property",
        "media": []
    }
    
    with patch('apps.chatbot.app.agent.tools.information_tools.get_property_details_tool') as mock_details:
        mock_details.return_value = mock_property_no_media
        
        result = await get_property_media_tool(property_id=6, limit=5)
        
        assert len(result) == 0
        mock_details.assert_called_once_with(property_id=6)


@pytest.mark.asyncio
async def test_get_property_media_invalid_property():
    """Test getting media for invalid property ID."""
    with patch('apps.chatbot.app.agent.tools.information_tools.get_property_details_tool') as mock_details:
        mock_details.return_value = None
        
        result = await get_property_media_tool(property_id=999, limit=5)
        
        assert len(result) == 0
        mock_details.assert_called_once_with(property_id=999)


@pytest.mark.asyncio
async def test_get_property_media_exception():
    """Test handling of exception in property media retrieval."""
    with patch('apps.chatbot.app.agent.tools.information_tools.get_property_details_tool') as mock_details:
        mock_details.side_effect = Exception("Database error")
        
        result = await get_property_media_tool(property_id=6, limit=5)
        
        assert len(result) == 0
        mock_details.assert_called_once_with(property_id=6)


# Tests for get_court_media_tool

@pytest.mark.asyncio
async def test_get_court_media_valid_id(mock_court_details):
    """Test getting court media with valid ID."""
    with patch('apps.chatbot.app.agent.tools.information_tools.get_court_details_tool') as mock_details:
        mock_details.return_value = mock_court_details
        
        result = await get_court_media_tool(court_id=23, limit=5)
        
        assert len(result) == 1
        assert result[0]["media_type"] == "photo"
        assert result[0]["url"] == "https://example.com/court1.jpg"
        mock_details.assert_called_once_with(court_id=23)


@pytest.mark.asyncio
async def test_get_court_media_with_limit():
    """Test getting court media with limit."""
    mock_court_with_media = {
        "id": 23,
        "name": "Test Court",
        "media": [
            {"id": i, "media_type": "photo", "url": f"https://example.com/court{i}.jpg"}
            for i in range(10)
        ]
    }
    
    with patch('apps.chatbot.app.agent.tools.information_tools.get_court_details_tool') as mock_details:
        mock_details.return_value = mock_court_with_media
        
        result = await get_court_media_tool(court_id=23, limit=3)
        
        assert len(result) == 3
        mock_details.assert_called_once_with(court_id=23)


@pytest.mark.asyncio
async def test_get_court_media_no_media():
    """Test getting court media when no media exists."""
    mock_court_no_media = {
        "id": 23,
        "name": "Test Court",
        "media": []
    }
    
    with patch('apps.chatbot.app.agent.tools.information_tools.get_court_details_tool') as mock_details:
        mock_details.return_value = mock_court_no_media
        
        result = await get_court_media_tool(court_id=23, limit=5)
        
        assert len(result) == 0
        mock_details.assert_called_once_with(court_id=23)


@pytest.mark.asyncio
async def test_get_court_media_invalid_court():
    """Test getting media for invalid court ID."""
    with patch('apps.chatbot.app.agent.tools.information_tools.get_court_details_tool') as mock_details:
        mock_details.return_value = None
        
        result = await get_court_media_tool(court_id=999, limit=5)
        
        assert len(result) == 0
        mock_details.assert_called_once_with(court_id=999)


@pytest.mark.asyncio
async def test_get_court_media_exception():
    """Test handling of exception in court media retrieval."""
    with patch('apps.chatbot.app.agent.tools.information_tools.get_court_details_tool') as mock_details:
        mock_details.side_effect = Exception("Database error")
        
        result = await get_court_media_tool(court_id=23, limit=5)
        
        assert len(result) == 0
        mock_details.assert_called_once_with(court_id=23)
