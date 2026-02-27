"""
Test script for the health check endpoint.

This script verifies that the GET /api/chat/health endpoint works correctly
by checking database connectivity and LLM provider availability.
"""

import asyncio
import sys
from pathlib import Path

# Add Backend directory to Python path for shared module imports
backend_path = Path(__file__).parent.parent.parent
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

# Add current directory to path for app imports
sys.path.insert(0, '.')

from app.core.database import AsyncSessionLocal
from app.routers.health import health_check, _check_database, _check_llm_provider


async def test_health_endpoint():
    """Test the health check endpoint functionality."""
    
    print("=" * 60)
    print("Testing Health Check Endpoint")
    print("=" * 60)
    
    # Test 1: Check database connectivity
    print(f"\n[Test 1] Testing database connectivity check...")
    
    async with AsyncSessionLocal() as session:
        db_status = await _check_database(session)
        
        print(f"Database status: {db_status}")
        
        if db_status["healthy"]:
            print("✓ Database connectivity check passed")
            assert db_status["message"] == "Database connection successful"
        else:
            print("✗ Database connectivity check failed")
            print(f"  Error: {db_status.get('error')}")
            print(f"  Message: {db_status.get('message')}")
    
    # Test 2: Check LLM provider availability
    print(f"\n[Test 2] Testing LLM provider availability check...")
    
    llm_status = await _check_llm_provider()
    
    print(f"LLM provider status: {llm_status}")
    
    if llm_status["healthy"]:
        print("✓ LLM provider availability check passed")
        print(f"  Provider: {llm_status.get('provider')}")
    else:
        print("✗ LLM provider availability check failed")
        print(f"  Error: {llm_status.get('error')}")
        print(f"  Message: {llm_status.get('message')}")
    
    # Test 3: Full health check endpoint
    print(f"\n[Test 3] Testing full health check endpoint...")
    
    async with AsyncSessionLocal() as session:
        health_status = await health_check(session)
        
        print(f"\nHealth check response:")
        print(f"  Service: {health_status['service']}")
        print(f"  Status: {health_status['status']}")
        print(f"  Version: {health_status['version']}")
        print(f"  Timestamp: {health_status['timestamp']}")
        
        print(f"\n  Component checks:")
        for component, status in health_status['checks'].items():
            print(f"    {component}:")
            print(f"      Healthy: {status['healthy']}")
            print(f"      Message: {status['message']}")
            if 'provider' in status:
                print(f"      Provider: {status['provider']}")
            if 'error' in status:
                print(f"      Error: {status['error']}")
        
        # Verify response structure
        assert "service" in health_status, "Response should include 'service'"
        assert "status" in health_status, "Response should include 'status'"
        assert "version" in health_status, "Response should include 'version'"
        assert "timestamp" in health_status, "Response should include 'timestamp'"
        assert "checks" in health_status, "Response should include 'checks'"
        assert "database" in health_status["checks"], "Checks should include 'database'"
        assert "llm_provider" in health_status["checks"], "Checks should include 'llm_provider'"
        
        print("\n✓ Health check response structure is correct")
        
        # Verify status logic
        db_healthy = health_status["checks"]["database"]["healthy"]
        llm_healthy = health_status["checks"]["llm_provider"]["healthy"]
        overall_status = health_status["status"]
        
        if not db_healthy:
            assert overall_status == "unhealthy", "Status should be 'unhealthy' when database is down"
            print("✓ Status correctly set to 'unhealthy' (database down)")
        elif not llm_healthy:
            assert overall_status == "degraded", "Status should be 'degraded' when LLM provider is unavailable"
            print("✓ Status correctly set to 'degraded' (LLM provider unavailable)")
        else:
            assert overall_status == "healthy", "Status should be 'healthy' when all components are operational"
            print("✓ Status correctly set to 'healthy' (all components operational)")
    
    print("\n" + "=" * 60)
    print("All tests passed! ✓")
    print("=" * 60)
    
    # Print summary
    print("\nSummary:")
    print(f"  Service: {health_status['service']}")
    print(f"  Overall status: {health_status['status']}")
    print(f"  Database: {'✓' if db_healthy else '✗'}")
    print(f"  LLM Provider: {'✓' if llm_healthy else '✗'}")
    print(f"  Version: {health_status['version']}")


if __name__ == "__main__":
    asyncio.run(test_health_endpoint())
