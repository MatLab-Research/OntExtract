"""Temporal, definition, and enhanced extraction execution."""

from app import db
from app.models import ExperimentDocument
from app.models.experiment_processing import ExperimentDocumentProcessing, ProcessingArtifact, DocumentProcessingIndex


class PipelineExtractionMixin:
    def _process_temporal(
        self,
        processing_op: ExperimentDocumentProcessing,
        index_entry: DocumentProcessingIndex,
        exp_doc: ExperimentDocument,
        processing_method: str
    ):
        """Process temporal extraction for a document"""
        from app.services.processing_tools import DocumentProcessor

        config = processing_op.get_configuration()
        processor = DocumentProcessor(
            user_id=config.get('created_by'),
            experiment_id=exp_doc.experiment_id
        )

        content = exp_doc.document.content
        if not content:
            processing_op.mark_completed({'temporal_expressions': 0})
            index_entry.status = 'completed'
            return

        # Run temporal extraction
        result = processor.extract_temporal(content)

        if result.status == 'success':
            # Create artifacts for each temporal expression
            for i, expr in enumerate(result.data):
                artifact = ProcessingArtifact(
                    processing_id=processing_op.id,
                    document_id=exp_doc.document_id,
                    artifact_type='temporal_marker',  # Must match extraction_tools.py ARTIFACT_TYPE_MAP
                    artifact_index=i
                )
                artifact.set_content({
                    'text': expr['text'],
                    'type': expr['type'],
                    'normalized': expr.get('normalized'),
                    'confidence': expr['confidence']
                })
                artifact.set_metadata({
                    'method': processing_method,
                    'start_char': expr['start'],
                    'end_char': expr['end']
                })
                db.session.add(artifact)

            processing_op.mark_completed({
                'temporal_method': processing_method,
                'expressions_found': result.metadata.get('total_expressions', 0),
                'expression_types': result.metadata.get('expression_types', {}),
                'service_used': result.metadata.get('method', 'spacy_ner_plus_regex')
            })
            index_entry.status = 'completed'
        else:
            raise RuntimeError(f"Temporal extraction failed: {result.metadata.get('error', 'Unknown error')}")

    def _process_definitions(
        self,
        processing_op: ExperimentDocumentProcessing,
        index_entry: DocumentProcessingIndex,
        exp_doc: ExperimentDocument,
        processing_method: str
    ):
        """Process definition extraction for a document"""
        from app.services.processing_tools import DocumentProcessor

        config = processing_op.get_configuration()
        processor = DocumentProcessor(
            user_id=config.get('created_by'),
            experiment_id=exp_doc.experiment_id
        )

        content = exp_doc.document.content
        if not content:
            processing_op.mark_completed({'definitions': 0})
            index_entry.status = 'completed'
            return

        # Run definition extraction
        result = processor.extract_definitions(content)

        if result.status == 'success':
            # Create artifacts for each definition
            for i, definition in enumerate(result.data):
                artifact = ProcessingArtifact(
                    processing_id=processing_op.id,
                    document_id=exp_doc.document_id,
                    artifact_type='term_definition',
                    artifact_index=i
                )
                artifact.set_content({
                    'term': definition['term'],
                    'definition': definition['definition'],
                    'pattern': definition['pattern'],
                    'confidence': definition['confidence'],
                    'sentence': definition.get('sentence', '')
                })
                artifact.set_metadata({
                    'method': processing_method,
                    'start_char': definition['start'],
                    'end_char': definition['end']
                })
                db.session.add(artifact)

            processing_op.mark_completed({
                'definitions_method': processing_method,
                'definitions_found': result.metadata.get('total_definitions', 0),
                'pattern_types': result.metadata.get('pattern_types', {}),
                'service_used': result.metadata.get('method', 'pattern_matching')
            })
            index_entry.status = 'completed'
        else:
            raise RuntimeError(f"Definition extraction failed: {result.metadata.get('error', 'Unknown error')}")

    def _process_enhanced(
        self,
        processing_op: ExperimentDocumentProcessing,
        index_entry: DocumentProcessingIndex,
        exp_doc: ExperimentDocument,
        processing_method: str
    ):
        """
        Process enhanced extraction (term extraction + OED enrichment)

        This is a placeholder implementation that will be expanded to include:
        - Term extraction from document
        - OED API integration for historical definitions
        - Period-aware analysis
        """
        content = exp_doc.document.content
        if not content:
            processing_op.mark_completed({'terms_extracted': 0})
            index_entry.status = 'completed'
            return

        try:
            # For now, create a simple stub that marks processing as completed
            # TODO: Implement actual term extraction and OED enrichment
            # This should call term_extraction_service and oed_period_service

            # Placeholder: Extract basic terms (simple implementation)
            import re
            words = re.findall(r'\b[A-Za-z]{4,}\b', content)
            unique_terms = list(set(words[:50]))  # Limit to 50 unique terms

            # Create artifacts for extracted terms
            for i, term in enumerate(unique_terms):
                artifact = ProcessingArtifact(
                    processing_id=processing_op.id,
                    document_id=exp_doc.document_id,
                    artifact_type='extracted_term',
                    artifact_index=i
                )
                artifact.set_content({
                    'term': term,
                    'oed_enriched': False,  # Not yet implemented
                    'note': 'Basic term extraction - OED enrichment pending implementation'
                })
                artifact.set_metadata({
                    'method': processing_method,
                    'extraction_type': 'basic'
                })
                db.session.add(artifact)

            processing_op.mark_completed({
                'enhanced_method': processing_method,
                'terms_extracted': len(unique_terms),
                'oed_enriched': 0,  # Not yet implemented
                'service_used': 'Basic regex term extraction (placeholder)',
                'note': 'Full implementation pending - includes OED integration'
            })
            index_entry.status = 'completed'

        except Exception as e:
            raise RuntimeError(f"Enhanced processing failed: {str(e)}")
