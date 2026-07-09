"""Read-only processing result views."""

from flask import render_template

from app.models.document import Document
from app.models.processing_job import ProcessingJob
from app.models.text_segment import TextSegment
from app.services.inheritance_versioning_service import InheritanceVersioningService

from . import processing_bp


@processing_bp.route('/document/<string:document_uuid>/results/embeddings', methods=['GET'])
def view_embeddings_results(document_uuid):
    """View embeddings results for a document (supports both manual and experiment processing)"""
    try:
        document = Document.query.filter_by(uuid=document_uuid).first_or_404()

        # Get all embedding jobs for this document (including processing versions)
        jobs = ProcessingJob.query.filter_by(document_id=document.id, job_type='generate_embeddings').all()

        # Also check for jobs in processing versions
        all_potential_jobs = ProcessingJob.query.filter(
            ProcessingJob.document_id != document.id,
            ProcessingJob.job_type == 'generate_embeddings'
        ).all()

        for job in all_potential_jobs:
            params = job.get_parameters()
            if params.get('original_document_id') == document.id:
                jobs.append(job)

        # ALSO check for experiment processing records
        from app.models.experiment_processing import ExperimentDocumentProcessing
        from app.models.experiment_document import ExperimentDocument

        # Wrapper for template compatibility
        class JobWrapper:
            def __init__(self, exp_processing):
                self._exp = exp_processing
                self.status = exp_processing.status
                self.created_at = exp_processing.created_at
                self.completed_at = exp_processing.completed_at
                self.job_type = exp_processing.processing_type

            def get_parameters(self):
                return {
                    'method': self._exp.processing_method,
                    'processing_type': self._exp.processing_type
                }

        exp_docs = ExperimentDocument.query.filter_by(document_id=document.id).all()
        for exp_doc in exp_docs:
            exp_processing = ExperimentDocumentProcessing.query.filter_by(
                experiment_document_id=exp_doc.id,
                processing_type='embeddings'
            ).all()
            for exp_job in exp_processing:
                jobs.append(JobWrapper(exp_job))

        # Sort by created_at desc
        jobs.sort(key=lambda j: (j.created_at is None, j.created_at), reverse=True)

        # Get embeddings from multiple sources
        from app.services.inheritance_versioning_service import InheritanceVersioningService
        base_doc_id = InheritanceVersioningService._get_base_document_id(document)

        # Query all versions that derive from the base document
        all_versions = Document.query.filter_by(source_document_id=base_doc_id).all()
        all_version_ids = [v.id for v in all_versions]

        # Always include the base document itself
        if base_doc_id not in all_version_ids:
            all_version_ids.append(base_doc_id)

        # Get embeddings from ProcessingArtifact table (unified storage)
        embeddings = []
        from app.models.experiment_processing import ProcessingArtifact

        artifact_embeddings = ProcessingArtifact.query.filter(
            ProcessingArtifact.document_id.in_(all_version_ids),
            ProcessingArtifact.artifact_type == 'embedding_vector'
        ).order_by(ProcessingArtifact.artifact_index).all()

        for emb in artifact_embeddings:
            content = emb.get_content()
            metadata = emb.get_metadata() or {}
            embeddings.append({
                'document_id': emb.document_id,
                'index': emb.artifact_index,
                'level': 'document' if emb.artifact_index == -1 else 'segment',
                'method': metadata.get('method', 'unknown'),
                'model': content.get('model', metadata.get('model', 'unknown')),
                'dimensions': metadata.get('dimensions', len(content.get('vector', []))),
                'text': content.get('text', '')[:500],  # Truncate for display
                'vector': content.get('vector', []),
                'source': 'artifact',
                # Period-aware metadata
                'period_category': metadata.get('period_category'),
                'document_year': metadata.get('document_year'),
                'selection_reason': metadata.get('selection_reason'),
                'selection_confidence': metadata.get('selection_confidence'),
                # Extended period-aware metadata
                'model_full': metadata.get('model_full'),
                'model_description': metadata.get('model_description'),
                'expected_dimension': metadata.get('expected_dimension'),
                'handles_archaic': metadata.get('handles_archaic'),
                'era': metadata.get('era'),
                'intended_model': metadata.get('intended_model'),
                'fallback_used': metadata.get('fallback_used', False)
            })

        # Compute statistics
        total_embeddings = len(embeddings)
        document_level = [e for e in embeddings if e['level'] == 'document']
        segment_level = [e for e in embeddings if e['level'] == 'segment']

        # Get consistent metadata from first embedding
        first_emb = embeddings[0] if embeddings else {}

        # Check if any embedding is period-aware
        period_aware_emb = next((e for e in embeddings if e.get('period_category')), None)

        from flask import render_template
        return render_template('processing/embeddings_results.html',
                             document=document,
                             jobs=jobs,
                             embeddings=embeddings,
                             total_embeddings=total_embeddings,
                             document_level_count=len(document_level),
                             segment_level_count=len(segment_level),
                             method=first_emb.get('method', 'N/A'),
                             model=first_emb.get('model', 'N/A'),
                             dimensions=first_emb.get('dimensions', 'N/A'),
                             # Period-aware info
                             is_period_aware=period_aware_emb is not None,
                             period_category=period_aware_emb.get('period_category') if period_aware_emb else None,
                             document_year=period_aware_emb.get('document_year') if period_aware_emb else None,
                             selection_reason=period_aware_emb.get('selection_reason') if period_aware_emb else None,
                             selection_confidence=period_aware_emb.get('selection_confidence') if period_aware_emb else None,
                             # Extended period-aware info
                             model_full=period_aware_emb.get('model_full') if period_aware_emb else None,
                             model_description=period_aware_emb.get('model_description') if period_aware_emb else None,
                             expected_dimension=period_aware_emb.get('expected_dimension') if period_aware_emb else None,
                             handles_archaic=period_aware_emb.get('handles_archaic') if period_aware_emb else None,
                             era=period_aware_emb.get('era') if period_aware_emb else None,
                             intended_model=period_aware_emb.get('intended_model') if period_aware_emb else None,
                             fallback_used=period_aware_emb.get('fallback_used', False) if period_aware_emb else False)

    except Exception as e:
        from flask import render_template, abort
        from werkzeug.exceptions import HTTPException
        # Re-raise 404 and other HTTP exceptions properly
        if isinstance(e, HTTPException):
            raise
        # For non-HTTP exceptions, show error page
        return render_template('processing/error.html',
                             document=None,
                             error=str(e)), 500

@processing_bp.route('/document/<string:document_uuid>/results/entities', methods=['GET'])
def view_entities_results(document_uuid):
    """View entity extraction results for a document (supports both manual and experiment processing)"""
    try:
        document = Document.query.filter_by(uuid=document_uuid).first_or_404()

        # Get all entity extraction jobs
        jobs = ProcessingJob.query.filter_by(
            document_id=document.id,
            job_type='extract_entities'
        ).order_by(ProcessingJob.created_at.desc()).all()

        # ALSO check for experiment processing records
        from app.models.experiment_processing import ExperimentDocumentProcessing
        from app.models.experiment_document import ExperimentDocument

        # Wrapper for template compatibility
        class JobWrapper:
            def __init__(self, exp_processing):
                self._exp = exp_processing
                self.status = exp_processing.status
                self.created_at = exp_processing.created_at
                self.completed_at = exp_processing.completed_at
                self.job_type = exp_processing.processing_type

            def get_parameters(self):
                return {
                    'method': self._exp.processing_method,
                    'processing_type': self._exp.processing_type
                }

        exp_docs = ExperimentDocument.query.filter_by(document_id=document.id).all()
        for exp_doc in exp_docs:
            exp_processing = ExperimentDocumentProcessing.query.filter_by(
                experiment_document_id=exp_doc.id,
                processing_type='entities'
            ).all()
            for exp_job in exp_processing:
                jobs.append(JobWrapper(exp_job))

        jobs.sort(key=lambda j: (j.created_at is None, j.created_at), reverse=True)

        # Get entities from multiple sources
        from app.services.inheritance_versioning_service import InheritanceVersioningService
        base_doc_id = InheritanceVersioningService._get_base_document_id(document)

        # Query all versions that derive from the base document
        all_versions = Document.query.filter_by(source_document_id=base_doc_id).all()
        all_version_ids = [v.id for v in all_versions]

        # Always include the base document itself
        if base_doc_id not in all_version_ids:
            all_version_ids.append(base_doc_id)

        # Get entities from ProcessingArtifact table (unified storage)
        entities = []
        from app.models.experiment_processing import ProcessingArtifact

        artifacts = ProcessingArtifact.query.filter(
            ProcessingArtifact.document_id.in_(all_version_ids),
            ProcessingArtifact.artifact_type == 'extracted_entity'
        ).order_by(ProcessingArtifact.artifact_index).all()

        for artifact in artifacts:
            content_data = artifact.get_content()
            # Handle field naming from processing_tools.py: entity, type, start, end
            entity_text = content_data.get('entity', content_data.get('text', ''))
            entity_type = content_data.get('type', content_data.get('entity_type', 'UNKNOWN'))
            start_pos = content_data.get('start', content_data.get('start_char'))
            end_pos = content_data.get('end', content_data.get('end_char'))
            entities.append({
                'entity_text': entity_text,
                'text': entity_text,
                'entity_type': entity_type,
                'start_position': start_pos,
                'end_position': end_pos,
                'confidence_score': content_data.get('confidence', 0),
                'confidence': content_data.get('confidence', 0),
                'context': content_data.get('context', ''),
                'source': 'artifact'
            })

        # Group entities by type
        entities_by_type = {}
        for entity in entities:
            entity_type = entity.get('entity_type', 'UNKNOWN')
            if entity_type not in entities_by_type:
                entities_by_type[entity_type] = []
            entities_by_type[entity_type].append(entity)

        # Prepare displaCy-style data
        displacy_data = {
            'text': document.content[:5000] if document.content else '',  # Limit to first 5000 chars
            'ents': []
        }

        for entity in entities:
            start_pos = entity.get('start_position')
            end_pos = entity.get('end_position')
            if start_pos is not None and end_pos is not None:
                displacy_data['ents'].append({
                    'start': start_pos,
                    'end': end_pos,
                    'label': entity.get('entity_type', 'UNKNOWN')
                })

        from flask import render_template
        return render_template('processing/entities_results.html',
                             document=document,
                             jobs=jobs,
                             entities=entities,
                             entities_by_type=entities_by_type,
                             displacy_data=displacy_data,
                             total_entities=len(entities))

    except Exception as e:
        from flask import render_template
        return render_template('processing/error.html',
                             document=document,
                             error=str(e)), 500

@processing_bp.route('/document/<string:document_uuid>/results/segments', methods=['GET'])
def view_segments_results(document_uuid):
    """View segmentation results for a document (supports both manual and experiment processing)"""
    try:
        document = Document.query.filter_by(uuid=document_uuid).first_or_404()

        # Get segmentation jobs for this document AND all its versions
        from app.services.inheritance_versioning_service import InheritanceVersioningService
        base_doc_id = InheritanceVersioningService._get_base_document_id(document)

        # Query all versions that derive from the base document (using source_document_id)
        all_versions = Document.query.filter_by(source_document_id=base_doc_id).all()
        all_version_ids = [v.id for v in all_versions]

        # Always include the base document itself
        if base_doc_id not in all_version_ids:
            all_version_ids.append(base_doc_id)

        # Get segmentation jobs from all versions (manual processing)
        jobs = ProcessingJob.query.filter(
            ProcessingJob.document_id.in_(all_version_ids),
            ProcessingJob.job_type == 'segment_document'
        ).order_by(ProcessingJob.created_at.desc()).all()

        # Also check for jobs that reference this document as original_document_id
        all_potential_jobs = ProcessingJob.query.filter(
            ProcessingJob.document_id.notin_(all_version_ids),
            ProcessingJob.job_type == 'segment_document'
        ).all()

        for job in all_potential_jobs:
            params = job.get_parameters()
            if params.get('original_document_id') in all_version_ids:
                jobs.append(job)

        # ALSO check for experiment processing records
        from app.models.experiment_processing import ExperimentDocumentProcessing
        from app.models.experiment_document import ExperimentDocument

        # Create a wrapper class to make ExperimentDocumentProcessing look like ProcessingJob
        class JobWrapper:
            def __init__(self, exp_processing):
                self._exp = exp_processing
                self.status = exp_processing.status
                self.created_at = exp_processing.created_at
                self.completed_at = exp_processing.completed_at
                self.job_type = exp_processing.processing_type

            def get_parameters(self):
                return {
                    'method': self._exp.processing_method,
                    'processing_type': self._exp.processing_type
                }

        # Find experiment-document associations for all versions
        for doc_id in all_version_ids:
            exp_docs = ExperimentDocument.query.filter_by(document_id=doc_id).all()
            for exp_doc in exp_docs:
                # Get segmentation processing for this experiment-document
                exp_processing = ExperimentDocumentProcessing.query.filter_by(
                    experiment_document_id=exp_doc.id,
                    processing_type='segmentation'
                ).all()
                # Wrap each experiment processing record
                for exp_job in exp_processing:
                    jobs.append(JobWrapper(exp_job))

        jobs.sort(key=lambda j: (j.created_at is None, j.created_at), reverse=True)

        # Get segments from all versions (prioritize latest version by document_id DESC)
        # Check both old TextSegment table and new ProcessingArtifact table
        old_segments = TextSegment.query.filter(
            TextSegment.document_id.in_(all_version_ids)
        ).order_by(TextSegment.document_id.desc(), TextSegment.segment_number).all()

        # Also get segments from ProcessingArtifact (new experiment processing)
        from app.models.experiment_processing import ProcessingArtifact
        new_artifacts = ProcessingArtifact.query.filter(
            ProcessingArtifact.document_id.in_(all_version_ids),
            ProcessingArtifact.artifact_type == 'text_segment'
        ).order_by(ProcessingArtifact.artifact_index).all()

        # Create a wrapper class to make ProcessingArtifact look like TextSegment
        class SegmentWrapper:
            def __init__(self, artifact):
                content_data = artifact.get_content()
                metadata = artifact.get_metadata() or {}
                self.segment_number = artifact.artifact_index + 1

                # Content can be a string (segment text) or dict with 'text' key
                if isinstance(content_data, str):
                    self.content = content_data
                else:
                    self.content = content_data.get('text', '') if content_data else ''

                self.word_count = metadata.get('word_count', len(self.content.split()))
                self.character_count = len(self.content)

                # Determine segmentation method from tool_name in metadata
                # tool_name will be 'segment_paragraph' or 'segment_sentence'
                tool_name = metadata.get('tool_name', '')
                if 'paragraph' in tool_name.lower():
                    self.segmentation_method = 'paragraph'
                elif 'sentence' in tool_name.lower():
                    self.segmentation_method = 'sentence'
                else:
                    # Fallback: check other metadata fields
                    self.segmentation_method = content_data.get('segment_type') if isinstance(content_data, dict) else None
                    if not self.segmentation_method:
                        self.segmentation_method = metadata.get('method', 'unknown')

        # Combine old and new segments, adding segmentation_method to old segments
        segments = []
        for seg in old_segments:
            # Add segmentation_method attribute to old TextSegment objects
            # Try to infer from segmentation_type field if it exists, otherwise 'paragraph'
            if hasattr(seg, 'segmentation_type'):
                seg.segmentation_method = seg.segmentation_type
            else:
                # Default to paragraph for old segments without type info
                seg.segmentation_method = 'paragraph'
            segments.append(seg)

        for artifact in new_artifacts:
            segments.append(SegmentWrapper(artifact))

        # Sort by segment number
        segments.sort(key=lambda s: s.segment_number)

        # Calculate statistics
        if segments:
            avg_length = sum(s.character_count or 0 for s in segments) / len(segments)
            avg_words = sum(s.word_count or 0 for s in segments) / len(segments)
        else:
            avg_length = 0
            avg_words = 0

        from flask import render_template
        return render_template('processing/segments_results.html',
                             document=document,
                             jobs=jobs,
                             segments=segments,
                             total_segments=len(segments),
                             avg_length=avg_length,
                             avg_words=avg_words)

    except Exception as e:
        from flask import render_template
        return render_template('processing/error.html',
                             document=document,
                             error=str(e)), 500

@processing_bp.route('/document/<string:document_uuid>/results/clean-text', methods=['GET'])
def view_clean_text_results(document_uuid):
    """View text cleanup results for a document"""
    try:
        document = Document.query.filter_by(uuid=document_uuid).first_or_404()

        # Get clean text jobs
        jobs = ProcessingJob.query.filter_by(
            document_id=document.id,
            job_type='clean_text'
        ).order_by(ProcessingJob.created_at.desc()).all()

        from flask import render_template
        return render_template('processing/clean_text_results.html',
                             document=document,
                             jobs=jobs)

    except Exception as e:
        from flask import render_template
        return render_template('processing/error.html',
                             document=document,
                             error=str(e)), 500

@processing_bp.route('/document/<string:document_uuid>/results/enhanced', methods=['GET'])
def view_enhanced_results(document_uuid):
    """View enhanced processing results for a document (supports both manual and experiment processing)"""
    try:
        document = Document.query.filter_by(uuid=document_uuid).first_or_404()

        # Get enhanced processing jobs
        jobs = ProcessingJob.query.filter_by(
            document_id=document.id,
            job_type='enhanced_processing'
        ).order_by(ProcessingJob.created_at.desc()).all()

        # ALSO check for experiment processing records
        from app.models.experiment_processing import ExperimentDocumentProcessing
        from app.models.experiment_document import ExperimentDocument

        # Wrapper for template compatibility
        class JobWrapper:
            def __init__(self, exp_processing):
                self._exp = exp_processing
                self.status = exp_processing.status
                self.created_at = exp_processing.created_at
                self.completed_at = exp_processing.completed_at
                self.job_type = exp_processing.processing_type

            def get_parameters(self):
                return {
                    'method': self._exp.processing_method,
                    'processing_type': self._exp.processing_type
                }

        exp_docs = ExperimentDocument.query.filter_by(document_id=document.id).all()
        for exp_doc in exp_docs:
            exp_processing = ExperimentDocumentProcessing.query.filter_by(
                experiment_document_id=exp_doc.id,
                processing_type='enhanced_processing'
            ).all()
            for exp_job in exp_processing:
                jobs.append(JobWrapper(exp_job))

        jobs.sort(key=lambda j: (j.created_at is None, j.created_at), reverse=True)

        # Note: Terms are standalone entities for semantic change analysis, not extracted from documents
        # They are created manually via /terms/add, not from document processing
        terms = []

        from flask import render_template
        return render_template('processing/enhanced_results.html',
                             document=document,
                             jobs=jobs,
                             terms=terms,
                             total_terms=len(terms))

    except Exception as e:
        from flask import render_template
        return render_template('processing/error.html',
                             document=document,
                             error=str(e)), 500

@processing_bp.route('/document/<string:document_uuid>/results/definitions', methods=['GET'])
def view_definitions_results(document_uuid):
    """View definition extraction results for a document (supports both manual and experiment processing)"""
    try:
        document = Document.query.filter_by(uuid=document_uuid).first_or_404()

        # Get definition extraction jobs from all versions
        from app.services.inheritance_versioning_service import InheritanceVersioningService
        base_doc_id = InheritanceVersioningService._get_base_document_id(document)

        # Query all versions that derive from the base document
        all_versions = Document.query.filter_by(source_document_id=base_doc_id).all()
        all_version_ids = [v.id for v in all_versions]

        # Always include the base document itself
        if base_doc_id not in all_version_ids:
            all_version_ids.append(base_doc_id)

        # Get definition extraction jobs from ProcessingJob (manual processing)
        jobs = ProcessingJob.query.filter(
            ProcessingJob.document_id.in_(all_version_ids),
            ProcessingJob.job_type == 'definition_extraction'
        ).order_by(ProcessingJob.created_at.desc()).all()

        # ALSO check for experiment processing records
        from app.models.experiment_processing import ExperimentDocumentProcessing
        from app.models.experiment_document import ExperimentDocument

        # Wrapper for template compatibility
        class JobWrapper:
            def __init__(self, exp_processing):
                self._exp = exp_processing
                self.status = exp_processing.status
                self.created_at = exp_processing.created_at
                self.completed_at = exp_processing.completed_at
                self.job_type = exp_processing.processing_type

            def get_parameters(self):
                return {
                    'method': self._exp.processing_method,
                    'processing_type': self._exp.processing_type
                }

        # Find experiment-document associations for all versions
        for doc_id in all_version_ids:
            exp_docs = ExperimentDocument.query.filter_by(document_id=doc_id).all()
            for exp_doc in exp_docs:
                exp_processing = ExperimentDocumentProcessing.query.filter_by(
                    experiment_document_id=exp_doc.id,
                    processing_type='definitions'
                ).all()
                for exp_job in exp_processing:
                    jobs.append(JobWrapper(exp_job))

        jobs.sort(key=lambda j: (j.created_at is None, j.created_at), reverse=True)

        # Get definitions from ProcessingArtifact table (unified storage)
        definitions = []
        from app.models.experiment_processing import ProcessingArtifact

        artifacts = ProcessingArtifact.query.filter(
            ProcessingArtifact.document_id.in_(all_version_ids),
            ProcessingArtifact.artifact_type == 'term_definition'
        ).order_by(ProcessingArtifact.artifact_index).all()

        for artifact in artifacts:
            content = artifact.get_content()
            metadata = artifact.get_metadata()
            definitions.append({
                'term': content.get('term', ''),
                'definition': content.get('definition', ''),
                'pattern': content.get('pattern', 'unknown'),
                'confidence': content.get('confidence', 0),
                'sentence': content.get('sentence', ''),
                'start_char': metadata.get('start_char'),
                'end_char': metadata.get('end_char'),
                'method': metadata.get('method', 'artifact'),
                'source': 'artifact'
            })

        # Group definitions by pattern type
        definitions_by_pattern = {}
        for defn in definitions:
            pattern = defn.get('pattern', 'unknown')
            if pattern not in definitions_by_pattern:
                definitions_by_pattern[pattern] = []
            definitions_by_pattern[pattern].append(defn)

        from flask import render_template
        return render_template('processing/definitions_results.html',
                             document=document,
                             jobs=jobs,
                             definitions=definitions,
                             definitions_by_pattern=definitions_by_pattern,
                             total_definitions=len(definitions))

    except Exception as e:
        from flask import render_template
        return render_template('processing/error.html',
                             document=document,
                             error=str(e)), 500

@processing_bp.route('/document/<string:document_uuid>/results/temporal', methods=['GET'])
def view_temporal_results(document_uuid):
    """View temporal extraction results for a document (supports both manual and experiment processing)"""
    try:
        document = Document.query.filter_by(uuid=document_uuid).first_or_404()

        # Get temporal extraction jobs from all versions
        from app.services.inheritance_versioning_service import InheritanceVersioningService
        base_doc_id = InheritanceVersioningService._get_base_document_id(document)

        # Query all versions that derive from the base document
        all_versions = Document.query.filter_by(source_document_id=base_doc_id).all()
        all_version_ids = [v.id for v in all_versions]

        # Always include the base document itself
        if base_doc_id not in all_version_ids:
            all_version_ids.append(base_doc_id)

        # Get temporal extraction jobs from ProcessingJob (manual processing)
        jobs = ProcessingJob.query.filter(
            ProcessingJob.document_id.in_(all_version_ids),
            ProcessingJob.job_type == 'temporal_extraction'
        ).order_by(ProcessingJob.created_at.desc()).all()

        # ALSO check for experiment processing records
        from app.models.experiment_processing import ExperimentDocumentProcessing
        from app.models.experiment_document import ExperimentDocument

        # Wrapper for template compatibility
        class JobWrapper:
            def __init__(self, exp_processing):
                self._exp = exp_processing
                self.status = exp_processing.status
                self.created_at = exp_processing.created_at
                self.completed_at = exp_processing.completed_at
                self.job_type = exp_processing.processing_type

            def get_parameters(self):
                return {
                    'method': self._exp.processing_method,
                    'processing_type': self._exp.processing_type
                }

        # Find experiment-document associations for all versions
        for doc_id in all_version_ids:
            exp_docs = ExperimentDocument.query.filter_by(document_id=doc_id).all()
            for exp_doc in exp_docs:
                exp_processing = ExperimentDocumentProcessing.query.filter_by(
                    experiment_document_id=exp_doc.id,
                    processing_type='temporal'
                ).all()
                for exp_job in exp_processing:
                    jobs.append(JobWrapper(exp_job))

        jobs.sort(key=lambda j: (j.created_at is None, j.created_at), reverse=True)

        # Get temporal expressions from ProcessingArtifact table
        # This is the unified storage for both orchestrated and manual processing
        temporal_expressions = []
        from app.models.experiment_processing import ProcessingArtifact

        artifacts = ProcessingArtifact.query.filter(
            ProcessingArtifact.document_id.in_(all_version_ids),
            ProcessingArtifact.artifact_type == 'temporal_marker'
        ).order_by(ProcessingArtifact.artifact_index).all()

        for artifact in artifacts:
            content = artifact.get_content()
            metadata = artifact.get_metadata()

            # Handle both dict and string content
            if isinstance(content, str):
                expr_text = content
                expr_type = 'UNKNOWN'
                normalized = None
                confidence = 0.75
            else:
                expr_text = content.get('text', '')
                expr_type = content.get('type', 'UNKNOWN')
                normalized = content.get('normalized')
                confidence = content.get('confidence', 0.75)

            # Get position from content first, fall back to metadata
            start_char = content.get('start') if isinstance(content, dict) else None
            end_char = content.get('end') if isinstance(content, dict) else None
            if start_char is None and isinstance(metadata, dict):
                start_char = metadata.get('start_char')
                end_char = metadata.get('end_char')

            temporal_expressions.append({
                'text': expr_text,
                'type': expr_type,
                'normalized': normalized,
                'confidence': confidence,
                'start_char': start_char,
                'end_char': end_char,
                'method': metadata.get('method', 'spacy_ner_plus_regex') if isinstance(metadata, dict) else 'spacy_ner_plus_regex',
                'context': content.get('context', '') if isinstance(content, dict) else '',
                'source': 'spacy'
            })

        # Group expressions by type
        expressions_by_type = {}
        for expr in temporal_expressions:
            expr_type = expr['type']
            if expr_type not in expressions_by_type:
                expressions_by_type[expr_type] = []
            expressions_by_type[expr_type].append(expr)

        from flask import render_template
        return render_template('processing/temporal_results.html',
                             document=document,
                             jobs=jobs,
                             temporal_expressions=temporal_expressions,
                             expressions_by_type=expressions_by_type,
                             total_expressions=len(temporal_expressions))

    except Exception as e:
        from flask import render_template
        return render_template('processing/error.html',
                             document=document,
                             error=str(e)), 500
