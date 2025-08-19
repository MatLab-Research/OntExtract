"""
Temporal Analysis Service for tracking term evolution over time.
This service provides advanced temporal analysis capabilities including:
- Historical term extraction from documents with timestamps
- Semantic drift detection
- Frequency analysis over time periods
- Context evolution tracking
- Integration with ontology mappings for temporal consistency
"""

import json
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from collections import defaultdict, Counter
import logging

logger = logging.getLogger(__name__)


class TemporalAnalysisService:
    """Service for analyzing temporal evolution of terms across documents."""
    
    def __init__(self, ontology_importer=None):
        """
        Initialize the temporal analysis service.
        
        Args:
            ontology_importer: Optional OntologyImporter instance for ontology mappings
        """
        self.ontology_importer = ontology_importer
        self.temporal_cache = {}
        
    def extract_temporal_data(self, documents: List[Any], term: str, 
                             time_periods: List[int]) -> Dict[str, Any]:
        """
        Extract temporal data for a term across documents and time periods.
        
        Args:
            documents: List of document objects with content and metadata
            term: The term to track
            time_periods: List of years/periods to analyze
            
        Returns:
            Dictionary with temporal data for each period
        """
        temporal_data = {}
        
        for period in time_periods:
            period_data = self._analyze_period(documents, term, period)
            temporal_data[str(period)] = period_data
            
        return temporal_data
    
    def _analyze_period(self, documents: List[Any], term: str, period: int) -> Dict[str, Any]:
        """
        Analyze a term within a specific time period.
        
        Args:
            documents: List of documents to analyze
            term: The term to search for
            period: The time period (year) to analyze
            
        Returns:
            Dictionary with analysis results for the period
        """
        # Filter documents for this period
        period_docs = self._filter_documents_by_period(documents, period)
        
        if not period_docs:
            return {
                'definition': None,
                'source': None,
                'evolution': 'absent',
                'contexts': [],
                'frequency': 0,
                'semantic_field': []
            }
        
        # Extract definitions and contexts
        definitions = self._extract_definitions(period_docs, term)
        contexts = self._extract_contexts(period_docs, term)
        frequency = self._calculate_frequency(period_docs, term)
        semantic_field = self._extract_semantic_field(period_docs, term)
        
        # Determine evolution status
        evolution = self._determine_evolution_status(frequency, len(definitions))
        
        # Select best definition
        best_definition = definitions[0] if definitions else None
        
        return {
            'definition': best_definition.get('text') if best_definition else f'No clear definition found for "{term}" in {period}',
            'source': best_definition.get('source') if best_definition else 'Multiple sources',
            'evolution': evolution,
            'contexts': contexts[:5],  # Top 5 contexts
            'frequency': frequency,
            'semantic_field': semantic_field[:10],  # Top 10 related terms
            'definition_count': len(definitions),
            'document_count': len(period_docs)
        }
    
    def _filter_documents_by_period(self, documents: List[Any], period: int, 
                                   window: int = 2) -> List[Any]:
        """
        Filter documents that fall within a time period window.
        
        Args:
            documents: List of all documents
            period: Target year
            window: Years before/after to include
            
        Returns:
            Filtered list of documents
        """
        period_docs = []
        
        for doc in documents:
            # Try to extract year from document metadata or content
            doc_year = self._extract_document_year(doc)
            
            if doc_year and abs(doc_year - period) <= window:
                period_docs.append(doc)
        
        return period_docs
    
    def _extract_document_year(self, document: Any) -> Optional[int]:
        """
        Extract publication year from document metadata or content.
        
        Args:
            document: Document object
            
        Returns:
            Year as integer or None
        """
        # Check metadata first
        if hasattr(document, 'metadata'):
            metadata = document.metadata
            if isinstance(metadata, str):
                try:
                    metadata = json.loads(metadata)
                except:
                    pass
            
            if isinstance(metadata, dict):
                # Look for year in various fields
                for field in ['year', 'publication_year', 'date', 'published']:
                    if field in metadata:
                        try:
                            return int(metadata[field])
                        except:
                            # Try to extract year from date string
                            year_match = re.search(r'\b(19|20)\d{2}\b', str(metadata[field]))
                            if year_match:
                                return int(year_match.group())
        
        # Try to extract from content
        if hasattr(document, 'content'):
            content = document.content[:1000]  # Check first 1000 chars
            year_matches = re.findall(r'\b(19|20)\d{2}\b', content)
            if year_matches:
                # Return most common year
                year_counts = Counter(year_matches)
                return int(year_counts.most_common(1)[0][0])
        
        return None
    
    def _extract_definitions(self, documents: List[Any], term: str) -> List[Dict[str, str]]:
        """
        Extract definitions of a term from documents.
        
        Args:
            documents: List of documents to search
            term: Term to find definitions for
            
        Returns:
            List of definition dictionaries
        """
        definitions = []
        term_lower = term.lower()
        
        # Common definition patterns
        patterns = [
            rf'{re.escape(term)} is defined as ([^.]+)',
            rf'{re.escape(term)} means ([^.]+)',
            rf'{re.escape(term)} refers to ([^.]+)',
            rf'{re.escape(term)}: ([^.]+)',
            rf'define {re.escape(term)} as ([^.]+)',
            rf'{re.escape(term)} \(([^)]+)\)',
        ]
        
        for doc in documents:
            if not hasattr(doc, 'content'):
                continue
                
            content = doc.content
            doc_name = doc.get_display_name() if hasattr(doc, 'get_display_name') else 'Unknown source'
            
            # Search for definitions using patterns
            for pattern in patterns:
                matches = re.finditer(pattern, content, re.IGNORECASE)
                for match in matches:
                    definition_text = match.group(1).strip()
                    if len(definition_text) > 20:  # Filter out very short matches
                        definitions.append({
                            'text': definition_text[:500],  # Limit length
                            'source': doc_name,
                            'pattern': pattern
                        })
            
            # Also look for sentences containing the term
            sentences = re.split(r'[.!?]+', content)
            for sentence in sentences:
                if term_lower in sentence.lower():
                    # Check if sentence appears to be definitional
                    if any(indicator in sentence.lower() for indicator in 
                          ['is a', 'is an', 'are', 'means', 'defined', 'refers to', 'denotes']):
                        definitions.append({
                            'text': sentence.strip()[:500],
                            'source': doc_name,
                            'pattern': 'sentence'
                        })
        
        # Remove duplicates and sort by relevance
        seen = set()
        unique_definitions = []
        for defn in definitions:
            text_key = defn['text'][:100].lower()
            if text_key not in seen:
                seen.add(text_key)
                unique_definitions.append(defn)
        
        return unique_definitions
    
    def _extract_contexts(self, documents: List[Any], term: str) -> List[str]:
        """
        Extract usage contexts for a term.
        
        Args:
            documents: List of documents
            term: Term to find contexts for
            
        Returns:
            List of context strings
        """
        contexts = []
        term_lower = term.lower()
        
        for doc in documents:
            if not hasattr(doc, 'content'):
                continue
                
            # Find sentences containing the term
            sentences = re.split(r'[.!?]+', doc.content)
            for sentence in sentences:
                if term_lower in sentence.lower():
                    # Extract key phrases around the term
                    words = sentence.split()
                    for i, word in enumerate(words):
                        if term_lower in word.lower():
                            # Get surrounding context
                            start = max(0, i - 3)
                            end = min(len(words), i + 4)
                            context = ' '.join(words[start:end])
                            contexts.append(context)
        
        # Group similar contexts
        context_groups = self._group_similar_contexts(contexts)
        
        return context_groups
    
    def _group_similar_contexts(self, contexts: List[str]) -> List[str]:
        """
        Group similar contexts to avoid redundancy.
        
        Args:
            contexts: List of context strings
            
        Returns:
            List of representative contexts
        """
        if not contexts:
            return []
        
        # Simple grouping by common words
        grouped = defaultdict(list)
        
        for context in contexts:
            # Extract key words (excluding common words)
            words = set(context.lower().split())
            common_words = {'the', 'a', 'an', 'is', 'are', 'was', 'were', 'in', 'on', 'at', 'to', 'for', 'of', 'and', 'or'}
            key_words = words - common_words
            
            if key_words:
                # Use first key word as group key
                key = sorted(key_words)[0]
                grouped[key].append(context)
        
        # Select representative from each group
        representatives = []
        for group in grouped.values():
            # Choose the longest context as representative
            representative = max(group, key=len)
            representatives.append(representative)
        
        return representatives[:10]  # Return top 10
    
    def _calculate_frequency(self, documents: List[Any], term: str) -> int:
        """
        Calculate term frequency across documents.
        
        Args:
            documents: List of documents
            term: Term to count
            
        Returns:
            Total frequency count
        """
        frequency = 0
        term_lower = term.lower()
        
        for doc in documents:
            if hasattr(doc, 'content'):
                # Count occurrences (case-insensitive)
                frequency += doc.content.lower().count(term_lower)
        
        return frequency
    
    def _extract_semantic_field(self, documents: List[Any], term: str) -> List[str]:
        """
        Extract semantically related terms that co-occur with the target term.
        
        Args:
            documents: List of documents
            term: Target term
            
        Returns:
            List of related terms
        """
        related_terms = Counter()
        term_lower = term.lower()
        
        for doc in documents:
            if not hasattr(doc, 'content'):
                continue
            
            # Find sentences containing the term
            sentences = re.split(r'[.!?]+', doc.content)
            for sentence in sentences:
                if term_lower in sentence.lower():
                    # Extract nouns and adjectives (simplified)
                    words = re.findall(r'\b[a-z]+\b', sentence.lower())
                    
                    # Filter out common words and the term itself
                    common_words = {'the', 'a', 'an', 'is', 'are', 'was', 'were', 'in', 'on', 'at', 
                                  'to', 'for', 'of', 'and', 'or', 'but', 'with', 'from', 'by', 
                                  'as', 'this', 'that', 'these', 'those', 'it', 'its', 'they', 'their'}
                    
                    for word in words:
                        if word != term_lower and word not in common_words and len(word) > 3:
                            related_terms[word] += 1
        
        # Return most common related terms
        return [term for term, _ in related_terms.most_common(20)]
    
    def _determine_evolution_status(self, frequency: int, definition_count: int) -> str:
        """
        Determine the evolution status of a term based on metrics.
        
        Args:
            frequency: Term frequency in period
            definition_count: Number of definitions found
            
        Returns:
            Evolution status string
        """
        if frequency == 0:
            return 'absent'
        elif frequency < 10:
            return 'emerging'
        elif frequency < 50:
            return 'developing'
        elif definition_count > 3:
            return 'evolving'
        else:
            return 'established'
    
    def analyze_semantic_drift(self, documents: List[Any], term: str, 
                              time_periods: List[int]) -> Dict[str, Any]:
        """
        Analyze semantic drift of a term over time periods.
        
        Args:
            documents: List of documents
            term: Term to analyze
            time_periods: List of time periods
            
        Returns:
            Analysis of semantic drift
        """
        period_semantics = {}
        
        for period in time_periods:
            period_docs = self._filter_documents_by_period(documents, period)
            if period_docs:
                semantic_field = self._extract_semantic_field(period_docs, term)
                period_semantics[period] = set(semantic_field[:10])
        
        # Calculate drift between consecutive periods
        drift_analysis = {
            'periods': {},
            'total_drift': 0,
            'stable_terms': set(),
            'new_terms': {},
            'lost_terms': {}
        }
        
        periods_sorted = sorted(period_semantics.keys())
        
        for i in range(len(periods_sorted)):
            current_period = periods_sorted[i]
            current_terms = period_semantics[current_period]
            
            if i == 0:
                drift_analysis['stable_terms'] = current_terms
            else:
                prev_period = periods_sorted[i-1]
                prev_terms = period_semantics[prev_period]
                
                # Calculate Jaccard similarity
                intersection = current_terms & prev_terms
                union = current_terms | prev_terms
                similarity = len(intersection) / len(union) if union else 0
                drift = 1 - similarity
                
                drift_analysis['periods'][f"{prev_period}-{current_period}"] = {
                    'drift_score': drift,
                    'similarity': similarity,
                    'new_terms': list(current_terms - prev_terms),
                    'lost_terms': list(prev_terms - current_terms),
                    'stable_terms': list(intersection)
                }
                
                drift_analysis['total_drift'] += drift
                drift_analysis['stable_terms'] &= current_terms
                drift_analysis['new_terms'][current_period] = list(current_terms - prev_terms)
                drift_analysis['lost_terms'][current_period] = list(prev_terms - current_terms)
        
        # Calculate average drift
        if len(periods_sorted) > 1:
            drift_analysis['average_drift'] = drift_analysis['total_drift'] / (len(periods_sorted) - 1)
        else:
            drift_analysis['average_drift'] = 0
        
        drift_analysis['stable_terms'] = list(drift_analysis['stable_terms'])
        
        return drift_analysis
    
    def generate_evolution_narrative(self, temporal_data: Dict[str, Any], 
                                    term: str, time_periods: List[int]) -> str:
        """
        Generate a narrative description of term evolution.
        
        Args:
            temporal_data: Temporal analysis data
            term: The analyzed term
            time_periods: List of time periods
            
        Returns:
            Narrative text describing the evolution
        """
        narrative_parts = []
        
        # Introduction
        narrative_parts.append(f"Evolution of '{term}' from {time_periods[0]} to {time_periods[-1]}:\n")
        
        # Analyze each period
        for i, period in enumerate(time_periods):
            period_data = temporal_data.get(str(period), {})
            
            if i == 0:
                # First appearance
                if period_data.get('frequency', 0) > 0:
                    narrative_parts.append(
                        f"\n{period}: The term '{term}' appears with a frequency of {period_data['frequency']}. "
                        f"Status: {period_data.get('evolution', 'unknown')}."
                    )
                    if period_data.get('definition'):
                        narrative_parts.append(f" Primary definition: {period_data['definition'][:200]}...")
            else:
                # Evolution from previous period
                prev_period = time_periods[i-1]
                prev_data = temporal_data.get(str(prev_period), {})
                
                freq_change = period_data.get('frequency', 0) - prev_data.get('frequency', 0)
                
                if freq_change > 0:
                    narrative_parts.append(
                        f"\n{period}: Usage increases by {freq_change} occurrences. "
                    )
                elif freq_change < 0:
                    narrative_parts.append(
                        f"\n{period}: Usage decreases by {abs(freq_change)} occurrences. "
                    )
                else:
                    narrative_parts.append(
                        f"\n{period}: Usage remains stable. "
                    )
                
                # Note evolution status changes
                if period_data.get('evolution') != prev_data.get('evolution'):
                    narrative_parts.append(
                        f"Evolution status changes from '{prev_data.get('evolution')}' to '{period_data.get('evolution')}'. "
                    )
                
                # Note semantic changes
                if period_data.get('semantic_field') and prev_data.get('semantic_field'):
                    current_semantic = set(period_data['semantic_field'][:5])
                    prev_semantic = set(prev_data['semantic_field'][:5])
                    new_associations = current_semantic - prev_semantic
                    
                    if new_associations:
                        narrative_parts.append(
                            f"New semantic associations: {', '.join(list(new_associations)[:3])}. "
                        )
        
        # Summary
        total_freq = sum(temporal_data.get(str(p), {}).get('frequency', 0) for p in time_periods)
        narrative_parts.append(
            f"\n\nSummary: Over {len(time_periods)} periods, '{term}' appeared {total_freq} times total. "
        )
        
        # Identify peak period
        peak_period = max(time_periods, 
                         key=lambda p: temporal_data.get(str(p), {}).get('frequency', 0))
        peak_freq = temporal_data.get(str(peak_period), {}).get('frequency', 0)
        
        narrative_parts.append(
            f"Peak usage occurred in {peak_period} with {peak_freq} occurrences."
        )
        
        return ''.join(narrative_parts)
