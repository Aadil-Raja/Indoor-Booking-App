"""
Agent runtime package.

This package contains runtime utilities for LangGraph graph execution,
including initialization, compilation, and execution wrappers.

The main component is GraphRuntime, which provides a clean interface for
executing the conversation graph with proper error handling, logging, and
state management.

Usage:
    from app.agent.runtime import create_graph_runtime, GraphRuntime
    from app.services.llm.openai_provider import OpenAIProvider
    
    # Create runtime
    llm = OpenAIProvider(api_key="...")
    runtime = create_graph_runtime(llm_provider=llm)
    
    # Execute graph
    state = {
        "chat_id": "123",
        "user_id": "456",
        "owner_id": "789",
        "user_message": "Hello",
        "flow_state": {},
        "bot_memory": {},
        "messages": []
    }
    result = await runtime.execute(state)
"""

from app.agent.runtime.graph_runtime import (
    GraphRuntime,
    GraphExecutionError,
    create_graph_runtime,
)

__all__ = [
    "GraphRuntime",
    "GraphExecutionError",
    "create_graph_runtime",
]
