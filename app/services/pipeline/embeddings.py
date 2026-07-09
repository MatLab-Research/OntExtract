"""Hierarchical embedding execution for experiment documents."""

from app import db
from app.models import ExperimentDocument
from app.models.experiment_processing import ExperimentDocumentProcessing, ProcessingArtifact, DocumentProcessingIndex


class PipelineEmbeddingMixin:
    def _process_embeddings(
        self,
        processing_op: ExperimentDocumentProcessing,
        index_entry: DocumentProcessingIndex,
        exp_doc: ExperimentDocument,
        processing_method: str
    ):
        """
        Process embeddings for a document - hierarchical approach

        Creates:
        1. Document-level embedding (always) - for document similarity/clustering
        2. Segment-level embeddings (if segments exist) - for fine-grained search
        """
        from app.services.experiment_embedding_service import ExperimentEmbeddingService
        embedding_service = ExperimentEmbeddingService()

        # Check if method is available
        if not embedding_service.is_method_available(processing_method):
            raise RuntimeError(f"Embedding method '{processing_method}' not available")

        content = exp_doc.document.content or "No content available"
        embeddings_created = 0
        total_tokens = 0

        # Get document year for period-aware embeddings
        doc_year = None
        if exp_doc.document.publication_date:
            try:
                doc_year = exp_doc.document.publication_date.year
            except AttributeError:
                pass

        # STEP 1: Always create document-level embedding
        text_to_embed = content[:2000]  # First 2000 chars represents the document
        doc_embedding_result = embedding_service.generate_embeddings(text_to_embed, processing_method, year=doc_year)

        doc_embedding_artifact = ProcessingArtifact(
            processing_id=processing_op.id,
            document_id=exp_doc.document_id,
            artifact_type='embedding_vector',
            artifact_index=-1  # -1 indicates document-level embedding
        )
        doc_embedding_artifact.set_content({
            'text': text_to_embed,
            'vector': doc_embedding_result['vector'],
            'model': doc_embedding_result['model'],
            'embedding_level': 'document'
        })
        doc_metadata = {
            'dimensions': doc_embedding_result['dimensions'],
            'method': processing_method,
            'chunk_size': len(text_to_embed),
            'original_length': len(content),
            'tokens_used': doc_embedding_result.get('tokens_used', 'N/A'),
            'embedding_level': 'document'
        }
        # Add period-aware metadata if available
        if doc_embedding_result.get('period_category'):
            doc_metadata['period_category'] = doc_embedding_result['period_category']
            doc_metadata['document_year'] = doc_embedding_result.get('document_year')
            doc_metadata['selection_reason'] = doc_embedding_result.get('selection_reason')
            doc_metadata['selection_confidence'] = doc_embedding_result.get('selection_confidence')
            # Extended period-aware metadata
            doc_metadata['model_full'] = doc_embedding_result.get('model_full')
            doc_metadata['model_description'] = doc_embedding_result.get('model_description')
            doc_metadata['expected_dimension'] = doc_embedding_result.get('expected_dimension')
            doc_metadata['handles_archaic'] = doc_embedding_result.get('handles_archaic')
            doc_metadata['era'] = doc_embedding_result.get('era')
            doc_metadata['intended_model'] = doc_embedding_result.get('intended_model')
            doc_metadata['fallback_used'] = doc_embedding_result.get('fallback_used', False)
        doc_embedding_artifact.set_metadata(doc_metadata)
        db.session.add(doc_embedding_artifact)
        db.session.flush()  # Get the ID for linking

        embeddings_created += 1
        total_tokens += doc_embedding_result.get('tokens_used', 0) if isinstance(doc_embedding_result.get('tokens_used'), int) else 0

        document_embedding_id = str(doc_embedding_artifact.id)

        # STEP 2: Create segment-level embeddings if segments exist
        existing_segments = ProcessingArtifact.query.filter(
            ProcessingArtifact.document_id == exp_doc.document_id,
            ProcessingArtifact.artifact_type == 'text_segment'
        ).order_by(ProcessingArtifact.artifact_index).all()

        segment_embeddings_created = 0

        if existing_segments:
            for idx, segment_artifact in enumerate(existing_segments):
                segment_data = segment_artifact.get_content()
                text_to_embed = segment_data.get('text', '')[:2000]

                if not text_to_embed:
                    continue

                # Generate embedding for this segment
                embedding_result = embedding_service.generate_embeddings(text_to_embed, processing_method, year=doc_year)

                # Create segment embedding artifact
                embedding_artifact = ProcessingArtifact(
                    processing_id=processing_op.id,
                    document_id=exp_doc.document_id,
                    artifact_type='embedding_vector',
                    artifact_index=idx
                )
                embedding_artifact.set_content({
                    'text': text_to_embed,
                    'vector': embedding_result['vector'],
                    'model': embedding_result['model'],
                    'segment_index': idx,
                    'embedding_level': 'segment'
                })
                segment_metadata = {
                    'dimensions': embedding_result['dimensions'],
                    'method': processing_method,
                    'chunk_size': len(text_to_embed),
                    'tokens_used': embedding_result.get('tokens_used', 'N/A'),
                    'source_segment_id': str(segment_artifact.id),
                    'document_embedding_id': document_embedding_id,  # Link to parent
                    'embedding_level': 'segment'
                }
                # Add period-aware metadata if available
                if embedding_result.get('period_category'):
                    segment_metadata['period_category'] = embedding_result['period_category']
                    segment_metadata['document_year'] = embedding_result.get('document_year')
                    segment_metadata['selection_reason'] = embedding_result.get('selection_reason')
                    segment_metadata['selection_confidence'] = embedding_result.get('selection_confidence')
                    # Extended period-aware metadata
                    segment_metadata['model_full'] = embedding_result.get('model_full')
                    segment_metadata['model_description'] = embedding_result.get('model_description')
                    segment_metadata['expected_dimension'] = embedding_result.get('expected_dimension')
                    segment_metadata['handles_archaic'] = embedding_result.get('handles_archaic')
                    segment_metadata['era'] = embedding_result.get('era')
                    segment_metadata['intended_model'] = embedding_result.get('intended_model')
                    segment_metadata['fallback_used'] = embedding_result.get('fallback_used', False)
                embedding_artifact.set_metadata(segment_metadata)
                db.session.add(embedding_artifact)
                embeddings_created += 1
                segment_embeddings_created += 1
                total_tokens += embedding_result.get('tokens_used', 0) if isinstance(embedding_result.get('tokens_used'), int) else 0

        # Mark processing as completed
        processing_op.mark_completed({
            'embedding_method': processing_method,
            'dimensions': doc_embedding_result['dimensions'],
            'total_embeddings': embeddings_created,
            'document_embeddings': 1,
            'segment_embeddings': segment_embeddings_created,
            'total_tokens': total_tokens if total_tokens > 0 else 'N/A',
            'model_used': doc_embedding_result['model'],
            'note': f'Hierarchical: 1 document + {segment_embeddings_created} segment embeddings'
        })
        index_entry.status = 'completed'
