from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app
from flask_login import login_required, current_user
from app import db
from app.models import Term, TermVersion, ContextAnchor, FuzzinessAdjustment, AnalysisAgent
from app.services.term_analysis_service import TermAnalysisService, TermAnalysisResult
from sqlalchemy import func, desc
from datetime import datetime
import json
import uuid

terms_bp = Blueprint('terms', __name__, url_prefix='/terms')

# Initialize term analysis service (singleton)
_term_analysis_service = None

def get_term_analysis_service():
    """Get or create term analysis service instance."""
    global _term_analysis_service
    if _term_analysis_service is None:
        try:
            _term_analysis_service = TermAnalysisService()
            current_app.logger.info("TermAnalysisService initialized successfully")
        except Exception as e:
            current_app.logger.error(f"Failed to initialize TermAnalysisService: {e}")
            _term_analysis_service = None
    return _term_analysis_service


@terms_bp.route('/')
@login_required
def term_index():
    """Display alphabetical index of all terms"""
    page = request.args.get('page', 1, type=int)
    per_page = 50  # Show 50 terms per page
    
    # Search functionality
    search_query = request.args.get('search', '').strip()
    status_filter = request.args.get('status', '')
    domain_filter = request.args.get('domain', '')
    
    # Base query
    query = Term.query
    
    # Apply filters
    if search_query:
        query = query.filter(Term.term_text.ilike(f'%{search_query}%'))
    
    if status_filter:
        query = query.filter(Term.status == status_filter)
    
    if domain_filter:
        query = query.filter(Term.research_domain == domain_filter)
    
    # Order alphabetically
    query = query.order_by(Term.term_text)
    
    # Paginate
    terms = query.paginate(page=page, per_page=per_page, error_out=False)
    
    # Get available domains for filter dropdown
    domains = db.session.query(Term.research_domain).distinct().filter(
        Term.research_domain.isnot(None)
    ).all()
    domains = [d[0] for d in domains]
    
    return render_template('terms/index.html', 
                         terms=terms, 
                         search_query=search_query,
                         status_filter=status_filter,
                         domain_filter=domain_filter,
                         domains=domains)


@terms_bp.route('/add', methods=['GET', 'POST'])
@login_required 
def add_term():
    """Add new term with wizard interface"""
    if request.method == 'POST':
        try:
            # Parse form data
            term_text = request.form.get('term_text', '').strip()
            description = request.form.get('description', '').strip()
            etymology = request.form.get('etymology', '').strip()
            notes = request.form.get('notes', '').strip()
            research_domain = request.form.get('research_domain', '').strip()
            selection_rationale = request.form.get('selection_rationale', '').strip()
            historical_significance = request.form.get('historical_significance', '').strip()
            
            # First version data
            temporal_period = request.form.get('temporal_period', '').strip()
            temporal_start_year = request.form.get('temporal_start_year', type=int)
            temporal_end_year = request.form.get('temporal_end_year', type=int)
            meaning_description = request.form.get('meaning_description', '').strip()
            corpus_source = request.form.get('corpus_source', '').strip()
            confidence_level = request.form.get('confidence_level', 'medium')
            context_anchors = request.form.get('context_anchors', '').strip()
            
            # Validation
            if not term_text:
                flash('Term text is required.', 'error')
                return render_template('terms/add.html')
            
            if not meaning_description:
                flash('Meaning description is required for the first version.', 'error')
                return render_template('terms/add.html')
                
            if not temporal_period:
                flash('Temporal period is required for the first version.', 'error')
                return render_template('terms/add.html')
            
            # Check for duplicate
            existing = Term.query.filter_by(term_text=term_text, created_by=current_user.id).first()
            if existing:
                flash(f'You already have a term "{term_text}". Please choose a different term.', 'error')
                return render_template('terms/add.html')
            
            # Create term
            term = Term(
                term_text=term_text,
                description=description,
                etymology=etymology,
                notes=notes,
                research_domain=research_domain,
                selection_rationale=selection_rationale,
                historical_significance=historical_significance,
                created_by=current_user.id,
                status='active'
            )
            
            db.session.add(term)
            db.session.flush()  # Get the term ID
            
            # Parse context anchors
            anchor_list = []
            if context_anchors:
                anchor_list = [anchor.strip() for anchor in context_anchors.split(',') if anchor.strip()]
            
            # Create first version
            version = TermVersion(
                term_id=term.id,
                temporal_period=temporal_period,
                temporal_start_year=temporal_start_year,
                temporal_end_year=temporal_end_year,
                meaning_description=meaning_description,
                corpus_source=corpus_source,
                confidence_level=confidence_level,
                extraction_method='manual',
                context_anchor=anchor_list,  # Store as JSON
                generated_at_time=datetime.utcnow(),
                version_number=1,
                is_current=True,
                created_by=current_user.id
            )
            
            db.session.add(version)
            db.session.flush()  # Get the version ID
            
            # Add context anchors to the relationship table
            for anchor_term in anchor_list:
                anchor = ContextAnchor.get_or_create(anchor_term)
                version.add_context_anchor(anchor_term)
            
            db.session.commit()
            
            flash(f'Term "{term_text}" created successfully with first temporal version.', 'success')
            return redirect(url_for('terms.view_term', term_id=term.id))
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error creating term: {str(e)}")
            flash('An error occurred while creating the term. Please try again.', 'error')
            return render_template('terms/add.html')
    
    return render_template('terms/add.html')


@terms_bp.route('/<uuid:term_id>')
@login_required
def view_term(term_id):
    """View term details and all versions"""
    term = Term.query.get_or_404(term_id)
    
    # Get all versions ordered by temporal period
    versions = term.get_all_versions_ordered()
    
    # Get semantic drift activities
    drift_activities = term.get_semantic_drift_activities()
    
    return render_template('terms/view.html', 
                         term=term, 
                         versions=versions,
                         drift_activities=drift_activities)


@terms_bp.route('/<uuid:term_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_term(term_id):
    """Edit term basic information"""
    term = Term.query.get_or_404(term_id)
    
    # Check permissions
    if term.created_by != current_user.id and not current_user.is_admin:
        flash('You do not have permission to edit this term.', 'error')
        return redirect(url_for('terms.view_term', term_id=term_id))
    
    if request.method == 'POST':
        try:
            # Update term fields
            term.description = request.form.get('description', '').strip()
            term.etymology = request.form.get('etymology', '').strip()
            term.notes = request.form.get('notes', '').strip()
            term.research_domain = request.form.get('research_domain', '').strip()
            term.selection_rationale = request.form.get('selection_rationale', '').strip()
            term.historical_significance = request.form.get('historical_significance', '').strip()
            term.status = request.form.get('status', term.status)
            term.updated_by = current_user.id
            
            db.session.commit()
            
            flash(f'Term "{term.term_text}" updated successfully.', 'success')
            return redirect(url_for('terms.view_term', term_id=term_id))
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error updating term: {str(e)}")
            flash('An error occurred while updating the term.', 'error')
    
    return render_template('terms/edit.html', term=term)


@terms_bp.route('/<uuid:term_id>/add-version', methods=['GET', 'POST'])
@login_required
def add_version(term_id):
    """Add new temporal version to existing term"""
    term = Term.query.get_or_404(term_id)
    
    if request.method == 'POST':
        try:
            # Parse version data
            temporal_period = request.form.get('temporal_period', '').strip()
            temporal_start_year = request.form.get('temporal_start_year', type=int)
            temporal_end_year = request.form.get('temporal_end_year', type=int)
            meaning_description = request.form.get('meaning_description', '').strip()
            corpus_source = request.form.get('corpus_source', '').strip()
            confidence_level = request.form.get('confidence_level', 'medium')
            context_anchors = request.form.get('context_anchors', '').strip()
            was_derived_from = request.form.get('was_derived_from')
            derivation_type = request.form.get('derivation_type', 'revision')
            certainty_notes = request.form.get('certainty_notes', '').strip()
            
            # Validation
            if not temporal_period or not meaning_description:
                flash('Temporal period and meaning description are required.', 'error')
                return render_template('terms/add_version.html', term=term)
            
            # Get next version number
            max_version = db.session.query(func.max(TermVersion.version_number)).filter_by(term_id=term_id).scalar() or 0
            next_version = max_version + 1
            
            # Parse context anchors
            anchor_list = []
            if context_anchors:
                anchor_list = [anchor.strip() for anchor in context_anchors.split(',') if anchor.strip()]
            
            # Create new version
            version = TermVersion(
                term_id=term.id,
                temporal_period=temporal_period,
                temporal_start_year=temporal_start_year,
                temporal_end_year=temporal_end_year,
                meaning_description=meaning_description,
                corpus_source=corpus_source,
                confidence_level=confidence_level,
                certainty_notes=certainty_notes,
                extraction_method='manual',
                context_anchor=anchor_list,
                generated_at_time=datetime.utcnow(),
                version_number=next_version,
                is_current=request.form.get('is_current') == 'on',
                created_by=current_user.id,
                was_derived_from=uuid.UUID(was_derived_from) if was_derived_from else None,
                derivation_type=derivation_type
            )
            
            db.session.add(version)
            db.session.flush()
            
            # If this is set as current, update other versions
            if version.is_current:
                term.versions.filter(TermVersion.id != version.id).update({'is_current': False})
            
            # Add context anchors
            for anchor_term in anchor_list:
                anchor = ContextAnchor.get_or_create(anchor_term)
                version.add_context_anchor(anchor_term)
            
            db.session.commit()
            
            flash(f'New version added for "{term.term_text}" ({temporal_period}).', 'success')
            return redirect(url_for('terms.view_term', term_id=term_id))
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error adding version: {str(e)}")
            flash('An error occurred while adding the version.', 'error')
    
    # Get existing versions for derivation dropdown
    existing_versions = term.get_all_versions_ordered()
    
    return render_template('terms/add_version.html', term=term, existing_versions=existing_versions)


@terms_bp.route('/api/context-anchors')
@login_required
def api_context_anchors():
    """API endpoint for context anchor autocomplete"""
    query = request.args.get('query', '').strip()
    limit = request.args.get('limit', 20, type=int)
    
    anchors = ContextAnchor.search_anchors(query, limit)
    
    return jsonify([{
        'id': str(anchor.id),
        'term': anchor.anchor_term,
        'frequency': anchor.frequency
    } for anchor in anchors])


@terms_bp.route('/api/terms/search')
@login_required 
def api_term_search():
    """API endpoint for term search autocomplete"""
    query = request.args.get('query', '').strip()
    limit = request.args.get('limit', 10, type=int)
    
    terms = Term.search_terms(query).limit(limit).all()
    
    return jsonify([term.to_dict() for term in terms])


@terms_bp.route('/<uuid:term_id>/versions/<uuid:version_id>/adjust-fuzziness', methods=['POST'])
@login_required
def adjust_fuzziness(term_id, version_id):
    """Adjust fuzziness score with audit trail"""
    version = TermVersion.query.get_or_404(version_id)
    
    if version.term_id != term_id:
        flash('Invalid version for this term.', 'error')
        return redirect(url_for('terms.view_term', term_id=term_id))
    
    try:
        new_score = request.form.get('fuzziness_score', type=float)
        reason = request.form.get('adjustment_reason', '').strip()
        
        if new_score is None or not (0 <= new_score <= 1):
            flash('Fuzziness score must be between 0 and 1.', 'error')
            return redirect(url_for('terms.view_term', term_id=term_id))
            
        if not reason:
            flash('Adjustment reason is required.', 'error')
            return redirect(url_for('terms.view_term', term_id=term_id))
        
        # Create adjustment record
        adjustment = FuzzinessAdjustment(
            term_version_id=version.id,
            original_score=version.fuzziness_score or 0.0,
            adjusted_score=new_score,
            adjustment_reason=reason,
            adjusted_by=current_user.id
        )
        
        # Update version
        version.fuzziness_score = new_score
        
        db.session.add(adjustment)
        db.session.commit()
        
        flash(f'Fuzziness score adjusted to {new_score:.3f}.', 'success')
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error adjusting fuzziness: {str(e)}")
        flash('An error occurred while adjusting the fuzziness score.', 'error')
    
    return redirect(url_for('terms.view_term', term_id=term_id))


@terms_bp.route('/<uuid:term_id>/analyze', methods=['POST'])
@login_required
def analyze_term(term_id):
    """Perform comprehensive term analysis using shared services."""
    term = Term.query.get_or_404(term_id)
    analysis_service = get_term_analysis_service()
    
    if not analysis_service:
        flash('Term analysis service is not available.', 'warning')
        return redirect(url_for('terms.view_term', term_id=term_id))
    
    try:
        # Get corpus texts from request (optional)
        corpus_texts = request.json.get('corpus_texts', []) if request.is_json else []
        
        # Perform analysis
        result = analysis_service.analyze_term(term, corpus_texts)
        
        # Update term version with analysis results
        current_version = term.get_current_version()
        if current_version and result.fuzziness_score > 0:
            # Only update if we have a meaningful score
            if current_version.fuzziness_score is None:
                current_version.fuzziness_score = result.fuzziness_score
                current_version.confidence_level = result.confidence_level
        
        # Add discovered context anchors
        if result.context_anchors and current_version:
            existing_anchors = set(current_version.context_anchor or [])
            new_anchors = [anchor for anchor in result.context_anchors if anchor not in existing_anchors]
            
            if new_anchors:
                current_version.context_anchor = list(existing_anchors) + new_anchors[:5]  # Limit additions
                
                # Add to relationship table
                for anchor_term in new_anchors[:5]:
                    current_version.add_context_anchor(anchor_term)
        
        db.session.commit()
        
        if request.is_json:
            return jsonify({
                'success': True,
                'analysis': {
                    'fuzziness_score': result.fuzziness_score,
                    'confidence_level': result.confidence_level,
                    'context_anchors': result.context_anchors,
                    'has_embeddings': result.embeddings is not None,
                    'temporal_contexts_count': len(result.temporal_contexts or [])
                }
            })
        else:
            flash(f'Analysis completed for "{term.term_text}". Fuzziness score: {result.fuzziness_score:.3f}', 'success')
            return redirect(url_for('terms.view_term', term_id=term_id))
            
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error analyzing term {term.term_text}: {str(e)}")
        
        if request.is_json:
            return jsonify({'success': False, 'error': str(e)}), 500
        else:
            flash('An error occurred during analysis. Please try again.', 'error')
            return redirect(url_for('terms.view_term', term_id=term_id))


@terms_bp.route('/<uuid:term_id>/detect-drift', methods=['POST'])
@login_required
def detect_semantic_drift(term_id):
    """Detect semantic drift between term versions."""
    term = Term.query.get_or_404(term_id)
    analysis_service = get_term_analysis_service()
    
    if not analysis_service:
        return jsonify({'success': False, 'error': 'Analysis service not available'}), 503
    
    try:
        # Get version IDs from request
        baseline_version_id = request.json.get('baseline_version_id')
        comparison_version_id = request.json.get('comparison_version_id')
        
        if not baseline_version_id or not comparison_version_id:
            return jsonify({'success': False, 'error': 'Both version IDs required'}), 400
        
        baseline_version = TermVersion.query.get_or_404(baseline_version_id)
        comparison_version = TermVersion.query.get_or_404(comparison_version_id)
        
        # Detect drift
        drift_result = analysis_service.detect_semantic_drift(term, baseline_version, comparison_version)
        
        if not drift_result:
            return jsonify({'success': False, 'error': 'Drift detection failed'}), 500
        
        # Create semantic drift activity
        activity = analysis_service.create_semantic_drift_activity(
            term, baseline_version, comparison_version, drift_result
        )
        
        db.session.add(activity)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'drift': drift_result.to_dict(),
            'activity_id': str(activity.id)
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error detecting drift for term {term.term_text}: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@terms_bp.route('/api/discover-context-anchors')
@login_required
def api_discover_context_anchors():
    """API endpoint for discovering context anchors using embeddings."""
    term_text = request.args.get('term_text', '').strip()
    meaning_description = request.args.get('meaning_description', '').strip()
    limit = request.args.get('limit', 10, type=int)
    
    if not term_text:
        return jsonify({'error': 'Term text is required'}), 400
    
    analysis_service = get_term_analysis_service()
    if not analysis_service or not analysis_service.embedding_service:
        # Fallback to existing context anchors
        existing_anchors = ContextAnchor.query.order_by(ContextAnchor.frequency.desc()).limit(limit).all()
        return jsonify([{
            'term': anchor.anchor_term,
            'frequency': anchor.frequency,
            'similarity': 0.0,  # No similarity calculation available
            'source': 'existing'
        } for anchor in existing_anchors])
    
    try:
        # Create a temporary term-like object for analysis
        combined_text = term_text
        if meaning_description:
            combined_text += f". {meaning_description}"
        
        # Get embedding for the term
        term_embedding = analysis_service.embedding_service.get_embedding(combined_text)
        
        # Compare with existing context anchors
        existing_anchors = ContextAnchor.query.limit(100).all()  # Limit for performance
        similarities = []
        
        for anchor in existing_anchors:
            try:
                anchor_embedding = analysis_service.embedding_service.get_embedding(anchor.anchor_term)
                similarity = analysis_service.embedding_service.similarity(term_embedding, anchor_embedding)
                
                similarities.append({
                    'term': anchor.anchor_term,
                    'frequency': anchor.frequency,
                    'similarity': round(similarity, 3),
                    'source': 'embedding_similarity'
                })
            except Exception as e:
                current_app.logger.debug(f"Failed to compare with anchor {anchor.anchor_term}: {e}")
                continue
        
        # Sort by similarity and return top matches
        similarities.sort(key=lambda x: x['similarity'], reverse=True)
        return jsonify(similarities[:limit])
        
    except Exception as e:
        current_app.logger.error(f"Error discovering context anchors: {str(e)}")
        return jsonify({'error': 'Context anchor discovery failed'}), 500


@terms_bp.route('/api/calculate-fuzziness', methods=['POST'])
@login_required
def api_calculate_fuzziness():
    """API endpoint for calculating fuzziness score."""
    term_id = request.json.get('term_id')
    version_id = request.json.get('version_id')
    
    if not term_id or not version_id:
        return jsonify({'error': 'Term ID and version ID required'}), 400
    
    try:
        term = Term.query.get_or_404(term_id)
        version = TermVersion.query.get_or_404(version_id)
        
        analysis_service = get_term_analysis_service()
        if not analysis_service:
            return jsonify({'error': 'Analysis service not available'}), 503
        
        # Calculate fuzziness score
        fuzziness_score, confidence_level = analysis_service._calculate_fuzziness_score(term, version)
        
        return jsonify({
            'success': True,
            'fuzziness_score': round(fuzziness_score, 3),
            'confidence_level': confidence_level,
            'method': 'shared_services' if analysis_service.semantic_tracker else 'heuristic'
        })
        
    except Exception as e:
        current_app.logger.error(f"Error calculating fuzziness: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@terms_bp.route('/service-status')
@login_required
def service_status():
    """Display status of all shared services."""
    analysis_service = get_term_analysis_service()
    
    if not analysis_service:
        status = {'analysis_service': {'available': False, 'reason': 'Service not initialized'}}
    else:
        status = analysis_service.get_service_status()
        status['analysis_service'] = {'available': True, 'initialized': True}
    
    return render_template('terms/service_status.html', status=status)


@terms_bp.route('/stats')
@login_required
def term_stats():
    """Display term statistics and analytics"""
    # Basic counts
    total_terms = Term.query.count()
    total_versions = TermVersion.query.count()
    user_terms = Term.query.filter_by(created_by=current_user.id).count()
    user_versions = TermVersion.query.filter_by(created_by=current_user.id).count()
    
    # Domain breakdown
    domain_stats = db.session.query(
        Term.research_domain, 
        func.count(Term.id).label('count')
    ).group_by(Term.research_domain).all()
    
    # Most active users
    user_stats = db.session.query(
        Term.created_by,
        func.count(Term.id).label('term_count')
    ).join(Term.creator).group_by(Term.created_by).order_by(desc('term_count')).limit(10).all()
    
    # Recent activity
    recent_terms = Term.query.order_by(Term.created_at.desc()).limit(5).all()
    recent_versions = TermVersion.query.order_by(TermVersion.created_at.desc()).limit(5).all()
    
    return render_template('terms/stats.html',
                         total_terms=total_terms,
                         total_versions=total_versions,
                         user_terms=user_terms,
                         user_versions=user_versions,
                         domain_stats=domain_stats,
                         user_stats=user_stats,
                         recent_terms=recent_terms,
                         recent_versions=recent_versions)