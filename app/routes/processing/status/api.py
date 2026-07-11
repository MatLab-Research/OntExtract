"""Processing job status and diagnostic APIs."""

from flask import jsonify

from app.services.base_service import NotFoundError, ValidationError
from app.utils.auth_decorators import api_require_login_for_write

from .. import processing_bp
from . import processing_status_service


@processing_bp.route('/api/processing/job/<int:job_id>/langextract-details')
@api_require_login_for_write
def get_langextract_details(job_id):
    """Return detailed LangExtract analysis for a legacy processing job."""
    try:
        return jsonify(processing_status_service.get_langextract_details(job_id))
    except NotFoundError as exc:
        return jsonify({'success': False, 'error': str(exc)}), 404
    except ValidationError as exc:
        return jsonify({'success': False, 'error': str(exc)}), 400
    except Exception as exc:
        return jsonify({'success': False, 'error': str(exc)}), 500


@processing_bp.route('/job/<int:job_id>/status', methods=['GET'])
def get_job_status(job_id):
    """Return status and progress for a legacy processing job."""
    try:
        return jsonify(processing_status_service.get_job_status(job_id))
    except NotFoundError as exc:
        return jsonify({'success': False, 'error': str(exc)}), 404
    except Exception as exc:
        return jsonify({'success': False, 'error': str(exc)}), 500


@processing_bp.route(
    '/document/<string:document_uuid>/processing-jobs',
    methods=['GET'],
)
def get_document_processing_jobs(document_uuid):
    """Return grouped legacy processing jobs for a document."""
    try:
        return jsonify(
            processing_status_service.get_document_processing_jobs(document_uuid)
        )
    except NotFoundError as exc:
        return jsonify({'success': False, 'error': str(exc)}), 404
    except Exception as exc:
        return jsonify({'success': False, 'error': str(exc)}), 500
