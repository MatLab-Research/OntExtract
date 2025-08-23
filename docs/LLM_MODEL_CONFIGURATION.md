# LLM Model Configuration Guide

## Overview

This guide explains how to configure the latest Large Language Model (LLM) providers for OntExtract. The system supports multiple providers with automatic fallback capabilities.

## Latest Models (January 2025)

### Claude Models (Anthropic)

| Model | API Name | Description | Use Case |
|-------|----------|-------------|----------|
| Claude Opus 4.1 | `claude-opus-4-1-20250805` | Most capable and intelligent model | Complex reasoning, advanced coding |
| Claude Sonnet 4 | `claude-sonnet-4-20250514` | High-performance model | Balanced performance and cost |
| Claude Sonnet 3.7 | `claude-3-7-sonnet-20250219` | Extended thinking capabilities | Tasks requiring deep analysis |
| Claude Haiku 3.5 | `claude-3-5-haiku-20241022` | Fastest model | Quick responses, simple tasks |

**Default:** `claude-sonnet-4-20250514` (Claude Sonnet 4)

### OpenAI Models

| Model | API Name | Description | Use Case |
|-------|----------|-------------|----------|
| GPT-4o | `gpt-4o` | Latest multimodal model | Vision + text tasks |
| GPT-4o Mini | `gpt-4o-mini` | Cost-effective multimodal | Balanced performance |
| GPT-4 Turbo | `gpt-4-turbo` | Latest GPT-4 Turbo | High-quality text generation |
| GPT-3.5 Turbo | `gpt-3.5-turbo` | Fast and cost-effective | Quick, simple tasks |

**Default:** `gpt-4o` (GPT-4o)

## Configuration

### Environment Variables

Models are configured through environment variables in your `.env` file:

```bash
# Claude Configuration
CLAUDE_DEFAULT_MODEL=claude-sonnet-4-20250514
CLAUDE_API_VERSION=2023-06-01

# OpenAI Configuration  
OPENAI_DEFAULT_MODEL=gpt-4o

# Provider Priority
LLM_PROVIDER_PRIORITY=anthropic,openai
# Or use DEFAULT_LLM_PROVIDER for backwards compatibility
DEFAULT_LLM_PROVIDER=anthropic
```

### Model Selection Priority

The system selects models based on:
1. **Explicit model specification** in code
2. **Environment variable** (`CLAUDE_DEFAULT_MODEL` or `OPENAI_DEFAULT_MODEL`)
3. **Hardcoded defaults** in code

### Provider Priority

When no specific provider is requested, the system tries providers in order:
1. First checks `DEFAULT_LLM_PROVIDER` environment variable
2. Falls back to `LLM_PROVIDER_PRIORITY` (comma-separated list)
3. Default order: `openai,claude`

## How It Works

### Automatic Fallback

If the primary provider fails or is unavailable, the system automatically tries the next provider:

```python
# Example: System tries Claude first, falls back to OpenAI if needed
LLM_PROVIDER_PRIORITY=claude,openai
```

### Model Configuration in Code

The models are referenced from environment variables in `shared_services/llm/base_service.py`:

```python
# Claude provider reads from environment
self.model = os.environ.get("CLAUDE_DEFAULT_MODEL", "claude-sonnet-4-20250514")

# OpenAI provider reads from environment
self.model = os.environ.get("OPENAI_DEFAULT_MODEL", "gpt-4o-mini")
```

## Testing Configuration

Run the test script to verify your configuration:

```bash
python test_llm_config.py
```

This will show:
- Current environment variables
- Available providers
- Active models
- Provider status

## Switching Models

To switch to a different model:

### Option 1: Update `.env` file
```bash
# For Claude Opus 4.1 (most capable)
CLAUDE_DEFAULT_MODEL=claude-opus-4-1-20250805

# For Claude Haiku 3.5 (fastest)
CLAUDE_DEFAULT_MODEL=claude-3-5-haiku-20241022

# For GPT-4o Mini (cost-effective)
OPENAI_DEFAULT_MODEL=gpt-4o-mini
```

### Option 2: Set environment variable directly
```bash
export CLAUDE_DEFAULT_MODEL=claude-opus-4-1-20250805
```

## Advanced Configuration

### Temperature Settings

Control creativity vs consistency:

```bash
LLM_TEMPERATURE_DEFAULT=0.7   # Balanced
LLM_TEMPERATURE_CREATIVE=0.9  # More creative
LLM_TEMPERATURE_ANALYTICAL=0.3 # More focused
```

### Token Limits

Control response length:

```bash
LLM_MAX_TOKENS_DEFAULT=1000   # Standard responses
LLM_MAX_TOKENS_SUMMARY=500    # Summaries
LLM_MAX_TOKENS_EXTENDED=4000  # Long-form content
```

## Troubleshooting

### Provider Not Available

If a provider shows as "Not Available":
1. Check API key is set correctly
2. Verify API key is valid (not starting with "your-")
3. Ensure API key has sufficient length (>20 characters)

### Model Not Found

If you get a model not found error:
1. Verify model name is correct (check spelling)
2. Ensure you're using the full model name with date
3. Check if the model is available in your API plan

### Testing a Specific Model

To test a specific model directly:

```python
from shared_services.llm.base_service import BaseLLMService

# Initialize service
llm_service = BaseLLMService()

# Test with specific provider
response = llm_service.generate_text(
    prompt="Hello, which model are you?",
    provider="claude"  # or "openai"
)
```

## Best Practices

1. **Use environment variables** - Never hardcode API keys or models in code
2. **Set appropriate defaults** - Choose models that balance capability and cost
3. **Configure fallbacks** - Ensure system reliability with provider priority
4. **Test regularly** - Run configuration tests after updates
5. **Monitor usage** - Track API costs and adjust models as needed

## Updates

Models are updated regularly. To stay current:
1. Check provider documentation for new models
2. Update environment variables with new model names
3. Test thoroughly before deploying to production

## Resources

- [Anthropic Models Documentation](https://docs.anthropic.com/en/docs/about-claude/models)
- [OpenAI Models Documentation](https://platform.openai.com/docs/models)
- [OntExtract Documentation](../README.md)
