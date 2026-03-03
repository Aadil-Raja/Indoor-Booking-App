"""
Agent tools package.

This package contains tools that the LangGraph agent can use to interact
with external services and data sources.

The tool registry provides a centralized dictionary of all available tools
that can be used by the LangGraph agent. Tools are organized by category:
- Property tools: Search and retrieve property information
- Court tools: Search and retrieve court information
- Availability tools: Check availability and get available time slots
- Pricing tools: Get pricing information and calculate costs
- Booking tools: Create, retrieve, and cancel bookings

Usage:
    from app.agent.tools import initialize_tools
    
    # Initialize tools with dependencies
    tools = initialize_tools()
    
    # Access individual tools
    properties = await tools["search_properties"](owner_id="123", city="New York")
    booking = await tools["create_booking"](customer_id=1, court_id=2, ...)
"""

from typing import Dict, Callable, Any
import logging

from app.agent.tools.sync_bridge import (
    run_sync_in_executor,
    sync_to_async,
    call_sync_service,
    get_sync_db,
    shutdown_executor,
    SyncDBContext,
)

# Import tool functions from individual modules
from app.agent.tools.property_tool import (
    search_properties_tool,
    get_property_details_tool,
    get_owner_properties_tool,
)

from app.agent.tools.court_tool import (
    search_courts_tool,
    get_court_details_tool,
    get_property_courts_tool,
)

from app.agent.tools.availability_tool import (
    check_availability_tool,
    get_available_slots_tool,
)

from app.agent.tools.pricing_tool import (
    get_pricing_tool,
    calculate_total_price,
)

from app.agent.tools.booking_tool import (
    create_booking_tool,
    get_booking_details_tool,
    cancel_booking_tool,
)

logger = logging.getLogger(__name__)


# Tool registry dictionary mapping tool names to tool functions
TOOL_REGISTRY: Dict[str, Callable] = {
    # Property tools
    "search_properties": search_properties_tool,
    "get_property_details": get_property_details_tool,
    "get_owner_properties": get_owner_properties_tool,
    
    # Court tools
    "search_courts": search_courts_tool,
    "get_court_details": get_court_details_tool,
    "get_property_courts": get_property_courts_tool,
    
    # Availability tools
    "check_availability": check_availability_tool,
    "get_available_slots": get_available_slots_tool,
    
    # Pricing tools
    "get_pricing": get_pricing_tool,
    "calculate_total_price": calculate_total_price,
    
    # Booking tools
    "create_booking": create_booking_tool,
    "get_booking_details": get_booking_details_tool,
    "cancel_booking": cancel_booking_tool,
}


def initialize_tools(**dependencies) -> Dict[str, Callable]:
    """
    Initialize and return the tool registry with dependency injection.
    
    This function provides a central point for initializing all agent tools
    with any required dependencies. Currently, all tools use the sync bridge
    for service integration, so no additional dependencies are required.
    
    In the future, this function can be extended to inject:
    - Database sessions
    - Service instances
    - Configuration objects
    - External API clients
    
    Args:
        **dependencies: Optional keyword arguments for dependency injection.
                       Currently unused but reserved for future extensions.
                       
    Returns:
        Dictionary mapping tool names to callable tool functions
        
    Example:
        # Basic initialization
        tools = initialize_tools()
        
        # Future: Initialize with custom dependencies
        tools = initialize_tools(
            db_session=session,
            config=app_config
        )
        
        # Use tools in agent
        properties = await tools["search_properties"](
            owner_id="123",
            city="New York"
        )
    """
    logger.info(
        f"Initializing tool registry with {len(TOOL_REGISTRY)} tools"
    )
    
    # Log available tools by category
    property_tools = [k for k in TOOL_REGISTRY.keys() if "property" in k or "properties" in k]
    court_tools = [k for k in TOOL_REGISTRY.keys() if "court" in k]
    availability_tools = [k for k in TOOL_REGISTRY.keys() if "availability" in k or "slots" in k]
    pricing_tools = [k for k in TOOL_REGISTRY.keys() if "pricing" in k or "price" in k]
    booking_tools = [k for k in TOOL_REGISTRY.keys() if "booking" in k]
    
    logger.debug(f"Property tools: {property_tools}")
    logger.debug(f"Court tools: {court_tools}")
    logger.debug(f"Availability tools: {availability_tools}")
    logger.debug(f"Pricing tools: {pricing_tools}")
    logger.debug(f"Booking tools: {booking_tools}")
    
    # Currently, tools don't require dependency injection as they use
    # the sync bridge which manages its own database sessions.
    # This function returns the registry as-is but provides a hook
    # for future dependency injection if needed.
    
    if dependencies:
        logger.info(f"Received dependencies: {list(dependencies.keys())}")
        # Future: Apply dependency injection here
        # For now, we just log and ignore
    
    return TOOL_REGISTRY.copy()


def get_tool(tool_name: str) -> Callable:
    """
    Get a specific tool by name.
    
    Args:
        tool_name: Name of the tool to retrieve
        
    Returns:
        Tool function
        
    Raises:
        KeyError: If tool name is not found in registry
        
    Example:
        search_tool = get_tool("search_properties")
        results = await search_tool(owner_id="123")
    """
    if tool_name not in TOOL_REGISTRY:
        available_tools = ", ".join(TOOL_REGISTRY.keys())
        raise KeyError(
            f"Tool '{tool_name}' not found in registry. "
            f"Available tools: {available_tools}"
        )
    
    return TOOL_REGISTRY[tool_name]


def list_tools() -> list[str]:
    """
    Get a list of all available tool names.
    
    Returns:
        List of tool names
        
    Example:
        tools = list_tools()
        print(f"Available tools: {', '.join(tools)}")
    """
    return list(TOOL_REGISTRY.keys())


__all__ = [
    # Sync bridge utilities
    "run_sync_in_executor",
    "sync_to_async",
    "call_sync_service",
    "get_sync_db",
    "shutdown_executor",
    "SyncDBContext",
    
    # Tool registry
    "TOOL_REGISTRY",
    "initialize_tools",
    "get_tool",
    "list_tools",
    
    # Individual tool functions (for direct import if needed)
    "search_properties_tool",
    "get_property_details_tool",
    "get_owner_properties_tool",
    "search_courts_tool",
    "get_court_details_tool",
    "get_property_courts_tool",
    "check_availability_tool",
    "get_available_slots_tool",
    "get_pricing_tool",
    "calculate_total_price",
    "create_booking_tool",
    "get_booking_details_tool",
    "cancel_booking_tool",
]
