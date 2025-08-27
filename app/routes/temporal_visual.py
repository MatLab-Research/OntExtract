from flask import Blueprint, render_template, request, jsonify, current_app
from app.models import Experiment, Document
import logging

logger = logging.getLogger(__name__)

# Create blueprint
temporal_visual_bp = Blueprint('temporal_visual', __name__, url_prefix='/temporal-visual')

@temporal_visual_bp.route('/')
def index():
    """Main temporal evolution visual interface."""
    return render_template('experiments/temporal_evolution_visual.html')

@temporal_visual_bp.route('/experiment/<int:experiment_id>')
def experiment_view(experiment_id):
    """View temporal evolution for a specific experiment."""
    try:
        experiment = Experiment.query.get_or_404(experiment_id)
        
        # Verify this is a temporal evolution experiment
        if experiment.experiment_type != 'temporal_evolution':
            return jsonify({
                'error': 'This experiment is not a temporal evolution type',
                'experiment_type': experiment.experiment_type
            }), 400
            
        return render_template('experiments/temporal_evolution_visual.html', 
                             experiment=experiment)
    except Exception as e:
        logger.error(f"Error loading temporal evolution experiment {experiment_id}: {str(e)}")
        return jsonify({'error': 'Failed to load experiment'}), 500

@temporal_visual_bp.route('/api/experiment/<int:experiment_id>/data')
def get_experiment_data(experiment_id):
    """API endpoint to get temporal evolution data for visualization."""
    try:
        experiment = Experiment.query.get_or_404(experiment_id)
        
        # Get experiment documents and references
        documents = []
        references = []
        
        if hasattr(experiment, 'documents'):
            for doc in experiment.documents:
                documents.append({
                    'id': doc.id,
                    'title': doc.title,
                    'type': getattr(doc, 'document_type', 'unknown'),
                    'year': getattr(doc, 'year', None),
                    'metadata': doc.source_metadata or {}
                })
                
        # Note: OntExtract doesn't have a References model, only Documents
        # This section is kept for compatibility but may not be used
        if hasattr(experiment, 'references') and experiment.references:
            for ref in experiment.references:
                references.append({
                    'id': ref.id,
                    'title': ref.title,
                    'type': getattr(ref, 'document_type', 'unknown'), 
                    'year': getattr(ref, 'year', None),
                    'metadata': getattr(ref, 'source_metadata', {}) or {}
                })
        
        # Get temporal evolution specific data
        temporal_data = None
        if hasattr(experiment, 'temporal_evolution'):
            temporal_evolution = experiment.temporal_evolution
            if temporal_evolution:
                temporal_data = {
                    'terms_tracked': temporal_evolution.terms_tracked or [],
                    'time_periods': temporal_evolution.time_periods or [],
                    'analysis_results': temporal_evolution.analysis_results or {}
                }
        
        return jsonify({
            'experiment': {
                'id': experiment.id,
                'name': experiment.name,
                'description': experiment.description,
                'created_at': experiment.created_at.isoformat() if experiment.created_at else None,
                'experiment_type': experiment.experiment_type
            },
            'documents': documents,
            'references': references,
            'temporal_data': temporal_data
        })
        
    except Exception as e:
        logger.error(f"Error getting experiment data for {experiment_id}: {str(e)}")
        return jsonify({'error': 'Failed to get experiment data'}), 500

@temporal_visual_bp.route('/api/analyze', methods=['POST'])
def analyze_temporal_evolution():
    """API endpoint to analyze temporal evolution for a term."""
    try:
        data = request.get_json()
        term = data.get('term', '').strip()
        time_range = data.get('time_range', '2000-2024')
        period_length = data.get('period_length', 5)
        experiment_id = data.get('experiment_id')
        
        if not term:
            return jsonify({'error': 'Term is required'}), 400
            
        # Parse time range
        try:
            start_year, end_year = map(int, time_range.split('-'))
        except ValueError:
            return jsonify({'error': 'Invalid time range format. Use YYYY-YYYY'}), 400
            
        # Generate time periods
        periods = []
        current_year = start_year
        while current_year <= end_year:
            period_end = min(current_year + period_length - 1, end_year)
            periods.append({
                'id': f'period-{current_year}',
                'label': f'{current_year}-{period_end}',
                'start_year': current_year,
                'end_year': period_end
            })
            current_year += period_length
            
        # Get documents for analysis (if experiment_id provided)
        documents_by_period = {}
        total_documents = 0
        
        if experiment_id:
            experiment = Experiment.query.get(experiment_id)
            if experiment:
                # Group documents by period based on their year
                all_docs = []
                if hasattr(experiment, 'documents'):
                    all_docs.extend(experiment.documents)
                if hasattr(experiment, 'references'):
                    all_docs.extend(experiment.references)
                    
                for period in periods:
                    period_docs = []
                    for doc in all_docs:
                        doc_year = getattr(doc, 'year', None)
                        if doc_year and period['start_year'] <= doc_year <= period['end_year']:
                            period_docs.append({
                                'id': doc.id,
                                'title': doc.title,
                                'year': doc_year,
                                'type': getattr(doc, 'document_type', getattr(doc, 'reference_type', 'unknown'))
                            })
                    documents_by_period[period['id']] = period_docs
                    total_documents += len(period_docs)
        
        # Generate mock analysis results for now
        # In a real implementation, this would call the temporal analysis service
        import random
        analysis_results = {
            'semantic_drift': round(random.uniform(0.3, 0.9), 2),
            'context_stability': f"{random.randint(20, 80)}%",
            'documents_analyzed': total_documents or random.randint(15, 30),
            'confidence_score': f"{random.randint(75, 95)}%",
            'key_findings': [
                f"Significant semantic shift detected in {random.choice(['early', 'middle', 'recent'])} periods",
                f"Term usage evolved from {random.choice(['academic', 'technical', 'legal'])} to {random.choice(['commercial', 'popular', 'specialized'])} applications",
                f"Context stability {'increased' if random.random() > 0.5 else 'decreased'} by {random.randint(10, 40)}% over time",
                f"New associations: {', '.join(random.sample(['machine learning', 'artificial intelligence', 'data science', 'neural networks', 'automation'], 3))}"
            ]
        }
        
        return jsonify({
            'success': True,
            'term': term,
            'time_range': time_range,
            'period_length': period_length,
            'periods': periods,
            'documents_by_period': documents_by_period,
            'analysis_results': analysis_results
        })
        
    except Exception as e:
        logger.error(f"Error analyzing temporal evolution: {str(e)}")
        return jsonify({'error': 'Analysis failed', 'details': str(e)}), 500

@temporal_visual_bp.route('/api/documents/<int:document_id>/details')
def get_document_details(document_id):
    """Get detailed information about a specific document."""
    try:
        # Find the document
        document = Document.query.get(document_id)
            
        if not document:
            return jsonify({'error': 'Document not found'}), 404
            
        details = {
            'id': document.id,
            'title': document.title,
            'type': getattr(document, 'document_type', 'unknown'),
            'year': getattr(document, 'year', None),
            'metadata': getattr(document, 'source_metadata', {}) or {},
            'content_preview': getattr(document, 'content', '')[:500] if hasattr(document, 'content') else None,
            'file_path': getattr(document, 'file_path', None),
            'created_at': document.created_at.isoformat() if hasattr(document, 'created_at') and document.created_at else None
        }
        
        return jsonify(details)
        
    except Exception as e:
        logger.error(f"Error getting document details for {document_id}: {str(e)}")
        return jsonify({'error': 'Failed to get document details'}), 500

@temporal_visual_bp.route('/api/experiments/temporal')
def list_temporal_experiments():
    """List all temporal evolution experiments."""
    try:
        experiments = Experiment.query.filter_by(experiment_type='temporal_evolution').all()
        
        experiment_list = []
        for exp in experiments:
            experiment_list.append({
                'id': exp.id,
                'name': exp.name,
                'description': exp.description,
                'created_at': exp.created_at.isoformat() if exp.created_at else None,
                'status': getattr(exp, 'status', 'unknown'),
                'document_count': len(exp.documents) if hasattr(exp, 'documents') and exp.documents else 0,
                'reference_count': len(exp.references) if hasattr(exp, 'references') and exp.references else 0
            })
            
        return jsonify({
            'experiments': experiment_list,
            'total_count': len(experiment_list)
        })
        
    except Exception as e:
        logger.error(f"Error listing temporal experiments: {str(e)}")
        return jsonify({'error': 'Failed to list experiments'}), 500
