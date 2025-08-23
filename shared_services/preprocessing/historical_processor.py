"""
Historical Document Processor for temporal linguistic analysis.

This module handles processing of historical documents including newspapers,
period books, and other time-stamped texts for tracking word evolution.
"""

import re
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, date
from dataclasses import dataclass, field
import json

logger = logging.getLogger(__name__)

@dataclass
class TemporalMetadata:
    """Metadata about the temporal context of a document."""
    publication_date: Optional[date] = None
    period_name: Optional[str] = None
    year: Optional[int] = None
    decade: Optional[int] = None
    century: Optional[int] = None
    confidence: float = 0.0
    extraction_method: str = "unknown"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'publication_date': self.publication_date.isoformat() if self.publication_date else None,
            'period_name': self.period_name,
            'year': self.year,
            'decade': self.decade,
            'century': self.century,
            'confidence': self.confidence,
            'extraction_method': self.extraction_method
        }

@dataclass
class ProcessedHistoricalDocument:
    """Result of processing a historical document."""
    temporal_metadata: TemporalMetadata
    original_text: str
    normalized_text: str
    semantic_units: List[Dict[str, Any]]
    columns: Optional[List[str]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'temporal_metadata': self.temporal_metadata.to_dict(),
            'original_text': self.original_text,
            'normalized_text': self.normalized_text,
            'semantic_units': self.semantic_units,
            'columns': self.columns,
            'metadata': self.metadata
        }

class HistoricalDocumentProcessor:
    """
    Specialized processor for newspaper articles and period books.
    Handles OCR, layout analysis, and temporal metadata extraction.
    """
    
    # Historical spelling variations mapping
    HISTORICAL_SPELLINGS = {
        # Early Modern English (1500-1700)
        'hath': 'has',
        'doth': 'does',
        'thou': 'you',
        'thy': 'your',
        'thee': 'you',
        'ye': 'you',
        'whilſt': 'whilst',
        'ſ': 's',  # Long s
        'vpon': 'upon',
        'haue': 'have',
        'giue': 'give',
        'doe': 'do',
        'vp': 'up',
        'vs': 'us',
        'euery': 'every',
        'onely': 'only',
        'publick': 'public',
        'musick': 'music',
        'compleat': 'complete',
        'shew': 'show',
        'chuse': 'choose'
    }
    
    # Date patterns for different periods
    DATE_PATTERNS = [
        # Modern format: 2024-01-15, 01/15/2024
        (r'\b(\d{4})-(\d{1,2})-(\d{1,2})\b', 'iso'),
        (r'\b(\d{1,2})/(\d{1,2})/(\d{4})\b', 'us'),
        (r'\b(\d{1,2})-(\d{1,2})-(\d{4})\b', 'us'),
        
        # Historical formats: 15th January, 1850
        (r'\b(\d{1,2})(?:st|nd|rd|th)?\s+([A-Za-z]+),?\s+(\d{4})\b', 'historical'),
        (r'\b([A-Za-z]+)\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+(\d{4})\b', 'historical'),
        
        # Year only
        (r'\b(1[5-9]\d{2}|2[0-1]\d{2})\b', 'year'),
        
        # Roman numerals for centuries
        (r'\b([MDCLXVI]+)\s+century\b', 'century')
    ]
    
    def __init__(self, google_services_enabled: bool = False):
        """
        Initialize the processor.
        
        Args:
            google_services_enabled: Whether to use Google Document AI/NLP services
        """
        self.google_services_enabled = google_services_enabled
        
        if google_services_enabled:
            try:
                from .google_integration import GoogleServicesIntegration
                self.google_services = GoogleServicesIntegration()
            except ImportError:
                logger.warning("Google services requested but not available")
                self.google_services = None
                self.google_services_enabled = False
        else:
            self.google_services = None
    
    def process_historical_document(self, document: Any) -> ProcessedHistoricalDocument:
        """
        Process a historical document with temporal analysis.
        
        Args:
            document: Document object with content and metadata
            
        Returns:
            ProcessedHistoricalDocument with extracted information
        """
        # Extract text content
        if hasattr(document, 'content'):
            text = document.content
        elif hasattr(document, 'full_text'):
            text = document.full_text
        else:
            text = str(document)
        
        # Extract temporal metadata
        temporal_metadata = self.extract_temporal_metadata(text, document)
        
        # Process with Google services if available and document is scanned
        columns = None
        if self.google_services_enabled and self.google_services and self._is_scanned(document):
            try:
                ocr_result = self.google_services.ocr_with_layout(document.file_path)
                text = ocr_result['text']
                columns = ocr_result.get('columns', None)
            except Exception as e:
                logger.error(f"Error with Google OCR: {e}")
        
        # Normalize historical spelling
        normalized_text = self.normalize_historical_spelling(text, temporal_metadata.period_name)
        
        # Extract semantic units
        semantic_units = self.extract_semantic_units(normalized_text)
        
        # Build metadata
        metadata = {
            'source_type': self._detect_source_type(document),
            'language': self._detect_language(text),
            'word_count': len(normalized_text.split()),
            'processing_date': datetime.now().isoformat()
        }
        
        return ProcessedHistoricalDocument(
            temporal_metadata=temporal_metadata,
            original_text=text,
            normalized_text=normalized_text,
            semantic_units=semantic_units,
            columns=columns,
            metadata=metadata
        )
    
    def extract_temporal_metadata(self, text: str, document: Any = None) -> TemporalMetadata:
        """
        Extract temporal metadata from document text and metadata.
        
        Args:
            text: Document text
            document: Optional document object with metadata
            
        Returns:
            TemporalMetadata object
        """
        metadata = TemporalMetadata()
        
        # Try to extract from document metadata first
        if document and hasattr(document, 'metadata'):
            doc_meta = document.metadata if isinstance(document.metadata, dict) else {}
            
            # Check various metadata fields
            for field in ['publication_date', 'date', 'year', 'created_at']:
                if field in doc_meta:
                    metadata = self._parse_date_field(doc_meta[field], metadata)
                    metadata.extraction_method = 'metadata'
                    metadata.confidence = 0.9
                    break
        
        # Extract from text if not found in metadata
        if not metadata.year:
            metadata = self._extract_date_from_text(text, metadata)
        
        # Derive period information
        if metadata.year:
            metadata.decade = (metadata.year // 10) * 10
            metadata.century = ((metadata.year - 1) // 100) + 1
            metadata.period_name = self._get_period_name(metadata.year)
        
        return metadata
    
    def normalize_historical_spelling(self, text: str, period: Optional[str] = None) -> str:
        """
        Normalize historical spelling variations to modern equivalents.
        
        Args:
            text: Original text
            period: Historical period name
            
        Returns:
            Normalized text
        """
        normalized = text
        
        # Apply historical spelling corrections
        for old_spelling, modern_spelling in self.HISTORICAL_SPELLINGS.items():
            # Use word boundaries for whole word replacement
            pattern = r'\b' + re.escape(old_spelling) + r'\b'
            normalized = re.sub(pattern, modern_spelling, normalized, flags=re.IGNORECASE)
        
        # Handle long s (ſ) specially
        normalized = normalized.replace('ſ', 's')
        
        # Normalize whitespace
        normalized = re.sub(r'\s+', ' ', normalized)
        
        # Fix common OCR errors in historical texts
        if period and 'early' in period.lower():
            normalized = self._fix_historical_ocr_errors(normalized)
        
        return normalized.strip()
    
    def extract_semantic_units(self, text: str) -> List[Dict[str, Any]]:
        """
        Extract semantic units (articles, chapters, sections) from text.
        
        Args:
            text: Normalized document text
            
        Returns:
            List of semantic units with metadata
        """
        units = []
        
        # Try to identify newspaper articles (multiple short pieces)
        article_boundaries = self._detect_article_boundaries(text)
        if article_boundaries:
            for i, (start, end) in enumerate(article_boundaries):
                unit_text = text[start:end]
                units.append({
                    'type': 'article',
                    'index': i,
                    'text': unit_text,
                    'start_pos': start,
                    'end_pos': end,
                    'title': self._extract_title(unit_text),
                    'word_count': len(unit_text.split())
                })
        
        # Try to identify book chapters
        chapter_boundaries = self._detect_chapter_boundaries(text)
        if chapter_boundaries:
            for i, (start, end) in enumerate(chapter_boundaries):
                unit_text = text[start:end]
                units.append({
                    'type': 'chapter',
                    'index': i,
                    'text': unit_text,
                    'start_pos': start,
                    'end_pos': end,
                    'title': self._extract_title(unit_text),
                    'word_count': len(unit_text.split())
                })
        
        # If no clear structure, treat as single unit
        if not units:
            units.append({
                'type': 'document',
                'index': 0,
                'text': text,
                'start_pos': 0,
                'end_pos': len(text),
                'title': None,
                'word_count': len(text.split())
            })
        
        return units
    
    def _parse_date_field(self, date_value: Any, metadata: TemporalMetadata) -> TemporalMetadata:
        """Parse date from various field formats."""
        if isinstance(date_value, str):
            # Try parsing ISO format
            try:
                dt = datetime.fromisoformat(date_value.replace('Z', '+00:00'))
                metadata.publication_date = dt.date()
                metadata.year = dt.year
            except:
                # Try extracting year
                year_match = re.search(r'\b(1[5-9]\d{2}|2[0-1]\d{2})\b', date_value)
                if year_match:
                    metadata.year = int(year_match.group(1))
        elif isinstance(date_value, (int, float)):
            if 1500 <= date_value <= 2100:
                metadata.year = int(date_value)
        elif isinstance(date_value, datetime):
            metadata.publication_date = date_value.date()
            metadata.year = date_value.year
        elif isinstance(date_value, date):
            metadata.publication_date = date_value
            metadata.year = date_value.year
            
        return metadata
    
    def _extract_date_from_text(self, text: str, metadata: TemporalMetadata) -> TemporalMetadata:
        """Extract date information from document text."""
        # Look for dates in first 500 characters (likely header/metadata area)
        search_text = text[:min(500, len(text))]
        
        for pattern, format_type in self.DATE_PATTERNS:
            matches = re.finditer(pattern, search_text, re.IGNORECASE)
            for match in matches:
                if format_type == 'year':
                    year = int(match.group(1))
                    if 1500 <= year <= 2100:
                        metadata.year = year
                        metadata.extraction_method = 'text_pattern'
                        metadata.confidence = 0.7
                        return metadata
                elif format_type == 'iso':
                    year = int(match.group(1))
                    month = int(match.group(2))
                    day = int(match.group(3))
                    try:
                        metadata.publication_date = date(year, month, day)
                        metadata.year = year
                        metadata.extraction_method = 'text_pattern'
                        metadata.confidence = 0.8
                        return metadata
                    except ValueError:
                        continue
        
        return metadata
    
    def _get_period_name(self, year: int) -> str:
        """Get historical period name for a given year."""
        if year < 1500:
            return "Medieval"
        elif year < 1600:
            return "Early Modern (16th century)"
        elif year < 1700:
            return "Early Modern (17th century)"
        elif year < 1800:
            return "Enlightenment (18th century)"
        elif year < 1850:
            return "Early 19th century"
        elif year < 1900:
            return "Late 19th century"
        elif year < 1920:
            return "Early 20th century"
        elif year < 1945:
            return "Interwar period"
        elif year < 1970:
            return "Post-war period"
        elif year < 2000:
            return "Late 20th century"
        else:
            return "21st century"
    
    def _detect_article_boundaries(self, text: str) -> List[Tuple[int, int]]:
        """Detect boundaries of newspaper articles in text."""
        boundaries = []
        
        # Look for article patterns (headlines followed by body text)
        # This is a simplified heuristic - could be enhanced with ML
        article_pattern = r'([A-Z][A-Z\s,\-\']+[.!?]?\n+)'
        
        matches = list(re.finditer(article_pattern, text))
        for i, match in enumerate(matches):
            start = match.start()
            end = matches[i+1].start() if i+1 < len(matches) else len(text)
            
            # Check if this looks like an article (minimum length, etc.)
            article_text = text[start:end]
            if len(article_text.split()) > 50:  # At least 50 words
                boundaries.append((start, end))
        
        return boundaries
    
    def _detect_chapter_boundaries(self, text: str) -> List[Tuple[int, int]]:
        """Detect chapter boundaries in book text."""
        boundaries = []
        
        # Look for chapter headings
        chapter_pattern = r'((?:CHAPTER|Chapter|Chap\.?)\s+[IVXLCDM\d]+[^\n]*\n)'
        
        matches = list(re.finditer(chapter_pattern, text))
        for i, match in enumerate(matches):
            start = match.start()
            end = matches[i+1].start() if i+1 < len(matches) else len(text)
            boundaries.append((start, end))
        
        return boundaries
    
    def _extract_title(self, text: str) -> Optional[str]:
        """Extract title from beginning of text unit."""
        lines = text.split('\n')
        for line in lines[:5]:  # Check first 5 lines
            line = line.strip()
            if line and len(line) < 100 and line[0].isupper():
                return line
        return None
    
    def _detect_source_type(self, document: Any) -> str:
        """Detect the type of source document."""
        if hasattr(document, 'metadata') and isinstance(document.metadata, dict):
            source_type = document.metadata.get('source_type', '')
            if source_type:
                return source_type
        
        # Try to infer from filename or content
        if hasattr(document, 'filename'):
            filename = document.filename.lower()
            if 'news' in filename or 'gazette' in filename or 'times' in filename:
                return 'newspaper'
            elif 'book' in filename or 'chapter' in filename:
                return 'book'
        
        return 'unknown'
    
    def _detect_language(self, text: str) -> str:
        """Detect the language of the text."""
        # Simple heuristic - could be enhanced with langdetect library
        # For now, assume English for historical texts
        return 'en'
    
    def _is_scanned(self, document: Any) -> bool:
        """Check if document is a scanned image requiring OCR."""
        if hasattr(document, 'file_type'):
            return document.file_type.lower() in ['pdf', 'png', 'jpg', 'jpeg', 'tiff']
        return False
    
    def _fix_historical_ocr_errors(self, text: str) -> str:
        """Fix common OCR errors in historical texts."""
        # Common OCR substitutions in old texts
        ocr_fixes = {
            'tlie': 'the',
            'tbe': 'the',
            'aud': 'and',
            'iu': 'in',
            'ou': 'on',
            'bo': 'be',
            'ot': 'of',
            'thc': 'the',
            'aud': 'and'
        }
        
        for error, correction in ocr_fixes.items():
            text = re.sub(r'\b' + error + r'\b', correction, text, flags=re.IGNORECASE)
        
        return text
