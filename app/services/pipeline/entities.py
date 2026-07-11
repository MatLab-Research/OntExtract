"""Entity extraction execution and provider-specific implementations."""

import logging
from typing import Any, Dict, List

from app import db
from app.models import ExperimentDocument
from app.models.experiment_processing import ExperimentDocumentProcessing, ProcessingArtifact, DocumentProcessingIndex

logger = logging.getLogger(__name__)


class PipelineEntityMixin:
    def _process_entities(
        self,
        processing_op: ExperimentDocumentProcessing,
        index_entry: DocumentProcessingIndex,
        exp_doc: ExperimentDocument,
        processing_method: str
    ):
        """Process entity extraction for a document"""
        content = exp_doc.document.content
        extracted_entities = []

        if processing_method == 'spacy':
            extracted_entities = self._extract_entities_spacy(content)
        elif processing_method == 'nltk':
            extracted_entities = self._extract_entities_nltk(content)
        else:  # llm method
            extracted_entities = self._extract_entities_llm(content, exp_doc)

        # Remove duplicates
        unique_entities = []
        seen_texts = set()

        for entity in extracted_entities:
            entity_key = entity['entity'].lower().strip()
            if entity_key not in seen_texts and len(entity_key) > 1:
                seen_texts.add(entity_key)
                unique_entities.append(entity)

        # Sort by confidence and position
        unique_entities.sort(key=lambda x: (-x['confidence'], x['start_char']))

        # Create artifacts
        for i, entity_data in enumerate(unique_entities):
            artifact = ProcessingArtifact(
                processing_id=processing_op.id,
                document_id=exp_doc.document_id,
                artifact_type='extracted_entity',
                artifact_index=i
            )
            artifact.set_content({
                'entity': entity_data['entity'],
                'entity_type': entity_data['type'],
                'confidence': entity_data['confidence'],
                'context': entity_data['context'],
                'start_char': entity_data['start_char'],
                'end_char': entity_data['end_char']
            })
            artifact.set_metadata({
                'method': processing_method,
                'extraction_confidence': entity_data['confidence'],
                'character_position': f"{entity_data['start_char']}-{entity_data['end_char']}"
            })
            db.session.add(artifact)

        # Determine service info
        if processing_method == 'spacy':
            service_used = "spaCy NLP + Enhanced Extraction"
            model_info = "en_core_web_sm + noun phrase extraction"
        elif processing_method == 'nltk':
            service_used = "NLTK Named Entity Chunker"
            model_info = "maxent_ne_chunker + POS tagging"
        else:
            service_used = "LangExtract + Gemini Integration"
            model_info = "Google Gemini-1.5-flash with character-level positioning"

        # Extract unique entity types
        entity_types = list(set([e['type'] for e in unique_entities]))

        processing_op.mark_completed({
            'extraction_method': processing_method,
            'entities_found': len(unique_entities),
            'entity_types': entity_types,
            'service_used': service_used,
            'model_info': model_info,
            'avg_confidence': sum(e['confidence'] for e in unique_entities) / len(unique_entities) if unique_entities else 0
        })
        index_entry.status = 'completed'

    def _extract_entities_spacy(self, content: str) -> List[Dict[str, Any]]:
        """Extract entities using spaCy"""
        import spacy
        from collections import defaultdict

        nlp = spacy.load('en_core_web_sm')
        doc = nlp(content)

        extracted_entities = []
        seen_entities = set()

        # Extract named entities
        for ent in doc.ents:
            entity_text = ent.text.strip()
            entity_key = (entity_text.lower(), ent.label_)

            if len(entity_text) < 2 or entity_key in seen_entities:
                continue

            seen_entities.add(entity_key)

            sent_text = ent.sent.text.strip()
            ent_start_in_sent = ent.start_char - ent.sent.start_char
            ent_end_in_sent = ent.end_char - ent.sent.start_char

            context_start = max(0, ent_start_in_sent - 50)
            context_end = min(len(sent_text), ent_end_in_sent + 50)
            context = sent_text[context_start:context_end].strip()

            extracted_entities.append({
                'entity': entity_text,
                'type': ent.label_,
                'confidence': 0.85,
                'context': context,
                'start_char': ent.start_char,
                'end_char': ent.end_char
            })

        # Extract noun phrases as concepts
        for np in doc.noun_chunks:
            np_text = np.text.strip()
            np_key = np_text.lower()

            if (len(np_text) < 3 or len(np_text) > 100 or
                any(np_key in seen_ent[0] for seen_ent in seen_entities)):
                continue

            if (any(token.pos_ in ['PROPN', 'NOUN'] for token in np) and
                not all(token.is_stop for token in np)):

                context_start = max(0, np.start_char - 50)
                context_end = min(len(content), np.end_char + 50)
                context = content[context_start:context_end].strip()

                extracted_entities.append({
                    'entity': np_text,
                    'type': 'CONCEPT',
                    'confidence': 0.65,
                    'context': context,
                    'start_char': np.start_char,
                    'end_char': np.end_char
                })

        return extracted_entities

    def _extract_entities_nltk(self, content: str) -> List[Dict[str, Any]]:
        """Extract entities using NLTK"""
        import nltk
        from nltk.tokenize import sent_tokenize, word_tokenize
        from nltk.tag import pos_tag
        from nltk.chunk import ne_chunk
        from nltk.tree import Tree

        # Ensure NLTK data
        for resource in ['punkt', 'averaged_perceptron_tagger', 'maxent_ne_chunker', 'words']:
            try:
                nltk.data.find(f'tokenizers/{resource}' if resource == 'punkt' else f'taggers/{resource}' if 'tagger' in resource else f'chunkers/{resource}' if 'chunker' in resource else f'corpora/{resource}')
            except LookupError:
                nltk.download(resource if resource != 'punkt' else 'punkt_tab', quiet=True)

        extracted_entities = []
        sentences = sent_tokenize(content)
        char_offset = 0

        for sent in sentences:
            words = word_tokenize(sent)
            pos_tags = pos_tag(words)
            chunks = ne_chunk(pos_tags, binary=False)

            word_offset = 0
            for chunk in chunks:
                if isinstance(chunk, Tree):
                    entity_words = [word for word, pos in chunk.leaves()]
                    entity_text = ' '.join(entity_words)
                    entity_type = chunk.label()

                    entity_start = sent.find(entity_text, word_offset)
                    if entity_start != -1:
                        context_start = max(0, entity_start - 50)
                        context_end = min(len(sent), entity_start + len(entity_text) + 50)
                        context = sent[context_start:context_end].strip()

                        extracted_entities.append({
                            'entity': entity_text,
                            'type': entity_type,
                            'confidence': 0.70,
                            'context': context,
                            'start_char': char_offset + entity_start,
                            'end_char': char_offset + entity_start + len(entity_text)
                        })
                        word_offset = entity_start + len(entity_text)

            char_offset += len(sent) + 1

        return extracted_entities

    def _extract_entities_llm(self, content: str, exp_doc: ExperimentDocument) -> List[Dict[str, Any]]:
        """Extract entities using LLM (LangExtract)"""
        try:
            from app.services.integrated_langextract import IntegratedLangExtractService

            langextract_service = IntegratedLangExtractService()

            if not langextract_service.service_ready:
                raise Exception(f"LangExtract service not ready: {langextract_service.initialization_error}")

            analysis_result = langextract_service.analyze_document_for_entities(
                text=content,
                document_metadata={
                    'document_id': exp_doc.document_id,
                    'experiment_id': exp_doc.experiment_id,
                    'title': exp_doc.document.title
                }
            )

            extracted_entities = []

            # Extract entities
            if 'entities' in analysis_result:
                for entity_data in analysis_result['entities']:
                    extracted_entities.append({
                        'entity': entity_data.get('text', ''),
                        'type': entity_data.get('type', 'ENTITY'),
                        'confidence': entity_data.get('confidence', 0.85),
                        'context': entity_data.get('context', ''),
                        'start_char': entity_data.get('start_pos', 0),
                        'end_char': entity_data.get('end_pos', 0)
                    })

            # Extract key concepts
            if 'key_concepts' in analysis_result:
                for concept in analysis_result['key_concepts']:
                    extracted_entities.append({
                        'entity': concept.get('term', ''),
                        'type': 'CONCEPT',
                        'confidence': concept.get('confidence', 0.80),
                        'context': concept.get('context', ''),
                        'start_char': concept.get('position', [0, 0])[0],
                        'end_char': concept.get('position', [0, 0])[1]
                    })

            return extracted_entities

        except Exception as e:
            logger.warning(f"LangExtract extraction failed, falling back to pattern-based: {e}")

            # Fallback to pattern-based extraction
            import re
            patterns = [
                r'\b[A-Z][a-z]+ [A-Z][a-z]+\b',  # Proper names
                r'\b[A-Z]{2,}\b',  # Acronyms
                r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s+(?:Inc|Corp|LLC|Ltd|Company|University|Institute)\b',
                r'\b(?:Dr|Prof|Mr|Ms|Mrs)\.?\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b',
            ]

            extracted_entities = []
            for pattern in patterns:
                matches = re.finditer(pattern, content)
                for match in matches:
                    entity_text = match.group().strip()
                    start_pos = match.start()
                    end_pos = match.end()
                    context_start = max(0, start_pos - 50)
                    context_end = min(len(content), end_pos + 50)
                    context = content[context_start:context_end].strip()

                    extracted_entities.append({
                        'entity': entity_text,
                        'type': 'ENTITY',
                        'confidence': 0.60,
                        'context': context,
                        'start_char': start_pos,
                        'end_char': end_pos
                    })

            return extracted_entities
