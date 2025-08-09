from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
import os
import json
from datetime import datetime
from app import db
from app.models.document import Document
from app.models.experiment import Experiment
from app.services.text_processing import TextProcessingService
from app.utils.file_handler import FileHandler

references_bp = Blueprint('references', __name__, url_prefix='/references')

@references_bp.route('/')
@login_required
def index():
    """List all references for the current user"""
    references = Document.query.filter_by(
        user_id=current_user.id,
        document_type='reference'
    ).order_by(Document.created_at.desc()).all()
    
    return render_template('references/index.html', references=references)

@references_bp.route('/upload', methods=['GET', 'POST'])
@login_required
def upload():
    """Upload a new reference document"""
    # Check if we should use the new tabbed interface
    use_tabbed = request.args.get('tabbed', 'true').lower() == 'true'
    
    if request.method == 'POST':
        # Check if file was uploaded
        if 'file' not in request.files:
            flash('No file provided', 'error')
            return redirect(request.url)
        
        file = request.files['file']
        if file.filename == '':
            flash('No file selected', 'error')
            return redirect(request.url)
        
        # Get metadata from form
        title = request.form.get('title')
        reference_subtype = request.form.get('reference_subtype', 'other')
        authors = request.form.get('authors', '').split(',')
        authors = [a.strip() for a in authors if a.strip()]
        publication_date = request.form.get('publication_date')
        journal = request.form.get('journal')
        doi = request.form.get('doi')
        isbn = request.form.get('isbn')
        url = request.form.get('url')
        abstract = request.form.get('abstract')
        citation = request.form.get('citation')
        
        # Save file
        from flask import current_app
        file_handler = FileHandler(current_app.config['UPLOAD_FOLDER'])
        saved_path, file_size = file_handler.save_file(file)
        
        if not saved_path:
            flash('Failed to save file', 'error')
            return redirect(request.url)
        
        # Create source metadata
        source_metadata = {
            'authors': authors,
            'publication_date': publication_date,
            'journal': journal,
            'doi': doi,
            'isbn': isbn,
            'url': url,
            'abstract': abstract,
            'citation': citation
        }
        
        # Remove empty values
        source_metadata = {k: v for k, v in source_metadata.items() if v}
        
        # Create document record
        document = Document(
            title=title or secure_filename(file.filename),
            content_type='file',
            document_type='reference',
            reference_subtype=reference_subtype,
            file_type=file_handler.get_file_extension(file.filename),
            original_filename=file.filename,
            file_path=saved_path,
            file_size=file_size,
            source_metadata=source_metadata if source_metadata else None,
            user_id=current_user.id,
            status='uploaded'
        )
        
        db.session.add(document)
        db.session.commit()
        
        # Process the reference document
        try:
            processing_service = TextProcessingService()
            processing_service.process_document(document)
            flash(f'Reference "{document.title}" uploaded and processed successfully', 'success')
        except Exception as e:
            flash(f'Reference uploaded but processing failed: {str(e)}', 'warning')
        
        # Check if this was uploaded from an experiment
        experiment_id = request.form.get('experiment_id')
        if experiment_id:
            experiment = Experiment.query.get(experiment_id)
            if experiment and experiment.user_id == current_user.id:
                experiment.add_reference(document, 
                                       include_in_analysis=request.form.get('include_in_analysis') == 'true')
                flash(f'Reference linked to experiment "{experiment.name}"', 'success')
                return redirect(url_for('experiments.view', id=experiment_id))
        
        return redirect(url_for('references.view', id=document.id))
    
    # GET request - show upload form
    experiment_id = request.args.get('experiment_id')
    experiment = None
    if experiment_id:
        experiment = Experiment.query.filter_by(
            id=experiment_id,
            user_id=current_user.id
        ).first()
    
    # Use tabbed interface by default for better UX
    if use_tabbed:
        return render_template('references/upload_tabbed.html', experiment=experiment)
    else:
        return render_template('references/upload.html', experiment=experiment)

@references_bp.route('/parse_oed_pdf', methods=['POST'])
@login_required
def parse_oed_pdf():
    """Parse uploaded OED PDF and return structured data"""
    import tempfile
    from app.services.oed_parser import OEDParser
    from flask import current_app
    
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    # Check if it's a PDF
    if not file.filename.lower().endswith('.pdf'):
        return jsonify({'error': 'Only PDF files are supported'}), 400
    
    # Save temporarily
    temp_dir = tempfile.gettempdir()
    temp_path = os.path.join(temp_dir, secure_filename(file.filename))
    
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

@references_bp.route('/<int:id>')
@login_required
def view(id):
    """View reference details"""
    reference = Document.query.filter_by(
        id=id,
        user_id=current_user.id,
        document_type='reference'
    ).first_or_404()
    
    # Get experiments that use this reference
    experiments_using = Experiment.query.join(
        Experiment.references
    ).filter(
        Document.id == reference.id,
        Experiment.user_id == current_user.id
    ).all()
    
    return render_template('references/view.html', 
                         reference=reference,
                         experiments_using=experiments_using)

@references_bp.route('/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit(id):
    """Edit reference metadata"""
    reference = Document.query.filter_by(
        id=id,
        user_id=current_user.id,
        document_type='reference'
    ).first_or_404()
    
    if request.method == 'POST':
        # Update basic info
        reference.title = request.form.get('title', reference.title)
        reference.reference_subtype = request.form.get('reference_subtype', reference.reference_subtype)
        
        # Update source metadata
        authors = request.form.get('authors', '').split(',')
        authors = [a.strip() for a in authors if a.strip()]
        
        source_metadata = {
            'authors': authors,
            'publication_date': request.form.get('publication_date'),
            'journal': request.form.get('journal'),
            'doi': request.form.get('doi'),
            'isbn': request.form.get('isbn'),
            'url': request.form.get('url'),
            'abstract': request.form.get('abstract'),
            'citation': request.form.get('citation')
        }
        
        # Remove empty values
        source_metadata = {k: v for k, v in source_metadata.items() if v}
        reference.source_metadata = source_metadata if source_metadata else None
        
        db.session.commit()
        flash('Reference updated successfully', 'success')
        return redirect(url_for('references.view', id=reference.id))
    
    return render_template('references/edit.html', reference=reference)

@references_bp.route('/<int:id>/delete', methods=['POST'])
@login_required
def delete(id):
    """Delete a reference"""
    reference = Document.query.filter_by(
        id=id,
        user_id=current_user.id,
        document_type='reference'
    ).first_or_404()
    
    # Delete file if exists
    reference.delete_file()
    
    # Delete from database
    db.session.delete(reference)
    db.session.commit()
    
    flash('Reference deleted successfully', 'success')
    return redirect(url_for('references.index'))

# API endpoints for AJAX operations
@references_bp.route('/api/search')
@login_required
def api_search():
    """Search references for autocomplete/selection"""
    query = request.args.get('q', '')
    
    if not query:
        references = Document.query.filter_by(
            user_id=current_user.id,
            document_type='reference'
        ).limit(20).all()
    else:
        references = Document.query.filter(
            Document.user_id == current_user.id,
            Document.document_type == 'reference',
            Document.title.contains(query)
        ).limit(20).all()
    
    return jsonify([{
        'id': ref.id,
        'title': ref.title,
        'source_info': ref.get_source_info(),
        'citation': ref.get_citation()
    } for ref in references])

@references_bp.route('/upload_dictionary', methods=['POST'])
@login_required
def upload_dictionary():
    """Upload a dictionary entry (OED or general)"""
    # Get form data
    title = request.form.get('title')
    content = request.form.get('content')  # This is the full text field
    reference_subtype = request.form.get('reference_subtype', 'dictionary_general')
    
    if not title or not content:
        flash('Term and definition are required', 'error')
        return redirect(url_for('references.upload'))
    
    # Build source metadata based on dictionary type
    source_metadata = {}
    
    if reference_subtype == 'dictionary_oed':
        # OED-specific fields - store everything in metadata for reference
        source_metadata = {
            'pronunciation': request.form.get('pronunciation'),
            'etymology': request.form.get('etymology'),
            'usage_notes': request.form.get('usage_notes'),
            'examples': request.form.get('examples'),  # Temporal quotations
            'first_use': request.form.get('first_use'),
            'edition': request.form.get('edition'),
            'journal': 'Oxford English Dictionary',
            'url': request.form.get('url'),
            'citation': request.form.get('citation'),
            'pdf_link': request.form.get('pdf_link')  # Store PDF filename reference
        }
        
        # Store the FULL content as-is (no formatting, just the complete text)
        # This ensures we capture everything from the OED entry
        formatted_content = content  # Use full content directly
            
    else:
        # General dictionary fields
        source_metadata = {
            'journal': request.form.get('journal'),  # Dictionary source
            'context': request.form.get('context'),
            'synonyms': request.form.get('synonyms'),
            'url': request.form.get('url')
        }
        
        # Format the content for general dictionary
        formatted_content = f"Term: {title}\n\n"
        formatted_content += f"Source: {source_metadata.get('journal', 'Unknown')}\n\n"
        if source_metadata.get('context'):
            formatted_content += f"Context/Domain: {source_metadata['context']}\n\n"
        formatted_content += f"Definition:\n{content}\n"
        if source_metadata.get('synonyms'):
            formatted_content += f"\nSynonyms: {source_metadata['synonyms']}\n"
    
    # Remove empty values from metadata
    source_metadata = {k: v for k, v in source_metadata.items() if v}
    
    # Create document record
    document = Document(
        title=title,
        content_type='text',
        document_type='reference',
        reference_subtype=reference_subtype,
        content=formatted_content,
        content_preview=formatted_content[:500] + ('...' if len(formatted_content) > 500 else ''),
        source_metadata=source_metadata if source_metadata else None,
        user_id=current_user.id,
        status='completed',  # Text entries are immediately available
        word_count=len(formatted_content.split()),
        character_count=len(formatted_content)
    )
    
    db.session.add(document)
    db.session.commit()
    
    flash(f'Dictionary entry "{document.title}" saved successfully', 'success')
    
    # Check if this was linked from an experiment
    experiment_id = request.form.get('experiment_id')
    if experiment_id:
        experiment = Experiment.query.get(experiment_id)
        if experiment and experiment.user_id == current_user.id:
            experiment.add_reference(document, 
                                   include_in_analysis=request.form.get('include_in_analysis') == 'true')
            flash(f'Dictionary entry linked to experiment "{experiment.name}"', 'success')
            return redirect(url_for('experiments.view', id=experiment_id))
    
    return redirect(url_for('references.view', id=document.id))
