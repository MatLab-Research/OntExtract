from flask import Blueprint, request, jsonify, render_template, flash, redirect, url_for
from flask_login import login_required, current_user
from app import db
from app.models.document import Document
from app.services.composite_document_service import CompositeDocumentService

composite_bp = Blueprint('composite', __name__, url_prefix='/composite')


@composite_bp.route('/create', methods=['POST'])
@login_required
def create_composite():
    """Create a composite document from selected source documents"""
    try:
        data = request.get_json() if request.is_json else request.form
        
        source_ids = data.get('source_documents', [])
        title = data.get('title', '').strip()
        strategy = data.get('strategy', 'all_processing')
        
        if not source_ids:
            return jsonify({'error': 'No source documents specified'}), 400
        
        if not title:
            return jsonify({'error': 'Title is required'}), 400
        
        # Validate source documents exist and belong to user
        source_documents = Document.query.filter(
            Document.id.in_(source_ids),
            Document.user_id == current_user.id
        ).all()
        
        if len(source_documents) != len(source_ids):
            return jsonify({'error': 'One or more source documents not found'}), 400
        
        if len(source_documents) < 2:
            return jsonify({'error': 'At least 2 source documents required for composite'}), 400
        
        # Create composite document
        composite_doc = Document.create_composite(
            title=title,
            source_documents=source_documents,
            strategy=strategy,
            user_id=current_user.id
        )
        
        # Create provenance
        CompositeDocumentService.create_composite_provenance(composite_doc, source_documents)
        
        if request.is_json:
            return jsonify({
                'success': True,
                'composite_document_id': composite_doc.id,
                'message': f'Composite document created with {len(source_documents)} sources',
                'redirect_url': url_for('text_input.document_detail', document_id=composite_doc.id)
            })
        
        flash(f'Composite document "{title}" created successfully!', 'success')
        return redirect(url_for('text_input.document_detail', document_id=composite_doc.id))
        
    except Exception as e:
        db.session.rollback()
        error_msg = f'Error creating composite document: {str(e)}'
        
        if request.is_json:
            return jsonify({'error': error_msg}), 500
        
        flash(error_msg, 'error')
        return redirect(url_for('text_input.document_list'))


@composite_bp.route('/auto-create/<int:original_document_id>', methods=['POST'])
@login_required
def auto_create_composite(original_document_id):
    """Automatically create composite document for an original with multiple processed versions"""
    try:
        original_doc = Document.query.filter_by(
            id=original_document_id,
            user_id=current_user.id
        ).first_or_404()
        
        composite_doc = CompositeDocumentService.auto_create_composite(original_doc)
        
        if not composite_doc:
            return jsonify({
                'error': 'Not enough processed versions to create composite document'
            }), 400
        
        return jsonify({
            'success': True,
            'composite_document_id': composite_doc.id,
            'message': 'Composite document created automatically',
            'redirect_url': url_for('text_input.document_detail', document_id=composite_doc.id),
            'available_processing': list(composite_doc.get_available_processing().keys())
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Error auto-creating composite: {str(e)}'}), 500


@composite_bp.route('/update/<int:composite_id>', methods=['POST'])
@login_required
def update_composite(composite_id):
    """Update an existing composite document with latest processing"""
    try:
        composite_doc = Document.query.filter_by(
            id=composite_id,
            user_id=current_user.id,
            version_type='composite'
        ).first_or_404()
        
        updated_composite = CompositeDocumentService.update_composite(composite_doc)
        
        return jsonify({
            'success': True,
            'message': 'Composite document updated',
            'available_processing': list(updated_composite.get_available_processing().keys()),
            'last_updated': updated_composite.updated_at.isoformat()
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Error updating composite: {str(e)}'}), 500


@composite_bp.route('/recommendations/<int:document_id>')
@login_required
def get_recommendations(document_id):
    """Get recommendations for composite document creation or usage"""
    try:
        document = Document.query.filter_by(
            id=document_id,
            user_id=current_user.id
        ).first_or_404()
        
        recommendations = CompositeDocumentService.get_processing_recommendations(document)
        
        return jsonify({
            'success': True,
            'recommendations': recommendations,
            'document_type': document.version_type
        })
        
    except Exception as e:
        return jsonify({'error': f'Error getting recommendations: {str(e)}'}), 500


@composite_bp.route('/processing-status/<int:document_id>')
@login_required
def get_processing_status(document_id):
    """Get comprehensive processing status for any document type"""
    try:
        document = Document.query.filter_by(
            id=document_id,
            user_id=current_user.id
        ).first_or_404()
        
        status = CompositeDocumentService.get_document_processing_status(document)
        
        return jsonify({
            'success': True,
            'processing_status': status
        })
        
    except Exception as e:
        return jsonify({'error': f'Error getting processing status: {str(e)}'}), 500


@composite_bp.route('/sources/<int:composite_id>')
@login_required 
def get_composite_sources(composite_id):
    """Get detailed information about composite document sources"""
    try:
        composite_doc = Document.query.filter_by(
            id=composite_id,
            user_id=current_user.id,
            version_type='composite'
        ).first_or_404()
        
        sources = composite_doc.get_composite_sources()
        source_details = []
        
        for source_doc in sources:
            processing_jobs = source_doc.processing_jobs.filter_by(status='completed').all()
            source_details.append({
                'id': source_doc.id,
                'title': source_doc.title,
                'version_type': source_doc.version_type,
                'created_at': source_doc.created_at.isoformat(),
                'processing_types': [job.job_type for job in processing_jobs],
                'processing_count': len(processing_jobs)
            })
        
        return jsonify({
            'success': True,
            'composite_id': composite_id,
            'composite_title': composite_doc.title,
            'strategy': composite_doc.composite_strategy,
            'source_documents': source_details,
            'total_sources': len(source_details),
            'available_processing': list(composite_doc.get_available_processing().keys())
        })
        
    except Exception as e:
        return jsonify({'error': f'Error getting composite sources: {str(e)}'}), 500


@composite_bp.route('/selection')
@login_required
def composite_selection():
    """Show interface for selecting documents to create composite"""
    # Get user's documents that could be used for composites
    user_documents = Document.query.filter_by(
        user_id=current_user.id
    ).filter(
        Document.version_type.in_(['original', 'processed'])
    ).order_by(Document.created_at.desc()).all()
    
    # Group by original document for easier selection
    document_groups = {}
    for doc in user_documents:
        if doc.version_type == 'original':
            root_id = doc.id
        else:
            root_id = doc.source_document_id or doc.id
        
        if root_id not in document_groups:
            document_groups[root_id] = {'original': None, 'processed': []}
        
        if doc.version_type == 'original':
            document_groups[root_id]['original'] = doc
        else:
            document_groups[root_id]['processed'].append(doc)
    
    return render_template('composite/selection.html', 
                         document_groups=document_groups)


# Error handlers
@composite_bp.errorhandler(404)
def composite_not_found(e):
    if request.is_json:
        return jsonify({'error': 'Composite document not found'}), 404
    flash('Composite document not found', 'error')
    return redirect(url_for('text_input.document_list'))


@composite_bp.errorhandler(403)
def composite_forbidden(e):
    if request.is_json:
        return jsonify({'error': 'Access denied to composite document'}), 403
    flash('Access denied', 'error')
    return redirect(url_for('text_input.document_list'))