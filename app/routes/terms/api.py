"""
Terms API Routes

This module handles API endpoints for terms.

Routes:
- GET  /terms/api/context-anchors                              - Context anchor autocomplete
- GET  /terms/api/terms/search                                 - Term search autocomplete
- POST /terms/<uuid:term_id>/versions/<uuid:version_id>/adjust-fuzziness - Adjust fuzziness
- GET  /terms/api/discover-context-anchors                     - Discover context anchors
- POST /terms/api/calculate-fuzziness                          - Calculate fuzziness score
"""

from flask import request, redirect, url_for, flash, jsonify, current_app
from flask_login import current_user
from app.utils.auth_decorators import api_require_login_for_write
from app import db
from app.models import Term, TermVersion, ContextAnchor, FuzzinessAdjustment

from . import terms_bp, get_term_analysis_service


@terms_bp.route('/api/context-anchors')
@api_require_login_for_write
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
@api_require_login_for_write
def api_term_search():
    """API endpoint for term search autocomplete"""
    query = request.args.get('query', '').strip()
    limit = request.args.get('limit', 10, type=int)

    terms = Term.search_terms(query).limit(limit).all()

    return jsonify([term.to_dict() for term in terms])


@terms_bp.route('/<uuid:term_id>/versions/<uuid:version_id>/adjust-fuzziness', methods=['POST'])
@api_require_login_for_write
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


@terms_bp.route('/api/discover-context-anchors')
@api_require_login_for_write
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
            'similarity': 0.0,
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
        existing_anchors = ContextAnchor.query.limit(100).all()
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
@api_require_login_for_write
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
        return jsonify({'error': 'Fuzziness calculation failed'}), 500
