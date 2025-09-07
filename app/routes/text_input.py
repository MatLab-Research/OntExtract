from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
import os
import uuid
from datetime import datetime
from docx import Document as DocxDocument
from langdetect import detect

from app import db
from app.models.document import Document
from app.models.processing_job import ProcessingJob
from app.services.text_processing import TextProcessingService
from app.utils.file_handler import FileHandler

text_input_bp = Blueprint('text_input', __name__)

@text_input_bp.route('/')
@text_input_bp.route('/upload')
@login_required
def upload_form():
    """Main upload form page"""
    return render_template('text_input/upload.html')

@text_input_bp.route('/paste')
@login_required
def paste_form():
    """Text paste form page"""
    return render_template('text_input/paste.html')

@text_input_bp.route('/submit_text', methods=['POST'])
@login_required
def submit_text():
    """Handle pasted text submission"""
    try:
        data = request.get_json() if request.is_json else request.form
        
        # Get form data
        title = data.get('title', '').strip()
        content = data.get('content', '').strip()
        
        if not content:
            if request.is_json:
                return jsonify({'error': 'Content is required'}), 400
            flash('Content is required', 'error')
            return redirect(url_for('text_input.paste_form'))
        
        # Auto-generate title if not provided
        if not title:
            first_line = content.split('\n')[0].strip()
            title = first_line[:50] + ('...' if len(first_line) > 50 else '') or 'Untitled Text'
        
        # Detect language
        detected_language = None
        language_confidence = 0.0
        try:
            detected_language = detect(content)
            language_confidence = 0.9  # Langdetect doesn't provide confidence, using default
        except:
            detected_language = 'en'  # Default to English
            language_confidence = 0.5
        
        # Create document record
        document = Document(
            title=title,
            content_type='text',
            content=content,
            detected_language=detected_language,
            language_confidence=language_confidence,
            status='uploaded',
            user_id=current_user.id
        )
        
        db.session.add(document)
        db.session.commit()
        
        # Note: Segmentation is now manual from document processing page
        # Removed automatic segmentation to allow user control
        
        if request.is_json:
            return jsonify({
                'success': True,
                'document_id': document.id,
                'message': 'Text submitted successfully',
                'redirect_url': url_for('text_input.document_detail', document_id=document.id)
            })
        
        flash('Text submitted successfully!', 'success')
        return redirect(url_for('text_input.document_detail', document_id=document.id))
        
    except Exception as e:
        current_app.logger.error(f"Error submitting text: {str(e)}")
        if request.is_json:
            return jsonify({'error': 'An error occurred while processing your text'}), 500
        flash('An error occurred while processing your text', 'error')
        return redirect(url_for('text_input.paste_form'))

@text_input_bp.route('/upload_file', methods=['POST'])
@login_required
def upload_file():
    """Handle file upload submission"""
    try:
        if 'file' not in request.files:
            if request.is_json:
                return jsonify({'error': 'No file selected'}), 400
            flash('No file selected', 'error')
            return redirect(url_for('text_input.upload_form'))
        
        file = request.files['file']
        title = request.form.get('title', '').strip()
        
        if file.filename == '':
            if request.is_json:
                return jsonify({'error': 'No file selected'}), 400
            flash('No file selected', 'error')
            return redirect(url_for('text_input.upload_form'))
        
        # Validate file type
        file_handler = FileHandler()
        fname = file.filename or ''
        if not file_handler.allowed_file(fname):
            allowed = ', '.join(current_app.config['ALLOWED_EXTENSIONS'])
            error_msg = f'File type not allowed. Allowed types: {allowed}'
            if request.is_json:
                return jsonify({'error': error_msg}), 400
            flash(error_msg, 'error')
            return redirect(url_for('text_input.upload_form'))
        
        # Generate secure filename
        original_filename = fname
        filename = secure_filename(original_filename or '')
        unique_filename = f"{uuid.uuid4().hex}_{filename}"
        
        # Save file
        upload_folder = current_app.config['UPLOAD_FOLDER']
        os.makedirs(upload_folder, exist_ok=True)
        file_path = os.path.join(upload_folder, unique_filename)
        file.save(file_path)
        
        # Get file size
        file_size = os.path.getsize(file_path)
        
        # Extract text content
        content = file_handler.extract_text_from_file(file_path, original_filename or '')
        
        if not content:
            os.remove(file_path)  # Clean up file
            error_msg = 'Could not extract text from file'
            if request.is_json:
                return jsonify({'error': error_msg}), 400
            flash(error_msg, 'error')
            return redirect(url_for('text_input.upload_form'))
        
        # Auto-generate title if not provided
        if not title:
            title = os.path.splitext(original_filename or '')[0]
        
        # Detect language
        detected_language = None
        language_confidence = 0.0
        try:
            detected_language = detect(content)
            language_confidence = 0.9
        except:
            detected_language = 'en'
            language_confidence = 0.5
        
        # Get file extension
        file_extension = file_handler.get_file_extension(original_filename or '')
        
        # Create document record
        document = Document(
            title=title,
            content_type='file',
            file_type=file_extension,
            original_filename=original_filename,
            file_path=file_path,
            file_size=file_size,
            content=content,
            detected_language=detected_language,
            language_confidence=language_confidence,
            status='uploaded',
            user_id=current_user.id
        )
        
        db.session.add(document)
        db.session.commit()
        
        # Note: Segmentation is now manual from document processing page
        # Removed automatic segmentation to allow user control
        
        if request.is_json:
            return jsonify({
                'success': True,
                'document_id': document.id,
                'message': 'File uploaded successfully',
                'redirect_url': url_for('text_input.document_detail', document_id=document.id)
            })
        
        flash('File uploaded successfully!', 'success')
        return redirect(url_for('text_input.document_detail', document_id=document.id))
        
    except Exception as e:
        current_app.logger.error(f"Error uploading file: {str(e)}")
        # Clean up file if it was saved
        if 'file_path' in locals() and os.path.exists(file_path):
            os.remove(file_path)
        
        if request.is_json:
            return jsonify({'error': 'An error occurred while uploading your file'}), 500
        flash('An error occurred while uploading your file', 'error')
        return redirect(url_for('text_input.upload_form'))

@text_input_bp.route('/documents')
@login_required
def document_list():
    """List all user documents (both source documents and references)"""
    page = request.args.get('page', 1, type=int)
    per_page = 10
    
    # Show ALL documents regardless of type
    documents = Document.query\
        .order_by(Document.created_at.desc())\
        .paginate(page=page, per_page=per_page, error_out=False)
    
    return render_template('text_input/document_list.html', documents=documents)

@text_input_bp.route('/document/<int:document_id>')
@login_required
def document_detail(document_id):
    """Show document details"""
    document = Document.query.filter_by(id=document_id).first_or_404()
    
    # Get processing jobs for this document
    processing_jobs = document.processing_jobs.order_by(ProcessingJob.created_at.desc()).limit(5).all()
    
    # Get available experiments for dropdown
    from app.models.experiment import Experiment
    experiments = Experiment.query.order_by(Experiment.created_at.desc()).all()
    
    return render_template('text_input/document_detail.html', 
                         document=document, 
                         processing_jobs=processing_jobs,
                         experiments=experiments)

@text_input_bp.route('/document/<int:document_id>/delete', methods=['POST'])
@login_required
def delete_document(document_id):
    """Delete a document"""
    document = Document.query.filter_by(id=document_id).first_or_404()
    
    try:
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
        return redirect(url_for('text_input.document_detail', document_id=document_id))

@text_input_bp.route('/api/document/<int:document_id>/content')
@login_required
def api_document_content(document_id):
    """API endpoint to get document content"""
    document = Document.query.filter_by(id=document_id).first_or_404()
    return jsonify(document.to_dict(include_content=True))

@text_input_bp.route('/api/documents')
@login_required
def api_document_list():
    """API endpoint to list user's documents"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    
    documents = Document.query\
        .order_by(Document.created_at.desc())\
        .paginate(page=page, per_page=per_page, error_out=False)
    
    return jsonify({
        'documents': [doc.to_dict() for doc in documents.items],
        'total': documents.total,
        'pages': documents.pages,
        'current_page': documents.page,
        'has_next': documents.has_next,
        'has_prev': documents.has_prev
    })

@text_input_bp.route('/documents/<int:document_id>/apply_embeddings', methods=['POST'])
@login_required
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
            max_length = 8000  # Conservative limit for most embedding models
            
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
