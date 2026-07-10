"""HTTP endpoints for document segmentation."""

from flask import current_app, jsonify, request
from flask_login import current_user

from app import db
from app.models.document import Document
from app.models.processing_job import ProcessingJob
from app.models.text_segment import TextSegment
from app.services.inheritance_versioning_service import InheritanceVersioningService
from app.utils.auth_decorators import api_require_login_for_write

from .. import processing_bp
from .langextract import run_langextract_segmentation
from .traditional import run_traditional_segmentation
from .versioning import get_segmentation_version


@processing_bp.route('/document/<string:document_uuid>/segment', methods=['POST'])
@api_require_login_for_write
def segment_document(document_uuid):
    """Segment a document into chunks and create a processing version."""
    try:
        original_document = Document.query.filter_by(
            uuid=document_uuid
        ).first_or_404()

        data = request.get_json() or {}
        method = data.get('method', 'paragraph')
        chunk_size = data.get('chunk_size', 500)
        overlap = data.get('overlap', 50)
        experiment_id = data.get('experiment_id')

        if not original_document.content:
            return jsonify({
                'success': False,
                'error': 'Document has no content to segment'
            }), 400

        processing_version = get_segmentation_version(
            original_document,
            experiment_id,
            current_user,
            method,
            chunk_size,
            overlap,
            current_app.logger,
        )

        if method == 'langextract':
            payload, status = run_langextract_segmentation(
                processing_version,
                original_document,
                current_user,
            )
            return jsonify(payload), status

        outcome, status = run_traditional_segmentation(
            processing_version,
            original_document,
            current_user,
            method,
            chunk_size,
            overlap,
        )
        if not outcome.get('job'):
            return jsonify(outcome), status

        job = outcome['job']
        segment_count = outcome['segment_count']
        base_document_id = InheritanceVersioningService._get_base_document_id(
            original_document
        )
        response_data = {
            'success': True,
            'job_id': job.id,
            'segments_created': segment_count,
            'base_document_id': base_document_id,
            'latest_version_id': processing_version.id,
            'processing_version_id': processing_version.id,
            'processing_version_uuid': processing_version.uuid,
            'version_number': processing_version.version_number,
            'message': (
                f'Document segmented into {segment_count} chunks '
                f'(version {processing_version.version_number} with inherited '
                'processing)'
            ),
            'redirect_url': f'/input/document/{processing_version.uuid}'
        }

        current_app.logger.info(
            'Segmentation response: latest_version_id=%s, '
            'processing_version_uuid=%s, redirect_url=%s',
            processing_version.id,
            processing_version.uuid,
            response_data['redirect_url'],
        )
        return jsonify(response_data)

    except Exception as exc:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(exc)}), 500


@processing_bp.route('/document/<int:document_id>/segments', methods=['DELETE'])
@api_require_login_for_write
def delete_document_segments(document_id):
    """Delete all segments for a document."""
    try:
        document = Document.query.get_or_404(document_id)
        segment_count = document.text_segments.count()

        if segment_count == 0:
            return jsonify({
                'success': False,
                'error': 'No segments found to delete'
            }), 400

        deleted_count = TextSegment.query.filter_by(
            document_id=document_id
        ).delete()

        job = ProcessingJob(
            document_id=document_id,
            job_type='delete_segments',
            status='completed',
            user_id=current_user.id
        )
        job.set_parameters({'segments_deleted': deleted_count})
        job.set_result_data({
            'segments_deleted': deleted_count,
            'deletion_method': 'bulk_delete'
        })
        db.session.add(job)
        db.session.commit()

        return jsonify({
            'success': True,
            'job_id': job.id,
            'segments_deleted': deleted_count,
            'message': f'Deleted {deleted_count} text segments'
        })

    except Exception as exc:
        return jsonify({'success': False, 'error': str(exc)}), 500
