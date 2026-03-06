"""
Unit tests for select_property node with auto-selection support.

This module tests the property selection node implementation including:
- Skipping when property already selected
- Auto-selection when single property exists
- Presenting options when multiple properties exist
- Error handling when no properties exist
- On-demand property fetching and caching

Requirements: 5.2, 5.3, 6.1, 6.2, 6.4, 7.1, 8.2
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from app.agent.nodes.booking.select_property import select_property


@pytest.mark.asyncio
async def test_skip_when_property_already_selected():
    """
    Test that property selection is skipped when property_id exists in flow_state.
    
    Validates Requirement 7.1: Skip property selection step when Flow_State contains property_id
    """
    # Arrange
    state = {
        "chat_id": "test-123",
        "owner_profile_id": "456",
        "flow_state": {
            "property_id": 1,
            "property_name": "Sports Center"
        }
    }
    tools = {}
    
    # Act
    result = await select_property(state, tools)
    
    # Assert
    assert result["next_node"] == "select_court"
    assert result["flow_state"]["property_id"] == 1


@pytest.mark.asyncio
async def test_auto_select_single_property():
    """
    Test that single property is auto-selected and stored in flow_state.
    
    Validates Requirements:
    - 6.1: Auto-select single property and store in Flow_State
    - 6.2: Skip property selection question when auto-selected
    - 8.2: Update booking_step field when step is completed
    """
    # Arrange
    state = {
        "chat_id": "test-123",
        "owner_profile_id": "456",
        "flow_state": {}
    }
    
    # Mock get_owner_properties_tool
    mock_properties = [
        {"id": 1, "name": "Downtown Sports Center"}
    ]
    
    # Create mock tools
    tools = {}
    
    # Mock the get_owner_properties_tool function
    import app.agent.nodes.booking.select_property as select_property_module
    original_get_owner_properties = select_property_module.get_owner_properties_tool
    select_property_module.get_owner_properties_tool = AsyncMock(return_value=mock_properties)
    
    try:
        # Act
        result = await select_property(state, tools)
        
        # Assert
        assert result["flow_state"]["property_id"] == 1
        assert result["flow_state"]["property_name"] == "Downtown Sports Center"
        assert result["flow_state"]["booking_step"] == "property_selected"
        assert result["next_node"] == "select_court"
        assert result["response_type"] == "text"
        
    finally:
        # Restore original function
        select_property_module.get_owner_properties_tool = original_get_owner_properties


@pytest.mark.asyncio
async def test_present_options_for_multiple_properties():
    """
    Test that multiple properties are presented as button options.
    
    Validates that when multiple properties exist, they are presented to the user
    for selection.
    """
    # Arrange
    state = {
        "chat_id": "test-123",
        "owner_profile_id": "456",
        "flow_state": {}
    }
    
    # Mock get_owner_properties_tool
    mock_properties = [
        {"id": 1, "name": "Downtown Sports Center"},
        {"id": 2, "name": "Uptown Arena"},
        {"id": 3, "name": "Westside Courts"}
    ]
    
    # Create mock tools
    tools = {}
    
    # Mock the get_owner_properties_tool function
    import app.agent.nodes.booking.select_property as select_property_module
    original_get_owner_properties = select_property_module.get_owner_properties_tool
    select_property_module.get_owner_properties_tool = AsyncMock(return_value=mock_properties)
    
    try:
        # Act
        result = await select_property(state, tools)
        
        # Assert
        assert result["response_type"] == "button"
        assert "buttons" in result["response_metadata"]
        assert len(result["response_metadata"]["buttons"]) == 3
        assert result["response_metadata"]["buttons"][0]["id"] == "1"
        assert result["response_metadata"]["buttons"][0]["text"] == "Downtown Sports Center"
        assert result["next_node"] == "wait_for_selection"
        assert result["flow_state"]["booking_step"] == "awaiting_property_selection"
        
    finally:
        # Restore original function
        select_property_module.get_owner_properties_tool = original_get_owner_properties


@pytest.mark.asyncio
async def test_error_when_no_properties():
    """
    Test that error message is returned when no properties exist.
    
    Validates that the system handles the case where owner has no properties.
    """
    # Arrange
    state = {
        "chat_id": "test-123",
        "owner_profile_id": "456",
        "flow_state": {}
    }
    
    # Mock get_owner_properties_tool to return empty list
    mock_properties = []
    
    # Create mock tools
    tools = {}
    
    # Mock the get_owner_properties_tool function
    import app.agent.nodes.booking.select_property as select_property_module
    original_get_owner_properties = select_property_module.get_owner_properties_tool
    select_property_module.get_owner_properties_tool = AsyncMock(return_value=mock_properties)
    
    try:
        # Act
        result = await select_property(state, tools)
        
        # Assert
        assert result["response_type"] == "text"
        assert "don't have any properties" in result["response_content"]
        assert result["next_node"] == "end"
        
    finally:
        # Restore original function
        select_property_module.get_owner_properties_tool = original_get_owner_properties


@pytest.mark.asyncio
async def test_use_cached_properties():
    """
    Test that cached properties in flow_state are used without fetching.
    
    Validates Requirements:
    - 5.2: Use cached data if owner_properties exists in flow_state
    - 5.3: Cache Owner_Properties in Flow_State
    """
    # Arrange
    cached_properties = [
        {"id": 1, "name": "Cached Sports Center"}
    ]
    
    state = {
        "chat_id": "test-123",
        "owner_profile_id": "456",
        "flow_state": {
            "owner_properties": cached_properties
        }
    }
    
    # Create mock tools (should not be called)
    tools = {}
    
    # Mock the get_owner_properties_tool function to track if it's called
    import app.agent.nodes.booking.select_property as select_property_module
    original_get_owner_properties = select_property_module.get_owner_properties_tool
    mock_get_owner_properties = AsyncMock(return_value=[])
    select_property_module.get_owner_properties_tool = mock_get_owner_properties
    
    try:
        # Act
        result = await select_property(state, tools)
        
        # Assert
        # Should use cached properties and auto-select
        assert result["flow_state"]["property_id"] == 1
        assert result["flow_state"]["property_name"] == "Cached Sports Center"
        assert result["next_node"] == "select_court"
        
        # Verify get_owner_properties_tool was NOT called
        mock_get_owner_properties.assert_not_called()
        
    finally:
        # Restore original function
        select_property_module.get_owner_properties_tool = original_get_owner_properties


@pytest.mark.asyncio
async def test_cache_fetched_properties():
    """
    Test that fetched properties are cached in flow_state.
    
    Validates Requirement 5.3: Cache Owner_Properties in Flow_State
    """
    # Arrange
    state = {
        "chat_id": "test-123",
        "owner_profile_id": "456",
        "flow_state": {}
    }
    
    # Mock get_owner_properties_tool
    mock_properties = [
        {"id": 1, "name": "Sports Center"}
    ]
    
    # Create mock tools
    tools = {}
    
    # Mock the get_owner_properties_tool function
    import app.agent.nodes.booking.select_property as select_property_module
    original_get_owner_properties = select_property_module.get_owner_properties_tool
    select_property_module.get_owner_properties_tool = AsyncMock(return_value=mock_properties)
    
    try:
        # Act
        result = await select_property(state, tools)
        
        # Assert
        # Verify properties were cached in flow_state
        assert "owner_properties" in result["flow_state"]
        assert result["flow_state"]["owner_properties"] == mock_properties
        
    finally:
        # Restore original function
        select_property_module.get_owner_properties_tool = original_get_owner_properties
