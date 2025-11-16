"""
LangExtract Document Analyzer Package

Stage 1 of Two-Stage Architecture: Performs structured extraction of definitions,
temporal markers, and domain indicators from documents with character-level position
tracking for PROV-O traceability.

This package has been refactored into focused modules for better maintainability:
- analyzer.py: Main coordinator service
- text_preprocessing.py: Text cleaning and preparation
- extraction.py: Core LangExtract structured extraction
- result_processing.py: Process and validate extraction results
- entity_extraction.py: Specialized entity extraction
- orchestration_summary.py: Generate orchestration guidance
- fallback.py: Pattern-based fallback when LangExtract fails
"""

from .analyzer import LangExtractDocumentAnalyzer

__all__ = ['LangExtractDocumentAnalyzer']
