"""
LangChain LLM wrapper utility.

This module provides a utility function to create LangChain ChatOpenAI instances
from our LLMProvider abstraction. This ensures all nodes use LangChain's ChatOpenAI
wrapper instead of making direct OpenAI API calls.
"""

import logging
from typing import Optional

from langchain_openai import ChatOpenAI

from app.services.llm.base import LLMProvider

logger = logging.getLogger(__name__)


def create_langchain_llm(
    llm_provider: LLMProvider,
    model: Optional[str] = None,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
    **kwargs
) -> ChatOpenAI:
    """
    Create a LangChain ChatOpenAI instance from an LLMProvider.
    
    This function extracts the necessary configuration from our LLMProvider
    abstraction and creates a ChatOpenAI instance that can be used with
    LangChain agents and chains.
    
    Args:
        llm_provider: The LLMProvider instance containing API key and config
        model: Optional model override (uses provider's model if None)
        temperature: Optional temperature override (uses provider's temperature if None)
        max_tokens: Optional max_tokens override (uses provider's max_tokens if None)
        **kwargs: Additional parameters to pass to ChatOpenAI
        
    Returns:
        Configured ChatOpenAI instance ready for use with LangChain
        
    Raises:
        ValueError: If llm_provider doesn't have required attributes
        
    Example:
        >>> from app.services.llm import get_llm_provider
        >>> from app.services.llm.langchain_wrapper import create_langchain_llm
        >>> 
        >>> llm_provider = get_llm_provider()
        >>> llm = create_langchain_llm(llm_provider)
        >>> response = await llm.ainvoke("Hello, how are you?")
    """
    # Extract configuration from LLMProvider
    if not hasattr(llm_provider, 'api_key'):
        raise ValueError("LLMProvider must have 'api_key' attribute")
    
    api_key = llm_provider.api_key
    
    # Use provider's configuration as defaults, allow overrides
    model_name = model or getattr(llm_provider, 'model', 'gpt-4o-mini')
    temp = temperature if temperature is not None else getattr(llm_provider, 'temperature', 0.7)
    max_tok = max_tokens or getattr(llm_provider, 'max_tokens', 500)
    
    logger.info(
        f"Creating LangChain ChatOpenAI instance: "
        f"model={model_name}, temperature={temp}, max_tokens={max_tok}"
    )
    
    # Create and return ChatOpenAI instance
    llm = ChatOpenAI(
        model=model_name,
        api_key=api_key,
        temperature=temp,
        max_tokens=max_tok,
        **kwargs
    )
    
    logger.debug("ChatOpenAI instance created successfully")
    
    return llm
