"""
Information node handler for LangGraph conversation management.

This module implements the information_node that handles all information-related
queries using LangChain AgentExecutor with automatic tool calling. It processes
queries about properties, courts, availability, pricing, and media.

The node uses LangChain's create_openai_functions_agent to automatically select
and execute appropriate tools based on user queries, without manual tool extraction.

Requirements: 1.1-1.5, 2.1-2.5, 3.1-3.5, 4.1-4.5, 5.1-5.5, 6.1-6.5, 7.1-7.5,
             8.1-8.5, 9.1-9.6, 10.1-10.5, 11.1-11.5
"""

from typing import Optional
import logging

from langchain.agents import create_openai_functions_agent, AgentExecutor

from app.agent.state.conversation_state import ConversationState
from app.services.llm.base import LLMProvider
from app.services.llm.langchain_wrapper import create_langchain_llm
from app.agent.tools.information_tools import INFORMATION_TOOLS
from app.agent.tools.langchain_converter import create_langchain_tools
from app.agent.prompts.information_prompts import create_information_prompt
from app.agent.state.memory_manager import update_bot_memory

logger = logging.getLogger(__name__)


async def information_node(
    state: ConversationState,
    llm_provider: Optional[LLMProvider] = None
) -> ConversationState:
    """
    Handle information queries using LangChain agent with automatic tool calling.
    
    This node processes all information-related queries about properties, courts,
    availability, pricing, and media. It uses a LangChain AgentExecutor that
    automatically selects and executes appropriate tools based on the user's query.
    
    The node follows the standard LangGraph node pattern:
    1. Extract state (user_message, owner_profile_id, bot_memory, flow_state)
    2. Create LangChain tools from INFORMATION_TOOLS registry
    3. Build context-aware prompt with bot_memory
    4. Create ChatOpenAI LLM using create_langchain_llm()
    5. Create agent using create_openai_functions_agent()
    6. Execute AgentExecutor with automatic tool calling
    7. Update bot_memory with results
    8. Return updated state with response
    
    Implements Requirements:
    - 1.1-1.5: Property search functionality
    - 2.1-2.5: Property details retrieval
    - 3.1-3.5: Court details retrieval
    - 4.1-4.5: Court availability checking
    - 5.1-5.5: Court pricing information
    - 6.1-6.5: Media retrieval for properties and courts
    - 7.1-7.5: Complex multi-tool queries
    - 8.1-8.5: Context-aware conversations with bot_memory
    - 9.1-9.6: LangChain agent with ChatOpenAI and automatic tool calling
    - 10.1-10.5: LangGraph integration and routing
    - 11.1-11.5: State management with bot_memory updates
    
    Args:
        state: ConversationState containing user message and context
        llm_provider: LLMProvider instance for creating ChatOpenAI
        
    Returns:
        ConversationState: Updated state with response_content and bot_memory
        
    Example:
        state = {
            "user_message": "Show me tennis courts in New York",
            "owner_profile_id": "1",
            "bot_memory": {},
            ...
        }
        
        result = await information_node(state, llm_provider=provider)
        # result["response_content"] contains the agent's response
        # result["bot_memory"] contains updated context
    """
    # 1. Extract state
    chat_id = state["chat_id"]
    user_message = state["user_message"]
    owner_profile_id = state["owner_profile_id"]
    bot_memory = state.get("bot_memory", {})
    flow_state = state.get("flow_state", {})
    
    logger.info(
        f"Processing information query for chat {chat_id} - "
        f"message_preview={user_message[:50]}..."
    )
    
    try:
        # 2. Convert tools to LangChain format
        logger.debug("Converting information tools to LangChain format")
        langchain_tools = create_langchain_tools(INFORMATION_TOOLS)
        logger.info(f"Created {len(langchain_tools)} LangChain tools")
        
        # 3. Create ChatOpenAI LLM using wrapper
        if not llm_provider:
            raise ValueError("llm_provider is required for information node")
        
        logger.debug("Creating ChatOpenAI LLM instance")
        llm = create_langchain_llm(
            llm_provider,
            temperature=0.7,  # Balanced creativity for natural responses
            max_tokens=1000   # Allow longer responses for detailed information
        )
        
        # 4. Build context-aware prompt
        logger.debug("Building context-aware prompt with bot_memory")
        prompt = create_information_prompt(
            owner_profile_id=int(owner_profile_id),
            bot_memory=bot_memory
        )
        
        # 5. Create agent using create_openai_functions_agent
        logger.debug("Creating OpenAI functions agent")
        agent = create_openai_functions_agent(llm, langchain_tools, prompt)
        
        # 6. Create AgentExecutor with agent and tools
        logger.debug("Creating AgentExecutor")
        agent_executor = AgentExecutor(
            agent=agent,
            tools=langchain_tools,
            verbose=True,  # Enable verbose logging for debugging
            max_iterations=5,  # Limit iterations to prevent infinite loops
            handle_parsing_errors=True  # Gracefully handle parsing errors
        )
        
        # 7. Execute agent with ainvoke() passing user_message
        logger.info(f"Executing agent for chat {chat_id}")
        result = await agent_executor.ainvoke({
            "input": user_message,
            "chat_history": [],  # Could be populated from bot_memory if needed
        })
        
        # 8. Update state with response_content from agent result
        response_content = result.get("output", "")
        state["response_content"] = response_content
        state["response_type"] = "text"
        state["response_metadata"] = {}
        
        logger.info(
            f"Agent execution completed for chat {chat_id} - "
            f"response_length={len(response_content)}"
        )
        
        # 9. Update bot_memory using update_bot_memory()
        logger.debug("Updating bot_memory with agent results")
        updated_bot_memory = update_bot_memory(bot_memory, result)
        state["bot_memory"] = updated_bot_memory
        
        # Log tools used for debugging
        tools_used = updated_bot_memory.get("context", {}).get("last_tools_used", [])
        if tools_used:
            logger.info(f"Tools used in this interaction: {', '.join(tools_used)}")
        
        logger.info(f"Information node completed successfully for chat {chat_id}")
        
    except Exception as e:
        # 10. Handle exceptions and return error message on failure
        logger.error(
            f"Error in information node for chat {chat_id}: {e}",
            exc_info=True
        )
        
        state["response_content"] = (
            "I'm sorry, I encountered an error while processing your request. "
            "Please try again or rephrase your question."
        )
        state["response_type"] = "text"
        state["response_metadata"] = {}
    
    return state
