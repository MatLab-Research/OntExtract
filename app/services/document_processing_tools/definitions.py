"""Definition extraction tools."""

import os

from .context import ProcessorContext
from .result import ProcessingResult


class DefinitionExtractionTools(ProcessorContext):
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
                default=0.45  # Default: 45% confidence (zero-shot scores are typically lower)
            )

            # Zero-shot classifier disabled - too slow on CPU for large documents
            # Pattern matching with strict validation provides good results
            # To re-enable: set ENABLE_ZERO_SHOT_DEFINITIONS=true in environment
            classifier_available = False
            definition_classifier = None

            if os.environ.get('ENABLE_ZERO_SHOT_DEFINITIONS', '').lower() == 'true':
                try:
                    from transformers import pipeline
                    # Use zero-shot classification to score definition sentences
                    definition_classifier = pipeline(
                        "zero-shot-classification",
                        model="facebook/bart-large-mnli",
                        device=-1  # CPU (-1), use 0 for GPU
                    )
                    classifier_available = True
                except (ImportError, Exception):
                    classifier_available = False

            # Load spaCy model for sentence segmentation and dependency parsing
            try:
                nlp = spacy.load('en_core_web_sm')
            except OSError:
                nlp = None

            definitions = []

            # Definition patterns (more specific patterns first)
            definition_patterns = [
                # Dictionary-style definitions (e.g., "AGE. Signifies those periods...")
                # Term in ALL CAPS followed by period, definition starts with verb
                (r'\b([A-Z][A-Z]+(?:\s+[A-Z]+)*)\.\s+((?:Signifies|Means|Denotes|Describes|Refers to|Is|Are|Was|Were|The|A|An|One who|In)\s+.+?)(?:\.\s*\n|\.\s*$)', 'dictionary', 0.90),

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

                # Acronym expansions - STRICT patterns only
                # Pattern: "IRA (Information Retrieval Agent)" - acronym before expansion
                # Requires: 2-6 uppercase letters, expansion must start with matching letters
                (r'\b([A-Z]{2,6})\s+\(([A-Z][a-z]+(?:\s+[A-Z]?[a-z]+)*)\)', 'acronym', 0.85),

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

            # Use zero-shot classification to score sentences (for confidence boosting, not filtering)
            # Zero-shot often misclassifies definition-containing sentences as "example"
            # so we don't use it for filtering, only for confidence adjustment
            sentence_scores = {}
            classifier_used_for_boost = False

            if classifier_available and definition_classifier:
                try:
                    # Score each sentence
                    for sent in sentences:
                        if len(sent) < 20 or len(sent) > 500:
                            continue

                        result = definition_classifier(
                            sent,
                            candidate_labels=['definition', 'example', 'statement'],
                            multi_label=False
                        )

                        # Store the definition probability for confidence boosting
                        def_idx = result['labels'].index('definition')
                        sentence_scores[sent] = result['scores'][def_idx]

                    classifier_used_for_boost = True

                except Exception as e:
                    # If classifier fails, proceed without it
                    pass

            seen_terms = set()

            # First, check for dictionary-style document format (term entries spanning multiple lines)
            # Pattern: "TERM. Definition text..." where TERM is ALL CAPS
            # This runs on full text before sentence splitting
            dict_pattern = r'\n([A-Z][A-Z]+(?:\s+[A-Z]+)*)\.\s+([A-Za-z].+?)(?=\n[A-Z][A-Z]+\.\s|\n-[A-Z]|\Z)'
            dict_matches = re.finditer(dict_pattern, '\n' + text, re.DOTALL)

            for match in dict_matches:
                term = match.group(1).strip()
                definition_text = match.group(2).strip()

                # Clean up OCR artifacts (line breaks in middle of words)
                definition_text = re.sub(r'(\w)-\s*\n\s*(\w)', r'\1\2', definition_text)
                definition_text = re.sub(r'\s*\n\s*', ' ', definition_text)
                definition_text = re.sub(r'\s+', ' ', definition_text)

                # Truncate very long definitions to first sentence or 500 chars
                if len(definition_text) > 500:
                    # Try to find first sentence end
                    first_sent_end = re.search(r'[.!?]\s+[A-Z]', definition_text[:500])
                    if first_sent_end:
                        definition_text = definition_text[:first_sent_end.start() + 1]
                    else:
                        definition_text = definition_text[:500] + '...'

                # Quality filters
                if len(term) < 2 or len(definition_text) < 15:
                    continue

                # Skip if term looks like a section header (too long)
                if len(term) > 30:
                    continue

                term_lower = term.lower()
                if term_lower not in seen_terms:
                    seen_terms.add(term_lower)
                    definitions.append({
                        'term': term.title(),  # Convert to title case for readability
                        'definition': definition_text,
                        'pattern': 'dictionary',
                        'confidence': 0.90,
                        'start': match.start(),
                        'end': match.end(),
                        'sentence': definition_text[:100] + ('...' if len(definition_text) > 100 else '')
                    })

            # Always use all sentences - pattern validation handles quality
            candidate_sentences = sentences

            # Apply patterns to candidate sentences
            for sent in candidate_sentences:
                for pattern, pattern_type, confidence in definition_patterns:
                    # Use IGNORECASE for most patterns, but not for acronym (needs exact case matching)
                    flags = 0 if pattern_type == 'acronym' else re.IGNORECASE
                    matches = re.finditer(pattern, sent, flags)

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

                        # REJECT: Run-together words (PDF extraction artifacts)
                        # E.g., "byAgent", "ofmle-solver", "andTatsunori"
                        # Detect: lowercase followed immediately by uppercase, or common words without spaces
                        if re.search(r'[a-z][A-Z]', term) or re.search(r'[a-z][A-Z]', definition_text):
                            continue

                        # REJECT: Stop words or function words as terms
                        stop_terms = {'which', 'that', 'this', 'these', 'those', 'what', 'who', 'whom',
                                     'where', 'when', 'why', 'how', 'the', 'a', 'an', 'is', 'are', 'was',
                                     'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does',
                                     'did', 'will', 'would', 'could', 'should', 'may', 'might', 'must',
                                     'shall', 'can', 'your', 'my', 'his', 'her', 'its', 'our', 'their'}
                        if term.lower() in stop_terms:
                            continue

                        # REJECT: Terms that look like variable placeholders (e.g., "where COMMAND", "where title here")
                        if term.lower().startswith('where '):
                            continue

                        # REJECT: All-caps terms (usually placeholders or labels, not definitional terms)
                        # Exception: acronym patterns are expected to be all-caps
                        if term.isupper() and pattern_type != 'acronym':
                            continue

                        # REJECT: Terms starting with possessive pronouns (instruction text, not definitions)
                        if re.match(r'^(your|my|his|her|its|our|their)\s', term, re.IGNORECASE):
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
                        if pattern_type == 'acronym':
                            # Strict acronym validation
                            # Good: "IRA (Information Retrieval Agent)"
                            # Bad: "AI (LNAI Volume 478)"

                            # Contains a year - likely citation
                            if re.search(r'\d{4}', definition_text):
                                continue

                            # Must have at least 2 words in expansion
                            words = definition_text.split()
                            if len(words) < 2:
                                continue

                            # Expansion should start with letters matching acronym
                            # E.g., "IRA" should expand to "Information Retrieval Agent"
                            acronym_letters = list(term.upper())
                            expansion_words = [w for w in words if w[0].isupper()]
                            if len(expansion_words) >= len(acronym_letters):
                                # Check if first letters match
                                first_letters = [w[0].upper() for w in expansion_words[:len(acronym_letters)]]
                                if first_letters != acronym_letters:
                                    continue
                            else:
                                # Not enough capitalized words to match acronym
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

                            # REJECT: Run-together words (PDF extraction artifacts)
                            if re.search(r'[a-z][A-Z]', term_phrase) or re.search(r'[a-z][A-Z]', definition_phrase):
                                continue

                            # REJECT: Single character terms or definitions
                            if len(term_phrase.strip()) < 3 or len(definition_phrase.strip()) < 5:
                                continue

                            # REJECT: Terms that are just author names (contains comma-separated names pattern)
                            if re.search(r'[A-Z][a-z]+\s*,\s*and\s*[A-Z]', term_phrase):
                                continue

                            # REJECT: arXiv references or citation artifacts
                            if re.search(r'arXiv|arxiv|\d{4}\.\d+', term_phrase) or re.search(r'arXiv|arxiv|\d{4}\.\d+', definition_phrase):
                                continue

                            # REJECT: Stop words as the main term
                            main_term = term.lower()
                            stop_terms = {'which', 'that', 'this', 'these', 'those', 'what', 'who', 'where',
                                         'when', 'why', 'how', 'the', 'a', 'an', 'it', 'they', 'we', 'you'}
                            if main_term in stop_terms:
                                continue

                            # REJECT: Definition is just author names or citations
                            if re.match(r'^[A-Z][a-z]+\s+[A-Z]', definition_phrase) and ',' in definition_phrase:
                                # Looks like "FirstName LastName, ..." - likely author list
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
            if classifier_available:
                method_parts.append("zero_shot_filtering")
            method_parts.append("pattern_matching")
            if nlp:
                method_parts.append("dependency_parsing")

            metadata = {
                "total_definitions": len(definitions),
                "sentences_scored": len(sentence_scores) if classifier_used_for_boost else 0,
                "total_sentences_analyzed": len(candidate_sentences),
                "pattern_types": pattern_counts,
                "unique_patterns": len(pattern_counts),
                "unique_terms": len(seen_terms),
                "method": "+".join(method_parts),
                "classifier_model": "facebook/bart-large-mnli" if classifier_available else None,
                "classifier_used": classifier_used_for_boost,
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
