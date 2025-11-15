"""
Integrated LangExtract Service Package

Combines LangExtract document analysis, LLM orchestration coordination, and PROV-O tracking
into a unified service that implements section 3.1 of the JCDL paper.
"""

from .orchestrator import IntegratedLangExtractService

__all__ = ['IntegratedLangExtractService']
