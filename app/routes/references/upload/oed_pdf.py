"""OED PDF parsing routes."""

import os
import tempfile

from flask import current_app, jsonify, request
from werkzeug.utils import secure_filename

from app.utils.auth_decorators import api_require_login_for_write

from .. import references_bp


@references_bp.route('/parse_oed_pdf', methods=['POST'])
@api_require_login_for_write
def parse_oed_pdf():
    """Parse uploaded OED PDF and return structured data"""
    from app.services.oed_parser_final import OEDParser

    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    # Check if it's a PDF
    if not (file.filename or '').lower().endswith('.pdf'):
        return jsonify({'error': 'Only PDF files are supported'}), 400

    # Save temporarily
    temp_dir = tempfile.gettempdir()
    temp_name = secure_filename(file.filename or 'oed.pdf')
    temp_path = os.path.join(temp_dir, temp_name)

    try:
        file.save(temp_path)

        # Parse with OED parser
        parser = OEDParser()
        extracted_data = parser.parse_pdf(temp_path)

        # Format for frontend
        response_data = {
            'success': True,
            'data': extracted_data,
            'message': 'Successfully parsed OED entry'
        }

        return jsonify(response_data)

    except Exception as e:
        current_app.logger.error(f"Error parsing OED PDF: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e),
            'message': 'Failed to parse OED PDF'
        }), 500

    finally:
        # Clean up temp file
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except:
                pass
