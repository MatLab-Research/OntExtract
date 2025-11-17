# LLM Configuration Guide

**Last Updated**: November 16, 2025
**Version**: 1.0
**Status**: Production Ready ✅

---

## Overview

OntExtract uses a **task-specific LLM configuration system** that automatically selects the optimal AI model for each type of operation. This approach balances performance, cost, and capability based on the specific requirements of each task.

### Benefits

- ✅ **Cost Optimization**: Use expensive models only where needed
- ✅ **Performance**: Fast models for simple tasks, capable models for complex analysis
- ✅ **Flexibility**: Easy to swap providers or models via environment variables
- ✅ **Centralized Management**: Single source of truth for all LLM configuration
- ✅ **Provider Independence**: Support for Gemini, Claude, and GPT models

---

## Model Selection Strategy

### Task Categories

OntExtract identifies 6 distinct task types, each with specific model requirements:

| Task Type | Default Model | Provider | Use Case | Cost |
|-----------|--------------|----------|----------|------|
| **Extraction** | gemini-2.5-flash | Google | Structured data extraction, definitions, temporal markers | 💰 Low |
| **Synthesis** | claude-sonnet-4-5-20250929 | Anthropic | Complex reasoning, semantic analysis, cross-document synthesis | 💰💰💰 High |
| **Orchestration** | claude-haiku-4-5-20251001 | Anthropic | Tool routing, task coordination, confidence scoring | 💰 Low |
| **OED Parsing** | gemini-2.5-pro | Google | Complex dictionary parsing, nested structures | 💰💰 Medium |
| **Long Context** | claude-sonnet-4-5-20250929 | Anthropic | Long documents (200k+ tokens), multi-document comparison | 💰💰💰 High |
| **Classification** | gemini-2.5-flash-lite | Google | Fast categorization, domain detection | 💰 Very Low |

### Latest Verified Models (November 2025)

All model IDs have been verified as of November 16, 2025:

- **Gemini 2.5 Flash**: `gemini-2.5-flash` (stable since June 2025)
- **Gemini 2.5 Flash-Lite**: `gemini-2.5-flash-lite` (stable since Nov 13, 2025)
- **Gemini 2.5 Pro**: `gemini-2.5-pro` (stable)
- **Claude Sonnet 4.5**: `claude-sonnet-4-5-20250929` (released Sep 29, 2025)
- **Claude Haiku 4.5**: `claude-haiku-4-5-20251001` (released Oct 15, 2025)
- **GPT-5 mini**: `gpt-5-mini` (stable since Aug 2025)
- **GPT-5.1**: `gpt-5.1` (released Nov 2025)

---

## Configuration

### Environment Variables

Configure LLM models via environment variables in your `.env` file:

```bash
# Provider API Keys (Required)
GOOGLE_GEMINI_API_KEY=your_gemini_api_key_here
ANTHROPIC_API_KEY=your_anthropic_api_key_here
OPENAI_API_KEY=your_openai_api_key_here  # Optional

# Task-Specific Model Configuration (Optional - uses defaults if not set)
# Extraction tasks
LLM_EXTRACTION_PROVIDER=gemini
LLM_EXTRACTION_MODEL=gemini-2.5-flash

# Synthesis tasks
LLM_SYNTHESIS_PROVIDER=anthropic
LLM_SYNTHESIS_MODEL=claude-sonnet-4-5-20250929

# Orchestration tasks
LLM_ORCHESTRATION_PROVIDER=anthropic
LLM_ORCHESTRATION_MODEL=claude-haiku-4-5-20251001

# OED parsing tasks
LLM_OED_PARSING_PROVIDER=gemini
LLM_OED_PARSING_MODEL=gemini-2.5-pro

# Long context tasks
LLM_LONG_CONTEXT_PROVIDER=anthropic
LLM_LONG_CONTEXT_MODEL=claude-sonnet-4-5-20250929

# Classification tasks
LLM_CLASSIFICATION_PROVIDER=gemini
LLM_CLASSIFICATION_MODEL=gemini-2.5-flash-lite

# Fallback
LLM_FALLBACK_PROVIDER=openai
LLM_FALLBACK_MODEL=gpt-5.1
```

### Using Defaults

If you don't set task-specific environment variables, OntExtract will use the recommended defaults from `config/__init__.py`. This is the recommended approach for most users.

**Minimum required configuration**:
```bash
# Only API keys are required - models will use optimal defaults
GOOGLE_GEMINI_API_KEY=your_key_here
ANTHROPIC_API_KEY=your_key_here
```

---

## Usage in Code

### Using LLMConfigManager

The `LLMConfigManager` provides a clean interface for accessing LLM configuration:

```python
from config.llm_config import get_llm_config, LLMTaskType

# Get the singleton config manager
llm_config = get_llm_config()

# Get configuration for specific task
extraction_config = llm_config.get_extraction_config()
# Returns: {'provider': 'gemini', 'model': 'gemini-2.5-flash', 'api_key': '...', ...}

# Or get provider and model directly
provider, model = llm_config.get_model_for_task(LLMTaskType.ORCHESTRATION)
# Returns: ('anthropic', 'claude-haiku-4-5-20251001')

# Get API key for a provider
api_key = llm_config.get_api_key_for_provider('gemini')
```

### Service Integration Example

Here's how services integrate with the LLM configuration system:

```python
from config.llm_config import get_llm_config, LLMTaskType
import logging

logger = logging.getLogger(__name__)

class MyService:
    def __init__(self, provider=None, model_id=None):
        """Initialize with optional provider/model override"""
        llm_config = get_llm_config()

        if provider is None or model_id is None:
            # Use task-specific configuration
            task_config = llm_config.get_extraction_config()
            self.provider = provider or task_config['provider']
            self.model_id = model_id or task_config['model']
            self.api_key = task_config['api_key']
        else:
            # Use provided override
            self.provider = provider
            self.model_id = model_id
            self.api_key = llm_config.get_api_key_for_provider(provider)

        if not self.api_key:
            raise ValueError(f"API key required for {self.provider} provider")

        logger.info(f"✓ Initialized with {self.provider} provider, model: {self.model_id}")
```

### Configuration Validation

Validate all LLM configurations at startup:

```python
from config.llm_config import get_llm_config

llm_config = get_llm_config()
validation_results = llm_config.validate_configuration()

if not validation_results['valid']:
    print("⚠️ Missing API keys for:", validation_results['missing_api_keys'])
else:
    print("✅ All LLM configurations valid")

# View all configured providers
for provider, info in validation_results['providers'].items():
    print(f"{provider}: {info['tasks_using']}")
```

---

## Cost Optimization Tips

### 1. Use Appropriate Models for Each Task

Don't use expensive models for simple tasks:

```bash
# ❌ Expensive: Using Sonnet for everything
LLM_EXTRACTION_MODEL=claude-sonnet-4-5-20250929  # $3/$15 per 1M tokens
LLM_CLASSIFICATION_MODEL=claude-sonnet-4-5-20250929

# ✅ Optimized: Use task-specific models
LLM_EXTRACTION_MODEL=gemini-2.5-flash  # $0.10/$0.40 per 1M tokens
LLM_CLASSIFICATION_MODEL=gemini-2.5-flash-lite  # $0.10/$0.40 per 1M tokens
```

### 2. Consider Claude Haiku 4.5 for Fast Tasks

Claude Haiku 4.5 (Oct 2025) is significantly faster than Haiku 3.5 at 1/3 the cost of Sonnet 4.5:

```bash
# Perfect for orchestration, routing, classification
LLM_ORCHESTRATION_MODEL=claude-haiku-4-5-20251001  # $1/$5 per 1M tokens
```

### 3. Estimated Cost Comparison

Typical monthly costs for 1 million tokens (input/output combined):

| Model | Cost per 1M tokens | Best For |
|-------|-------------------|----------|
| gemini-2.5-flash-lite | $0.25 | High-volume classification |
| gemini-2.5-flash | $0.25 | Structured extraction |
| claude-haiku-4-5 | $3.00 | Fast routing decisions |
| gemini-2.5-pro | TBD | Complex parsing |
| claude-sonnet-4-5 | $9.00 | Complex analysis only |

---

## Troubleshooting

### Missing API Keys

**Error**: `ValueError: API key required for gemini provider`

**Solution**: Add the required API key to your `.env` file:
```bash
GOOGLE_GEMINI_API_KEY=your_key_here
```

### Provider Not Supported

**Error**: `NotImplementedError: Claude provider not yet supported by LangExtract`

**Solution**: LangExtract currently only supports Gemini. Use Gemini for extraction tasks:
```bash
LLM_EXTRACTION_PROVIDER=gemini
```

### Model Not Found

**Error**: `Model 'gemini-2.5-flash-old' not found`

**Solution**: Update to latest verified model IDs (see table above):
```bash
LLM_EXTRACTION_MODEL=gemini-2.5-flash
```

---

## Advanced Configuration

### Override Models for Specific Use Cases

You can override the default model for specific operations:

```python
from app.services.langextract_document_analyzer import LangExtractExtractor

# Use default extraction model (gemini-2.5-flash)
analyzer = LangExtractExtractor()

# Override with specific model
analyzer = LangExtractExtractor(provider='gemini', model_id='gemini-2.5-pro')
```

### Multi-Provider Fallback

The configuration system automatically falls back to alternative providers if the primary is unavailable:

```python
llm_config = get_llm_config()

# If orchestration provider fails, fallback to GPT-5.1
orchestration_config = llm_config.get_orchestration_config()  # Try Claude Haiku 4.5
if not orchestration_config['api_key']:
    fallback_provider, fallback_model = llm_config.get_model_for_task(LLMTaskType.FALLBACK)
```

### View All Configurations

```python
from config.llm_config import get_llm_config

llm_config = get_llm_config()
all_configs = llm_config.get_all_configurations()

for task_name, config in all_configs.items():
    print(f"{task_name}: {config['model']} ({config['provider']})")
```

---

## Migration from Old Configuration

### Before (Direct Environment Access)

```python
import os

# Old approach - direct environment variable access
api_key = os.environ.get('GOOGLE_GEMINI_API_KEY')
model = 'gemini-1.5-flash'  # Hardcoded model
```

### After (LLMConfigManager)

```python
from config.llm_config import get_llm_config

# New approach - centralized configuration
llm_config = get_llm_config()
config = llm_config.get_extraction_config()
api_key = config['api_key']
model = config['model']  # Task-specific, configurable
```

---

## Best Practices

1. ✅ **Use defaults** unless you have specific requirements
2. ✅ **Set API keys** in `.env` file, not in code
3. ✅ **Validate configuration** at application startup
4. ✅ **Log model selection** for debugging and cost tracking
5. ✅ **Use task-specific models** to optimize cost
6. ✅ **Consider Haiku 4.5** for fast, economical tasks
7. ✅ **Update model IDs** when new stable versions are released

---

## References

- [Anthropic Claude Models](https://docs.anthropic.com/en/docs/about-claude/models/overview)
- [Google Gemini API](https://ai.google.dev/gemini-api/docs/models)
- [OpenAI Models](https://platform.openai.com/docs/models)
- OntExtract Configuration: `config/__init__.py`
- LLM Config Manager: `config/llm_config.py`

---

**Questions or Issues?** Check `REFACTORING_PROGRESS.md` for latest updates or consult the development team.
