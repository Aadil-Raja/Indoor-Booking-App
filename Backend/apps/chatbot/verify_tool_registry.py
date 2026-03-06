"""
Verification script to check if information tools are properly registered.
"""

import sys
from pathlib import Path

# Add the chatbot app to the path
chatbot_path = Path(__file__).parent
sys.path.insert(0, str(chatbot_path))

from app.agent.tools import TOOL_REGISTRY, INFORMATION_TOOLS

# Expected tool names from create_langchain_tools()
EXPECTED_TOOLS = [
    "search_properties",
    "get_property_details",
    "get_court_details",
    "get_court_availability",
    "get_court_pricing",
    "get_property_media",
    "get_court_media",
]

print("=" * 60)
print("Tool Registry Verification")
print("=" * 60)

print(f"\nTotal tools in TOOL_REGISTRY: {len(TOOL_REGISTRY)}")
print(f"Total tools in INFORMATION_TOOLS: {len(INFORMATION_TOOLS)}")

print("\n" + "-" * 60)
print("Checking Information Tools Registration:")
print("-" * 60)

all_registered = True
for tool_name in EXPECTED_TOOLS:
    in_registry = tool_name in TOOL_REGISTRY
    in_info_tools = tool_name in INFORMATION_TOOLS
    status = "✓" if in_registry else "✗"
    
    print(f"{status} {tool_name}")
    print(f"   - In TOOL_REGISTRY: {in_registry}")
    print(f"   - In INFORMATION_TOOLS: {in_info_tools}")
    
    if in_registry:
        tool_func = TOOL_REGISTRY[tool_name]
        print(f"   - Function: {tool_func.__name__}")
        print(f"   - Module: {tool_func.__module__}")
    
    if not in_registry:
        all_registered = False
    
    print()

print("-" * 60)
if all_registered:
    print("✓ SUCCESS: All information tools are properly registered!")
else:
    print("✗ FAILURE: Some information tools are missing from registry!")

print("\n" + "=" * 60)
print("All Tools in TOOL_REGISTRY:")
print("=" * 60)
for tool_name in sorted(TOOL_REGISTRY.keys()):
    print(f"  - {tool_name}")

print("\n" + "=" * 60)
