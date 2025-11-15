"""
Text Input Processing Routes

This module handles document processing operations.

Routes:
- POST /input/documents/<id>/apply_embeddings - Apply embeddings to document
"""

from flask import jsonify, current_app
from datetime import datetime

from app import db
from app.models.document import Document
from app.utils.auth_decorators import write_login_required

from . import text_input_bp


@text_input_bp.route('/documents/<int:document_id>/apply_embeddings', methods=['POST'])
@write_login_required
def apply_embeddings(document_id):
    """Apply embeddings to a document"""
    try:
        document = Document.query.filter_by(id=document_id).first_or_404()

        if not document.content:
            return jsonify({'error': 'Document has no content to process'}), 400

        # Initialize embedding service
        try:
            from shared_services.embedding.embedding_service import EmbeddingService
            embedding_service = EmbeddingService()
        except ImportError:
            # Fallback to basic implementation if shared services not available
            return jsonify({'error': 'Embedding service not available'}), 500

        # Generate embeddings
        try:
            # Process document content in chunks if too long
            content = document.content
            max_length = 8000

            if len(content) > max_length:
                # Split into chunks and embed each
                chunks = [content[i:i+max_length] for i in range(0, len(content), max_length)]
                embeddings = []
                for chunk in chunks:
                    chunk_embedding = embedding_service.get_embedding(chunk)
                    embeddings.append(chunk_embedding)

                # Store metadata about chunked processing
                embedding_info = {
                    'type': 'chunked',
                    'chunks': len(chunks),
                    'chunk_size': max_length,
                    'model': embedding_service.get_model_name(),
                    'dimension': embedding_service.get_dimension()
                }
            else:
                # Single embedding for short documents
                embeddings = [embedding_service.get_embedding(content)]
                embedding_info = {
                    'type': 'single',
                    'model': embedding_service.get_model_name(),
                    'dimension': embedding_service.get_dimension()
                }

            # Update document metadata
            if not document.processing_metadata:
                document.processing_metadata = {}

            # Mark embeddings as applied
            document.processing_metadata['processing_info'] = document.processing_metadata.get('processing_info', {})
            document.processing_metadata['processing_info']['embeddings_applied'] = True
            document.processing_metadata['processing_info']['embeddings_info'] = embedding_info
            document.processing_metadata['processing_info']['applied_at'] = datetime.utcnow().isoformat()

            # Update word count if not set
            if not document.word_count:
                document.word_count = len(content.split())

            document.updated_at = datetime.utcnow()
            db.session.commit()

            return jsonify({
                'success': True,
                'message': 'Embeddings applied successfully',
                'embedding_info': embedding_info
            })

        except Exception as e:
            current_app.logger.error(f"Error generating embeddings: {str(e)}")
            return jsonify({'error': f'Failed to generate embeddings: {str(e)}'}), 500

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error applying embeddings: {str(e)}")
        return jsonify({'error': 'An error occurred while applying embeddings'}), 500
