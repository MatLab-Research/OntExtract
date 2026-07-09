"""Processing-result cleanup routes."""

from flask import jsonify

from app import db
from app.models.document import Document
from app.models.processing_job import ProcessingJob
from app.services.inheritance_versioning_service import InheritanceVersioningService
from app.utils.auth_decorators import api_require_login_for_write

from . import processing_bp


@processing_bp.route('/document/<string:document_uuid>/clear/definitions', methods=['DELETE'])
@api_require_login_for_write
def clear_definitions(document_uuid):
    """Clear all definition extraction results for a document."""
    try:
        document = Document.query.filter_by(uuid=document_uuid).first_or_404()

        # Get all versions of this document
        from app.services.inheritance_versioning_service import InheritanceVersioningService
        base_doc_id = InheritanceVersioningService._get_base_document_id(document)
        all_versions = Document.query.filter_by(source_document_id=base_doc_id).all()
        all_version_ids = [v.id for v in all_versions]
        if base_doc_id not in all_version_ids:
            all_version_ids.append(base_doc_id)

        # Use bulk delete operations to avoid autoflush issues
        from app.models.experiment_processing import (
            ProcessingArtifact,
            ExperimentDocumentProcessing,
            DocumentProcessingIndex
        )
        from app.models.experiment_document import ExperimentDocument

        # Count before deleting
        deleted_artifacts = ProcessingArtifact.query.filter(
            ProcessingArtifact.document_id.in_(all_version_ids),
            ProcessingArtifact.artifact_type == 'term_definition'
        ).count()

        deleted_jobs = ProcessingJob.query.filter(
            ProcessingJob.document_id.in_(all_version_ids),
            ProcessingJob.job_type == 'definition_extraction'
        ).count()

        # Get experiment document IDs and processing IDs
        exp_doc_ids = [ed.id for ed in ExperimentDocument.query.filter(
            ExperimentDocument.document_id.in_(all_version_ids)
        ).all()]

        exp_processing_count = 0
        exp_processing_ids = []
        if exp_doc_ids:
            exp_processing_records = ExperimentDocumentProcessing.query.filter(
                ExperimentDocumentProcessing.experiment_document_id.in_(exp_doc_ids),
                ExperimentDocumentProcessing.processing_type == 'definitions'
            ).all()
            exp_processing_count = len(exp_processing_records)
            exp_processing_ids = [ep.id for ep in exp_processing_records]

        # Delete in correct order to avoid foreign key violations:
        # 1. First delete DocumentProcessingIndex (references ExperimentDocumentProcessing)
        if exp_processing_ids:
            DocumentProcessingIndex.query.filter(
                DocumentProcessingIndex.processing_id.in_(exp_processing_ids)
            ).delete(synchronize_session=False)
            db.session.flush()  # Force execution before next deletion

        # 2. Delete ProcessingArtifacts that reference ExperimentDocumentProcessing
        if exp_processing_ids:
            ProcessingArtifact.query.filter(
                ProcessingArtifact.processing_id.in_(exp_processing_ids)
            ).delete(synchronize_session=False)
            db.session.flush()  # Force execution before next deletion

        # 3. Then delete ExperimentDocumentProcessing
        if exp_doc_ids:
            ExperimentDocumentProcessing.query.filter(
                ExperimentDocumentProcessing.experiment_document_id.in_(exp_doc_ids),
                ExperimentDocumentProcessing.processing_type == 'definitions'
            ).delete(synchronize_session=False)
            db.session.flush()  # Force execution before next deletion

        # 4. Delete remaining ProcessingArtifacts (by document_id)
        ProcessingArtifact.query.filter(
            ProcessingArtifact.document_id.in_(all_version_ids),
            ProcessingArtifact.artifact_type == 'term_definition'
        ).delete(synchronize_session=False)

        # 5. Delete ProcessingJobs (old manual processing)
        ProcessingJob.query.filter(
            ProcessingJob.document_id.in_(all_version_ids),
            ProcessingJob.job_type == 'definition_extraction'
        ).delete(synchronize_session=False)

        db.session.commit()

        # Update total deleted jobs
        deleted_jobs = deleted_jobs + exp_processing_count

        from flask import jsonify
        return jsonify({
            'success': True,
            'deleted_count': deleted_artifacts,
            'jobs_deleted': deleted_jobs,
            'message': f'Deleted {deleted_artifacts} definitions and {deleted_jobs} processing jobs'
        })

    except Exception as e:
        db.session.rollback()
        from flask import jsonify
        return jsonify({'error': str(e)}), 500
