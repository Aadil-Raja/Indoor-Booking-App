"""
LangChain tool converter for the chatbot agent.

This module converts custom async tools to LangChain StructuredTool format
with proper Pydantic schemas for input validation. Each tool is wrapped with
its schema to enable LangChain agents to automatically call tools based on
user queries.

Requirements: 9.1, 9.6
"""

import logging
from typing import List, Dict, Any, Callable, Optional
from pydantic import BaseModel, Field
from langchain.tools import StructuredTool

logger = logging.getLogger(__name__)


# Pydantic schemas for each tool

class SearchPropertiesInput(BaseModel):
    """Input schema for search_properties tool."""
    owner_profile_id: int = Field(
        description="Owner profile ID to filter properties by (required - use the owner_profile_id from context)",
        gt=0
    )
    city: Optional[str] = Field(
        None,
        description="City name to filter properties by (e.g., 'New York', 'Los Angeles')"
    )
    sport_type: Optional[str] = Field(
        None,
        description="Sport type to filter by (e.g., 'tennis', 'basketball', 'soccer')"
    )
    min_price: Optional[float] = Field(
        None,
        description="Minimum price per hour in dollars",
        ge=0
    )
    max_price: Optional[float] = Field(
        None,
        description="Maximum price per hour in dollars",
        ge=0
    )
    limit: int = Field(
        10,
        description="Maximum number of results to return",
        ge=1,
        le=50
    )


class GetPropertyDetailsInput(BaseModel):
    """Input schema for get_property_details tool."""
    property_id: int = Field(
        description="Unique identifier of the property to retrieve details for",
        gt=0
    )


class GetCourtDetailsInput(BaseModel):
    """Input schema for get_court_details tool."""
    court_id: int = Field(
        description="Unique identifier of the court to retrieve details for",
        gt=0
    )


class GetCourtAvailabilityInput(BaseModel):
    """Input schema for get_court_availability tool."""
    court_id: int = Field(
        description="Unique identifier of the court to check availability for",
        gt=0
    )
    date_val: str = Field(
        description="Date to check availability for in ISO format (YYYY-MM-DD), e.g., '2026-03-10'"
    )


class GetCourtPricingInput(BaseModel):
    """Input schema for get_court_pricing tool."""
    court_id: int = Field(
        description="Unique identifier of the court to get pricing for",
        gt=0
    )
    date_val: str = Field(
        description="Date to get pricing for in ISO format (YYYY-MM-DD), e.g., '2026-03-10'"
    )


class GetPropertyMediaInput(BaseModel):
    """Input schema for get_property_media tool."""
    property_id: int = Field(
        description="Unique identifier of the property to get media for",
        gt=0
    )
    limit: int = Field(
        5,
        description="Maximum number of media items to return",
        ge=1,
        le=20
    )


class GetCourtMediaInput(BaseModel):
    """Input schema for get_court_media tool."""
    court_id: int = Field(
        description="Unique identifier of the court to get media for",
        gt=0
    )
    limit: int = Field(
        5,
        description="Maximum number of media items to return",
        ge=1,
        le=20
    )


def create_langchain_tools(tool_registry: Dict[str, Callable]) -> List[StructuredTool]:
    """
    Convert tool registry to LangChain StructuredTools.
    
    This function takes a dictionary of tool functions and converts them to
    LangChain StructuredTool instances with proper schemas, names, and descriptions.
    Each tool is configured with the coroutine parameter for async execution.
    
    Args:
        tool_registry: Dictionary mapping tool names to async tool functions
        
    Returns:
        List of LangChain StructuredTool instances ready for agent use
        
    Example:
        from app.agent.tools.information_tools import INFORMATION_TOOLS
        langchain_tools = create_langchain_tools(INFORMATION_TOOLS)
    """
    tools = []
    
    try:
        # Search properties tool
        if "search_properties" in tool_registry:
            tools.append(StructuredTool.from_function(
                func=tool_registry["search_properties"],
                name="search_properties",
                description=(
                    "Search for sports properties and facilities. Use this tool to find "
                    "properties by location (city) and/or sport type (tennis, basketball, etc.). "
                    "You can also filter by price range. Returns a list of properties with "
                    "basic information including name, address, city, and amenities."
                ),
                args_schema=SearchPropertiesInput,
                coroutine=tool_registry["search_properties"]
            ))
            logger.debug("Added search_properties tool")
        
        # Get property details tool
        if "get_property_details" in tool_registry:
            tools.append(StructuredTool.from_function(
                func=tool_registry["get_property_details"],
                name="get_property_details",
                description=(
                    "Get detailed information about a specific property. Use this tool when "
                    "the user asks for more details about a property, including its full "
                    "description, location, contact information, amenities, available courts, "
                    "and media. Requires a property_id."
                ),
                args_schema=GetPropertyDetailsInput,
                coroutine=tool_registry["get_property_details"]
            ))
            logger.debug("Added get_property_details tool")
        
        # Get court details tool
        if "get_court_details" in tool_registry:
            tools.append(StructuredTool.from_function(
                func=tool_registry["get_court_details"],
                name="get_court_details",
                description=(
                    "Get detailed information about a specific court. Use this tool to get "
                    "court specifications, amenities, sport type, surface material, and "
                    "associated property information. Also includes pricing rules and media. "
                    "Requires a court_id."
                ),
                args_schema=GetCourtDetailsInput,
                coroutine=tool_registry["get_court_details"]
            ))
            logger.debug("Added get_court_details tool")
        
        # Get court availability tool
        if "get_court_availability" in tool_registry:
            tools.append(StructuredTool.from_function(
                func=tool_registry["get_court_availability"],
                name="get_court_availability",
                description=(
                    "Check available time slots for a court on a specific date. Use this tool "
                    "when the user wants to know when a court is available for booking. "
                    "Returns available time slots with pricing information. Requires court_id "
                    "and date in ISO format (YYYY-MM-DD)."
                ),
                args_schema=GetCourtAvailabilityInput,
                coroutine=tool_registry["get_court_availability"]
            ))
            logger.debug("Added get_court_availability tool")
        
        # Get court pricing tool
        if "get_court_pricing" in tool_registry:
            tools.append(StructuredTool.from_function(
                func=tool_registry["get_court_pricing"],
                name="get_court_pricing",
                description=(
                    "Get pricing information for a court on a specific date. Use this tool "
                    "when the user asks about court rates, hourly pricing, or cost. Returns "
                    "time-based pricing rules showing different rates for different times of day. "
                    "Requires court_id and date in ISO format (YYYY-MM-DD)."
                ),
                args_schema=GetCourtPricingInput,
                coroutine=tool_registry["get_court_pricing"]
            ))
            logger.debug("Added get_court_pricing tool")
        
        # Get property media tool
        if "get_property_media" in tool_registry:
            tools.append(StructuredTool.from_function(
                func=tool_registry["get_property_media"],
                name="get_property_media",
                description=(
                    "Get photos and videos of a property. Use this tool when the user asks "
                    "to see pictures, photos, images, or videos of a property. Returns a list "
                    "of media items with URLs and descriptions. Requires property_id."
                ),
                args_schema=GetPropertyMediaInput,
                coroutine=tool_registry["get_property_media"]
            ))
            logger.debug("Added get_property_media tool")
        
        # Get court media tool
        if "get_court_media" in tool_registry:
            tools.append(StructuredTool.from_function(
                func=tool_registry["get_court_media"],
                name="get_court_media",
                description=(
                    "Get photos and videos of a specific court. Use this tool when the user "
                    "asks to see pictures, photos, images, or videos of a court. Returns a list "
                    "of media items with URLs and descriptions. Requires court_id."
                ),
                args_schema=GetCourtMediaInput,
                coroutine=tool_registry["get_court_media"]
            ))
            logger.debug("Added get_court_media tool")
        
        logger.info(f"Successfully created {len(tools)} LangChain tools")
        return tools
        
    except Exception as e:
        logger.error(f"Error creating LangChain tools: {e}", exc_info=True)
        raise
