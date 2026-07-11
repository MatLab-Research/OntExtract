"""Named-entity and concept extraction tools."""

from .context import ProcessorContext
from .result import ProcessingResult


class EntityExtractionTools(ProcessorContext):
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
