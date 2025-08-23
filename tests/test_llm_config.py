#!/usr/bin/env python3
"""
Test script to verify LLM configuration is reading from environment correctly.
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the current directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_llm_configuration():
    """Test that LLM providers are correctly configured from environment."""
    print("=" * 60)
    print("LLM Configuration Test")
    print("=" * 60)
    
    # Check environment variables
    print("\n1. Environment Variables:")
    print("-" * 40)
    
    env_vars = {
        "OPENAI_API_KEY": os.environ.get("OPENAI_API_KEY", "NOT SET"),
        "OPENAI_DEFAULT_MODEL": os.environ.get("OPENAI_DEFAULT_MODEL", "NOT SET"),
        "ANTHROPIC_API_KEY": os.environ.get("ANTHROPIC_API_KEY", "NOT SET"),
        "CLAUDE_DEFAULT_MODEL": os.environ.get("CLAUDE_DEFAULT_MODEL", "NOT SET"),
        "DEFAULT_LLM_PROVIDER": os.environ.get("DEFAULT_LLM_PROVIDER", "NOT SET"),
        "LLM_PROVIDER_PRIORITY": os.environ.get("LLM_PROVIDER_PRIORITY", "NOT SET"),
    }
    
    for key, value in env_vars.items():
        # Mask API keys for security
        if "API_KEY" in key and value != "NOT SET":
            display_value = value[:10] + "..." if len(value) > 10 else "***"
        else:
            display_value = value
        print(f"  {key}: {display_value}")
    
    # Test importing the LLM service
    print("\n2. Testing LLM Service Import:")
    print("-" * 40)
    
    try:
        from shared_services.llm.base_service import BaseLLMService, OpenAILLMProvider, ClaudeLLMProvider
        print("  ✓ Successfully imported LLM service modules")
    except ImportError as e:
        print(f"  ✗ Failed to import LLM service: {e}")
        return
    
    # Test provider initialization
    print("\n3. Testing Provider Initialization:")
    print("-" * 40)
    
    # Test OpenAI provider
    try:
        openai_provider = OpenAILLMProvider()
        print(f"  OpenAI Provider:")
        print(f"    - Model: {openai_provider.model}")
        print(f"    - Available: {openai_provider.is_available()}")
    except Exception as e:
        print(f"  ✗ Failed to initialize OpenAI provider: {e}")
    
    # Test Claude provider
    try:
        claude_provider = ClaudeLLMProvider()
        print(f"  Claude Provider:")
        print(f"    - Model: {claude_provider.model}")
        print(f"    - Available: {claude_provider.is_available()}")
    except Exception as e:
        print(f"  ✗ Failed to initialize Claude provider: {e}")
    
    # Test main LLM service
    print("\n4. Testing Main LLM Service:")
    print("-" * 40)
    
    try:
        llm_service = BaseLLMService()
        print(f"  Provider Priority: {llm_service.provider_priority}")
        print(f"  Available Providers: {llm_service.list_available_providers()}")
        
        status = llm_service.get_provider_status()
        print(f"  Provider Status:")
        for provider, available in status.items():
            print(f"    - {provider}: {'Available' if available else 'Not Available'}")
    except Exception as e:
        print(f"  ✗ Failed to initialize LLM service: {e}")
    
    print("\n" + "=" * 60)
    print("Configuration test complete!")
    print("=" * 60)
    
    # Summary
    print("\nSUMMARY:")
    print("-" * 40)
    
    if os.environ.get("OPENAI_DEFAULT_MODEL"):
        print(f"✓ OpenAI model configured: {os.environ.get('OPENAI_DEFAULT_MODEL')}")
    else:
        print("✗ OpenAI model not configured (will use default: gpt-4o-mini)")
    
    if os.environ.get("CLAUDE_DEFAULT_MODEL"):
        print(f"✓ Claude model configured: {os.environ.get('CLAUDE_DEFAULT_MODEL')}")
    else:
        print("✗ Claude model not configured (will use default: claude-sonnet-4-20250514)")
    
    if os.environ.get("LLM_PROVIDER_PRIORITY") or os.environ.get("DEFAULT_LLM_PROVIDER"):
        priority = os.environ.get("LLM_PROVIDER_PRIORITY") or os.environ.get("DEFAULT_LLM_PROVIDER")
        print(f"✓ Provider priority configured: {priority}")
    else:
        print("✗ Provider priority not configured (will use default: openai,claude)")

if __name__ == "__main__":
    test_llm_configuration()
