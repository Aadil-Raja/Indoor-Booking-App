"""
Health check endpoint for the chatbot service.

This module provides comprehensive health checks including:
- Database connectivity (async Chat_Database)
- LLM provider availability
- Overall service health status
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import logging
from typing import Dict, Any
from datetime import datetime

from ..core.database import get_async_db
from ..services.llm import get_llm_provider, LLMProviderError

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/health")
async def health_check(
    db: AsyncSession = Depends(get_async_db)
) -> Dict[str, Any]:
    """
    Comprehensive health check endpoint.
    
    Checks:
    - Chat database connectivity
    - LLM provider availability
    - Overall service health
    
    Returns:
        Health status with detailed component checks
        
    Status values:
    - healthy: All components operational
    - degraded: Some components have issues but service is functional
    - unhealthy: Critical components are down
    """
    health_status = {
        "service": "chatbot",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0",
        "status": "healthy",
        "checks": {}
    }
    
    # Check database connectivity
    db_status = await _check_database(db)
    health_status["checks"]["database"] = db_status
    
    # Check LLM provider availability
    llm_status = await _check_llm_provider()
    health_status["checks"]["llm_provider"] = llm_status
    
    # Determine overall health status
    if not db_status["healthy"]:
        health_status["status"] = "unhealthy"
        logger.error("Health check failed: Database is unhealthy")
    elif not llm_status["healthy"]:
        health_status["status"] = "degraded"
        logger.warning("Health check degraded: LLM provider is unavailable")
    else:
        logger.info("Health check passed: All systems operational")
    
    return health_status


async def _check_database(db: AsyncSession) -> Dict[str, Any]:
    """
    Check async database connectivity.
    
    Args:
        db: Async database session
        
    Returns:
        Database health status
    """
    try:
        # Execute a simple query to verify connectivity
        result = await db.execute(text("SELECT 1"))
        result.scalar()
        
        logger.debug("Database connectivity check passed")
        return {
            "healthy": True,
            "message": "Database connection successful",
            "response_time_ms": None  # Could add timing if needed
        }
    except Exception as e:
        logger.error(f"Database connectivity check failed: {e}", exc_info=True)
        return {
            "healthy": False,
            "message": f"Database connection failed: {str(e)}",
            "error": type(e).__name__
        }


async def _check_llm_provider() -> Dict[str, Any]:
    """
    Check LLM provider availability.
    
    Returns:
        LLM provider health status
    """
    try:
        # Attempt to get the LLM provider instance
        provider = get_llm_provider()
        
        # Try a simple token count operation (doesn't require API call)
        token_count = provider.count_tokens("health check")
        
        logger.debug(f"LLM provider check passed, token count test: {token_count}")
        return {
            "healthy": True,
            "message": "LLM provider available",
            "provider": provider.__class__.__name__
        }
    except ValueError as e:
        # Configuration error (e.g., missing API key)
        logger.error(f"LLM provider configuration error: {e}")
        return {
            "healthy": False,
            "message": f"LLM provider configuration error: {str(e)}",
            "error": "ConfigurationError"
        }
    except LLMProviderError as e:
        # Provider-specific error
        logger.error(f"LLM provider error: {e}")
        return {
            "healthy": False,
            "message": f"LLM provider error: {str(e)}",
            "error": type(e).__name__
        }
    except Exception as e:
        # Unexpected error
        logger.error(f"Unexpected error checking LLM provider: {e}", exc_info=True)
        return {
            "healthy": False,
            "message": f"LLM provider check failed: {str(e)}",
            "error": type(e).__name__
        }
