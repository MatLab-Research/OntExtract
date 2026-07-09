"""Streaming document metadata extraction routes and response mapping."""

from datetime import datetime

from flask import Response, current_app, jsonify, request

from app.utils.auth_decorators import api_require_login_for_write

from . import upload_bp


@upload_bp.route('/extract_metadata_stream', methods=['POST'])
@api_require_login_for_write
def extract_metadata_stream():
    """
    Stream metadata extraction progress using Server-Sent Events (SSE).

    This endpoint provides real-time progress updates during PDF analysis
    and external API lookups (Semantic Scholar, CrossRef).
    """
    from app.services.upload_service import upload_service
    import json
    import queue
    import threading

    # Get the uploaded file
    if 'document_file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400

    file = request.files['document_file']
    title = request.form.get('title', '').strip()
    enable_crossref = request.form.get('enable_crossref', 'true').lower() == 'true'

    # Save to temporary location first (before streaming)
    upload_result = upload_service.save_to_temp(file)
    if not upload_result.success:
        return jsonify({'error': upload_result.error}), 400

    temp_path = upload_result.temp_path
    original_filename = upload_result.filename

    # Create a queue for progress messages
    progress_queue = queue.Queue()
    result_holder = {'result': None, 'error': None}

    def extraction_worker():
        """Run extraction in background thread, putting progress into queue."""
        try:
            if enable_crossref:
                # Use the streaming version of metadata extraction
                result = upload_service.extract_metadata_from_pdf_streaming(
                    temp_path,
                    progress_callback=lambda msg: progress_queue.put({'type': 'progress', 'message': msg})
                )
                result_holder['result'] = result
            else:
                # No extraction needed
                result_holder['result'] = {
                    'success': True,
                    'metadata': {},
                    'source': 'user'
                }
            progress_queue.put({'type': 'complete'})
        except Exception as e:
            result_holder['error'] = str(e)
            progress_queue.put({'type': 'error', 'message': str(e)})

    # Capture app context for the generator
    app = current_app._get_current_object()

    def generate():
        """Generator that yields SSE events."""
        # Start the extraction in a background thread
        worker = threading.Thread(target=extraction_worker)
        worker.start()

        try:
            while True:
                try:
                    # Wait for messages with timeout (for heartbeat)
                    msg = progress_queue.get(timeout=1.0)

                    if msg['type'] == 'progress':
                        yield f"data: {json.dumps({'type': 'progress', 'message': msg['message']})}\n\n"

                    elif msg['type'] == 'complete':
                        # Worker finished, send final result
                        result = result_holder['result']
                        if result:
                            # Build the full response similar to extract_metadata
                            with app.app_context():
                                final_data = _build_extraction_response(
                                    result, temp_path, original_filename, title, enable_crossref
                                )
                            yield f"data: {json.dumps({'type': 'complete', 'data': final_data})}\n\n"
                        break

                    elif msg['type'] == 'error':
                        yield f"data: {json.dumps({'type': 'error', 'message': msg['message']})}\n\n"
                        break

                except queue.Empty:
                    # Send heartbeat to keep connection alive
                    yield f"data: {json.dumps({'type': 'heartbeat'})}\n\n"

        finally:
            worker.join(timeout=30)  # Wait for worker to finish

    return Response(generate(), mimetype='text/event-stream')

def _build_extraction_response(result, temp_path, original_filename, title, enable_crossref):
    """Build the response data from extraction result (shared logic)."""
    from datetime import datetime

    crossref_metadata = {}
    crossref_provenance = {}
    pdf_extracted_title = None
    pdf_extracted_metadata = {}
    progress_messages = []
    extraction_method = None

    if hasattr(result, 'success'):
        # It's a MetadataExtractionResult
        if hasattr(result, 'progress') and result.progress:
            progress_messages = result.progress

        if result.success:
            crossref_metadata = result.metadata
            extraction_method = result.metadata.get('extraction_method', 'pdf_analysis')
            source_name = result.source

            # Capture PDF-extracted title
            if crossref_metadata.get('extracted_title'):
                pdf_extracted_title = crossref_metadata['extracted_title']
                pdf_extracted_metadata = {'title': pdf_extracted_title}
                if crossref_metadata.get('extracted_authors'):
                    pdf_extracted_metadata['authors'] = crossref_metadata['extracted_authors']

            # Track provenance
            for key, value in crossref_metadata.items():
                if value is not None:
                    if 'arxiv' in str(extraction_method):
                        confidence = 0.95
                    elif 'doi' in str(extraction_method):
                        confidence = 0.9
                    else:
                        confidence = 0.85

                    crossref_provenance[key] = {
                        'source': source_name,
                        'confidence': confidence,
                        'timestamp': datetime.utcnow().isoformat(),
                        'raw_value': value,
                        'extraction_method': extraction_method
                    }
        else:
            # Extraction failed, use fallback
            pdf_extracted_metadata = result.metadata or {}
            if pdf_extracted_metadata.get('title'):
                pdf_extracted_title = pdf_extracted_metadata['title']
    else:
        # It's a dict result
        crossref_metadata = result.get('metadata', {})
        progress_messages = result.get('progress', [])

    # Merge metadata
    merged_metadata = {**crossref_metadata}
    merged_metadata['filename'] = original_filename

    # Build provenance for filename
    provenance = {**crossref_provenance}
    provenance['filename'] = {
        'source': 'file',
        'confidence': 1.0,
        'timestamp': datetime.utcnow().isoformat()
    }

    # Determine confidence level for CrossRef matches
    confidence_level = crossref_metadata.get('confidence_level', 'high')
    crossref_found = bool(crossref_metadata.get('title'))

    return {
        'success': True,
        'metadata': merged_metadata,
        'provenance': provenance,
        'temp_path': temp_path,
        'crossref_found': crossref_found,
        'confidence_level': confidence_level,
        'match_score': crossref_metadata.get('confidence_value', 0.0),
        'progress': progress_messages,
        'pdf_extracted_title': pdf_extracted_title,
        'pdf_extracted_metadata': pdf_extracted_metadata
    }
