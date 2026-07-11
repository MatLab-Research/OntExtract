"""Streaming upload metadata extraction route."""

from flask import Response, current_app, jsonify, request

from app.services.base_service import ValidationError
from app.services.streaming_metadata_service import StreamingMetadataService
from app.services.upload_service import upload_service
from app.utils.auth_decorators import api_require_login_for_write

from . import upload_bp


@upload_bp.route('/extract_metadata_stream', methods=['POST'])
@api_require_login_for_write
def extract_metadata_stream():
    """Stream PDF/CrossRef metadata extraction progress as SSE events."""
    try:
        service = StreamingMetadataService(upload_service, current_app.logger)
        stream = service.create_stream(
            request.files.get('document_file'),
            request.form.get('title', '').strip(),
            request.form.get('enable_crossref', 'true').lower() == 'true',
            current_app._get_current_object(),
        )
        return Response(
            stream,
            mimetype='text/event-stream',
            headers={
                'Cache-Control': 'no-cache',
                'X-Accel-Buffering': 'no',
            },
        )
    except ValidationError as exc:
        return jsonify({'error': str(exc)}), 400
    except Exception as exc:
        current_app.logger.error(
            f'Error starting streaming metadata extraction: {exc}',
            exc_info=True,
        )
        return jsonify({'error': str(exc)}), 500
