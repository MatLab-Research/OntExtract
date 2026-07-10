"""Document and document-family deletion routes."""

from flask import current_app, flash, jsonify, redirect, request, url_for
from flask_login import current_user
from sqlalchemy import text

from app import db
from app.models.document import Document
from app.models.processing_job import ProcessingJob
from app.utils.auth_decorators import (
    api_require_login_for_write,
    write_login_required,
)

from .. import text_input_bp


@text_input_bp.route('/document/<int:document_id>/delete', methods=['POST'])
@write_login_required
def delete_document(document_id):
    """Delete a document"""
    document = Document.query.filter_by(id=document_id).first_or_404()

    # Check permissions - only owner or admin can delete
    if not current_user.can_delete_resource(document):
        if request.is_json:
            return jsonify({'error': 'Permission denied'}), 403
        flash('You do not have permission to delete this document', 'error')
        return redirect(url_for('text_input.document_detail', document_uuid=document.uuid))

    try:
        # Handle provenance records (purge or invalidate based on settings)
        from app.services.provenance_service import provenance_service
        prov_result = provenance_service.delete_or_invalidate_document_provenance(document_id)
        current_app.logger.info(f"Provenance handling for document {document_id}: {prov_result}")

        # Delete associated file
        document.delete_file()

        # Delete database record (cascades to related records)
        db.session.delete(document)
        db.session.commit()

        if request.is_json:
            return jsonify({'success': True, 'message': 'Document deleted successfully'})

        flash('Document deleted successfully', 'success')
        return redirect(url_for('text_input.document_list'))

    except Exception as e:
        current_app.logger.error(f"Error deleting document: {str(e)}")

        if request.is_json:
            return jsonify({'error': 'An error occurred while deleting the document'}), 500

        flash('An error occurred while deleting the document', 'error')
        return redirect(url_for('text_input.document_detail', document_uuid=document.uuid))


@text_input_bp.route('/document/<uuid:document_uuid>/delete', methods=['POST'])
@write_login_required
def delete_document_by_uuid(document_uuid):
    """Delete a document by UUID"""
    document = Document.query.filter_by(uuid=document_uuid).first_or_404()

    # Check permissions - only owner or admin can delete
    if not current_user.can_delete_resource(document):
        if request.is_json:
            return jsonify({'error': 'Permission denied'}), 403
        flash('You do not have permission to delete this document', 'error')
        return redirect(url_for('text_input.document_detail_by_uuid', document_uuid=document_uuid))

    # Check if document is part of any experiments
    experiments = db.session.execute(
        text('''
            SELECT DISTINCT e.id, e.name
            FROM experiments e
            LEFT JOIN experiment_documents_v2 ed ON ed.experiment_id = e.id
            LEFT JOIN experiment_documents ed_old ON ed_old.experiment_id = e.id
            WHERE ed.document_id = :doc_id OR ed_old.document_id = :doc_id
        '''),
        {'doc_id': document.id}
    ).fetchall()

    if experiments:
        # Document is referenced in experiments - cannot delete
        experiment_list = [{'id': exp.id, 'name': exp.name} for exp in experiments]

        if request.is_json:
            return jsonify({
                'error': 'Cannot delete document: still referenced in experiments',
                'experiments': experiment_list
            }), 409

        # Build helpful error message
        exp_names = ', '.join([f'"{exp.name}"' for exp in experiments[:3]])
        if len(experiments) > 3:
            exp_names += f' and {len(experiments) - 3} more'

        flash(f'Cannot delete this document because it is part of {len(experiments)} experiment(s): {exp_names}. Please remove the document from experiments first, or delete the experiment(s).', 'error')
        return redirect(url_for('text_input.document_detail_by_uuid', document_uuid=document_uuid))

    try:
        # Handle provenance records (purge or invalidate based on settings)
        from app.services.provenance_service import provenance_service
        prov_result = provenance_service.delete_or_invalidate_document_provenance(document.id)
        current_app.logger.info(f"Provenance handling for document {document.id}: {prov_result}")

        # Delete associated file
        document.delete_file()

        # Delete database record (cascades to related records)
        db.session.delete(document)
        db.session.commit()

        if request.is_json:
            return jsonify({'success': True, 'message': 'Document deleted successfully'})

        flash('Document deleted successfully', 'success')
        return redirect(url_for('text_input.document_list'))

    except Exception as e:
        current_app.logger.error(f"Error deleting document by UUID: {str(e)}")

        if request.is_json:
            return jsonify({'error': 'An error occurred while deleting the document'}), 500

        flash('An error occurred while deleting the document', 'error')
        return redirect(url_for('text_input.document_detail_by_uuid', document_uuid=document_uuid))


@text_input_bp.route('/document/<int:base_document_id>/delete-all-versions', methods=['POST'])
@api_require_login_for_write
def delete_all_versions(base_document_id):
    """Delete all versions of a document family"""
    try:
        # Find the base document
        base_document = Document.query.get_or_404(base_document_id)

        # Get all documents in this family (base + all versions that reference it)
        all_versions = []

        # If this is already a processed version, find its original
        if base_document.source_document_id:
            actual_base = Document.query.get(base_document.source_document_id)
            if actual_base:
                base_document = actual_base

        # Add the base document
        all_versions.append(base_document)

        # Find all versions that reference this base document
        derived_versions = Document.query.filter_by(source_document_id=base_document.id).all()
        all_versions.extend(derived_versions)

        # Also find any versions that might reference the same original as this one
        if base_document.source_document_id:
            sibling_versions = Document.query.filter_by(source_document_id=base_document.source_document_id).all()
            for sibling in sibling_versions:
                if sibling not in all_versions:
                    all_versions.append(sibling)

        deleted_count = 0
        document_title = base_document.title

        # Handle provenance records for all versions (purge or invalidate based on settings)
        from app.services.provenance_service import provenance_service
        for document in all_versions:
            prov_result = provenance_service.delete_or_invalidate_document_provenance(document.id)
            current_app.logger.info(f"Provenance handling for document {document.id}: {prov_result}")

        # Delete all documents in the family
        for document in all_versions:
            try:
                # Delete associated data first
                ProcessingJob.query.filter_by(document_id=document.id).delete()

                # Delete text segments
                db.session.execute(text("DELETE FROM text_segments WHERE document_id = :doc_id"),
                                 {'doc_id': document.id})

                # Delete document embeddings
                db.session.execute(text("DELETE FROM document_embeddings WHERE document_id = :doc_id"),
                                 {'doc_id': document.id})

                # Delete the document itself
                db.session.delete(document)
                deleted_count += 1

            except Exception as e:
                current_app.logger.error(f"Error deleting document {document.id}: {str(e)}")
                continue

        db.session.commit()

        current_app.logger.info(f"Successfully deleted {deleted_count} versions of document family '{document_title}'")

        if request.is_json:
            return jsonify({
                'success': True,
                'deleted_count': deleted_count,
                'document_title': document_title
            })

        flash(f'Successfully deleted {deleted_count} document versions', 'success')
        return redirect(url_for('text_input.document_list'))

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting document family {base_document_id}: {str(e)}")
        if request.is_json:
            return jsonify({'success': False, 'error': str(e)}), 500
        flash('An error occurred while deleting the document family', 'error')
        return redirect(url_for('text_input.document_list'))


@text_input_bp.route('/documents/delete-all', methods=['POST'])
@write_login_required
def delete_all_documents():
    """Delete ALL documents - Admin only"""
    # Check if user is admin
    if not current_user.is_admin:
        current_app.logger.warning(f"Non-admin user {current_user.id} attempted to delete all documents")
        return jsonify({'success': False, 'error': 'Admin access required'}), 403

    try:
        from app.models.provenance import ProvenanceEntity
        from app.models.experiment_document import ExperimentDocument
        from app.models.experiment_processing import ExperimentDocumentProcessing, ProcessingArtifact
        from app.models import Experiment

        # Check if there are any experiments - documents cannot be deleted while experiments exist
        experiments_with_docs = db.session.execute(
            text('''
                SELECT DISTINCT e.id, e.name
                FROM experiments e
                WHERE EXISTS (
                    SELECT 1 FROM experiment_documents_v2 ed WHERE ed.experiment_id = e.id
                ) OR EXISTS (
                    SELECT 1 FROM experiment_documents ed2 WHERE ed2.experiment_id = e.id
                )
                LIMIT 5
            ''')
        ).fetchall()

        if experiments_with_docs:
            exp_names = ', '.join([f'"{exp.name}"' for exp in experiments_with_docs[:3]])
            total_experiments = Experiment.query.count()
            if len(experiments_with_docs) > 3:
                exp_names += f' and {total_experiments - 3} more'

            return jsonify({
                'success': False,
                'error': f'Cannot delete documents: {total_experiments} experiment(s) still reference documents. '
                         f'Please delete experiments first: {exp_names}',
                'experiments': [{'id': exp.id, 'name': exp.name} for exp in experiments_with_docs]
            }), 409

        # Get count for logging
        total_documents = Document.query.count()

        current_app.logger.warning(f"Admin {current_user.id} initiating deletion of ALL {total_documents} documents")

        # Delete related records first (in order of dependencies)
        # Must delete all tables with FK to documents before deleting documents

        # 1. Delete provenance entities
        provenance_count = ProvenanceEntity.query.filter(ProvenanceEntity.document_id.isnot(None)).count()
        ProvenanceEntity.query.filter(ProvenanceEntity.document_id.isnot(None)).delete(synchronize_session=False)
        current_app.logger.info(f"Deleted {provenance_count} provenance entities")

        # 2. Delete processing artifacts
        artifact_count = ProcessingArtifact.query.count()
        ProcessingArtifact.query.delete(synchronize_session=False)
        current_app.logger.info(f"Deleted {artifact_count} processing artifacts")

        # 3. Delete processing artifact groups
        result = db.session.execute(text("DELETE FROM processing_artifact_groups"))
        current_app.logger.info(f"Deleted {result.rowcount} processing artifact groups")

        # 4. Delete document processing index FIRST (has FK to experiment_document_processing)
        result = db.session.execute(text("DELETE FROM document_processing_index"))
        current_app.logger.info(f"Deleted {result.rowcount} document processing index records")

        # 5. Delete experiment document processing operations
        processing_count = ExperimentDocumentProcessing.query.count()
        ExperimentDocumentProcessing.query.delete(synchronize_session=False)
        current_app.logger.info(f"Deleted {processing_count} experiment document processing operations")

        # 6. Delete experiment-document relationships (both tables)
        exp_doc_count = ExperimentDocument.query.count()
        ExperimentDocument.query.delete(synchronize_session=False)
        current_app.logger.info(f"Deleted {exp_doc_count} experiment-document relationships")

        result = db.session.execute(text("DELETE FROM experiment_documents_v2"))
        current_app.logger.info(f"Deleted {result.rowcount} experiment_documents_v2 records")

        # 7. Delete experiment references
        result = db.session.execute(text("DELETE FROM experiment_references"))
        current_app.logger.info(f"Deleted {result.rowcount} experiment references")

        # 8. Delete orchestration decisions
        result = db.session.execute(text("DELETE FROM orchestration_decisions"))
        current_app.logger.info(f"Deleted {result.rowcount} orchestration decisions")

        # 9. Delete version changelog
        result = db.session.execute(text("DELETE FROM version_changelog"))
        current_app.logger.info(f"Deleted {result.rowcount} version changelog entries")

        # 10. Delete document temporal metadata
        result = db.session.execute(text("DELETE FROM document_temporal_metadata"))
        current_app.logger.info(f"Deleted {result.rowcount} document temporal metadata")

        # 11. Delete term disciplinary definitions
        result = db.session.execute(text("DELETE FROM term_disciplinary_definitions"))
        current_app.logger.info(f"Deleted {result.rowcount} term disciplinary definitions")

        # 12. Delete semantic shift analysis
        result = db.session.execute(text("DELETE FROM semantic_shift_analysis"))
        current_app.logger.info(f"Deleted {result.rowcount} semantic shift analysis records")

        # 13. Delete processing jobs
        job_count = ProcessingJob.query.count()
        ProcessingJob.query.delete(synchronize_session=False)
        current_app.logger.info(f"Deleted {job_count} processing jobs")

        # 14. Delete text segments
        result = db.session.execute(text("DELETE FROM text_segments"))
        current_app.logger.info(f"Deleted {result.rowcount} text segments")

        # 15. Delete document files from disk
        documents = Document.query.all()
        deleted_files = 0
        for doc in documents:
            try:
                doc.delete_file()
                deleted_files += 1
            except Exception as e:
                current_app.logger.error(f"Error deleting file for document {doc.id}: {str(e)}")

        # 16. Finally, delete all documents (must clear self-references first)
        db.session.execute(text("UPDATE documents SET source_document_id = NULL, parent_document_id = NULL"))
        Document.query.delete(synchronize_session=False)

        db.session.commit()

        current_app.logger.warning(f"Successfully deleted ALL documents: {total_documents} documents, {deleted_files} files, {provenance_count} provenance records")

        return jsonify({
            'success': True,
            'message': f'Successfully deleted {total_documents} documents and all related data',
            'details': {
                'documents': total_documents,
                'files': deleted_files,
                'provenance_records': provenance_count,
                'processing_artifacts': artifact_count,
                'experiment_relationships': exp_doc_count
            }
        })

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error during delete all documents: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': f'An error occurred while deleting documents: {str(e)}'
        }), 500
