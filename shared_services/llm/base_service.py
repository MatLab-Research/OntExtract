"""
Base LLM service providing a unified interface for multiple LLM providers.

This service abstracts different LLM providers (OpenAI, Claude, local models)
behind a common interface for text generation and processing.
"""

import os
import logging
from typing import List, Dict, Any, Optional, Union
from abc import ABC, abstractmethod
import requests
import json

logger = logging.getLogger(__name__)

class BaseLLMProvider(ABC):
    """Abstract base class for LLM providers."""
    
    @abstractmethod
    def generate_text(self, 
                     prompt: str, 
                     max_tokens: int = 1000,
                     temperature: float = 0.7,
                     **kwargs) -> str:
        """Generate text from prompt."""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if provider is available."""
        pass
    
    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Get provider name."""
        pass

class OpenAILLMProvider(BaseLLMProvider):
    """OpenAI LLM provider."""
    
    def __init__(self, 
                 api_key: str = None, 
                 model: str = "gpt-3.5-turbo",
                 api_base: str = None):
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        self.model = model
        self.api_base = api_base or os.environ.get("OPENAI_API_BASE", "https://api.openai.com/v1")
    
    def generate_text(self, 
                     prompt: str, 
                     max_tokens: int = 1000,
                     temperature: float = 0.7,
                     **kwargs) -> str:
        """Generate text using OpenAI API."""
        if not self.is_available():
            raise RuntimeError("OpenAI API not available")
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        # Format for chat completion
        messages = [{"role": "user", "content": prompt}]
        
        data = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            **kwargs
        }
        
        response = requests.post(
            f"{self.api_base}/chat/completions",
            headers=headers,
            json=data
        )
        
        if response.status_code != 200:
            raise Exception(f"OpenAI API error: {response.status_code} {response.text}")
        
        result = response.json()
        return result["choices"][0]["message"]["content"]
    
    def is_available(self) -> bool:
        """Check if OpenAI API is available."""
        return (self.api_key and 
                not self.api_key.startswith("your-") and 
                len(self.api_key) > 20)
    
    @property
    def provider_name(self) -> str:
        """Get provider name."""
        return "openai"

class ClaudeLLMProvider(BaseLLMProvider):
    """Claude LLM provider."""
    
    def __init__(self, 
                 api_key: str = None, 
                 model: str = None,
                 api_base: str = None):
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        self.model = model or os.environ.get("CLAUDE_DEFAULT_MODEL", "claude-3-5-sonnet-20241022")
        self.api_base = api_base or os.environ.get("ANTHROPIC_API_BASE", "https://api.anthropic.com/v1")
    
    def generate_text(self, 
                     prompt: str, 
                     max_tokens: int = 1000,
                     temperature: float = 0.7,
                     **kwargs) -> str:
        """Generate text using Claude API."""
        if not self.is_available():
            raise RuntimeError("Claude API not available")
        
        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
            "anthropic-version": os.environ.get("CLAUDE_API_VERSION", "2023-06-01")
        }
        
        data = {
            "model": self.model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            **kwargs
        }
        
        response = requests.post(
            f"{self.api_base}/messages",
            headers=headers,
            json=data
        )
        
        if response.status_code != 200:
            raise Exception(f"Claude API error: {response.status_code} {response.text}")
        
        result = response.json()
        return result["content"][0]["text"]
    
    def is_available(self) -> bool:
        """Check if Claude API is available."""
        return (self.api_key and 
                not self.api_key.startswith("your-") and 
                len(self.api_key) > 20)
    
    @property
    def provider_name(self) -> str:
        """Get provider name."""
        return "claude"

class BaseLLMService:
    """
    Main LLM service that manages multiple providers with fallback support.
    """
    
    def __init__(self, 
                 provider_priority: List[str] = None,
                 default_model: str = None):
        """
        Initialize the LLM service.
        
        Args:
            provider_priority: List of providers in priority order
            default_model: Default model to use
        """
        self.provider_priority = provider_priority or self._get_default_priority()
        self.default_model = default_model
        self.providers = {}
        
        # Initialize providers
        self._setup_providers()
    
    def _get_default_priority(self) -> List[str]:
        """Get default provider priority from environment."""
        priority_str = os.environ.get("LLM_PROVIDER_PRIORITY", "openai,claude")
        return [p.strip().lower() for p in priority_str.split(',')]
    
    def _setup_providers(self):
        """Initialize all configured providers."""
        if "openai" in self.provider_priority:
            self.providers["openai"] = OpenAILLMProvider()
        
        if "claude" in self.provider_priority:
            self.providers["claude"] = ClaudeLLMProvider()
        
        # Log available providers
        available = [name for name, provider in self.providers.items() if provider.is_available()]
        logger.info(f"Available LLM providers: {available}")
    
    def generate_text(self, 
                     prompt: str,
                     max_tokens: int = 1000,
                     temperature: float = 0.7,
                     provider: str = None,
                     **kwargs) -> str:
        """
        Generate text using the first available provider.
        
        Args:
            prompt: Text prompt
            max_tokens: Maximum tokens to generate
            temperature: Generation temperature
            provider: Specific provider to use (optional)
            **kwargs: Additional provider-specific arguments
            
        Returns:
            Generated text
        """
        if not prompt or not prompt.strip():
            return ""
        
        # Use specific provider if requested
        if provider:
            if provider not in self.providers:
                raise ValueError(f"Unknown provider: {provider}")
            
            provider_obj = self.providers[provider]
            if not provider_obj.is_available():
                raise RuntimeError(f"Provider {provider} not available")
            
            return provider_obj.generate_text(
                prompt, max_tokens, temperature, **kwargs
            )
        
        # Try each provider in priority order
        for provider_name in self.provider_priority:
            if provider_name not in self.providers:
                continue
                
            provider_obj = self.providers[provider_name]
            if not provider_obj.is_available():
                continue
            
            try:
                result = provider_obj.generate_text(
                    prompt, max_tokens, temperature, **kwargs
                )
                logger.debug(f"Generated text using {provider_name}")
                return result
            except Exception as e:
                logger.warning(f"Provider {provider_name} failed: {e}")
                continue
        
        # All providers failed
        raise RuntimeError("All LLM providers failed or unavailable")
    
    def get_provider_status(self) -> Dict[str, bool]:
        """
        Get status of all configured providers.
        
        Returns:
            Dictionary mapping provider names to availability status
        """
        return {name: provider.is_available() 
                for name, provider in self.providers.items()}
    
    def list_available_providers(self) -> List[str]:
        """
        Get list of available providers.
        
        Returns:
            List of available provider names
        """
        return [name for name, provider in self.providers.items() 
                if provider.is_available()]
    
    def extract_entities(self, 
                        text: str, 
                        entity_types: List[str] = None,
                        **kwargs) -> List[Dict[str, Any]]:
        """
        Extract entities from text using LLM.
        
        Args:
            text: Text to analyze
            entity_types: Types of entities to extract
            **kwargs: Additional arguments
            
        Returns:
            List of extracted entities
        """
        if not entity_types:
            entity_types = ["PERSON", "ORGANIZATION", "LOCATION", "CONCEPT"]
        
        entity_types_str = ", ".join(entity_types)
        
        prompt = f"""
        Extract entities from the following text. Focus on these entity types: {entity_types_str}
        
        Text: {text}
        
        Return the results as a JSON list of objects with keys: "text", "type", "start", "end", "confidence".
        Only return the JSON, no other text.
        """
        
        try:
            response = self.generate_text(prompt, **kwargs)
            
            # Try to parse JSON response
            import json
            entities = json.loads(response.strip())
            return entities if isinstance(entities, list) else []
            
        except Exception as e:
            logger.error(f"Error extracting entities: {e}")
            return []
    
    def summarize_text(self, 
                      text: str, 
                      max_length: int = 500,
                      **kwargs) -> str:
        """
        Summarize text using LLM.
        
        Args:
            text: Text to summarize
            max_length: Maximum length of summary
            **kwargs: Additional arguments
            
        Returns:
            Summarized text
        """
        prompt = f"""
        Summarize the following text in approximately {max_length} characters or less.
        Focus on the key points and main ideas.
        
        Text: {text}
        
        Summary:
        """
        
        try:
            return self.generate_text(prompt, max_tokens=max_length//4, **kwargs)
        except Exception as e:
            logger.error(f"Error summarizing text: {e}")
            return f"Error: Could not summarize text - {str(e)}"
