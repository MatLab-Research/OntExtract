"""
Core Document Processing Tools

Pure Python implementations that can be used by:
1. Manual UI (direct function calls)
2. MCP Server (exposed via FastMCP)
3. LangChain orchestration (tool binding)

All tools return standardized ProcessingResult objects with PROV-O tracking.
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
import uuid


@dataclass
class ProcessingResult:
    """
    Standardized output format for all processing tools.

    Includes PROV-O provenance tracking for research reproducibility.
    """
    tool_name: str
    status: str  # success, error, partial
    data: Any
    metadata: Dict[str, Any]
    provenance: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return asdict(self)


class DocumentProcessor:
    """
    Core document processing tools.

    Each method is a standalone tool that can be called directly,
    exposed via MCP, or bound to LangChain.
    """

    def __init__(self, user_id: Optional[int] = None, experiment_id: Optional[int] = None):
        """
        Initialize processor with optional context.

        Args:
            user_id: ID of user running the tool (for provenance)
            experiment_id: ID of experiment (for provenance)
        """
        self.user_id = user_id
        self.experiment_id = experiment_id

    def _generate_provenance(self, tool_name: str, input_data: Any = None) -> Dict[str, Any]:
        """
        Generate PROV-O provenance record for tool execution.

        Args:
            tool_name: Name of the tool
            input_data: Optional input data description

        Returns:
            PROV-O compatible provenance dictionary
        """
        execution_id = str(uuid.uuid4())
        timestamp = datetime.utcnow().isoformat()

        return {
            "activity_id": f"urn:ontextract:activity:{execution_id}",
            "tool": tool_name,
            "started_at": timestamp,
            "ended_at": timestamp,
            "agent": f"urn:ontextract:user:{self.user_id}" if self.user_id else "urn:ontextract:agent:system",
            "experiment": f"urn:ontextract:experiment:{self.experiment_id}" if self.experiment_id else None,
            "input_summary": str(input_data)[:200] if input_data else None
        }

    # ========================================================================
    # SEGMENTATION TOOLS
    # ========================================================================

    def segment_paragraph(self, text: str) -> ProcessingResult:
        """
        Split document text into paragraphs.

        Uses regex pattern for robust paragraph splitting (handles various whitespace patterns).

        Args:
            text: The document text to segment

        Returns:
            ProcessingResult with list of paragraphs (minimum 10 chars each)
        """
        try:
            import re

            # Robust paragraph splitting that handles various whitespace patterns
            paragraphs = re.split(r'\n\s*\n', text.strip())

            # Filter empty paragraphs and very short ones (< 10 chars)
            paragraphs = [p.strip() for p in paragraphs if p.strip() and len(p.strip()) > 10]

            metadata = {
                "count": len(paragraphs),
                "avg_length": sum(len(p) for p in paragraphs) / len(paragraphs) if paragraphs else 0,
                "total_chars": len(text),
                "method": "regex_paragraph_split",
                "min_length": 10
            }

            return ProcessingResult(
                tool_name="segment_paragraph",
                status="success",
                data=paragraphs,
                metadata=metadata,
                provenance=self._generate_provenance("segment_paragraph", f"{len(text)} chars")
            )

        except Exception as e:
            return ProcessingResult(
                tool_name="segment_paragraph",
                status="error",
                data=[],
                metadata={"error": str(e)},
                provenance=self._generate_provenance("segment_paragraph")
            )

    def segment_sentence(self, text: str) -> ProcessingResult:
        """
        Split text into sentences using NLTK sentence tokenizer.

        Requires: nltk, punkt tokenizer

        Args:
            text: The document text to segment

        Returns:
            ProcessingResult with list of sentences
        """
        try:
            import nltk
            from nltk.tokenize import sent_tokenize

            # Download punkt if not already available
            try:
                nltk.data.find('tokenizers/punkt')
            except LookupError:
                nltk.download('punkt', quiet=True)

            sentences = sent_tokenize(text)

            metadata = {
                "count": len(sentences),
                "avg_length": sum(len(s) for s in sentences) / len(sentences) if sentences else 0,
                "method": "nltk_punkt"
            }

            return ProcessingResult(
                tool_name="segment_sentence",
                status="success",
                data=sentences,
                metadata=metadata,
                provenance=self._generate_provenance("segment_sentence", f"{len(text)} chars")
            )

        except ImportError:
            return ProcessingResult(
                tool_name="segment_sentence",
                status="error",
                data=[],
                metadata={"error": "NLTK not installed. Run: pip install nltk"},
                provenance=self._generate_provenance("segment_sentence")
            )
        except Exception as e:
            return ProcessingResult(
                tool_name="segment_sentence",
                status="error",
                data=[],
                metadata={"error": str(e)},
                provenance=self._generate_provenance("segment_sentence")
            )

    # ========================================================================
    # EXTRACTION TOOLS (Stubs for now - will implement next)
    # ========================================================================

    def extract_entities_spacy(self, text: str) -> ProcessingResult:
        """
        Extract named entities using spaCy NER.

        Extracts standard named entities (PERSON, ORG, GPE, DATE, etc.) and
        also identifies noun phrases as potential concepts.

        Requires: spacy, en_core_web_sm model

        Args:
            text: The document text to analyze

        Returns:
            ProcessingResult with list of entities containing:
            - entity: the entity text
            - type: entity type (PERSON, ORG, etc.)
            - start: character start position
            - end: character end position
            - confidence: extraction confidence score
        """
        try:
            import spacy
            from collections import defaultdict

            # Load spaCy model
            try:
                nlp = spacy.load('en_core_web_sm')
            except OSError:
                return ProcessingResult(
                    tool_name="extract_entities_spacy",
                    status="error",
                    data=[],
                    metadata={"error": "spaCy model not found. Run: python -m spacy download en_core_web_sm"},
                    provenance=self._generate_provenance("extract_entities_spacy")
                )

            # Process text
            doc = nlp(text)

            entities = []
            entity_counts = defaultdict(int)

            # Extract named entities
            for ent in doc.ents:
                entities.append({
                    'entity': ent.text,
                    'type': ent.label_,
                    'start': ent.start_char,
                    'end': ent.end_char,
                    'confidence': 0.85  # spaCy NER typically has high confidence
                })
                entity_counts[ent.label_] += 1

            # Extract significant noun phrases as potential concepts
            for chunk in doc.noun_chunks:
                # Only include noun phrases that aren't already entities
                # and have some substance (not just pronouns/determiners)
                if (len(chunk.text) > 3 and
                    not all(token.is_stop for token in chunk) and
                    any(token.pos_ in ['PROPN', 'NOUN'] for token in chunk)):

                    # Check if this noun phrase overlaps with existing entities
                    is_duplicate = any(
                        ent['start'] <= chunk.start_char < ent['end'] or
                        ent['start'] < chunk.end_char <= ent['end']
                        for ent in entities
                    )

                    if not is_duplicate:
                        entities.append({
                            'entity': chunk.text,
                            'type': 'CONCEPT',
                            'start': chunk.start_char,
                            'end': chunk.end_char,
                            'confidence': 0.65  # Lower confidence for noun phrases
                        })
                        entity_counts['CONCEPT'] += 1

            metadata = {
                "total_entities": len(entities),
                "entity_types": dict(entity_counts),
                "unique_types": len(entity_counts),
                "method": "spacy_ner_plus_noun_chunks",
                "model": "en_core_web_sm",
                "text_length": len(text)
            }

            return ProcessingResult(
                tool_name="extract_entities_spacy",
                status="success",
                data=entities,
                metadata=metadata,
                provenance=self._generate_provenance("extract_entities_spacy", f"{len(text)} chars")
            )

        except ImportError:
            return ProcessingResult(
                tool_name="extract_entities_spacy",
                status="error",
                data=[],
                metadata={"error": "spaCy not installed. Run: pip install spacy && python -m spacy download en_core_web_sm"},
                provenance=self._generate_provenance("extract_entities_spacy")
            )
        except Exception as e:
            return ProcessingResult(
                tool_name="extract_entities_spacy",
                status="error",
                data=[],
                metadata={"error": str(e)},
                provenance=self._generate_provenance("extract_entities_spacy")
            )

    def extract_temporal(self, text: str) -> ProcessingResult:
        """
        Extract temporal expressions and timelines.

        Extracts dates, time periods, and temporal markers using:
        - spaCy DATE entities
        - Regex patterns for common date formats
        - Historical period markers (e.g., "1950s", "early 2000s")
        - Relative time expressions (e.g., "last year", "recently")

        Args:
            text: The document text to analyze

        Returns:
            ProcessingResult with temporal expressions containing:
            - text: the temporal expression
            - type: temporal type (DATE, PERIOD, RELATIVE, etc.)
            - start: character start position
            - end: character end position
            - normalized: normalized form if parseable
        """
        try:
            import spacy
            import re
            from datetime import datetime
            from dateutil import parser as date_parser

            # Load spaCy model
            try:
                nlp = spacy.load('en_core_web_sm')
            except OSError:
                return ProcessingResult(
                    tool_name="extract_temporal",
                    status="error",
                    data=[],
                    metadata={"error": "spaCy model not found. Run: python -m spacy download en_core_web_sm"},
                    provenance=self._generate_provenance("extract_temporal")
                )

            # Process text with spaCy
            doc = nlp(text)

            temporal_expressions = []
            seen_positions = set()

            # Extract DATE entities from spaCy
            for ent in doc.ents:
                if ent.label_ == 'DATE':
                    # Try to normalize the date
                    normalized = None
                    try:
                        parsed_date = date_parser.parse(ent.text, fuzzy=True)
                        normalized = parsed_date.isoformat()
                    except:
                        normalized = ent.text

                    temporal_expressions.append({
                        'text': ent.text,
                        'type': 'DATE',
                        'start': ent.start_char,
                        'end': ent.end_char,
                        'normalized': normalized,
                        'confidence': 0.85
                    })
                    seen_positions.add((ent.start_char, ent.end_char))

            # Define regex patterns for temporal expressions
            temporal_patterns = [
                # Years (1900s, 2020, etc.)
                (r'\b(1[6-9]\d{2}|20[0-2]\d)\b', 'YEAR'),
                # Decades (1950s, 1960's, etc.)
                (r'\b(1[6-9]\d{2}|20[0-2]\d)s\b', 'DECADE'),
                # Century markers (19th century, twentieth century)
                (r'\b(\d{1,2}(?:st|nd|rd|th)\s+century|(?:eighteenth|nineteenth|twentieth|twenty-first)\s+century)\b', 'CENTURY'),
                # Periods (early/mid/late X)
                (r'\b(early|mid|late|middle)\s+(1[6-9]\d{2}|20[0-2]\d)s?\b', 'PERIOD'),
                # Historical periods
                (r'\b(Industrial Revolution|Renaissance|Victorian era|Cold War|World War (I|II|1|2))\b', 'HISTORICAL_PERIOD'),
                # Relative time
                (r'\b(recently|lately|nowadays|currently|presently|historically|traditionally)\b', 'RELATIVE'),
                # Temporal markers
                (r'\b(before|after|during|since|until|from|throughout|between)\s+(\d{4}|\d{4}s)\b', 'TEMPORAL_MARKER'),
            ]

            # Apply regex patterns
            for pattern, temp_type in temporal_patterns:
                for match in re.finditer(pattern, text, re.IGNORECASE):
                    start_pos = match.start()
                    end_pos = match.end()

                    # Skip if this position is already covered by spaCy
                    if any(start <= start_pos < end or start < end_pos <= end
                           for start, end in seen_positions):
                        continue

                    matched_text = match.group()
                    normalized = matched_text

                    # Try to normalize specific types
                    if temp_type in ['YEAR', 'DECADE']:
                        try:
                            # Extract year number
                            year_match = re.search(r'\d{4}', matched_text)
                            if year_match:
                                year = int(year_match.group())
                                if temp_type == 'DECADE':
                                    normalized = f"{year}-{year+9}"
                                else:
                                    normalized = str(year)
                        except:
                            pass

                    temporal_expressions.append({
                        'text': matched_text,
                        'type': temp_type,
                        'start': start_pos,
                        'end': end_pos,
                        'normalized': normalized,
                        'confidence': 0.75
                    })
                    seen_positions.add((start_pos, end_pos))

            # Sort by position in text
            temporal_expressions.sort(key=lambda x: x['start'])

            # Calculate metadata
            type_counts = {}
            for expr in temporal_expressions:
                type_counts[expr['type']] = type_counts.get(expr['type'], 0) + 1

            metadata = {
                "total_expressions": len(temporal_expressions),
                "expression_types": type_counts,
                "unique_types": len(type_counts),
                "method": "spacy_ner_plus_regex",
                "text_length": len(text)
            }

            return ProcessingResult(
                tool_name="extract_temporal",
                status="success",
                data=temporal_expressions,
                metadata=metadata,
                provenance=self._generate_provenance("extract_temporal", f"{len(text)} chars")
            )

        except ImportError as e:
            missing_module = "spaCy" if "spacy" in str(e).lower() else "dateutil"
            return ProcessingResult(
                tool_name="extract_temporal",
                status="error",
                data=[],
                metadata={"error": f"{missing_module} not installed. Run: pip install spacy python-dateutil"},
                provenance=self._generate_provenance("extract_temporal")
            )
        except Exception as e:
            return ProcessingResult(
                tool_name="extract_temporal",
                status="error",
                data=[],
                metadata={"error": str(e)},
                provenance=self._generate_provenance("extract_temporal")
            )

    def extract_causal(self, text: str) -> ProcessingResult:
        """
        Extract causal relationships between events.

        Uses pattern matching and dependency parsing to identify:
        - Explicit causal markers (because, since, therefore, etc.)
        - Consequence markers (result in, lead to, cause, etc.)
        - Conditional causation (if...then patterns)

        Args:
            text: The document text to analyze

        Returns:
            ProcessingResult with causal relationships containing:
            - cause: the causing event/condition
            - effect: the resulting event/state
            - marker: the causal marker word/phrase
            - confidence: extraction confidence score
            - start: character start position
            - end: character end position
        """
        try:
            import spacy
            import re

            # Load spaCy model
            try:
                nlp = spacy.load('en_core_web_sm')
            except OSError:
                return ProcessingResult(
                    tool_name="extract_causal",
                    status="error",
                    data=[],
                    metadata={"error": "spaCy model not found. Run: python -m spacy download en_core_web_sm"},
                    provenance=self._generate_provenance("extract_causal")
                )

            # Process text
            doc = nlp(text)

            causal_relations = []

            # Define causal markers and their patterns
            causal_markers = {
                # Backward causation (effect mentioned first)
                'backward': [
                    'because', 'since', 'as', 'due to', 'owing to', 'on account of',
                    'thanks to', 'as a result of', 'because of', 'given that'
                ],
                # Forward causation (cause mentioned first)
                'forward': [
                    'therefore', 'thus', 'hence', 'consequently', 'as a result',
                    'so', 'accordingly', 'for this reason', 'leads to', 'results in',
                    'causes', 'produces', 'brings about', 'gives rise to',
                    'contributes to', 'triggers', 'prompts'
                ],
                # Conditional causation
                'conditional': [
                    'if', 'when', 'whenever', 'in case', 'provided that',
                    'assuming that', 'on condition that'
                ]
            }

            # Process sentences
            for sent in doc.sents:
                sent_text = sent.text.strip()

                # Pattern 1: Backward causation (Effect because Cause)
                for marker in causal_markers['backward']:
                    pattern = r'(.+?)\s+' + re.escape(marker) + r'\s+(.+?)(?:[.;]|$)'
                    matches = re.finditer(pattern, sent_text, re.IGNORECASE)

                    for match in matches:
                        effect = match.group(1).strip()
                        cause = match.group(2).strip()

                        if len(cause) > 10 and len(effect) > 10:  # Filter very short matches
                            causal_relations.append({
                                'cause': cause,
                                'effect': effect,
                                'marker': marker,
                                'type': 'backward',
                                'confidence': 0.75,
                                'start': sent.start_char + match.start(),
                                'end': sent.start_char + match.end(),
                                'sentence': sent_text
                            })

                # Pattern 2: Forward causation (Cause therefore Effect)
                for marker in causal_markers['forward']:
                    # Build regex pattern
                    pattern = r'(.+?)\s+' + re.escape(marker) + r'\s+(.+?)(?:[.;]|$)'
                    matches = re.finditer(pattern, sent_text, re.IGNORECASE)

                    for match in matches:
                        cause = match.group(1).strip()
                        effect = match.group(2).strip()

                        if len(cause) > 10 and len(effect) > 10:
                            causal_relations.append({
                                'cause': cause,
                                'effect': effect,
                                'marker': marker,
                                'type': 'forward',
                                'confidence': 0.75,
                                'start': sent.start_char + match.start(),
                                'end': sent.start_char + match.end(),
                                'sentence': sent_text
                            })

                # Pattern 3: Conditional causation (If Cause then Effect)
                if_then_pattern = r'(?:if|when)\s+(.+?)[,\s]+(?:then\s+)?(.+?)(?:[.;]|$)'
                matches = re.finditer(if_then_pattern, sent_text, re.IGNORECASE)

                for match in matches:
                    condition = match.group(1).strip()
                    consequence = match.group(2).strip()

                    if len(condition) > 10 and len(consequence) > 10:
                        causal_relations.append({
                            'cause': condition,
                            'effect': consequence,
                            'marker': 'if-then',
                            'type': 'conditional',
                            'confidence': 0.70,
                            'start': sent.start_char + match.start(),
                            'end': sent.start_char + match.end(),
                            'sentence': sent_text
                        })

            # Use dependency parsing to find additional causal relationships
            for sent in doc.sents:
                for token in sent:
                    # Look for causal dependency relations
                    if token.dep_ in ['advcl', 'mark'] and token.lower_ in [
                        'because', 'since', 'if', 'when', 'as'
                    ]:
                        # Find the head (main clause) and the dependent clause
                        head = token.head
                        dependent_clause = ' '.join([t.text for t in token.subtree])
                        main_clause = ' '.join([t.text for t in head.subtree if t not in token.subtree])

                        if len(dependent_clause) > 10 and len(main_clause) > 10:
                            # Determine if it's backward or forward causation
                            is_backward = token.lower_ in ['because', 'since', 'as']

                            if is_backward:
                                cause = dependent_clause
                                effect = main_clause
                            else:
                                cause = main_clause
                                effect = dependent_clause

                            # Check if we already have this relation (avoid duplicates)
                            is_duplicate = any(
                                rel['cause'].lower() == cause.lower() and
                                rel['effect'].lower() == effect.lower()
                                for rel in causal_relations
                            )

                            if not is_duplicate:
                                causal_relations.append({
                                    'cause': cause,
                                    'effect': effect,
                                    'marker': token.text,
                                    'type': 'dependency',
                                    'confidence': 0.80,
                                    'start': sent.start_char,
                                    'end': sent.end_char,
                                    'sentence': sent.text
                                })

            # Sort by position in text
            causal_relations.sort(key=lambda x: x['start'])

            # Calculate metadata
            type_counts = {}
            for rel in causal_relations:
                type_counts[rel['type']] = type_counts.get(rel['type'], 0) + 1

            metadata = {
                "total_relations": len(causal_relations),
                "relation_types": type_counts,
                "unique_types": len(type_counts),
                "method": "pattern_matching_plus_dependency_parsing",
                "text_length": len(text),
                "sentences_analyzed": len(list(doc.sents))
            }

            return ProcessingResult(
                tool_name="extract_causal",
                status="success",
                data=causal_relations,
                metadata=metadata,
                provenance=self._generate_provenance("extract_causal", f"{len(text)} chars")
            )

        except ImportError:
            return ProcessingResult(
                tool_name="extract_causal",
                status="error",
                data=[],
                metadata={"error": "spaCy not installed. Run: pip install spacy && python -m spacy download en_core_web_sm"},
                provenance=self._generate_provenance("extract_causal")
            )
        except Exception as e:
            return ProcessingResult(
                tool_name="extract_causal",
                status="error",
                data=[],
                metadata={"error": str(e)},
                provenance=self._generate_provenance("extract_causal")
            )

    def extract_definitions(self, text: str) -> ProcessingResult:
        """
        Extract term definitions using transformer-enhanced pattern matching.

        Hybrid approach:
        1. Uses zero-shot classification (transformer) to identify candidate definition sentences
        2. Applies enhanced pattern extraction to candidates
        3. Falls back to pure pattern-based if transformers unavailable

        Identifies definitional patterns including:
        - Explicit definitions (X is defined as Y, X refers to Y)
        - Copula definitions (X is Y, X means Y)
        - Appositive definitions (X, a type of Y,)
        - Parenthetical definitions (X (also known as Y))

        Args:
            text: The document text to analyze

        Returns:
            ProcessingResult with definitions containing:
            - term: the term being defined
            - definition: the definition text
            - pattern: the definition pattern type
            - confidence: extraction confidence score (boosted by transformer)
            - start: character start position
            - end: character end position
        """
        try:
            import re
            import spacy

            # Get confidence threshold from settings
            from app.models.app_settings import AppSetting
            confidence_threshold = AppSetting.get_setting(
                'definition_extraction_confidence_threshold',
                user_id=self.user_id,
                default=0.70  # Default: 70% confidence
            )

            # Try to load transformer model for definition extraction
            transformer_available = False
            definition_extractor = None

            try:
                from transformers import pipeline
                # Use DeftEval model trained specifically on definition extraction
                # Replaces zero-shot with task-specific model (SemEval-2020 Task 6)
                definition_extractor = pipeline(
                    "token-classification",
                    model="DFKI-SLT/bert-defmod-deft",
                    aggregation_strategy="simple",
                    device=-1  # CPU (-1), use 0 for GPU
                )
                transformer_available = True
            except (ImportError, Exception):
                # Fall back to pattern-only approach
                transformer_available = False

            # Load spaCy model for sentence segmentation and dependency parsing
            try:
                nlp = spacy.load('en_core_web_sm')
            except OSError:
                nlp = None

            definitions = []

            # Definition patterns (more specific patterns first)
            definition_patterns = [
                # Explicit definitions
                (r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+is\s+defined\s+as\s+(.+?)(?:[.;]|$)', 'explicit_definition', 0.90),
                (r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+can\s+be\s+defined\s+as\s+(.+?)(?:[.;]|$)', 'explicit_definition', 0.90),
                (r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+refers\s+to\s+(.+?)(?:[.;]|$)', 'explicit_reference', 0.85),
                (r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+denotes\s+(.+?)(?:[.;]|$)', 'explicit_reference', 0.85),

                # Meaning/explanation patterns
                (r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+means\s+(.+?)(?:[.;]|$)', 'meaning', 0.80),
                (r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+represents\s+(.+?)(?:[.;]|$)', 'meaning', 0.75),
                (r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+describes\s+(.+?)(?:[.;]|$)', 'meaning', 0.70),

                # Copula definitions (be careful with these - higher false positive rate)
                (r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+is\s+(?:a|an|the)\s+(.+?)(?:[.;]|$)', 'copula', 0.65),

                # Acronym expansions
                (r'([A-Z]{2,})\s+\(([^)]+)\)', 'acronym', 0.85),
                (r'([^(]+)\s+\(([A-Z]{2,})\)', 'acronym_reverse', 0.85),

                # Also known as patterns
                (r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+\(also\s+known\s+as\s+([^)]+)\)', 'also_known_as', 0.80),
                (r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*),\s+also\s+known\s+as\s+(.+?),', 'also_known_as', 0.80),

                # Or/i.e. patterns
                (r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+\(i\.e\.,\s+([^)]+)\)', 'ie_explanation', 0.75),
                (r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*),\s+i\.e\.,\s+(.+?),', 'ie_explanation', 0.75),
            ]

            # Process text - get sentences
            if nlp:
                doc = nlp(text)
                sentences = [sent.text for sent in doc.sents]
            else:
                # Fallback: simple sentence splitting
                sentences = re.split(r'[.!?]+\s+', text)

            # Extract definitions using transformer (if available)
            transformer_definitions = []

            if transformer_available and definition_extractor:
                try:
                    # DeftEval model extracts term/definition pairs directly
                    # Process text in chunks (model has token limit)
                    max_length = 512  # BERT token limit
                    chunks = []
                    chunk_size = 2000  # Characters per chunk (rough approximation)

                    for i in range(0, len(text), chunk_size):
                        chunk = text[i:i+chunk_size]
                        if len(chunk) > 20:  # Skip very short chunks
                            chunks.append((i, chunk))

                    # Extract from each chunk
                    for offset, chunk in chunks:
                        results = definition_extractor(chunk)

                        # Group consecutive entities into term-definition pairs
                        current_term = None
                        current_def = None

                        for entity in results:
                            label = entity.get('entity_group', entity.get('entity', ''))
                            word = entity.get('word', '')
                            score = entity.get('score', 0)

                            # Skip low-confidence extractions
                            if score < confidence_threshold:
                                continue

                            if 'TERM' in label.upper():
                                # Save previous pair if exists
                                if current_term and current_def:
                                    transformer_definitions.append({
                                        'term': current_term.strip(),
                                        'definition': current_def.strip(),
                                        'pattern': 'transformer_direct',
                                        'confidence': min(score, 0.95),
                                        'start': offset + entity.get('start', 0),
                                        'end': offset + entity.get('end', 0)
                                    })
                                # Start new term
                                current_term = word
                                current_def = None
                            elif 'DEFINITION' in label.upper() or 'GLOSS' in label.upper():
                                if current_def:
                                    current_def += ' ' + word
                                else:
                                    current_def = word

                        # Save final pair
                        if current_term and current_def:
                            transformer_definitions.append({
                                'term': current_term.strip(),
                                'definition': current_def.strip(),
                                'pattern': 'transformer_direct',
                                'confidence': 0.90
                            })

                except Exception as e:
                    # If transformer fails, continue with pattern-only
                    pass

            seen_terms = set()

            # Add transformer-extracted definitions first (highest quality)
            for defn in transformer_definitions:
                term_key = defn['term'].lower()

                # Filter: Only keep terms with 1-3 words (single words or short phrases)
                term_word_count = len(defn['term'].split())
                if term_word_count > 3:
                    continue

                if term_key not in seen_terms and len(defn['term']) > 1 and len(defn['definition']) > 10:
                    seen_terms.add(term_key)
                    definitions.append(defn)

            # Also apply pattern-based extraction to catch anything transformer missed
            candidate_sentences = sentences

            # Apply patterns to candidate sentences
            for sent in candidate_sentences:
                for pattern, pattern_type, confidence in definition_patterns:
                    matches = re.finditer(pattern, sent, re.IGNORECASE)

                    for match in matches:
                        term = match.group(1).strip()
                        definition_text = match.group(2).strip()

                        # Quality filters - basic length checks
                        if (len(term) < 2 or len(definition_text) < 10 or
                            len(definition_text) > 200):  # Too short or too long
                            continue

                        # REJECT: Terms with more than 3 words (only keep single words or short phrases)
                        term_word_count = len(term.split())
                        if term_word_count > 3:
                            continue

                        # REJECT: Academic citations (e.g., "Dubossarsky et al., 2015")
                        if re.search(r'\bet\s+al\.\s*,?\s*\d{4}', definition_text):
                            continue

                        # REJECT: Multiple citations in parentheses
                        if definition_text.count('(') > 2 or definition_text.count(';') > 2:
                            continue

                        # REJECT: Year ranges or multiple years (reference lists)
                        if re.search(r'\d{4}\s*[-–]\s*\d{4}|\d{4}\s*,\s*\d{4}', definition_text):
                            continue

                        # REJECT: Sentences that are mostly technical symbols
                        symbol_ratio = len(re.findall(r'[(){}\[\];,—–]', definition_text)) / max(len(definition_text), 1)
                        if symbol_ratio > 0.15:  # More than 15% special characters
                            continue

                        # REJECT: Too many uppercase words (likely acronyms list)
                        uppercase_words = re.findall(r'\b[A-Z]{2,}\b', definition_text)
                        if len(uppercase_words) > 3:
                            continue

                        # REJECT: Starts with common non-definitional words
                        if re.match(r'^(e\.g\.|for example|such as|including|like)', definition_text, re.IGNORECASE):
                            continue

                        # Avoid duplicate terms (keep first occurrence)
                        term_key = term.lower()
                        if term_key in seen_terms:
                            continue

                        seen_terms.add(term_key)

                        # Find position in original text
                        start_pos = text.find(match.group(0))
                        if start_pos == -1:
                            continue  # Can't locate in original text

                        # Additional validation for copula patterns (prone to false positives)
                        if pattern_type == 'copula':
                            # Check if definition contains enough content words
                            content_words = re.findall(r'\b[a-z]{4,}\b', definition_text.lower())
                            if len(content_words) < 2:
                                continue

                        # Additional validation for acronym patterns
                        if pattern_type in ['acronym', 'acronym_reverse']:
                            # Ensure it's actually an expansion, not a citation
                            # Good: "OED (Oxford English Dictionary)"
                            # Bad: "example (Smith, 2015)"
                            if re.search(r'\d{4}', definition_text):  # Contains a year
                                continue
                            # Must have at least 3 words in expansion
                            words = definition_text.split()
                            if len(words) < 3:
                                continue

                        # Pattern-based confidence (transformer extractions already added above)
                        definitions.append({
                            'term': term,
                            'definition': definition_text,
                            'pattern': pattern_type,
                            'confidence': confidence,
                            'start': start_pos,
                            'end': start_pos + len(match.group(0)),
                            'sentence': sent
                        })

            # If spaCy is available, try to extract appositive definitions
            if nlp:
                doc = nlp(text)
                for sent in doc.sents:
                    for token in sent:
                        # Look for appositive constructions (noun, noun_phrase,)
                        if token.dep_ == 'appos' and token.head.pos_ in ['NOUN', 'PROPN']:
                            term = token.head.text
                            definition_text = token.text

                            # Get fuller context
                            term_phrase = ' '.join([t.text for t in token.head.subtree])
                            definition_phrase = ' '.join([t.text for t in token.subtree])

                            # Only keep terms with 1-3 words
                            term_word_count = len(term_phrase.split())
                            if term_word_count > 3:
                                continue

                            if (len(term_phrase) > 2 and len(definition_phrase) > 10 and
                                term_phrase.lower() not in seen_terms):

                                seen_terms.add(term_phrase.lower())

                                definitions.append({
                                    'term': term_phrase,
                                    'definition': definition_phrase,
                                    'pattern': 'appositive',
                                    'confidence': 0.70,
                                    'start': token.head.idx,
                                    'end': token.idx + len(definition_phrase),
                                    'sentence': sent.text
                                })

            # Sort by position in text
            definitions.sort(key=lambda x: x['start'])

            # Calculate metadata
            pattern_counts = {}
            for defn in definitions:
                pattern_counts[defn['pattern']] = pattern_counts.get(defn['pattern'], 0) + 1

            # Build method string based on what was used
            method_parts = []
            if transformer_available:
                method_parts.append("defteval_direct_extraction")
            method_parts.append("pattern_matching")
            if nlp:
                method_parts.append("dependency_parsing")

            # Count transformer vs pattern extractions
            transformer_count = sum(1 for d in definitions if d.get('pattern') == 'transformer_direct')
            pattern_count = len(definitions) - transformer_count

            metadata = {
                "total_definitions": len(definitions),
                "transformer_extracted": transformer_count,
                "pattern_extracted": pattern_count,
                "pattern_types": pattern_counts,
                "unique_patterns": len(pattern_counts),
                "unique_terms": len(seen_terms),
                "method": "+".join(method_parts),
                "transformer_model": "DFKI-SLT/bert-defmod-deft" if transformer_available else None,
                "transformer_used": transformer_available,
                "confidence_threshold": confidence_threshold,
                "text_length": len(text)
            }

            return ProcessingResult(
                tool_name="extract_definitions",
                status="success",
                data=definitions,
                metadata=metadata,
                provenance=self._generate_provenance("extract_definitions", f"{len(text)} chars")
            )

        except ImportError:
            # Try without spaCy
            return ProcessingResult(
                tool_name="extract_definitions",
                status="partial",
                data=[],
                metadata={"warning": "Running without spaCy - limited functionality. Install spacy for better results."},
                provenance=self._generate_provenance("extract_definitions")
            )
        except Exception as e:
            return ProcessingResult(
                tool_name="extract_definitions",
                status="error",
                data=[],
                metadata={"error": str(e)},
                provenance=self._generate_provenance("extract_definitions")
            )

    def period_aware_embedding(self, text: str, period: Optional[str] = None,
                                domain: Optional[str] = None) -> ProcessingResult:
        """
        Generate period-aware embeddings for semantic drift analysis.

        Uses the PeriodAwareEmbeddingService to:
        - Automatically detect document period from temporal markers or text analysis
        - Select appropriate embedding model for the period and domain
        - Generate embeddings suitable for diachronic analysis

        From the JCDL paper: "The architecture selects period-appropriate embedding
        models based on the temporal and domain characteristics of the text."

        Requires: sentence-transformers

        Args:
            text: The document text to embed
            period: Optional time period (e.g., "1950s", "1850", "2000-2010")
            domain: Optional domain hint (e.g., "scientific", "legal", "philosophy")

        Returns:
            ProcessingResult with embedding data containing:
            - embedding: the embedding vector (list of floats)
            - period: detected or specified period
            - model: model used for embedding
            - dimensions: embedding dimensionality
            - selection_reason: why this model was chosen
            - selection_confidence: confidence in model selection
        """
        try:
            from app.services.period_aware_embedding_service import get_period_aware_embedding_service
            import re

            # Initialize period-aware embedding service
            try:
                period_service = get_period_aware_embedding_service()
            except Exception as e:
                return ProcessingResult(
                    tool_name="period_aware_embedding",
                    status="error",
                    data=[],
                    metadata={"error": f"Failed to initialize period-aware embedding service: {str(e)}"},
                    provenance=self._generate_provenance("period_aware_embedding")
                )

            # Parse year from period parameter if provided
            doc_year = None
            if period:
                year_match = re.search(r'\b(1[6-9]\d{2}|20[0-2]\d)\b', str(period))
                if year_match:
                    doc_year = int(year_match.group(1))

            # Limit text length for embedding (most models have token limits)
            max_chars = 5000
            text_to_embed = text[:max_chars] if len(text) > max_chars else text

            # Generate period-aware embedding using the service
            try:
                result = period_service.generate_period_aware_embedding(
                    text=text_to_embed,
                    year=doc_year,
                    domain=domain,
                    metadata={"text_length": len(text), "truncated": len(text) > max_chars}
                )

                embedding_vector = result.get('embedding', [])
                model_name = result.get('model_used', 'unknown')
                dimensions = result.get('dimension', len(embedding_vector) if embedding_vector else 0)

                # Calculate some additional metadata
                token_estimate = len(text_to_embed.split())

                metadata = {
                    "period": result.get('period_detected') or period or "unknown",
                    "period_confidence": result.get('selection_confidence', 0.5),
                    "period_detection": "manual" if period else "automatic",
                    "model": model_name,
                    "model_description": result.get('model_description', ''),
                    "selection_reason": result.get('selection_reason', ''),
                    "dimensions": dimensions,
                    "text_length": len(text),
                    "text_embedded": len(text_to_embed),
                    "truncated": len(text) > max_chars,
                    "estimated_tokens": token_estimate,
                    "embedding_type": "period_aware",
                    "domain_detected": result.get('domain_detected'),
                    "generated_at": result.get('generated_at')
                }

                # The embedding is returned as both metadata and data
                # Data contains the actual vector for downstream processing
                data = {
                    "embedding": embedding_vector,
                    "period": metadata["period"],
                    "model": model_name,
                    "dimensions": dimensions,
                    "selection_confidence": result.get('selection_confidence', 0.5),
                    "selection_reason": result.get('selection_reason', '')
                }

                return ProcessingResult(
                    tool_name="period_aware_embedding",
                    status="success",
                    data=data,
                    metadata=metadata,
                    provenance=self._generate_provenance(
                        "period_aware_embedding",
                        f"{len(text)} chars, period={metadata['period']}, model={model_name}"
                    )
                )

            except Exception as e:
                return ProcessingResult(
                    tool_name="period_aware_embedding",
                    status="error",
                    data={},
                    metadata={
                        "error": f"Embedding generation failed: {str(e)}",
                        "period": period,
                        "text_length": len(text)
                    },
                    provenance=self._generate_provenance("period_aware_embedding")
                )

        except ImportError as e:
            return ProcessingResult(
                tool_name="period_aware_embedding",
                status="error",
                data={},
                metadata={
                    "error": "Required dependencies not installed. Run: pip install sentence-transformers",
                    "import_error": str(e)
                },
                provenance=self._generate_provenance("period_aware_embedding")
            )
        except Exception as e:
            return ProcessingResult(
                tool_name="period_aware_embedding",
                status="error",
                data={},
                metadata={"error": str(e)},
                provenance=self._generate_provenance("period_aware_embedding")
            )


# Convenience function for tool registry compatibility
def get_processor(user_id: Optional[int] = None, experiment_id: Optional[int] = None) -> DocumentProcessor:
    """
    Factory function to create DocumentProcessor instance.

    Args:
        user_id: Optional user ID for provenance
        experiment_id: Optional experiment ID for provenance

    Returns:
        Configured DocumentProcessor instance
    """
    return DocumentProcessor(user_id=user_id, experiment_id=experiment_id)
