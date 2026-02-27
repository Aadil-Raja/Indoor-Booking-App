"""
Example usage of the LLM provider factory with configuration.

This module demonstrates how to use the factory function to create
LLM provider instances based on application configuration.
"""

from app.core.config import settings
from app.services.llm import create_llm_provider, LLMProviderError


def get_configured_llm_provider():
    """
    Create an LLM provider instance using application configuration.
    
    This function reads settings from the environment and creates
    the appropriate provider instance. It's designed to be used
    as a dependency injection function.
    
    Returns:
        LLMProvider: Configured provider instance
        
    Raises:
        ValueError: If configured provider is not supported
        LLMProviderError: If provider initialization fails
        
    Example:
        >>> provider = get_configured_llm_provider()
        >>> response = await provider.generate("Hello, world!")
    """
    return create_llm_provider(
        provider_name=settings.LLM_PROVIDER,
        api_key=settings.OPENAI_API_KEY,
        model=settings.OPENAI_MODEL,
        max_tokens=settings.OPENAI_MAX_TOKENS,
        temperature=settings.OPENAI_TEMPERATURE
    )


async def example_basic_usage():
    """
    Example: Basic text generation using configured provider.
    """
    # Create provider from configuration
    provider = get_configured_llm_provider()
    
    # Generate a response
    prompt = "What is the capital of France?"
    response = await provider.generate(prompt)
    
    print(f"Prompt: {prompt}")
    print(f"Response: {response}")
    
    return response


async def example_custom_parameters():
    """
    Example: Text generation with custom parameters.
    """
    provider = get_configured_llm_provider()
    
    # Override default parameters for this specific call
    prompt = "Write a haiku about programming."
    response = await provider.generate(
        prompt=prompt,
        max_tokens=100,
        temperature=0.9  # Higher temperature for more creative output
    )
    
    print(f"Prompt: {prompt}")
    print(f"Response: {response}")
    
    return response


async def example_streaming():
    """
    Example: Streaming text generation.
    """
    provider = get_configured_llm_provider()
    
    prompt = "Tell me a short story about a robot."
    print(f"Prompt: {prompt}")
    print("Response (streaming): ", end="")
    
    # Stream the response
    async for chunk in provider.stream(prompt):
        print(chunk, end="", flush=True)
    
    print()  # New line after streaming


def example_token_counting():
    """
    Example: Count tokens in text.
    """
    provider = get_configured_llm_provider()
    
    texts = [
        "Hello, world!",
        "This is a longer text with more tokens to count.",
        "The quick brown fox jumps over the lazy dog."
    ]
    
    for text in texts:
        token_count = provider.count_tokens(text)
        print(f"Text: {text}")
        print(f"Tokens: {token_count}")
        print()


async def example_error_handling():
    """
    Example: Proper error handling with LLM provider.
    """
    try:
        provider = get_configured_llm_provider()
        response = await provider.generate("Test prompt")
        print(f"Success: {response}")
        
    except ValueError as e:
        # Unsupported provider configured
        print(f"Configuration error: {e}")
        print("Please check your LLM_PROVIDER setting in .env")
        
    except LLMProviderError as e:
        # Provider-specific error (API error, rate limit, etc.)
        print(f"Provider error: {e}")
        print("The LLM service may be unavailable or there may be an API key issue")
        
    except Exception as e:
        # Unexpected error
        print(f"Unexpected error: {e}")


async def example_dependency_injection():
    """
    Example: Using the provider in a service with dependency injection.
    
    This pattern is used throughout the chatbot application to inject
    the LLM provider into services that need it.
    """
    from typing import Optional
    
    class ChatService:
        """Example service that uses LLM provider."""
        
        def __init__(self, llm_provider):
            self.llm_provider = llm_provider
        
        async def generate_greeting(self, user_name: str) -> str:
            """Generate a personalized greeting."""
            prompt = f"Generate a friendly greeting for a user named {user_name}."
            return await self.llm_provider.generate(prompt, max_tokens=50)
        
        async def classify_intent(self, user_message: str) -> str:
            """Classify user intent from message."""
            prompt = f"""
            Classify the intent of this message into one of: greeting, search, booking, faq
            Message: {user_message}
            Intent:
            """
            return await self.llm_provider.generate(prompt, max_tokens=10, temperature=0.0)
    
    # Create service with injected provider
    provider = get_configured_llm_provider()
    chat_service = ChatService(llm_provider=provider)
    
    # Use the service
    greeting = await chat_service.generate_greeting("Alice")
    print(f"Generated greeting: {greeting}")
    
    intent = await chat_service.classify_intent("I want to book a tennis court")
    print(f"Classified intent: {intent}")


# Main execution example
if __name__ == "__main__":
    import asyncio
    
    print("=" * 60)
    print("LLM Provider Factory - Usage Examples")
    print("=" * 60)
    
    # Note: These examples require a valid API key in .env
    # Uncomment to run specific examples:
    
    # asyncio.run(example_basic_usage())
    # asyncio.run(example_custom_parameters())
    # asyncio.run(example_streaming())
    # example_token_counting()
    # asyncio.run(example_error_handling())
    # asyncio.run(example_dependency_injection())
    
    print("\nExamples are defined but not executed.")
    print("Uncomment the desired example in __main__ to run it.")
    print("Make sure you have a valid OPENAI_API_KEY in your .env file.")
