"""
Shared response utility for consistent API responses across all services.
"""
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from typing import Any, Optional


def make_response(
    success: bool,
    message: str,
    data: Any = None,
    next_action: Optional[str] = None,
    *,
    status_code: int = 200,
    error: Optional[str] = None,
):
    """
    Unified response with optional next_action and optional error (for debugging).
    Note: status_code and error are keyword-only to prevent positional mistakes.
    
    Args:
        success: Boolean indicating operation success
        message: Human-readable message
        data: Optional data payload
        next_action: Optional next action hint for client
        status_code: HTTP status code (keyword-only)
        error: Optional error details for debugging (keyword-only)
        
    Returns:
        JSONResponse with standardized format
    """
    payload = {"success": success, "message": message}
    if data is not None:
        payload["data"] = data
    if next_action is not None:
        payload["next_action"] = next_action
    if error is not None:
        payload["error"] = error
    return JSONResponse(status_code=status_code, content=jsonable_encoder(payload))
