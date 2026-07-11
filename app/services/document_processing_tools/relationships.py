"""Temporal and causal relationship extraction tools."""

from .context import ProcessorContext
from .result import ProcessingResult


class RelationshipExtractionTools(ProcessorContext):
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
                # Use [^,]+ to greedily match condition up to comma
                if_then_pattern = r'(?:if|when)\s+([^,]+),\s*(?:then\s+)?(.+?)(?:[.;]|$)'
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
