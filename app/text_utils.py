"""
This module provides utility functions for the OntExtract application.
"""
import re

def clean_jstor_boilerplate(text):
    """
    Removes recurring JSTOR boilerplate text from a document.

    Args:
        text (str): The raw text content of the document.

    Returns:
        str: The text content with boilerplate lines removed.
    """
    # This regex targets the specific boilerplate line, allowing for slight variations
    # in IP address, date, and time. It also removes surrounding whitespace.
    boilerplate_pattern = r"^\s*This content downloaded from [\d\.]* on .* All use subject to https://about.jstor.org/terms\s*$"
    
    # Use re.MULTILINE to match the pattern on a per-line basis
    cleaned_text = re.sub(boilerplate_pattern, "", text, flags=re.MULTILINE)
    
    return cleaned_text.strip()
