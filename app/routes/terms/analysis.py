"""
Terms Analysis Operations Routes

This module handles term analysis operations.

Routes:
- POST /terms/<uuid:term_id>/analyze       - Analyze term
- POST /terms/<uuid:term_id>/detect-drift  - Detect semantic drift
"""

from flask import request, redirect, url_for, flash, jsonify, current_app
from flask_login import current_user
from app.utils.auth_decorators import api_require_login_for_write
from app import db
from app.models import Term, TermVersion

from . import terms_bp, get_term_analysis_service


@terms_bp.route('/<uuid:term_id>/analyze', methods=['POST'])
@api_require_login_for_write
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
                current_version.context_anchor = list(existing_anchors) + new_anchors[:5]

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
@api_require_login_for_write
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
