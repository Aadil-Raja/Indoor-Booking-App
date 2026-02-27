# LLM Provider Factory Usage Guide

## Overview

The `create_llm_provider()` factory function provides a simple way to instantiate LLM providers based on configuration, enabling easy switching between different language model services (OpenAI, Gemini, etc.) without code changes.

## Factory Function

```python
from app.services.llm import create_llm_provider

def create_llm_provider(
    provider_name: str,
    api_key: str,
    model: Optional[str] = None,
    max_tokens: Optional[int] = None,
    temperature: Optional[float] = None,
    max_retries: int = 3,
    retry_delay: float = 1.0
) -> LLMProvider
```

### Parameters

- **provider_name** (str): Name of the provider ("openai" or "gemini")
  - Case insensitive
  - Whitespace is trimmed
  
- **api_key** (str): API key for the provider
  
- **model** (Optional[str]): Model name
  - OpenAI default: "gpt-4o-mini"
  - Gemini default: "gemini-pro"
  
- **max_tokens** (Optional[int]): Default max tokens for generation
  - Default: 500
  
- **temperature** (Optional[float]): Default temperature for generation
  - Default: 0.7
  - Range: 0.0 to 2.0
  
- **max_retries** (int): Maximum number of retry attempts
  - Default: 3
  
- **retry_delay** (float): Initial delay between retries in seconds
  - Default: 1.0
  - Uses exponential backoff

### Returns

- **LLMProvider**: Configured provider instance implementing the LLMProvider interface

### Raises

- **ValueError**: If provider_name is not supported
- **LLMProviderError**: If provider initialization fails

## Usage Examples

### Basic Usage with Settings

```python
from app.services.llm import create_llm_provider
from app.core.config import settings

# Create provider using configuration settings
provider = create_llm_provider(
    provider_name=settings.LLM_PROVIDER,
    api_key=settings.OPENAI_API_KEY,
    model=settings.OPENAI_MODEL,
    max_tokens=settings.OPENAI_MAX_TOKENS,
    temperature=settings.OPENAI_TEMPERATURE
)

# Use the provider
response = await provider.generate("What is the capital of France?")
print(response)
```

### OpenAI Provider with Defaults

```python
from app.services.llm import create_llm_provider

# Create OpenAI provider with defaults
provider = create_llm_provider(
    provider_name="openai",
    api_key="your-api-key-here"
)

# Provider will use:
# - model: "gpt-4o-mini"
# - max_tokens: 500
# - temperature: 0.7
```

### OpenAI Provider with Custom Parameters

```python
from app.services.llm import create_llm_provider

# Create OpenAI provider with custom settings
provider = create_llm_provider(
    provider_name="openai",
    api_key="your-api-key-here",
    model="gpt-4",
    max_tokens=1000,
    temperature=0.5,
    max_retries=5,
    retry_delay=2.0
)
```

### Gemini Provider (Placeholder)

```python
from app.services.llm import create_llm_provider

# Create Gemini provider (not yet implemented)
provider = create_llm_provider(
    provider_name="gemini",
    api_key="your-gemini-api-key",
    model="gemini-pro"
)

# Note: Gemini provider will raise NotImplementedError when methods are called
```

### Case Insensitive Provider Names

```python
# All of these work:
provider1 = create_llm_provider("openai", api_key)
provider2 = create_llm_provider("OPENAI", api_key)
provider3 = create_llm_provider("OpenAI", api_key)
provider4 = create_llm_provider("  openai  ", api_key)  # whitespace trimmed
```

### Error Handling

```python
from app.services.llm import create_llm_provider, LLMProviderError

try:
    provider = create_llm_provider(
        provider_name="unsupported-provider",
        api_key="test-key"
    )
except ValueError as e:
    print(f"Invalid provider: {e}")
    # Output: Unsupported LLM provider: 'unsupported-provider'

try:
    provider = create_llm_provider(
        provider_name="openai",
        api_key="invalid-key"
    )
    response = await provider.generate("test")
except LLMProviderError as e:
    print(f"Provider error: {e}")
```

## Configuration

The factory function is designed to work with the application's configuration system. Configure your provider in `.env`:

```env
# LLM Provider Selection
LLM_PROVIDER=openai

# OpenAI Configuration
OPENAI_API_KEY=your-openai-api-key-here
OPENAI_MODEL=gpt-4o-mini
OPENAI_MAX_TOKENS=500
OPENAI_TEMPERATURE=0.7
```

Then use it in your application:

```python
from app.core.config import settings
from app.services.llm import create_llm_provider

def get_llm_provider():
    """Dependency injection function for LLM provider."""
    return create_llm_provider(
        provider_name=settings.LLM_PROVIDER,
        api_key=settings.OPENAI_API_KEY,
        model=settings.OPENAI_MODEL,
        max_tokens=settings.OPENAI_MAX_TOKENS,
        temperature=settings.OPENAI_TEMPERATURE
    )
```

## Switching Providers

To switch from OpenAI to Gemini (when implemented), simply update your `.env` file:

```env
# Change from:
LLM_PROVIDER=openai

# To:
LLM_PROVIDER=gemini
```

No code changes required! The factory will automatically create the appropriate provider instance.

## Provider Interface

All providers created by the factory implement the `LLMProvider` interface:

```python
class LLMProvider(ABC):
    async def generate(
        self,
        prompt: str,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        **kwargs: Any
    ) -> str:
        """Generate text completion."""
        pass
    
    async def stream(
        self,
        prompt: str,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        **kwargs: Any
    ) -> AsyncIterator[str]:
        """Generate streaming text completion."""
        pass
    
    def count_tokens(self, text: str) -> int:
        """Count tokens in text."""
        pass
```

## Supported Providers

### OpenAI (Implemented)
- Provider name: `"openai"`
- Models: gpt-4o-mini, gpt-4, gpt-3.5-turbo, etc.
- Features: Full implementation with retry logic and token counting
- Status: ✅ Production ready

### Gemini (Placeholder)
- Provider name: `"gemini"`
- Models: gemini-pro, gemini-pro-vision
- Features: Placeholder implementation
- Status: ⚠️ Not yet implemented (raises NotImplementedError)

## Best Practices

1. **Use Configuration**: Always use settings from `app.core.config` rather than hardcoding values
2. **Error Handling**: Wrap provider calls in try-except blocks to handle errors gracefully
3. **Dependency Injection**: Create provider instances through dependency injection for testability
4. **Logging**: The factory logs provider creation and errors automatically
5. **Testing**: Mock the factory function in tests to avoid actual API calls

## Related Files

- `app/services/llm/__init__.py` - Factory implementation
- `app/services/llm/base.py` - LLMProvider interface and exceptions
- `app/services/llm/openai_provider.py` - OpenAI implementation
- `app/services/llm/gemini_provider.py` - Gemini placeholder
- `app/core/config.py` - Configuration settings
- `.env` - Environment variables
