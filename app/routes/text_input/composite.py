"""
Text Input Composite Document Routes

This module handles composite document operations.

Routes:
- POST /input/composite/create/<id>       - Create composite document
- GET  /input/composite/sources/<id>      - Get composite sources
- POST /input/composite/update/<id>       - Update composite document
"""

from flask import jsonify, current_app

from app.models.document import Document
from app.utils.auth_decorators import write_login_required, public_with_auth_context

from . import text_input_bp


@text_input_bp.route('/composite/create/<int:document_id>', methods=['POST'])
@write_login_required
def create_composite(document_id):
    """Create a composite document from all versions of the given document"""
    try:
        # Get the document and all its versions
        document = Document.query.get_or_404(document_id)
        all_versions = document.get_all_versions()

        # Filter to get only processed versions (exclude original and composites)
        processed_versions = [v for v in all_versions if v.version_type == 'processed']

        if len(processed_versions) < 2:
            return jsonify({
                'success': False,
                'error': 'Need at least 2 processed versions to create a composite'
            }), 400

        # Import the composite service
        from app.services.composite_versioning_service import CompositeVersioningService

        # Create the composite
        composite_doc = CompositeVersioningService.create_composite_from_versions(
            original_document=document.get_root_document(),
            source_versions=processed_versions
        )

        return jsonify({
            'success': True,
            'composite_id': composite_doc.id,
            'message': f'Composite created with {len(processed_versions)} source versions'
        })

    except Exception as e:
        current_app.logger.error(f"Error creating composite: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@text_input_bp.route('/composite/sources/<int:composite_id>')
@public_with_auth_context
def get_composite_sources(composite_id):
    """Get information about the source documents for a composite"""
    try:
        composite = Document.query.get_or_404(composite_id)

        if not composite.is_composite():
            return jsonify({
                'success': False,
                'error': 'Document is not a composite'
            }), 400

        sources = composite.get_composite_sources()

        source_data = []
        for source in sources:
            source_data.append({
                'id': source.id,
                'title': source.title,
                'version_type': source.version_type,
                'version_number': source.version_number,
                'created_at': source.created_at.isoformat() if source.created_at else None,
                'processing_metadata': source.processing_metadata
            })

        return jsonify({
            'success': True,
            'composite_id': composite_id,
            'source_documents': source_data
        })

    except Exception as e:
        current_app.logger.error(f"Error getting composite sources: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@text_input_bp.route('/composite/update/<int:composite_id>', methods=['POST'])
@write_login_required
def update_composite(composite_id):
    """Update a composite document with new versions"""
    try:
        composite = Document.query.get_or_404(composite_id)

        if not composite.is_composite():
            return jsonify({
                'success': False,
                'error': 'Document is not a composite'
            }), 400

        # Get the root document and find any new versions
        root_doc = composite.get_root_document()
        all_versions = root_doc.get_all_versions()
        existing_sources = set(composite.composite_sources or [])

        # Find new processed versions not in the composite
        new_versions = [
            v for v in all_versions
            if v.version_type == 'processed' and v.id not in existing_sources
        ]

        if not new_versions:
            return jsonify({
                'success': False,
                'error': 'No new versions to add to composite'
            }), 400

        # Import the composite service
        from app.services.composite_versioning_service import CompositeVersioningService

        # Update the composite with new versions
        for new_version in new_versions:
            CompositeVersioningService.update_composite_from_new_version(composite, new_version)

        return jsonify({
            'success': True,
            'message': f'Added {len(new_versions)} new versions to composite'
        })

    except Exception as e:
        current_app.logger.error(f"Error updating composite: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500
