"""Reference PDF metadata extraction routes."""

import os

from flask import current_app, jsonify, request

from app.utils.auth_decorators import api_require_login_for_write

from .. import references_bp


@references_bp.route('/extract_metadata', methods=['POST'])
@api_require_login_for_write
def extract_metadata():
    """
    Extract metadata from uploaded PDF file before form submission.

    This provides real-time feedback to the user about what was extracted
    from the PDF (arXiv ID, DOI, title, authors) and the results of
    lookups to Semantic Scholar and CrossRef.

    Returns JSON with:
    - success: boolean
    - metadata: extracted metadata dict
    - progress: list of progress messages for UI display
    - zotero_match: optional Zotero match info
    """
    from app.services.upload_service import upload_service

    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'No file provided'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'error': 'No file selected'}), 400

    # Only process PDFs
    if not (file.filename or '').lower().endswith('.pdf'):
        return jsonify({'success': False, 'error': 'Only PDF files support automatic extraction'}), 400

    # Save to temp location
    upload_result = upload_service.save_to_temp(file)
    if not upload_result.success:
        return jsonify({'success': False, 'error': upload_result.error}), 400

    try:
        # Extract metadata with progress tracking
        result = upload_service.extract_metadata_from_pdf(upload_result.temp_path)

        if result.success:
            return jsonify({
                'success': True,
                'metadata': result.metadata,
                'progress': result.progress or [],
                'source': result.source
            })
        else:
            # Return what we found even if API lookups failed
            return jsonify({
                'success': False,
                'metadata': result.metadata or {},
                'progress': result.progress or [],
                'error': result.error or 'Could not find paper in academic databases'
            })

    except Exception as e:
        current_app.logger.error(f"Error extracting metadata: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'progress': []
        }), 500

    finally:
        # Clean up temp file
        if upload_result.temp_path and os.path.exists(upload_result.temp_path):
            try:
                os.remove(upload_result.temp_path)
            except:
                pass
