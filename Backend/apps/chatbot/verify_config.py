"""
Verification script for task 1.1: Database configuration and engine setup.

This script verifies that:
1. Configuration loads correctly from .env
2. Async database engine is created with proper settings
3. Database connection can be established
"""

import sys
import asyncio
from pathlib import Path

# Add Backend directory to Python path
backend_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(backend_dir))

from app.core.config import settings
from app.core.database import async_engine, AsyncSessionLocal, get_async_db


async def verify_configuration():
    """Verify configuration settings."""
    print("=" * 60)
    print("CONFIGURATION VERIFICATION")
    print("=" * 60)
    
    # Check required settings
    checks = {
        "CHAT_DATABASE_URL": bool(settings.CHAT_DATABASE_URL),
        "MAIN_DATABASE_URL": bool(settings.MAIN_DATABASE_URL),
        "JWT_SECRET": bool(settings.JWT_SECRET),
        "SESSION_EXPIRY_HOURS": settings.SESSION_EXPIRY_HOURS == 24,
        "LLM_PROVIDER": settings.LLM_PROVIDER in ["openai", "gemini"],
    }
    
    for check_name, result in checks.items():
        status = "✓" if result else "✗"
        print(f"{status} {check_name}: {'PASS' if result else 'FAIL'}")
    
    print(f"\nConnection Pool Settings:")
    print(f"  - Pool Size: {settings.DB_POOL_SIZE}")
    print(f"  - Max Overflow: {settings.DB_MAX_OVERFLOW}")
    print(f"  - Pool Timeout: {settings.DB_POOL_TIMEOUT}s")
    print(f"  - Pool Recycle: {settings.DB_POOL_RECYCLE}s")
    
    return all(checks.values())


async def verify_database_engine():
    """Verify async database engine configuration."""
    print("\n" + "=" * 60)
    print("DATABASE ENGINE VERIFICATION")
    print("=" * 60)
    
    # For async engines, SQLAlchemy uses AsyncAdaptedQueuePool
    pool_class_name = async_engine.pool.__class__.__name__
    is_valid_pool = pool_class_name in ["AsyncAdaptedQueuePool", "QueuePool"]
    
    checks = {
        "Async Engine Created": async_engine is not None,
        "Engine URL": str(async_engine.url).startswith("postgresql+asyncpg://"),
        "Pool Class": is_valid_pool,
        "Session Factory": AsyncSessionLocal is not None,
    }
    
    for check_name, result in checks.items():
        status = "✓" if result else "✗"
        print(f"{status} {check_name}: {'PASS' if result else 'FAIL'}")
    
    if is_valid_pool:
        print(f"  Pool Type: {pool_class_name}")
    
    return all(checks.values())


async def verify_database_connection():
    """Verify database connection can be established."""
    print("\n" + "=" * 60)
    print("DATABASE CONNECTION VERIFICATION")
    print("=" * 60)
    
    try:
        async with async_engine.begin() as conn:
            print("✓ Database connection established successfully")
            return True
    except Exception as e:
        print(f"✗ Database connection failed: {e}")
        return False


async def verify_session_dependency():
    """Verify get_async_db dependency works."""
    print("\n" + "=" * 60)
    print("SESSION DEPENDENCY VERIFICATION")
    print("=" * 60)
    
    try:
        async for session in get_async_db():
            print("✓ AsyncSession created successfully")
            print(f"✓ Session type: {type(session).__name__}")
            print(f"✓ Session is async: {hasattr(session, 'execute')}")
            return True
    except Exception as e:
        print(f"✗ Session creation failed: {e}")
        return False


async def main():
    """Run all verification checks."""
    print("\n" + "=" * 60)
    print("TASK 1.1 VERIFICATION: Async Database Configuration")
    print("=" * 60 + "\n")
    
    results = []
    
    # Run all checks
    results.append(await verify_configuration())
    results.append(await verify_database_engine())
    results.append(await verify_database_connection())
    results.append(await verify_session_dependency())
    
    # Summary
    print("\n" + "=" * 60)
    print("VERIFICATION SUMMARY")
    print("=" * 60)
    
    passed = sum(results)
    total = len(results)
    
    print(f"Passed: {passed}/{total}")
    
    if all(results):
        print("\n✓ All checks passed! Task 1.1 implementation is correct.")
        return 0
    else:
        print("\n✗ Some checks failed. Please review the implementation.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
