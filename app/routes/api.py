"""
API routes for OntExtract - handles AJAX requests and API endpoints
"""

from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.models.term import Term
from app.services.oed_enrichment_service import OEDEnrichmentService

api_bp = Blueprint('api', __name__, url_prefix='/api')

@api_bp.route('/terms/enrich-oed', methods=['POST'])
@login_required
def enrich_term_with_oed():
    """
    API endpoint to enrich a term with OED data
    
    Expected JSON payload:
    {
        "term_text": "agent",
        "experiment_id": 31  # optional, for context
    }
    """
    try:
        data = request.get_json()
        
        if not data or not data.get('term_text'):
            return jsonify({
                'success': False,
                'error': 'term_text is required'
            }), 400
        
        term_text = data['term_text']
        experiment_id = data.get('experiment_id')
        
        # Find the term in database
        term = Term.query.filter_by(term_text=term_text).first()
        if not term:
            return jsonify({
                'success': False,
                'error': f'Term "{term_text}" not found in database'
            }), 404
        
        # Initialize OED enrichment service
        enrichment_service = OEDEnrichmentService()
        
        # Perform enrichment
        result = enrichment_service.enrich_term_with_oed_data(str(term.id))
        
        if result.get('success'):
            return jsonify(result)
        else:
            return jsonify(result), 500
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@api_bp.route('/terms/<term_id>/oed-data', methods=['GET'])
@login_required
def get_term_oed_data(term_id):
    """Get OED data for a specific term"""
    try:
        from app.models.oed_models import OEDEtymology, OEDDefinition, OEDHistoricalStats, OEDQuotationSummary
        
        term = Term.query.get(term_id)
        if not term:
            return jsonify({
                'success': False,
                'error': 'Term not found'
            }), 404
        
        # Get OED data
        etymology = OEDEtymology.query.filter_by(term_id=term.id).first()
        definitions = OEDDefinition.query.filter_by(term_id=term.id).order_by(OEDDefinition.first_cited_year.asc()).all()
        historical_stats = OEDHistoricalStats.query.filter_by(term_id=term.id).order_by(OEDHistoricalStats.start_year.asc()).all()
        quotation_summaries = OEDQuotationSummary.query.filter_by(term_id=term.id).order_by(OEDQuotationSummary.quotation_year.asc()).all()
        
        oed_data = {
            'term_text': term.term_text,
            'etymology': etymology.to_dict() if etymology else None,
            'definitions': [d.to_dict() for d in definitions],
            'historical_stats': [s.to_dict() for s in historical_stats],
            'quotation_summaries': [q.to_dict() for q in quotation_summaries],
            'date_range': {
                'earliest': min([d.first_cited_year for d in definitions if d.first_cited_year], default=None),
                'latest': max([d.last_cited_year for d in definitions if d.last_cited_year], default=None)
            }
        }
        
        return jsonify({
            'success': True,
            'data': oed_data
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@api_bp.route('/terms/search-oed', methods=['GET'])
@login_required  
def search_oed_entries():
    """Search for OED entries for a term"""
    try:
        term_text = request.args.get('term')
        if not term_text:
            return jsonify({
                'success': False,
                'error': 'term parameter is required'
            }), 400
        
        from app.services.oed_service import OEDService
        oed_service = OEDService()
        
        # Get suggestions
        result = oed_service.suggest_ids(term_text, limit=10)
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@api_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'OntExtract API'
    })