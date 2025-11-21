"""
Utility functions for handling LangChain prompt templates.

Provides safe escaping of prompts containing JSON examples or other literal braces.
"""

import re
from typing import Optional


def escape_for_langchain_template(text: str, preserve_variables: Optional[list[str]] = None) -> str:
    """
    Escape curly braces in text for use in LangChain ChatPromptTemplate.

    LangChain uses {variable_name} syntax for template variables. Any literal
    braces (like in JSON examples) must be escaped as {{ or }}.

    Args:
        text: Text to escape
        preserve_variables: List of variable names to preserve (not escape)

    Returns:
        Text with literal braces escaped for LangChain

    Examples:
        >>> escape_for_langchain_template('{"key": "value"}')
        '{{"key": "value"}}'

        >>> escape_for_langchain_template('Use {variable} here', preserve_variables=['variable'])
        'Use {variable} here'
    """
    if preserve_variables is None:
        preserve_variables = []

    # If no variables to preserve, simply escape all braces
    if not preserve_variables:
        return text.replace('{', '{{').replace('}', '}}')

    # Build regex pattern to match variables: {var1}|{var2}|...
    var_pattern = '|'.join(re.escape(f'{{{var}}}') for var in preserve_variables)

    # Split text into parts: preserved variables and everything else
    parts = re.split(f'({var_pattern})', text)

    # Escape braces in non-variable parts
    result = []
    for part in parts:
        # Check if this part is a preserved variable
        is_preserved = any(part == f'{{{var}}}' for var in preserve_variables)
        if is_preserved:
            result.append(part)
        else:
            # Escape all braces in non-variable parts
            result.append(part.replace('{', '{{').replace('}', '}}'))

    return ''.join(result)


def should_escape_prompt(text: str) -> bool:
    """
    Check if a prompt contains unescaped braces that could cause LangChain errors.

    Args:
        text: Prompt text to check

    Returns:
        True if prompt contains literal braces that need escaping
    """
    # Look for patterns like {"key": or { "key":  (JSON)
    json_pattern = r'\{\s*"[^"]+"\s*:'
    return bool(re.search(json_pattern, text))
