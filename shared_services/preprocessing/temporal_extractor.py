"""
Temporal Word Usage Extractor for linguistic evolution analysis.

This module extracts word usage patterns, contexts, collocations, and syntactic
roles from historical texts to track how language evolves over time.
"""

import re
import logging
from typing import Dict, List, Any, Optional, Tuple, Set
from collections import defaultdict, Counter
from dataclasses import dataclass, field
import json
import nltk
from datetime import datetime

logger = logging.getLogger(__name__)

# Download required NLTK data if not present
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')
    
try:
    nltk.data.find('taggers/averaged_perceptron_tagger')
except LookupError:
    nltk.download('averaged_perceptron_tagger')
    
try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('stopwords')

from nltk.tokenize import word_tokenize, sent_tokenize
from nltk.tag import pos_tag
from nltk.corpus import stopwords

@dataclass
class WordUsageContext:
    """Context information for a word usage instance."""
    word: str
    lemma: Optional[str] = None
    pos_tag: Optional[str] = None
    sentence: str = ""
    left_context: List[str] = field(default_factory=list)
    right_context: List[str] = field(default_factory=list)
    sentence_position: int = 0
    document_position: int = 0
    semantic_unit_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'word': self.word,
            'lemma': self.lemma,
            'pos_tag': self.pos_tag,
            'sentence': self.sentence,
            'left_context': self.left_context,
            'right_context': self.right_context,
            'sentence_position': self.sentence_position,
            'document_position': self.document_position,
            'semantic_unit_id': self.semantic_unit_id
        }

@dataclass
class Collocation:
    """Collocation pattern with frequency and context."""
    words: Tuple[str, ...]
    frequency: int = 0
    contexts: List[str] = field(default_factory=list)
    mutual_information: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'words': list(self.words),
            'frequency': self.frequency,
            'contexts': self.contexts[:5],  # Limit contexts to save space
            'mutual_information': self.mutual_information
        }

@dataclass
class SemanticField:
    """Semantic field or domain classification."""
    name: str
    confidence: float
    related_terms: List[str] = field(default_factory=list)
    indicators: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'name': self.name,
            'confidence': self.confidence,
            'related_terms': self.related_terms,
            'indicators': self.indicators
        }

@dataclass
class TemporalWordUsage:
    """Complete temporal word usage analysis results."""
    period: str
    year: Optional[int]
    word_contexts: Dict[str, List[WordUsageContext]]
    collocations: Dict[str, List[Collocation]]
    syntactic_patterns: Dict[str, Dict[str, int]]
    semantic_fields: Dict[str, List[SemanticField]]
    frequency_distribution: Dict[str, int]
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'period': self.period,
            'year': self.year,
            'word_contexts': {
                word: [ctx.to_dict() for ctx in contexts]
                for word, contexts in list(self.word_contexts.items())[:100]  # Limit for size
            },
            'collocations': {
                word: [col.to_dict() for col in cols]
                for word, cols in list(self.collocations.items())[:100]
            },
            'syntactic_patterns': dict(list(self.syntactic_patterns.items())[:100]),
            'semantic_fields': {
                word: [field.to_dict() for field in fields]
                for word, fields in list(self.semantic_fields.items())[:100]
            },
            'frequency_distribution': dict(list(self.frequency_distribution.items())[:1000]),
            'metadata': self.metadata
        }

class TemporalWordUsageExtractor:
    """
    Extracts detailed word usage patterns from historical texts for
    tracking linguistic evolution over time.
    """
    
    # Semantic field indicators (simplified - could be expanded)
    SEMANTIC_FIELDS = {
        'science': ['experiment', 'hypothesis', 'theory', 'observation', 'evidence', 
                   'research', 'study', 'analysis', 'data', 'method'],
        'religion': ['god', 'faith', 'prayer', 'church', 'soul', 'divine', 'holy',
                    'sacred', 'worship', 'spiritual', 'heaven', 'hell'],
        'politics': ['government', 'parliament', 'law', 'vote', 'election', 'policy',
                    'minister', 'democracy', 'republic', 'citizen', 'rights'],
        'commerce': ['trade', 'merchant', 'market', 'price', 'goods', 'commerce',
                    'business', 'profit', 'sell', 'buy', 'currency', 'exchange'],
        'military': ['war', 'battle', 'soldier', 'army', 'weapon', 'fight', 'defense',
                    'attack', 'victory', 'defeat', 'general', 'troops'],
        'social': ['society', 'community', 'family', 'friend', 'marriage', 'class',
                  'status', 'honor', 'reputation', 'custom', 'tradition'],
        'technology': ['machine', 'engine', 'invention', 'innovation', 'electric',
                      'telegraph', 'railway', 'steam', 'industry', 'factory'],
        'arts': ['art', 'painting', 'music', 'poetry', 'literature', 'theater',
                'performance', 'artist', 'creative', 'aesthetic', 'beauty']
    }
    
    def __init__(self, context_window: int = 5, min_collocation_freq: int = 3):
        """
        Initialize the extractor.
        
        Args:
            context_window: Number of words to capture on each side of target
            min_collocation_freq: Minimum frequency for collocation detection
        """
        self.context_window = context_window
        self.min_collocation_freq = min_collocation_freq
        self.stop_words = set(stopwords.words('english'))
        
        # Add historical stop words
        self.stop_words.update(['thou', 'thy', 'thee', 'ye', 'hath', 'doth'])
    
    def extract_usage(self, processed_doc: Any) -> TemporalWordUsage:
        """
        Extract temporal word usage patterns from a processed historical document.
        
        Args:
            processed_doc: ProcessedHistoricalDocument object
            
        Returns:
            TemporalWordUsage object with extracted patterns
        """
        # Initialize collections
        word_contexts = defaultdict(list)
        collocations = defaultdict(list)
        syntactic_patterns = defaultdict(lambda: defaultdict(int))
        semantic_fields = defaultdict(list)
        frequency_distribution = Counter()
        
        # Process each semantic unit
        for unit in processed_doc.semantic_units:
            unit_text = unit['text']
            unit_id = f"{unit['type']}_{unit['index']}"
            
            # Extract contexts and patterns from this unit
            self._extract_unit_patterns(
                unit_text, unit_id,
                word_contexts, collocations,
                syntactic_patterns, frequency_distribution
            )
        
        # Analyze semantic fields for frequent words
        top_words = [word for word, _ in frequency_distribution.most_common(500)]
        for word in top_words:
            if word.lower() not in self.stop_words:
                fields = self._classify_semantic_field(word, word_contexts[word])
                if fields:
                    semantic_fields[word] = fields
        
        # Calculate collocation strength
        self._calculate_collocation_strength(collocations, frequency_distribution)
        
        # Build metadata
        metadata = {
            'extraction_date': datetime.now().isoformat(),
            'total_words': sum(frequency_distribution.values()),
            'unique_words': len(frequency_distribution),
            'semantic_units_processed': len(processed_doc.semantic_units),
            'context_window': self.context_window
        }
        
        return TemporalWordUsage(
            period=processed_doc.temporal_metadata.period_name,
            year=processed_doc.temporal_metadata.year,
            word_contexts=dict(word_contexts),
            collocations=dict(collocations),
            syntactic_patterns=dict(syntactic_patterns),
            semantic_fields=dict(semantic_fields),
            frequency_distribution=dict(frequency_distribution),
            metadata=metadata
        )
    
    def _extract_unit_patterns(self, text: str, unit_id: str,
                              word_contexts: Dict, collocations: Dict,
                              syntactic_patterns: Dict, frequency_dist: Counter):
        """Extract patterns from a single semantic unit."""
        sentences = sent_tokenize(text)
        doc_position = 0
        
        for sent_idx, sentence in enumerate(sentences):
            # Tokenize and tag
            tokens = word_tokenize(sentence.lower())
            pos_tags = pos_tag(tokens)
            
            # Process each word
            for i, (word, pos) in enumerate(pos_tags):
                if not word.isalpha():
                    continue
                
                # Update frequency
                frequency_dist[word] += 1
                
                # Extract context
                left_context = tokens[max(0, i-self.context_window):i]
                right_context = tokens[i+1:min(len(tokens), i+self.context_window+1)]
                
                context = WordUsageContext(
                    word=word,
                    pos_tag=pos,
                    sentence=sentence,
                    left_context=left_context,
                    right_context=right_context,
                    sentence_position=i,
                    document_position=doc_position + i,
                    semantic_unit_id=unit_id
                )
                word_contexts[word].append(context)
                
                # Track syntactic patterns
                syntactic_patterns[word][pos] += 1
                
                # Extract collocations (bigrams and trigrams)
                if i > 0:
                    bigram = (tokens[i-1], word)
                    if all(w.isalpha() for w in bigram):
                        self._add_collocation(collocations, bigram, sentence)
                
                if i > 1:
                    trigram = (tokens[i-2], tokens[i-1], word)
                    if all(w.isalpha() for w in trigram):
                        self._add_collocation(collocations, trigram, sentence)
            
            doc_position += len(tokens)
    
    def _add_collocation(self, collocations: Dict, words: Tuple, context: str):
        """Add a collocation instance."""
        # Skip if contains stop words (except for specific patterns)
        if len([w for w in words if w not in self.stop_words]) < 2:
            return
        
        key = ' '.join(words)
        found = False
        
        for col in collocations[key]:
            if col.words == words:
                col.frequency += 1
                if len(col.contexts) < 10:  # Limit stored contexts
                    col.contexts.append(context[:100])
                found = True
                break
        
        if not found:
            collocations[key].append(Collocation(
                words=words,
                frequency=1,
                contexts=[context[:100]]
            ))
    
    def _calculate_collocation_strength(self, collocations: Dict, frequency_dist: Counter):
        """Calculate mutual information scores for collocations."""
        total_words = sum(frequency_dist.values())
        
        for word_key, cols in collocations.items():
            for col in cols:
                if col.frequency < self.min_collocation_freq:
                    continue
                
                # Calculate pointwise mutual information
                words = col.words
                if len(words) == 2:
                    p_xy = col.frequency / total_words
                    p_x = frequency_dist.get(words[0], 1) / total_words
                    p_y = frequency_dist.get(words[1], 1) / total_words
                    
                    if p_x > 0 and p_y > 0 and p_xy > 0:
                        import math
                        col.mutual_information = math.log2(p_xy / (p_x * p_y))
    
    def _classify_semantic_field(self, word: str, contexts: List[WordUsageContext]) -> List[SemanticField]:
        """Classify word into semantic fields based on context."""
        fields = []
        
        # Gather all context words
        context_words = set()
        for ctx in contexts[:20]:  # Sample contexts
            context_words.update(ctx.left_context)
            context_words.update(ctx.right_context)
        
        # Check each semantic field
        for field_name, indicators in self.SEMANTIC_FIELDS.items():
            overlap = context_words.intersection(set(indicators))
            if overlap:
                confidence = len(overlap) / len(indicators)
                if confidence > 0.1:  # Threshold for field assignment
                    fields.append(SemanticField(
                        name=field_name,
                        confidence=confidence,
                        related_terms=list(overlap)[:5],
                        indicators=indicators[:5]
                    ))
        
        return fields
