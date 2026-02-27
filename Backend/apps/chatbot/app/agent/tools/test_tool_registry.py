"""
Tests for the tool registry and initialization.

This module tests the tool registry functionality including:
- Tool registry structure
- Tool initialization
- Tool retrieval
- Tool listing
"""

import pytest
from app.agent.tools import (
    TOOL_REGISTRY,
    initialize_tools,
    get_tool,
    list_tools,
)


def test_tool_registry_structure():
    """Test that TOOL_REGISTRY contains all expected tools."""
    # Expected tool categories and counts
    expected_tools = {
        # Property tools (3)
        "search_properties",
        "get_property_details",
        "get_owner_properties",
        
        # Court tools (3)
        "search_courts",
        "get_court_details",
        "get_property_courts",
        
        # Availability tools (2)
        "check_availability",
        "get_available_slots",
        
        # Pricing tools (2)
        "get_pricing",
        "calculate_total_price",
        
        # Booking tools (3)
        "create_booking",
        "get_booking_details",
        "cancel_booking",
    }
    
    # Verify all expected tools are present
    assert set(TOOL_REGISTRY.keys()) == expected_tools
    
    # Verify total count
    assert len(TOOL_REGISTRY) == 13


def test_tool_registry_callables():
    """Test that all tools in registry are callable."""
    for tool_name, tool_func in TOOL_REGISTRY.items():
        assert callable(tool_func), f"Tool '{tool_name}' is not callable"


def test_initialize_tools_basic():
    """Test basic tool initialization without dependencies."""
    tools = initialize_tools()
    
    # Should return a copy of the registry
    assert len(tools) == len(TOOL_REGISTRY)
    assert set(tools.keys()) == set(TOOL_REGISTRY.keys())
    
    # Should be a copy, not the same object
    assert tools is not TOOL_REGISTRY


def test_initialize_tools_with_dependencies():
    """Test tool initialization with dependencies (currently ignored)."""
    # Pass some mock dependencies
    tools = initialize_tools(
        db_session="mock_session",
        config={"key": "value"}
    )
    
    # Should still return all tools
    assert len(tools) == len(TOOL_REGISTRY)


def test_get_tool_valid():
    """Test retrieving a valid tool by name."""
    # Test getting a property tool
    search_tool = get_tool("search_properties")
    assert callable(search_tool)
    
    # Test getting a booking tool
    booking_tool = get_tool("create_booking")
    assert callable(booking_tool)


def test_get_tool_invalid():
    """Test retrieving an invalid tool raises KeyError."""
    with pytest.raises(KeyError) as exc_info:
        get_tool("nonexistent_tool")
    
    # Error message should list available tools
    assert "not found in registry" in str(exc_info.value)
    assert "Available tools:" in str(exc_info.value)


def test_list_tools():
    """Test listing all available tools."""
    tools = list_tools()
    
    # Should return a list
    assert isinstance(tools, list)
    
    # Should contain all tool names
    assert len(tools) == 13
    assert "search_properties" in tools
    assert "create_booking" in tools
    assert "get_available_slots" in tools


def test_tool_categories():
    """Test that tools are properly categorized."""
    tools = list_tools()
    
    # Property tools (excluding get_property_courts which is a court tool)
    property_tools = [
        t for t in tools 
        if ("property" in t or "properties" in t) and "court" not in t
    ]
    assert len(property_tools) == 3
    
    # Court tools
    court_tools = [t for t in tools if "court" in t]
    assert len(court_tools) == 3
    
    # Availability tools
    availability_tools = [t for t in tools if "availability" in t or "slots" in t]
    assert len(availability_tools) == 2
    
    # Pricing tools
    pricing_tools = [t for t in tools if "pricing" in t or "price" in t]
    assert len(pricing_tools) == 2
    
    # Booking tools
    booking_tools = [t for t in tools if "booking" in t]
    assert len(booking_tools) == 3


def test_tool_registry_immutability():
    """Test that initialize_tools returns a copy, not the original."""
    tools1 = initialize_tools()
    tools2 = initialize_tools()
    
    # Should be different objects
    assert tools1 is not tools2
    
    # But should have the same content
    assert tools1.keys() == tools2.keys()


def test_all_tools_are_async():
    """Test that all tools are async functions (coroutines)."""
    import inspect
    
    for tool_name, tool_func in TOOL_REGISTRY.items():
        assert inspect.iscoroutinefunction(tool_func), \
            f"Tool '{tool_name}' is not an async function"
