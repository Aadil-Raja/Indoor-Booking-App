"""
Verification script for availability tool implementation.

This script verifies that the availability tool is correctly implemented
and can integrate with the sync availability_service through the sync bridge.
"""

import asyncio
import sys
from pathlib import Path
from datetime import date, timedelta

# Add Backend path for imports
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

# Add chatbot app path
chatbot_path = Path(__file__).parent
sys.path.insert(0, str(chatbot_path))


async def verify_availability_tool():
    """Verify availability tool implementation"""
    print("=" * 80)
    print("AVAILABILITY TOOL VERIFICATION")
    print("=" * 80)
    print()
    
    try:
        # Import the availability tool
        print("1. Importing availability tool module...")
        from app.agent.tools.availability_tool import (
            check_availability_tool,
            get_available_slots_tool,
            AVAILABILITY_TOOLS
        )
        print("   ✓ Successfully imported availability tool module")
        print()
        
        # Verify tool registry
        print("2. Verifying tool registry...")
        assert 'check_availability' in AVAILABILITY_TOOLS, "check_availability not in registry"
        assert 'get_available_slots' in AVAILABILITY_TOOLS, "get_available_slots not in registry"
        assert callable(AVAILABILITY_TOOLS['check_availability']), "check_availability not callable"
        assert callable(AVAILABILITY_TOOLS['get_available_slots']), "get_available_slots not callable"
        print("   ✓ Tool registry contains all expected tools")
        print(f"   ✓ Registered tools: {list(AVAILABILITY_TOOLS.keys())}")
        print()
        
        # Verify function signatures
        print("3. Verifying function signatures...")
        import inspect
        
        # Check check_availability_tool signature
        check_sig = inspect.signature(check_availability_tool)
        check_params = list(check_sig.parameters.keys())
        assert 'court_id' in check_params, "check_availability_tool missing court_id parameter"
        assert 'owner_id' in check_params, "check_availability_tool missing owner_id parameter"
        assert 'from_date' in check_params, "check_availability_tool missing from_date parameter"
        print("   ✓ check_availability_tool has correct parameters:")
        print(f"     Parameters: {check_params}")
        
        # Check get_available_slots_tool signature
        slots_sig = inspect.signature(get_available_slots_tool)
        slots_params = list(slots_sig.parameters.keys())
        assert 'court_id' in slots_params, "get_available_slots_tool missing court_id parameter"
        assert 'date_val' in slots_params, "get_available_slots_tool missing date_val parameter"
        print("   ✓ get_available_slots_tool has correct parameters:")
        print(f"     Parameters: {slots_params}")
        print()
        
        # Verify async functions
        print("4. Verifying functions are async...")
        assert asyncio.iscoroutinefunction(check_availability_tool), "check_availability_tool is not async"
        assert asyncio.iscoroutinefunction(get_available_slots_tool), "get_available_slots_tool is not async"
        print("   ✓ All tool functions are async")
        print()
        
        # Verify docstrings
        print("5. Verifying documentation...")
        assert check_availability_tool.__doc__, "check_availability_tool missing docstring"
        assert get_available_slots_tool.__doc__, "get_available_slots_tool missing docstring"
        print("   ✓ All functions have docstrings")
        print()
        
        # Verify sync bridge integration
        print("6. Verifying sync bridge integration...")
        from app.agent.tools.sync_bridge import call_sync_service
        print("   ✓ Successfully imported call_sync_service from sync_bridge")
        print()
        
        # Test with mock data (without actual database)
        print("7. Testing tool structure with mock data...")
        from unittest.mock import AsyncMock, patch
        
        # Mock check_availability_tool
        mock_blocked_result = {
            'success': True,
            'data': [
                {
                    'id': 1,
                    'date': '2024-01-15',
                    'start_time': '09:00:00',
                    'end_time': '11:00:00',
                    'reason': 'Maintenance'
                }
            ]
        }
        
        with patch('app.agent.tools.availability_tool.call_sync_service', new_callable=AsyncMock) as mock_call:
            mock_call.return_value = mock_blocked_result
            
            result = await check_availability_tool(
                court_id=123,
                owner_id=456,
                from_date=date.today()
            )
            
            assert isinstance(result, list), "check_availability_tool should return a list"
            assert len(result) == 1, "Expected 1 blocked slot"
            assert result[0]['reason'] == 'Maintenance', "Blocked slot reason mismatch"
            print("   ✓ check_availability_tool returns correct structure")
        
        # Mock get_available_slots_tool
        mock_slots_result = {
            'success': True,
            'data': {
                'date': '2024-01-15',
                'court_id': 123,
                'court_name': 'Tennis Court A',
                'available_slots': [
                    {
                        'start_time': '09:00:00',
                        'end_time': '10:00:00',
                        'price_per_hour': 50.0,
                        'label': 'Morning Rate'
                    }
                ]
            }
        }
        
        with patch('app.agent.tools.availability_tool.call_sync_service', new_callable=AsyncMock) as mock_call:
            mock_call.return_value = mock_slots_result
            
            result = await get_available_slots_tool(
                court_id=123,
                date_val=date.today()
            )
            
            assert isinstance(result, dict), "get_available_slots_tool should return a dict"
            assert 'available_slots' in result, "Result should contain available_slots"
            assert 'court_name' in result, "Result should contain court_name"
            assert len(result['available_slots']) == 1, "Expected 1 available slot"
            print("   ✓ get_available_slots_tool returns correct structure")
        print()
        
        # Test error handling
        print("8. Testing error handling...")
        
        # Test check_availability_tool with service failure
        with patch('app.agent.tools.availability_tool.call_sync_service', new_callable=AsyncMock) as mock_call:
            mock_call.return_value = {'success': False, 'message': 'Court not found'}
            
            result = await check_availability_tool(court_id=999, owner_id=456)
            assert result == [], "Should return empty list on failure"
            print("   ✓ check_availability_tool handles service failure")
        
        # Test get_available_slots_tool with service failure
        with patch('app.agent.tools.availability_tool.call_sync_service', new_callable=AsyncMock) as mock_call:
            mock_call.return_value = {'success': False, 'message': 'Court not found'}
            
            result = await get_available_slots_tool(court_id=999, date_val=date.today())
            assert result is None, "Should return None on failure"
            print("   ✓ get_available_slots_tool handles service failure")
        
        # Test exception handling
        with patch('app.agent.tools.availability_tool.call_sync_service', new_callable=AsyncMock) as mock_call:
            mock_call.side_effect = Exception("Database error")
            
            result = await check_availability_tool(court_id=123, owner_id=456)
            assert result == [], "Should return empty list on exception"
            print("   ✓ check_availability_tool handles exceptions")
        
        with patch('app.agent.tools.availability_tool.call_sync_service', new_callable=AsyncMock) as mock_call:
            mock_call.side_effect = Exception("Database error")
            
            result = await get_available_slots_tool(court_id=123, date_val=date.today())
            assert result is None, "Should return None on exception"
            print("   ✓ get_available_slots_tool handles exceptions")
        print()
        
        # Verify logging
        print("9. Verifying logging setup...")
        import logging
        from app.agent.tools import availability_tool
        
        # Check that module has logger
        assert hasattr(availability_tool, 'logger'), "Module should have logger"
        assert isinstance(availability_tool.logger, logging.Logger), "logger should be Logger instance"
        print("   ✓ Logging is properly configured")
        print()
        
        # Summary
        print("=" * 80)
        print("VERIFICATION COMPLETE")
        print("=" * 80)
        print()
        print("✓ All checks passed successfully!")
        print()
        print("Summary:")
        print("  - Module imports correctly")
        print("  - Tool registry is properly configured")
        print("  - Function signatures are correct")
        print("  - All functions are async")
        print("  - Documentation is present")
        print("  - Sync bridge integration works")
        print("  - Mock data tests pass")
        print("  - Error handling works correctly")
        print("  - Logging is configured")
        print()
        print("The availability tool is ready for integration!")
        print()
        
        return True
        
    except Exception as e:
        print()
        print("=" * 80)
        print("VERIFICATION FAILED")
        print("=" * 80)
        print()
        print(f"Error: {e}")
        print()
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(verify_availability_tool())
    sys.exit(0 if success else 1)
