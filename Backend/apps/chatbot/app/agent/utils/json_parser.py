"""
JSON parser utility for LLM responses.

Handles common issues with LLM JSON responses:
- Markdown code blocks (```json ... ```)
- Extra text before/after JSON
- Whitespace issues
"""

import json
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


def parse_llm_json_response(
    response: str,
    fallback: Optional[Dict[str, Any]] = None,
    context: str = "LLM response"
) -> Dict[str, Any]:
    """
    Parse JSON from LLM response, handling common formatting issues.
    
    This function handles:
    - Markdown code blocks (```json ... ``` or ``` ... ```)
    - Extra text before/after the JSON object
    - Whitespace issues
    
    Args:
        response: Raw response string from LLM
        fallback: Default value to return if parsing fails (defaults to empty dict)
        context: Description of what's being parsed (for error logging)
        
    Returns:
        Parsed JSON as dictionary, or fallback if parsing fails
        
    Example:
        # Response with markdown
        response = "```json\n{\"key\": \"value\"}\n```"
        result = parse_llm_json_response(response)
        # Returns: {"key": "value"}
        
        # Response with extra text
        response = "Here's the result: {\"key\": \"value\"} - done!"
        result = parse_llm_json_response(response)
        # Returns: {"key": "value"}
        
        # Invalid JSON
        response = "not json at all"
        result = parse_llm_json_response(response, fallback={"error": True})
        # Returns: {"error": True}
    """
    if fallback is None:
        fallback = {}
    
    try:
        # Strip whitespace
        json_str = response.strip()
        
        # Handle markdown code blocks
        if "```json" in json_str:
            # Extract content between ```json and ```
            json_str = json_str.split("```json")[1].split("```")[0].strip()
        elif "```" in json_str:
            # Extract content between ``` and ```
            json_str = json_str.split("```")[1].split("```")[0].strip()
        
        # Find the first { and last } to extract just the JSON object
        start_idx = json_str.find("{")
        end_idx = json_str.rfind("}") + 1
        
        if start_idx != -1 and end_idx > start_idx:
            json_str = json_str[start_idx:end_idx]
        else:
            # No JSON object found
            logger.error(
                f"No JSON object found in {context}. "
                f"Response: {response[:200]}"
            )
            return fallback
        
        # Parse JSON
        parsed = json.loads(json_str)
        
        if not isinstance(parsed, dict):
            logger.warning(
                f"Parsed JSON is not a dict in {context}: {type(parsed)}. "
                f"Using fallback."
            )
            return fallback
        
        return parsed
        
    except json.JSONDecodeError as e:
        logger.error(
            f"Failed to parse JSON in {context}: {e}. "
            f"Response: {response[:200]}"
        )
        return fallback
    except Exception as e:
        logger.error(
            f"Unexpected error parsing JSON in {context}: {e}. "
            f"Response: {response[:200]}",
            exc_info=True
        )
        return fallback


def extract_json_field(
    parsed_json: Dict[str, Any],
    field: str,
    default: Any = None,
    field_type: Optional[type] = None
) -> Any:
    """
    Safely extract a field from parsed JSON with type validation.
    
    Args:
        parsed_json: Parsed JSON dictionary
        field: Field name to extract
        default: Default value if field is missing or invalid
        field_type: Expected type of the field (for validation)
        
    Returns:
        Field value or default
        
    Example:
        data = {"name": "John", "age": 30}
        
        name = extract_json_field(data, "name", default="Unknown", field_type=str)
        # Returns: "John"
        
        age = extract_json_field(data, "age", default=0, field_type=int)
        # Returns: 30
        
        missing = extract_json_field(data, "email", default="no-email")
        # Returns: "no-email"
    """
    value = parsed_json.get(field, default)
    
    # Type validation if specified
    if field_type is not None and value is not None:
        if not isinstance(value, field_type):
            logger.warning(
                f"Field '{field}' has wrong type: expected {field_type.__name__}, "
                f"got {type(value).__name__}. Using default."
            )
            return default
    
    return value
