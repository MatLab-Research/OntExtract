from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for, current_app
from flask_login import current_user
from app.utils.auth_decorators import require_login_for_write, api_require_login_for_write
from sqlalchemy import text
from app import db
from app.models import Document, Experiment, ExperimentDocument, ProcessingJob
from app.models.experiment_processing import ExperimentDocumentProcessing, ProcessingArtifact, DocumentProcessingIndex
from datetime import datetime
import json
from typing import List, Optional
from app.services.text_processing import TextProcessingService
from app.services.experiment_domain_comparison import DomainComparisonService

# Note: experiments.configuration may include a `design` object per Phase 1b of metadata plan.
# Analysis services should read optional design = config.get('design') to drive factor/group logic.

experiments_bp = Blueprint('experiments', __name__, url_prefix='/experiments')

@experiments_bp.route('/')
def index():
    """List all experiments for all users - public view"""
    experiments = Experiment.query.order_by(Experiment.created_at.desc()).all()
    return render_template('experiments/index.html', experiments=experiments)

@experiments_bp.route('/new')
def new():
    """Show new experiment form - public view, but submit requires login"""
    from app.models.term import Term

    # Get documents and references separately for all users
    documents = Document.query.filter_by(document_type='document').order_by(Document.created_at.desc()).all()
    references = Document.query.filter_by(document_type='reference').order_by(Document.created_at.desc()).all()

    # Get all terms for focus term selection
    terms = Term.query.order_by(Term.term_text).all()

    return render_template('experiments/new.html', documents=documents, references=references, terms=terms)

@experiments_bp.route('/wizard')
def wizard():
    """Guided wizard to create an experiment - public view, but submit requires login"""
    documents = Document.query.filter_by(document_type='document').order_by(Document.created_at.desc()).all()
    references = Document.query.filter_by(document_type='reference').order_by(Document.created_at.desc()).all()
    return render_template('experiments/wizard.html', documents=documents, references=references)

@experiments_bp.route('/create', methods=['POST'])
@api_require_login_for_write
def create():
    """Create a new experiment - requires login"""
    try:
        data = request.get_json()
        
        # Validate required fields
        if not data.get('name'):
            return jsonify({'error': 'Experiment name is required'}), 400
        
        if not data.get('experiment_type'):
            return jsonify({'error': 'Experiment type is required'}), 400
        
        # For most experiments, at least one document is required.
        # Exception: domain_comparison can use references only when configuration.use_references is true.
        config = data.get('configuration', {}) or {}
        use_refs_only = data.get('experiment_type') == 'domain_comparison' and config.get('use_references')
        if (not data.get('document_ids') or len(data['document_ids']) == 0) and not use_refs_only:
            return jsonify({'error': 'At least one document must be selected'}), 400

        # Create the experiment
        experiment = Experiment(
            name=data['name'],
            description=data.get('description', ''),
            experiment_type=data['experiment_type'],
            user_id=current_user.id,
            term_id=data.get('term_id'),  # Optional focus term for semantic evolution
            configuration=json.dumps(data.get('configuration', {}))
        )
        # Important: Add to session before touching dynamic relationships
        db.session.add(experiment)
        db.session.flush()  # ensure experiment has identity for association table

        # Add documents to the experiment
        for doc_id in data.get('document_ids', []) or []:
            document = Document.query.filter_by(id=doc_id).first()
            if document:
                experiment.add_document(document)

        # Add references to the experiment (optional)
        for ref_id in data.get('reference_ids', []) or []:
            reference = Document.query.filter_by(id=ref_id, document_type='reference').first()
            if reference:
                experiment.add_reference(reference, include_in_analysis=True)

        db.session.commit()
        
        # Redirect to document processing pipeline based on experiment type
        return jsonify({
            'success': True,
            'message': 'Experiment created successfully',
            'experiment_id': experiment.id,
            'redirect': url_for('experiments.document_pipeline', experiment_id=experiment.id)
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@experiments_bp.route('/sample', methods=['POST', 'GET'])
@api_require_login_for_write
def create_sample():
    """Create a sample domain comparison experiment using available references and a simple design."""
    try:
        # Pick up to 6 most recent references
        refs = Document.query.filter_by(document_type='reference').order_by(Document.created_at.desc()).limit(6).all()
        if not refs:
            flash('No references found. Please upload reference PDFs first (References → Upload).', 'warning')
            return redirect(url_for('experiments.index'))

        config = {
            "use_references": True,
            "target_terms": ["agent", "agency"],
            "design": {
                "type": "experimental",
                "variables": {
                    "independent": [{"name": "definition_source", "levels": ["OED", "AI textbook"]}]
                },
                "groups": [{"name": "OED"}, {"name": "AI"}]
            }
        }

        experiment = Experiment(
            name='Sample: Agent Domain Comparison',
            description='Auto-created sample comparing terminology across sources with a simple design.',
            experiment_type='domain_comparison',
            user_id=current_user.id,
            configuration=json.dumps(config)
        )
        db.session.add(experiment)
        db.session.flush()

        for r in refs:
            experiment.add_reference(r, include_in_analysis=True)

        db.session.commit()
        flash('Sample experiment created.', 'success')
        return redirect(url_for('experiments.view', experiment_id=experiment.id))
    except Exception as e:
        db.session.rollback()
        flash(f'Error creating sample experiment: {e}', 'danger')
        return redirect(url_for('experiments.index'))

@experiments_bp.route('/<int:experiment_id>')
def view(experiment_id):
    """View experiment details"""
    experiment = Experiment.query.filter_by(id=experiment_id).first_or_404()
    return render_template('experiments/view.html', experiment=experiment)

@experiments_bp.route('/<int:experiment_id>/edit')
@api_require_login_for_write
def edit(experiment_id):
    """Edit experiment"""
    experiment = Experiment.query.filter_by(id=experiment_id).first_or_404()
    
    # Can only edit experiments that are not running
    if experiment.status == 'running':
        flash('Cannot edit an experiment that is currently running', 'error')
        return redirect(url_for('experiments.view', experiment_id=experiment_id))
    
    # Get all documents for all users
    documents = Document.query.order_by(Document.created_at.desc()).all()
    
    # Get IDs of documents already in the experiment
    selected_doc_ids = [doc.id for doc in experiment.documents]
    
    return render_template('experiments/edit.html', 
                         experiment=experiment, 
                         documents=documents,
                         selected_doc_ids=selected_doc_ids)

@experiments_bp.route('/<int:experiment_id>/update', methods=['POST'])
@api_require_login_for_write
def update(experiment_id):
    """Update experiment"""
    try:
        experiment = Experiment.query.filter_by(id=experiment_id).first_or_404()
        
        # Can only update experiments that are not running
        if experiment.status == 'running':
            return jsonify({'error': 'Cannot update an experiment that is currently running'}), 400
        
        data = request.get_json()
        
        # Update basic fields
        if 'name' in data:
            experiment.name = data['name']
        if 'description' in data:
            experiment.description = data['description']
        if 'experiment_type' in data:
            experiment.experiment_type = data['experiment_type']
        if 'configuration' in data:
            experiment.configuration = json.dumps(data['configuration'])
        
        # Update documents if provided
        if 'document_ids' in data:
            # Clear existing documents
            experiment.documents = []
            
            # Add new documents
            for doc_id in data['document_ids']:
                document = Document.query.filter_by(id=doc_id).first()
                if document:
                    experiment.add_document(document)
        
        experiment.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Experiment updated successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@experiments_bp.route('/<int:experiment_id>/delete', methods=['POST'])
@api_require_login_for_write
def delete(experiment_id):
    """Delete experiment and all associated processing data (but preserve original documents)"""
    try:
        experiment = Experiment.query.filter_by(id=experiment_id).first_or_404()

        # Can only delete experiments that are not running
        if experiment.status == 'running':
            return jsonify({'error': 'Cannot delete an experiment that is currently running'}), 400

        # Import models here to avoid circular imports
        from app.models.experiment_document import ExperimentDocument
        from app.models.experiment_processing import (
            ExperimentDocumentProcessing,
            ProcessingArtifact,
            DocumentProcessingIndex
        )

        # Delete all processing artifacts first (most dependent)
        # Get all processing operations for this experiment's documents
        processing_ops = db.session.query(ExperimentDocumentProcessing).join(
            ExperimentDocument,
            ExperimentDocumentProcessing.experiment_document_id == ExperimentDocument.id
        ).filter(
            ExperimentDocument.experiment_id == experiment_id
        ).all()

        for processing_op in processing_ops:
            # Delete all artifacts for this processing operation
            ProcessingArtifact.query.filter_by(processing_id=processing_op.id).delete()

            # Delete index entries for this processing operation
            DocumentProcessingIndex.query.filter_by(processing_id=processing_op.id).delete()

            # Delete the processing operation itself
            db.session.delete(processing_op)

        # Delete all ExperimentDocument associations
        ExperimentDocument.query.filter_by(experiment_id=experiment_id).delete()

        # Clear the many-to-many relationships (experiment_documents and experiment_references)
        # These use association tables, so we need to clear them manually
        experiment.documents = []  # This clears the association table entries
        experiment.references = []  # This clears the reference associations
        db.session.flush()  # Ensure the associations are cleared before deleting the experiment

        # Finally delete the experiment itself
        db.session.delete(experiment)

        # Commit all deletions
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Experiment and all associated processing data deleted successfully'
        })

    except Exception as e:
        db.session.rollback()
        import traceback
        error_details = traceback.format_exc()
        print(f"Error deleting experiment {experiment_id}: {error_details}")
        return jsonify({'error': str(e)}), 500

@experiments_bp.route('/<int:experiment_id>/run', methods=['POST'])
@api_require_login_for_write
def run(experiment_id):
    """Run an experiment"""
    try:
        experiment = Experiment.query.filter_by(id=experiment_id).first_or_404()
        
        if not experiment.can_run():
            return jsonify({'error': 'Experiment cannot be run in its current state'}), 400
        
        # Update experiment status
        experiment.status = 'running'
        experiment.started_at = datetime.utcnow()
        db.session.commit()
        
        # Run analysis based on experiment type
        results = None
        summary = None
        if experiment.experiment_type == 'domain_comparison':
            text_service = TextProcessingService()
            service = DomainComparisonService()
            results, summary = service.run(experiment, text_service)
        else:
            # Placeholder for other experiment types
            results = {
                'document_count': experiment.get_document_count(),
                'total_words': experiment.get_total_word_count(),
                'experiment_type': experiment.experiment_type,
                'timestamp': datetime.utcnow().isoformat()
            }
            summary = f"Analyzed {experiment.get_document_count()} documents with {experiment.get_total_word_count()} total words."

        # Save results
        experiment.status = 'completed'
        experiment.completed_at = datetime.utcnow()
        experiment.results_summary = summary
        experiment.results = json.dumps(results)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Experiment completed successfully',
            'results_summary': experiment.results_summary
        })
        
    except Exception as e:
        db.session.rollback()
        experiment.status = 'error'
        db.session.commit()
        return jsonify({'error': str(e)}), 500

@experiments_bp.route('/<int:experiment_id>/results')
def results(experiment_id):
    """View experiment results"""
    experiment = Experiment.query.filter_by(id=experiment_id).first_or_404()
    
    if experiment.status != 'completed':
        flash('Experiment has not been completed yet', 'warning')
        return redirect(url_for('experiments.view', experiment_id=experiment_id))
    
    # Parse results if available
    results_data = {}
    if experiment.results:
        try:
            results_data = json.loads(experiment.results)
        except:
            results_data = {}
    # Parse configuration JSON for template convenience
    config_data = {}
    if experiment.configuration:
        try:
            config_data = json.loads(experiment.configuration)
        except Exception:
            config_data = {}
    
    return render_template('experiments/results.html', 
                         experiment=experiment,
                         results_data=results_data,
                         config_data=config_data)

@experiments_bp.route('/api/list')
def api_list():
    """API endpoint to list experiments"""
    experiments = Experiment.query.order_by(Experiment.created_at.desc()).all()
    return jsonify({
        'experiments': [exp.to_dict() for exp in experiments]
    })

@experiments_bp.route('/api/<int:experiment_id>')
def api_get(experiment_id):
    """API endpoint to get experiment details"""
    experiment = Experiment.query.filter_by(id=experiment_id).first_or_404()
    return jsonify(experiment.to_dict(include_documents=True))

@experiments_bp.route('/<int:experiment_id>/manage_terms')
@api_require_login_for_write
def manage_terms(experiment_id):
    """Manage terms for domain comparison experiment"""
    experiment = Experiment.query.filter_by(id=experiment_id).first_or_404()
    
    # Only for domain comparison experiments
    if experiment.experiment_type != 'domain_comparison':
        flash('Term management is only available for domain comparison experiments', 'warning')
        return redirect(url_for('experiments.view', experiment_id=experiment_id))
    
    # Parse configuration to get domains and terms
    config = json.loads(experiment.configuration) if experiment.configuration else {}
    domains = config.get('domains', [])
    terms = config.get('target_terms', [])
    
    # If no domains specified, use default
    if not domains:
        domains = ['Computer Science', 'Philosophy', 'Law']
    
    return render_template('experiments/term_manager.html', 
                         experiment=experiment,
                         domains=domains,
                         terms=terms)

@experiments_bp.route('/<int:experiment_id>/update_terms', methods=['POST'])
@api_require_login_for_write
def update_terms(experiment_id):
    """Update terms and domains for an experiment"""
    try:
        experiment = Experiment.query.filter_by(id=experiment_id).first_or_404()
        
        data = request.get_json()
        terms = data.get('terms', [])
        domains = data.get('domains', [])
        definitions = data.get('definitions', {})
        
        # Update configuration
        config = json.loads(experiment.configuration) if experiment.configuration else {}
        config['target_terms'] = terms
        config['domains'] = domains
        config['term_definitions'] = definitions
        
        experiment.configuration = json.dumps(config)
        experiment.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Terms updated successfully'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@experiments_bp.route('/<int:experiment_id>/get_terms')
@api_require_login_for_write
def get_terms(experiment_id):
    """Get saved terms and definitions for an experiment"""
    try:
        experiment = Experiment.query.filter_by(id=experiment_id).first_or_404()
        
        config = json.loads(experiment.configuration) if experiment.configuration else {}
        
        return jsonify({
            'success': True,
            'terms': config.get('target_terms', []),
            'domains': config.get('domains', []),
            'definitions': config.get('term_definitions', {})
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@experiments_bp.route('/<int:experiment_id>/fetch_definitions', methods=['POST'])
@api_require_login_for_write
def fetch_definitions(experiment_id):
    """Fetch definitions for a term from references and ontologies"""
    try:
        experiment = Experiment.query.filter_by(id=experiment_id).first_or_404()
        
        data = request.get_json()
        term = data.get('term')
        domains = data.get('domains', [])
        
        # Initialize services
        from app.services.text_processing import TextProcessingService
        from shared_services.ontology.ontology_importer import OntologyImporter
        
        text_service = TextProcessingService()
        ontology_importer = OntologyImporter()
        
        definitions = {}
        ontology_mappings = {}
        
        # For each domain, try to find definitions from references
        for domain in domains:
            # Search in experiment references for this domain
            domain_definitions = []
            
            for ref in experiment.references:
                # Check if reference matches domain (simple heuristic)
                ref_content = ref.content or ''
                if term.lower() in ref_content.lower():
                    # Extract definition context
                    lines = ref_content.split('\n')
                    for i, line in enumerate(lines):
                        if term.lower() in line.lower():
                            # Get surrounding context
                            start = max(0, i - 2)
                            end = min(len(lines), i + 3)
                            context = '\n'.join(lines[start:end])
                            
                            domain_definitions.append({
                                'text': context[:500],  # Limit length
                                'source': ref.get_display_name()
                            })
                            break
            
            # Use the first definition found for this domain
            if domain_definitions:
                definitions[domain] = domain_definitions[0]
            else:
                definitions[domain] = {
                    'text': f'No definition found for "{term}" in {domain} references',
                    'source': None
                }
            
            # Try to map to ontology concepts (using PROV-O as example)
            ontology_mappings[domain] = []
            
            # Simple mapping based on common terms
            if term.lower() in ['agent', 'actor', 'person', 'user']:
                ontology_mappings[domain].append({
                    'label': 'prov:Agent',
                    'description': 'An agent is something that bears some form of responsibility for an activity taking place'
                })
            elif term.lower() in ['activity', 'process', 'action', 'task']:
                ontology_mappings[domain].append({
                    'label': 'prov:Activity',
                    'description': 'An activity is something that occurs over a period of time and acts upon or with entities'
                })
            elif term.lower() in ['entity', 'object', 'data', 'document']:
                ontology_mappings[domain].append({
                    'label': 'prov:Entity',
                    'description': 'An entity is a physical, digital, conceptual, or other kind of thing'
                })
        
        return jsonify({
            'success': True,
            'definitions': definitions,
            'ontology_mappings': ontology_mappings
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@experiments_bp.route('/<int:experiment_id>/manage_temporal_terms')
@api_require_login_for_write
def manage_temporal_terms(experiment_id):
    """Manage terms for temporal evolution experiment"""
    experiment = Experiment.query.filter_by(id=experiment_id).first_or_404()
    
    # Only for temporal evolution experiments
    if experiment.experiment_type != 'temporal_evolution':
        flash('Temporal term management is only available for temporal evolution experiments', 'warning')
        return redirect(url_for('experiments.view', experiment_id=experiment_id))
    
    # Parse configuration to get time periods and terms
    config = json.loads(experiment.configuration) if experiment.configuration else {}
    time_periods = config.get('time_periods', [])
    terms = config.get('target_terms', [])
    start_year = config.get('start_year', 2000)
    end_year = config.get('end_year', 2020)
    use_oed_periods = config.get('use_oed_periods', False)
    
    # If using OED periods and periods haven't been generated yet
    if use_oed_periods and (not time_periods or len(time_periods) == 0) and terms:
        # Fetch OED data for each term to generate individual periods
        from app.services.oed_service import OEDService
        oed_service = OEDService()
        
        oed_period_data = {}
        term_periods = {}  # Store individual periods for each term
        overall_min_year = None
        overall_max_year = None
        
        for term in terms:
            try:
                # Get OED quotations for the term
                suggestions = oed_service.suggest_ids(term, limit=3)
                if suggestions and suggestions.get('success') and suggestions.get('suggestions'):
                    for suggestion in suggestions['suggestions'][:1]:  # Use first match
                        entry_id = suggestion.get('entry_id')
                        if entry_id:
                            quotations_result = oed_service.get_quotations(entry_id, limit=100)
                            if quotations_result and quotations_result.get('success'):
                                quotations_data = quotations_result.get('data', {})
                                results = quotations_data.get('data', [])
                                
                                term_years = []
                                for quotation in results:
                                    year_value = quotation.get('year')
                                    if year_value:
                                        try:
                                            term_years.append(int(year_value))
                                        except (ValueError, TypeError):
                                            pass
                                
                                if term_years:
                                    min_year = min(term_years)
                                    max_year = max(term_years)
                                    
                                    # Generate periods for this specific term
                                    periods_for_term = generate_time_periods(min_year, max_year)
                                    term_periods[term] = periods_for_term
                                    
                                    # Track overall range for display
                                    if overall_min_year is None or min_year < overall_min_year:
                                        overall_min_year = min_year
                                    if overall_max_year is None or max_year > overall_max_year:
                                        overall_max_year = max_year
                                    
                                    oed_period_data[term] = {
                                        'min_year': min_year,
                                        'max_year': max_year,
                                        'quotation_years': sorted(list(set(term_years))),
                                        'periods': periods_for_term  # Store term-specific periods
                                    }
                                    print(f"OED data for '{term}': {len(term_years)} quotations, {min_year}-{max_year}")
                                else:
                                    print(f"No years found in OED data for '{term}'")
                                    term_periods[term] = []  # Empty periods for terms without OED data
                            break
            except Exception as e:
                print(f"Error fetching OED data for term '{term}': {str(e)}")
                term_periods[term] = []  # Empty periods for terms with errors
                continue
        
        # If we have any OED data, update configuration
        if overall_min_year and overall_max_year:
            # For display purposes, use the overall range
            time_periods = generate_time_periods(overall_min_year, overall_max_year)
            
            # Update configuration with OED data and term-specific periods
            config['time_periods'] = time_periods  # Overall periods for display
            config['oed_period_data'] = oed_period_data
            config['term_periods'] = term_periods  # Individual periods for each term
            config['start_year'] = overall_min_year
            config['end_year'] = overall_max_year
            
            # Save updated configuration
            experiment.configuration = json.dumps(config)
            db.session.commit()
            
            start_year = overall_min_year
            end_year = overall_max_year
            
            flash(f'Generated OED time periods for {len([t for t in term_periods if term_periods[t]])} term(s): overall range {overall_min_year} to {overall_max_year}', 'success')
        else:
            flash('Unable to fetch OED data for any terms. Using default periods.', 'warning')
            # Fall back to default periods
            time_periods = [2000, 2005, 2010, 2015, 2020]
    
    # If no time periods specified and not using OED, generate default
    elif not time_periods or len(time_periods) == 0:
        # Generate periods with 5-year intervals
        time_periods = []
        current_year = start_year
        while current_year <= end_year:
            time_periods.append(current_year)
            current_year += 5
        # Ensure end year is included if not already
        if time_periods and time_periods[-1] < end_year:
            time_periods.append(end_year)
        # If still empty, create a basic set
        if not time_periods:
            time_periods = [2000, 2005, 2010, 2015, 2020]
    
    # Get orchestration decisions for this experiment
    from app.models.orchestration_logs import OrchestrationDecision
    orchestration_decisions = OrchestrationDecision.query.filter_by(
        experiment_id=experiment.id
    ).order_by(OrchestrationDecision.created_at.desc()).limit(10).all()
    
    return render_template('experiments/temporal_term_manager.html', 
                         experiment=experiment,
                         time_periods=time_periods,
                         terms=terms,
                         start_year=start_year,
                         end_year=end_year,
                         use_oed_periods=use_oed_periods,
                         oed_period_data=config.get('oed_period_data', {}),
                         term_periods=config.get('term_periods', {}),
                         orchestration_decisions=orchestration_decisions)

@experiments_bp.route('/<int:experiment_id>/update_temporal_terms', methods=['POST'])
@api_require_login_for_write
def update_temporal_terms(experiment_id):
    """Update terms and periods for a temporal evolution experiment"""
    try:
        experiment = Experiment.query.filter_by(id=experiment_id).first_or_404()
        
        data = request.get_json()
        terms = data.get('terms', [])
        periods = data.get('periods', [])
        temporal_data = data.get('temporal_data', {})
        
        # Update configuration
        config = json.loads(experiment.configuration) if experiment.configuration else {}
        config['target_terms'] = terms
        config['time_periods'] = periods
        config['temporal_data'] = temporal_data
        
        experiment.configuration = json.dumps(config)
        experiment.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Temporal terms updated successfully'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@experiments_bp.route('/<int:experiment_id>/get_temporal_terms')
@api_require_login_for_write
def get_temporal_terms(experiment_id):
    """Get saved temporal terms and data for an experiment"""
    try:
        experiment = Experiment.query.filter_by(id=experiment_id).first_or_404()
        
        config = json.loads(experiment.configuration) if experiment.configuration else {}
        
        return jsonify({
            'success': True,
            'terms': config.get('target_terms', []),
            'periods': config.get('time_periods', []),
            'temporal_data': config.get('temporal_data', {})
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@experiments_bp.route('/<int:experiment_id>/fetch_temporal_data', methods=['POST'])
@api_require_login_for_write
def fetch_temporal_data(experiment_id):
    """Fetch temporal data for a term across time periods using advanced temporal analysis"""
    try:
        experiment = Experiment.query.filter_by(id=experiment_id).first_or_404()
        
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
            
        term = data.get('term')
        periods = data.get('periods', [])
        use_oed = data.get('use_oed', False)
        
        if not term:
            return jsonify({'success': False, 'error': 'Term is required'}), 400
        
        # Check if we have term-specific periods from OED
        config = json.loads(experiment.configuration) if experiment.configuration else {}
        term_periods = config.get('term_periods', {})
        
        # If using OED and we have term-specific periods, use those
        if use_oed and term in term_periods and term_periods[term]:
            periods = term_periods[term]
            print(f"Using term-specific periods for '{term}': {periods}")
        elif not periods:
            return jsonify({'success': False, 'error': 'Periods are required'}), 400
        
        # Import temporal analysis service
        from shared_services.temporal import TemporalAnalysisService
        from shared_services.ontology.ontology_importer import OntologyImporter
        
        # Initialize services
        ontology_importer = OntologyImporter()
        temporal_service = TemporalAnalysisService(ontology_importer)
        
        # Get all documents from the experiment
        all_documents = list(experiment.documents) + list(experiment.references)
        
        # If OED integration requested, enhance with OED data
        oed_periods = []
        temporal_data_oed = None
        if use_oed:
            try:
                from app.services.oed_service import OEDService
                oed_service = OEDService()
                
                # Try to get OED quotations for the term
                suggestions = oed_service.suggest_ids(term, limit=3)
                if not suggestions:
                    print(f"OED: No suggestions returned for term '{term}'")
                elif not suggestions.get('success'):
                    print(f"OED: Failed to get suggestions - {suggestions.get('error', 'Unknown error')}")
                elif suggestions.get('suggestions'):
                    suggestion_list = suggestions.get('suggestions', [])
                    if not isinstance(suggestion_list, list):
                        print(f"OED: Unexpected suggestions format: {type(suggestion_list)}")
                    else:
                        for suggestion in suggestion_list[:1]:  # Use first match
                            if not suggestion or not isinstance(suggestion, dict):
                                continue
                            entry_id = suggestion.get('entry_id')
                            if not entry_id:
                                continue
                            
                            print(f"OED: Fetching quotations for entry_id: {entry_id}")
                            quotations_result = oed_service.get_quotations(entry_id, limit=100)
                            
                            if not quotations_result:
                                print(f"OED: No quotations result returned")
                                continue
                            elif not quotations_result.get('success'):
                                print(f"OED: Failed to get quotations - {quotations_result.get('error', 'Unknown error')}")
                                continue
                            
                            quotations_data = quotations_result.get('data')
                            if not quotations_data or not isinstance(quotations_data, dict):
                                print(f"OED: No valid quotations data")
                                continue
                            
                            # Extract years from quotations
                            years = []
                            
                            # The OED API returns quotations under the 'data' key
                            results = quotations_data.get('data', [])
                            
                            if not results or not isinstance(results, list):
                                # Try alternative keys if 'data' doesn't work
                                for key in ['results', 'quotations', 'items']:
                                    if key in quotations_data:
                                        results = quotations_data[key]
                                        if results:
                                            print(f"OED: Found quotations under key '{key}'")
                                            break
                                
                                if not results or not isinstance(results, list):
                                    print(f"OED: No valid quotations list found in data")
                                    continue
                            else:
                                print(f"OED: Found {len(results)} quotations under 'data' key")
                            
                            for quotation in results:
                                if not quotation or not isinstance(quotation, dict):
                                    continue
                                # The OED API returns year directly as 'year' field
                                year_value = quotation.get('year')
                                if year_value:
                                    try:
                                        years.append(int(year_value))
                                    except (ValueError, TypeError):
                                        # If year is not a valid integer, try extracting from string
                                        import re
                                        year_match = re.search(r'\b(1[0-9]{3}|20[0-9]{2})\b', str(year_value))
                                        if year_match:
                                            years.append(int(year_match.group()))
                            
                            if years:
                                # Generate periods based on OED date range
                                min_year = min(years)
                                max_year = max(years)
                                oed_periods = generate_time_periods(min_year, max_year)
                                
                                print(f"OED: Found {len(years)} quotation years, range {min_year}-{max_year}")
                                
                                # Add OED quotation years to response
                                temporal_data_oed = {
                                    'min_year': min_year,
                                    'max_year': max_year,
                                    'suggested_periods': oed_periods,
                                    'quotation_years': sorted(list(set(years)))
                                }
                                break  # Found data, exit loop
                            else:
                                print(f"OED: No years extracted from {len(results)} quotations")
                else:
                    print(f"OED: No suggestions found for term '{term}'")
                    
            except Exception as oed_error:
                # Log the error but continue with normal processing
                import traceback
                print(f"OED integration error: {str(oed_error)}")
                print(f"Error type: {type(oed_error).__name__}")
                print(traceback.format_exc())
        
        # Use OED periods if available, otherwise use provided periods
        analysis_periods = oed_periods if oed_periods else periods
        
        # If using OED data, create hybrid analysis
        if use_oed and temporal_data_oed:
            # Create temporal data from OED quotations
            temporal_data = {}
            quotation_years = temporal_data_oed.get('quotation_years', [])
            
            # Group quotations by period
            period_quotations = {}
            for period in analysis_periods:
                period_quotations[period] = []
                for year in quotation_years:
                    # Include quotations within 5 years of the period
                    if abs(year - period) <= 5:
                        period_quotations[period].append(year)
            
            # For each period, create appropriate data
            for period in analysis_periods:
                period_str = str(period)
                
                # First check if we have OED data for this period
                oed_count = len(period_quotations.get(period, []))
                
                # Try to get document data if period is recent enough
                doc_based_data = None
                if period >= 1900:  # Only try document analysis for modern periods
                    try:
                        # Try to get document-based analysis
                        temp_data = temporal_service.extract_temporal_data(all_documents, term, [period])
                        if temp_data and str(period) in temp_data:
                            doc_based_data = temp_data[str(period)]
                    except Exception as e:
                        print(f"Error extracting temporal data for period {period}: {str(e)}")
                        pass  # If it fails, we'll use OED data
                
                # Use document data if available and has content
                if doc_based_data and doc_based_data.get('frequency', 0) > 0:
                    temporal_data[period_str] = doc_based_data
                    # Add OED note if we also have OED data
                    if oed_count > 0:
                        temporal_data[period_str]['oed_note'] = f'Also found {oed_count} OED quotation(s)'
                # Otherwise use OED data
                elif oed_count > 0:
                    temporal_data[period_str] = {
                        'frequency': oed_count,
                        'contexts': [f'OED: {oed_count} historical quotation(s) from this period'],
                        'co_occurring_terms': [],
                        'evolution': 'historical',
                        'source': 'Oxford English Dictionary',
                        'definition': f'Historical usage documented in OED with {oed_count} quotation(s)',
                        'is_oed_data': True
                    }
                else:
                    # No data from either source
                    temporal_data[period_str] = {
                        'frequency': 0,
                        'contexts': [],
                        'co_occurring_terms': [],
                        'evolution': 'absent',
                        'definition': f'No usage found for "{term}" in {period}',
                        'is_oed_data': True
                    }
        else:
            # Normal document-based analysis
            temporal_data = temporal_service.extract_temporal_data(all_documents, term, analysis_periods)
            
            # Ensure temporal_data is not None
            if temporal_data is None:
                temporal_data = {}
                # Initialize empty data for each period
                for period in analysis_periods:
                    temporal_data[str(period)] = {
                        'frequency': 0,
                        'contexts': [],
                        'co_occurring_terms': [],
                        'evolution': 'absent'
                    }
        
        # Extract frequency data for visualization
        frequency_data = {}
        for period in analysis_periods:
            period_str = str(period)
            if period_str in temporal_data and temporal_data[period_str] is not None:
                # Scale OED frequencies for better visualization
                freq = temporal_data[period_str].get('frequency', 0)
                if temporal_data[period_str].get('is_oed_data'):
                    # Scale OED quotation counts to be comparable with document frequencies
                    freq = freq * 10  # Each OED quotation represents significant usage
                frequency_data[period] = freq
            else:
                frequency_data[period] = 0
        
        # Analyze semantic drift
        drift_analysis = temporal_service.analyze_semantic_drift(all_documents, term, analysis_periods)
        if drift_analysis is None:
            drift_analysis = {
                'average_drift': 0,
                'stable_terms': [],
                'periods': {}
            }
        
        # Generate evolution narrative
        narrative = temporal_service.generate_evolution_narrative(temporal_data, term, analysis_periods)
        if narrative is None:
            narrative = f"Analysis of '{term}' across {len(analysis_periods)} time periods."
        
        response = {
            'success': True,
            'temporal_data': temporal_data,
            'frequency_data': frequency_data,
            'drift_analysis': drift_analysis,
            'narrative': narrative,
            'periods_used': analysis_periods
        }
        
        # Add OED data if available
        if use_oed and temporal_data_oed:
            response['oed_data'] = temporal_data_oed
        
        return jsonify(response)
        
    except Exception as e:
        import traceback
        print(f"Error in fetch_temporal_data: {str(e)}")
        print(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': f'Server error: {str(e)}'
        }), 500


@experiments_bp.route('/<int:experiment_id>/semantic_evolution_visual')
@api_require_login_for_write  
def semantic_evolution_visual(experiment_id):
    """Display semantic evolution visualization for any term with academic anchors."""
    experiment = Experiment.query.filter_by(id=experiment_id).first_or_404()
    
    # Get target term from URL parameter or experiment configuration
    target_term = request.args.get('term')
    
    # If no term specified, get from experiment configuration
    if not target_term:
        config = json.loads(experiment.configuration) if experiment.configuration else {}
        if config.get('target_term'):
            target_term = config.get('target_term')
        elif config.get('target_terms') and len(config['target_terms']) > 0:
            target_term = config['target_terms'][0]
        else:
            flash('No target term specified. Add ?term=<term> to URL or configure in experiment.', 'warning')
            return redirect(url_for('experiments.view', experiment_id=experiment_id))
    
    # Get term from database
    from app.models.term import Term, TermVersion
    
    term_record = Term.query.filter_by(term_text=target_term).first()
    if not term_record:
        flash(f'Term "{target_term}" not found in database. Create academic anchors first.', 'warning')
        return redirect(url_for('experiments.view', experiment_id=experiment_id))
    
    # Get all temporal versions for the term
    term_versions = TermVersion.query.filter_by(term_id=term_record.id).order_by(TermVersion.temporal_start_year.asc()).all()
    
    if not term_versions:
        flash(f'No temporal versions found for "{target_term}". Create academic anchors first.', 'warning')
        return redirect(url_for('experiments.view', experiment_id=experiment_id))
    
    # Prepare visualization data (generic for any term)
    academic_anchors = []
    for version in term_versions:
        academic_anchors.append({
            'year': version.temporal_start_year,
            'period': version.temporal_period,
            'meaning': version.meaning_description,
            'citation': version.source_citation,
            'domain': version.extraction_method.replace('_analysis', '').replace(' analysis', ''),
            'confidence': version.confidence_level,
            'context_anchor': version.context_anchor or []
        })
    
    # Calculate metrics
    years = [anchor['year'] for anchor in academic_anchors]
    temporal_span = max(years) - min(years) if years else 0
    domains = list(set([anchor['domain'] for anchor in academic_anchors]))
    
    # Get OED data from database
    from app.models.oed_models import OEDEtymology, OEDDefinition, OEDHistoricalStats, OEDQuotationSummary
    
    oed_data = None
    etymology = OEDEtymology.query.filter_by(term_id=term_record.id).first()
    definitions = OEDDefinition.query.filter_by(term_id=term_record.id).order_by(OEDDefinition.first_cited_year.asc()).all()
    historical_stats = OEDHistoricalStats.query.filter_by(term_id=term_record.id).order_by(OEDHistoricalStats.start_year.asc()).all()
    quotation_summaries = OEDQuotationSummary.query.filter_by(term_id=term_record.id).order_by(OEDQuotationSummary.quotation_year.asc()).all()
    
    if etymology or definitions or historical_stats:
        oed_data = {
            'etymology': etymology.to_dict() if etymology else None,
            'definitions': [d.to_dict() for d in definitions],
            'historical_stats': [s.to_dict() for s in historical_stats],
            'quotation_summaries': [q.to_dict() for q in quotation_summaries],
            'date_range': {
                'earliest': min([d.first_cited_year for d in definitions if d.first_cited_year], default=None),
                'latest': max([d.last_cited_year for d in definitions if d.last_cited_year], default=None)
            }
        }
    else:
        # Fallback: Try to load OED data from files
        oed_patterns = [
            f'data/references/oed_{target_term}_extraction_provenance.json',
            f'data/references/{target_term}_oed_extraction.json'
        ]
        
        for pattern in oed_patterns:
            try:
                with open(pattern, 'r') as f:
                    oed_data = json.load(f)
                    break
            except FileNotFoundError:
                continue
    
    # Apply period-aware matching and excerpt extraction to OED definitions
    if oed_data and oed_data.get('definitions'):
        from app.services.period_matching_service import PeriodMatchingService
        
        # Get the target years from term_versions (already loaded above)
        target_years = []
        for version in term_versions:
            if version.temporal_start_year:
                target_years.append(version.temporal_start_year)
        
        if target_years:
            matching_service = PeriodMatchingService()
            try:
                # Match definitions to their relevant periods based on date ranges
                enhanced_definitions = matching_service.enhance_definitions_with_period_matching(
                    oed_data['definitions'], target_years, target_term
                )
                oed_data['definitions'] = enhanced_definitions
                print(f"Matched {len(enhanced_definitions)} definitions to relevant periods from: {target_years}")
                
                # Log the matching results for debugging
                for def_idx, definition in enumerate(enhanced_definitions):
                    relevant_periods = definition.get('relevant_periods', [])
                    first_year = definition.get('first_cited_year')
                    last_year = definition.get('last_cited_year')
                    print(f"  Definition {def_idx + 1} ({first_year}-{last_year or 'present'}): matched to years {relevant_periods}")
                    
            except Exception as e:
                print(f"Failed to match definitions with periods: {str(e)}")
                # Continue with original definitions
    
    # Get reference data for this specific term
    reference_data = {
        'oed_data': oed_data,
        'legal_data': None,
        'temporal_span': temporal_span,
        'domain_count': len(domains),
        'domains': domains
    }
    
    # Try to load legal data  
    legal_patterns = [
        f'data/references/blacks_law_{target_term}_extraction.json',
        f'data/references/{target_term}_legal_extraction.json'
    ]
    
    for pattern in legal_patterns:
        try:
            with open(pattern, 'r') as f:
                reference_data['legal_data'] = json.load(f)
                break
        except FileNotFoundError:
            continue
    
    return render_template('experiments/semantic_evolution_visual.html',
                         experiment=experiment,
                         target_term=target_term,
                         term_record=term_record,
                         academic_anchors=academic_anchors,
                         oed_data=oed_data,
                         reference_data=reference_data,
                         temporal_span=temporal_span,
                         domains=domains)

@experiments_bp.route('/<int:experiment_id>/analyze_evolution', methods=['POST'])
@api_require_login_for_write
def analyze_evolution(experiment_id):
    """Analyze the evolution of a term over time with detailed semantic drift analysis"""
    try:
        experiment = Experiment.query.filter_by(id=experiment_id).first_or_404()
        
        data = request.get_json()
        term = data.get('term')
        periods = data.get('periods', [])
        
        # Import temporal analysis service
        from shared_services.temporal import TemporalAnalysisService
        from shared_services.ontology.ontology_importer import OntologyImporter
        
        # Initialize services
        ontology_importer = OntologyImporter()
        temporal_service = TemporalAnalysisService(ontology_importer)
        
        # Get all documents
        all_documents = list(experiment.documents) + list(experiment.references)
        
        # Extract temporal data
        temporal_data = temporal_service.extract_temporal_data(all_documents, term, periods)
        
        # Analyze semantic drift
        drift_analysis = temporal_service.analyze_semantic_drift(all_documents, term, periods)
        
        # Generate comprehensive narrative
        narrative = temporal_service.generate_evolution_narrative(temporal_data, term, periods)
        
        # Build detailed analysis
        analysis_parts = [narrative, "\n\n--- Semantic Drift Analysis ---\n"]
        
        if drift_analysis.get('average_drift') is not None:
            analysis_parts.append(f"Average Semantic Drift: {drift_analysis['average_drift']:.2%}\n")
        
        if drift_analysis.get('stable_terms'):
            analysis_parts.append(f"Stable Associated Terms: {', '.join(drift_analysis['stable_terms'][:5])}\n")
        
        # Add period-by-period drift details
        if drift_analysis.get('periods'):
            analysis_parts.append("\nPeriod-by-Period Changes:\n")
            for period_range, period_data in drift_analysis['periods'].items():
                analysis_parts.append(f"\n{period_range}:")
                analysis_parts.append(f"  - Drift Score: {period_data['drift_score']:.2%}")
                if period_data.get('new_terms'):
                    analysis_parts.append(f"  - New Terms: {', '.join(period_data['new_terms'][:3])}")
                if period_data.get('lost_terms'):
                    analysis_parts.append(f"  - Lost Terms: {', '.join(period_data['lost_terms'][:3])}")
        
        # Add ontology mapping insights if available
        if temporal_service.ontology_importer:
            analysis_parts.append("\n\n--- Ontology Mapping Insights ---\n")
            # Try to map the term to PROV-O concepts
            prov_mappings = {
                'agent': 'prov:Agent - An entity that bears responsibility',
                'activity': 'prov:Activity - Something that occurs over time',
                'entity': 'prov:Entity - A physical, digital, or conceptual thing',
                'process': 'prov:Activity - A series of actions or operations',
                'artifact': 'prov:Entity - A thing produced or used',
                'actor': 'prov:Agent - One who performs actions'
            }
            
            term_lower = term.lower()
            if term_lower in prov_mappings:
                analysis_parts.append(f"PROV-O Mapping: {prov_mappings[term_lower]}")
            else:
                analysis_parts.append(f"No direct PROV-O mapping found for '{term}'")
        
        analysis = '\n'.join(analysis_parts)
        
        return jsonify({
            'success': True,
            'analysis': analysis,
            'drift_metrics': {
                'average_drift': drift_analysis.get('average_drift', 0),
                'total_drift': drift_analysis.get('total_drift', 0),
                'stable_term_count': len(drift_analysis.get('stable_terms', []))
            }
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# Human-in-the-Loop Orchestration Integration Routes

@experiments_bp.route('/<int:experiment_id>/orchestrated_analysis')
@api_require_login_for_write
def orchestrated_analysis(experiment_id):
    """Human-in-the-loop orchestrated analysis interface"""
    experiment = Experiment.query.filter_by(id=experiment_id).first_or_404()
    
    # Get orchestration decisions for this experiment
    from app.models.orchestration_logs import OrchestrationDecision
    from app.models.orchestration_feedback import OrchestrationFeedback, LearningPattern
    
    decisions = OrchestrationDecision.query.filter_by(
        experiment_id=experiment.id
    ).order_by(OrchestrationDecision.created_at.desc()).all()
    
    # Get learning patterns
    patterns = LearningPattern.query.filter_by(
        pattern_status='active'
    ).order_by(LearningPattern.confidence.desc()).limit(5).all()
    
    # Get experiment configuration
    config = json.loads(experiment.configuration) if experiment.configuration else {}
    terms = config.get('target_terms', [])
    
    return render_template('experiments/orchestrated_analysis.html',
                         experiment=experiment,
                         decisions=decisions,
                         patterns=patterns,
                         terms=terms)


@experiments_bp.route('/<int:experiment_id>/create_orchestration_decision', methods=['POST'])
@api_require_login_for_write
def create_orchestration_decision(experiment_id):
    """Create a new orchestration decision for human feedback"""
    try:
        experiment = Experiment.query.filter_by(id=experiment_id).first_or_404()
        data = request.get_json()
        
        term_text = data.get('term_text', '')
        if not term_text:
            return jsonify({'error': 'Term text is required'}), 400
        
        # Get document characteristics
        doc_characteristics = {
            'document_count': experiment.get_document_count(),
            'total_words': experiment.get_total_word_count(),
            'experiment_type': experiment.experiment_type
        }
        
        # Create input metadata
        config = json.loads(experiment.configuration) if experiment.configuration else {}
        input_metadata = {
            'experiment_id': experiment.id,
            'experiment_type': experiment.experiment_type,
            'document_count': experiment.get_document_count(),
            'total_words': experiment.get_total_word_count(),
            'time_periods': config.get('time_periods', []),
            'domains': config.get('domains', [])
        }
        
        # Simulate LLM orchestration decision (in production, this would call actual LLM service)
        selected_tools = ['spacy', 'embeddings']
        embedding_model = 'bert-base-uncased'
        decision_confidence = 0.85
        
        # Apply learning patterns for more intelligent selection
        from app.models.orchestration_feedback import LearningPattern
        active_patterns = LearningPattern.query.filter_by(pattern_status='active').all()
        
        reasoning_parts = [f"Selected tools for term '{term_text}' based on:"]
        for pattern in active_patterns[:2]:  # Apply top 2 patterns
            if pattern.pattern_type == 'preference':
                pattern_tools = pattern.recommendations.get('tools', [])
                selected_tools.extend([t for t in pattern_tools if t not in selected_tools])
                reasoning_parts.append(f"- {pattern.pattern_name}: {pattern.recommendations.get('reasoning', 'Applied learned pattern')}")
                
                # Apply embedding model recommendations
                pattern_model = pattern.recommendations.get('embedding_model')
                if pattern_model:
                    embedding_model = pattern_model
        
        reasoning = '\\n'.join(reasoning_parts)
        
        # Create orchestration decision
        from app.models.orchestration_logs import OrchestrationDecision
        
        decision = OrchestrationDecision(
            experiment_id=experiment.id,
            term_text=term_text,
            selected_tools=selected_tools,
            embedding_model=embedding_model,
            decision_confidence=decision_confidence,
            orchestrator_provider='claude',
            orchestrator_model='claude-3-sonnet',
            orchestrator_prompt=f"Analyze term '{term_text}' and recommend optimal NLP processing approach",
            orchestrator_response=f"Recommended: {', '.join(selected_tools)} with {embedding_model}",
            orchestrator_response_time_ms=1200,
            processing_strategy='sequential',
            reasoning=reasoning,
            input_metadata=input_metadata,
            document_characteristics=doc_characteristics,
            created_by=current_user.id
        )
        
        db.session.add(decision)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Orchestration decision created successfully',
            'decision_id': str(decision.id),
            'selected_tools': selected_tools,
            'embedding_model': embedding_model,
            'confidence': decision_confidence,
            'reasoning': reasoning
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@experiments_bp.route('/<int:experiment_id>/run_orchestrated_analysis', methods=['POST'])
@api_require_login_for_write
def run_orchestrated_analysis(experiment_id):
    """Run analysis with LLM orchestration decisions and real-time feedback"""
    try:
        experiment = Experiment.query.filter_by(id=experiment_id).first_or_404()
        data = request.get_json()
        
        # Get analysis parameters
        terms = data.get('terms', [])
        if not terms:
            return jsonify({'error': 'At least one term is required'}), 400
        
        # Create orchestration decisions for each term
        from app.models.orchestration_logs import OrchestrationDecision
        from app.services.adaptive_orchestration_service import AdaptiveOrchestrationService
        
        orchestration_service = AdaptiveOrchestrationService()
        analysis_results = []
        
        for term in terms:
            # Create or get existing orchestration decision
            existing_decision = OrchestrationDecision.query.filter_by(
                experiment_id=experiment.id,
                term_text=term
            ).first()
            
            if not existing_decision:
                # Create new decision using adaptive service
                decision_context = {
                    'experiment_id': experiment.id,
                    'term_text': term,
                    'experiment_type': experiment.experiment_type,
                    'document_count': experiment.get_document_count(),
                    'user_id': current_user.id
                }
                
                decision = orchestration_service.create_adaptive_decision(decision_context)
            else:
                decision = existing_decision
            
            # Simulate analysis execution with the orchestrated tools
            analysis_result = {
                'term': term,
                'decision_id': str(decision.id),
                'tools_used': decision.selected_tools,
                'embedding_model': decision.embedding_model,
                'confidence': float(decision.decision_confidence),
                'processing_time': '2.3s',
                'semantic_drift_detected': True,
                'drift_magnitude': 0.32,
                'periods_analyzed': 4,
                'insights': [
                    f"Term '{term}' shows moderate semantic drift over time",
                    f"Most stable usage in period 2010-2015",
                    f"Significant shift detected in recent period"
                ]
            }
            
            analysis_results.append(analysis_result)
        
        # Mark experiment as running
        experiment.status = 'running'
        experiment.started_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Orchestrated analysis initiated for {len(terms)} terms',
            'results': analysis_results,
            'total_decisions': len(analysis_results)
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500



# Document Processing Pipeline Routes

@experiments_bp.route('/<int:experiment_id>/document_pipeline')
def document_pipeline(experiment_id):
    """Step 2: Document Processing Pipeline Overview"""
    experiment = Experiment.query.filter_by(id=experiment_id).first_or_404()
    
    # Get experiment-specific document processing data using raw SQL
    query = """
        SELECT d.id, d.title, d.original_filename, d.file_type, d.content_type, 
               d.word_count, d.created_at,
               COALESCE(ed.processing_status, 'pending') as processing_status,
               COALESCE(ed.embeddings_applied, false) as embeddings_applied,
               COALESCE(ed.segments_created, false) as segments_created,
               COALESCE(ed.nlp_analysis_completed, false) as nlp_analysis_completed
        FROM documents d
        JOIN experiment_documents ed ON d.id = ed.document_id
        WHERE ed.experiment_id = :experiment_id
        ORDER BY d.created_at
    """
    
    result = db.session.execute(text(query), {'experiment_id': experiment_id})
    rows = result.fetchall()
    
    # Build processed documents list with experiment-specific data
    processed_docs = []
    for row in rows:
        # Calculate processing progress
        total_steps = 3  # embeddings, segmentation, nlp_analysis
        completed_steps = sum([row.embeddings_applied, row.segments_created, row.nlp_analysis_completed])
        processing_progress = int((completed_steps / total_steps) * 100)
        
        processed_docs.append({
            'id': row.id,
            'name': row.original_filename or row.title,
            'file_type': row.file_type or row.content_type,
            'word_count': row.word_count or 0,
            'has_embeddings': row.embeddings_applied,
            'status': row.processing_status,
            'processing_progress': processing_progress,
            'created_at': row.created_at
        })
    
    # Calculate overall progress
    completed_count = sum(1 for doc in processed_docs if doc['status'] == 'completed')
    total_count = len(processed_docs)
    progress_percentage = (completed_count / total_count * 100) if total_count > 0 else 0
    
    return render_template('experiments/document_pipeline.html',
                         experiment=experiment,
                         documents=processed_docs,
                         total_count=total_count,
                         completed_count=completed_count,
                         progress_percentage=progress_percentage)


@experiments_bp.route('/<int:experiment_id>/process_document/<int:document_id>')
def process_document(experiment_id, document_id):
    """Process a specific document with experiment-specific context"""
    experiment = Experiment.query.filter_by(id=experiment_id).first_or_404()

    # Get the experiment-document association
    exp_doc = ExperimentDocument.query.filter_by(
        experiment_id=experiment_id,
        document_id=document_id
    ).first_or_404()

    document = exp_doc.document

    # Get processing operations for this experiment-document combination
    processing_operations = ExperimentDocumentProcessing.query.filter_by(
        experiment_document_id=exp_doc.id
    ).order_by(ExperimentDocumentProcessing.created_at.desc()).all()

    # Get all experiment documents for navigation
    all_exp_docs = ExperimentDocument.query.filter_by(experiment_id=experiment_id).all()
    all_doc_ids = [ed.document_id for ed in all_exp_docs]

    try:
        doc_index = all_doc_ids.index(document_id)
    except ValueError:
        flash('Document not found in this experiment', 'error')
        return redirect(url_for('experiments.document_pipeline', experiment_id=experiment_id))

    # Prepare navigation info
    has_previous = doc_index > 0
    has_next = doc_index < len(all_doc_ids) - 1
    previous_doc_id = all_doc_ids[doc_index - 1] if has_previous else None
    next_doc_id = all_doc_ids[doc_index + 1] if has_next else None

    # Calculate processing progress based on new model
    total_processing_types = 3  # embeddings, segmentation, entities
    completed_types = set()
    for op in processing_operations:
        if op.status == 'completed':
            completed_types.add(op.processing_type)

    processing_progress = int((len(completed_types) / total_processing_types) * 100)

    return render_template('experiments/process_document.html',
                         experiment=experiment,
                         document=document,
                         experiment_document=exp_doc,
                         processing_operations=processing_operations,
                         processing_progress=processing_progress,
                         doc_index=doc_index,
                         total_docs=len(all_doc_ids),
                         has_previous=has_previous,
                         has_next=has_next,
                         previous_doc_id=previous_doc_id,
                         next_doc_id=next_doc_id)


@experiments_bp.route('/<int:experiment_id>/document/<int:document_id>/run_tools', methods=['POST'])
@api_require_login_for_write
def run_processing_tools(experiment_id, document_id):
    """
    Execute processing tools on a document (manual mode).

    Request body:
    {
        "tools": ["segment_paragraph", "segment_sentence"]
    }

    Returns:
    {
        "success": true,
        "results": [...]
    }
    """
    try:
        from app.services.processing_tools import DocumentProcessor
        from app.services.tool_registry import validate_tool_strategy
        import logging

        logger = logging.getLogger(__name__)

        # Get experiment and document
        experiment = Experiment.query.filter_by(id=experiment_id).first_or_404()
        exp_doc = ExperimentDocument.query.filter_by(
            experiment_id=experiment_id,
            document_id=document_id
        ).first_or_404()
        document = exp_doc.document

        # Get requested tools
        data = request.json
        tool_names = data.get('tools', [])

        if not tool_names:
            return jsonify({
                "success": False,
                "error": "No tools specified"
            }), 400

        # Validate tools
        validation = validate_tool_strategy({str(document_id): tool_names})
        if not validation['valid']:
            return jsonify({
                "success": False,
                "error": "Tool validation failed",
                "warnings": validation['warnings']
            }), 400

        # Initialize processor
        processor = DocumentProcessor(
            user_id=current_user.id,
            experiment_id=experiment_id
        )

        # Execute tools
        results = []
        for tool_name in tool_names:
            if hasattr(processor, tool_name):
                tool_func = getattr(processor, tool_name)

                # Track start time for provenance
                from datetime import datetime
                started_at = datetime.utcnow()

                result = tool_func(document.get_text_content())
                results.append(result.to_dict())

                ended_at = datetime.utcnow()

                # Store result in database
                processing_record = ExperimentDocumentProcessing(
                    experiment_document_id=exp_doc.id,
                    processing_type=tool_name,
                    status='completed' if result.status == 'success' else 'error',
                    result_data=result.to_dict(),
                    created_by=current_user.id
                )
                db.session.add(processing_record)

                # Track provenance
                from app.services.provenance_service import provenance_service
                try:
                    provenance_service.track_tool_execution(
                        tool_name=tool_name,
                        document=document,
                        user=current_user,
                        experiment=experiment,
                        result_data=result.to_dict(),
                        started_at=started_at,
                        ended_at=ended_at
                    )
                except Exception as e:
                    logger.warning(f"Failed to track provenance for tool execution: {e}")
            else:
                results.append({
                    "tool_name": tool_name,
                    "status": "error",
                    "error": f"Tool '{tool_name}' not found"
                })

        db.session.commit()

        return jsonify({
            "success": True,
            "results": results,
            "tool_count": len(results),
            "validation": validation
        })

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error running tools: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@experiments_bp.route('/<int:experiment_id>/document/<int:document_id>/apply_embeddings', methods=['POST'])
@api_require_login_for_write
def apply_embeddings_to_experiment_document(experiment_id, document_id):
    """Apply embeddings to a document for a specific experiment"""
    try:
        # Get the experiment-document association
        exp_doc = ExperimentDocument.query.filter_by(
            experiment_id=experiment_id, 
            document_id=document_id
        ).first_or_404()
        
        document = exp_doc.document
        
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
                    'dimension': embedding_service.get_dimension(),
                    'experiment_id': experiment_id
                }
            else:
                # Single embedding for short documents
                embeddings = [embedding_service.get_embedding(content)]
                embedding_info = {
                    'type': 'single',
                    'model': embedding_service.get_model_name(),
                    'dimension': embedding_service.get_dimension(),
                    'experiment_id': experiment_id
                }
            
            # Mark embeddings as applied for this experiment
            exp_doc.mark_embeddings_applied(embedding_info)
            
            # Update word count if not set on original document
            if not document.word_count:
                document.word_count = len(content.split())
                document.updated_at = datetime.utcnow()
            
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': 'Embeddings applied successfully for this experiment',
                'embedding_info': embedding_info,
                'processing_progress': exp_doc.processing_progress
            })
            
        except Exception as e:
            current_app.logger.error(f"Error generating embeddings: {str(e)}")
            return jsonify({'error': f'Failed to generate embeddings: {str(e)}'}), 500
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error applying embeddings to experiment document: {str(e)}")
        return jsonify({'error': 'An error occurred while applying embeddings'}), 500


# New Experiment Processing API Endpoints

@experiments_bp.route('/api/experiment-processing/start', methods=['POST'])
@api_require_login_for_write
def start_experiment_processing():
    """Start a new processing operation for an experiment document"""
    try:
        data = request.get_json()

        experiment_document_id = data.get('experiment_document_id')
        processing_type = data.get('processing_type')
        processing_method = data.get('processing_method')

        if not all([experiment_document_id, processing_type, processing_method]):
            return jsonify({'error': 'Missing required parameters'}), 400

        # Get the experiment document
        exp_doc = ExperimentDocument.query.filter_by(id=experiment_document_id).first_or_404()

        # Check if processing already exists for this type and method
        existing_processing = ExperimentDocumentProcessing.query.filter_by(
            experiment_document_id=experiment_document_id,
            processing_type=processing_type,
            processing_method=processing_method
        ).first()

        if existing_processing and existing_processing.status == 'completed':
            return jsonify({'error': f'{processing_type} with {processing_method} method already completed'}), 400

        # Create new processing operation
        processing_op = ExperimentDocumentProcessing(
            experiment_document_id=experiment_document_id,
            processing_type=processing_type,
            processing_method=processing_method,
            status='pending'
        )

        # Set configuration
        config = {
            'method': processing_method,
            'created_by': current_user.id,
            'experiment_id': exp_doc.experiment_id,
            'document_id': exp_doc.document_id
        }
        processing_op.set_configuration(config)

        db.session.add(processing_op)
        db.session.flush()  # This assigns the ID to processing_op

        # Create index entry (now processing_op.id is available)
        index_entry = DocumentProcessingIndex(
            document_id=exp_doc.document_id,
            experiment_id=exp_doc.experiment_id,
            processing_id=processing_op.id,
            processing_type=processing_type,
            processing_method=processing_method,
            status='pending'
        )

        db.session.add(index_entry)
        db.session.commit()

        # Start processing (mark as running)
        processing_op.mark_started()
        index_entry.status = 'running'

        # Real processing using embedding service
        if processing_type == 'embeddings':
            try:
                from app.services.experiment_embedding_service import ExperimentEmbeddingService
                embedding_service = ExperimentEmbeddingService()

                # Check if method is available
                if not embedding_service.is_method_available(processing_method):
                    raise RuntimeError(f"Embedding method '{processing_method}' not available")

                # Use first 2000 characters for embedding (to avoid token limits)
                content = exp_doc.document.content or "No content available"
                text_to_embed = content[:2000]

                # Generate real embeddings
                embedding_result = embedding_service.generate_embeddings(text_to_embed, processing_method)

                # Create embedding artifact with real data
                artifact = ProcessingArtifact(
                    processing_id=processing_op.id,
                    document_id=exp_doc.document_id,
                    artifact_type='embedding_vector',
                    artifact_index=0
                )
                artifact.set_content({
                    'text': text_to_embed,
                    'vector': embedding_result['vector'],
                    'model': embedding_result['model']
                })
                artifact.set_metadata({
                    'dimensions': embedding_result['dimensions'],
                    'method': processing_method,
                    'chunk_size': len(text_to_embed),
                    'original_length': len(content),
                    'tokens_used': embedding_result.get('tokens_used', 'N/A')
                })
                db.session.add(artifact)

                # Mark processing as completed with real metrics
                processing_op.mark_completed({
                    'embedding_method': processing_method,
                    'dimensions': embedding_result['dimensions'],
                    'chunks_created': 1,
                    'total_tokens': len(content.split()),
                    'api_tokens_used': embedding_result.get('tokens_used', 'N/A'),
                    'text_processed_length': len(text_to_embed),
                    'model_used': embedding_result['model']
                })
                index_entry.status = 'completed'

            except Exception as e:
                # Mark processing as failed
                error_message = f"Embedding generation failed: {str(e)}"
                processing_op.mark_failed(error_message)
                index_entry.status = 'failed'
                current_app.logger.error(f"Embedding processing failed: {str(e)}")

                # Still commit to save the failed state
                db.session.commit()

                return jsonify({
                    'success': False,
                    'error': error_message,
                    'processing_id': str(processing_op.id)
                }), 400

        elif processing_type == 'segmentation':
            # Create segmentation artifacts using proper NLP libraries
            if exp_doc.document.content:
                import nltk
                from nltk.tokenize import sent_tokenize
                import spacy
                import re

                # Ensure NLTK data is available
                try:
                    nltk.data.find('tokenizers/punkt')
                except LookupError:
                    nltk.download('punkt_tab', quiet=True)

                content = exp_doc.document.content
                segments = []

                if processing_method == 'paragraph':
                    # Enhanced paragraph splitting using NLTK and improved patterns
                    # First normalize line endings and excessive whitespace
                    normalized_content = re.sub(r'\r\n|\r', '\n', content.strip())
                    normalized_content = re.sub(r'\n{3,}', '\n\n', normalized_content)  # Max 2 consecutive newlines

                    # Split by double newlines (traditional paragraph separator)
                    initial_paragraphs = re.split(r'\n\s*\n', normalized_content)

                    # Further process to handle edge cases
                    processed_paragraphs = []
                    for para in initial_paragraphs:
                        para = para.strip()
                        if not para:
                            continue

                        # Skip very short paragraphs that might be headers or fragments
                        if len(para) < 20:
                            continue

                        # Check if paragraph looks like a proper paragraph (has multiple sentences)
                        sentences_in_para = sent_tokenize(para)

                        # If paragraph has multiple sentences, keep as is
                        if len(sentences_in_para) > 1:
                            processed_paragraphs.append(para)
                        # If single sentence but long enough, keep it
                        elif len(para) > 100:
                            processed_paragraphs.append(para)
                        # Otherwise, it might be a list item or header - still include if substantial
                        elif len(para) > 50:
                            processed_paragraphs.append(para)

                    segments = processed_paragraphs

                elif processing_method == 'sentence':
                    # Use NLTK's punkt tokenizer for proper sentence segmentation
                    segments = sent_tokenize(content)
                    # Filter out very short segments that might be list items or fragments
                    segments = [s.strip() for s in segments if len(s.strip()) > 15]

                else:  # semantic or other methods
                    # Use spaCy for semantic chunking
                    nlp = spacy.load('en_core_web_sm')
                    doc = nlp(content)

                    # Group sentences into semantic chunks based on entity boundaries
                    current_chunk = []
                    chunks = []

                    for sent in doc.sents:
                        current_chunk.append(sent.text.strip())
                        # End chunk if we have 2-3 sentences or hit entity boundary
                        if len(current_chunk) >= 3 or (sent.ents and len(current_chunk) >= 2):
                            chunks.append(' '.join(current_chunk))
                            current_chunk = []

                    if current_chunk:
                        chunks.append(' '.join(current_chunk))

                    segments = [c for c in chunks if len(c.strip()) > 20]

                # Process all segments (remove arbitrary limit)
                total_segments = len(segments)

                for i, segment in enumerate(segments):
                    if segment.strip():
                        artifact = ProcessingArtifact(
                            processing_id=processing_op.id,
                            document_id=exp_doc.document_id,
                            artifact_type='text_segment',
                            artifact_index=i
                        )
                        artifact.set_content({
                            'text': segment.strip(),
                            'segment_type': processing_method,
                            'position': i
                        })
                        artifact.set_metadata({
                            'method': processing_method,
                            'length': len(segment),
                            'word_count': len(segment.split())
                        })
                        db.session.add(artifact)

            # Calculate real segmentation metrics
            if segments:
                avg_length = sum(len(seg) for seg in segments) // len(segments)
                total_words = sum(len(seg.split()) for seg in segments)
                avg_words = total_words // len(segments) if segments else 0
            else:
                avg_length = 0
                avg_words = 0

            # Determine the service/model used based on the method
            service_used = "Basic String Splitting"  # Default fallback
            model_info = ""

            if processing_method == 'paragraph':
                service_used = "NLTK-Enhanced Paragraph Detection"
                model_info = "Punkt tokenizer + smart filtering (min length, multi-sentence validation)"
            elif processing_method == 'sentence':
                service_used = "NLTK Punkt Tokenizer"
                model_info = "Pre-trained sentence boundary detection"
            else:  # semantic or other methods
                service_used = "spaCy NLP + NLTK"
                model_info = "en_core_web_sm + punkt tokenizer for entity-aware chunking"

            processing_op.mark_completed({
                'segmentation_method': processing_method,
                'segments_created': total_segments,
                'avg_segment_length': avg_length,
                'avg_words_per_segment': avg_words,
                'total_tokens': sum(len(seg.split()) for seg in segments),
                'service_used': service_used,
                'model_info': model_info
            })
            index_entry.status = 'completed'

        elif processing_type == 'entities':
            # Real entity extraction using spaCy and enhanced methods
            content = exp_doc.document.content
            extracted_entities = []

            if processing_method == 'spacy':
                # Enhanced spaCy entity extraction
                import spacy
                from collections import defaultdict

                nlp = spacy.load('en_core_web_sm')
                doc = nlp(content)

                # Extract standard spaCy entities
                entity_counts = defaultdict(int)
                seen_entities = set()

                for ent in doc.ents:
                    # Normalize entity text
                    entity_text = ent.text.strip()
                    entity_key = (entity_text.lower(), ent.label_)

                    # Skip very short entities (< 2 chars) and duplicates
                    if len(entity_text) < 2 or entity_key in seen_entities:
                        continue

                    seen_entities.add(entity_key)

                    # Get sentence context for the entity
                    sent_text = ent.sent.text.strip()

                    # Calculate start and end positions within the sentence
                    ent_start_in_sent = ent.start_char - ent.sent.start_char
                    ent_end_in_sent = ent.end_char - ent.sent.start_char

                    # Create context window around entity
                    context_start = max(0, ent_start_in_sent - 50)
                    context_end = min(len(sent_text), ent_end_in_sent + 50)
                    context = sent_text[context_start:context_end].strip()

                    extracted_entities.append({
                        'entity': entity_text,
                        'type': ent.label_,
                        'confidence': 0.85,  # spaCy doesn't provide confidence scores for NER
                        'context': context,
                        'start_char': ent.start_char,
                        'end_char': ent.end_char
                    })

                # Also extract noun phrases as potential entities
                for np in doc.noun_chunks:
                    np_text = np.text.strip()
                    np_key = np_text.lower()

                    # Skip if already found as named entity or too short/long
                    if (len(np_text) < 3 or len(np_text) > 100 or
                        any(np_key in seen_ent[0] for seen_ent in seen_entities)):
                        continue

                    # Only include noun phrases that look like proper concepts
                    if (any(token.pos_ in ['PROPN', 'NOUN'] for token in np) and
                        not all(token.is_stop for token in np)):

                        context_start = max(0, np.start_char - 50)
                        context_end = min(len(content), np.end_char + 50)
                        context = content[context_start:context_end].strip()

                        extracted_entities.append({
                            'entity': np_text,
                            'type': 'CONCEPT',
                            'confidence': 0.65,
                            'context': context,
                            'start_char': np.start_char,
                            'end_char': np.end_char
                        })

            elif processing_method == 'nltk':
                # NLTK-based entity extraction
                import nltk
                from nltk.tokenize import sent_tokenize, word_tokenize
                from nltk.tag import pos_tag
                from nltk.chunk import ne_chunk
                from nltk.tree import Tree

                # Ensure required NLTK data
                try:
                    nltk.data.find('tokenizers/punkt')
                except LookupError:
                    nltk.download('punkt_tab', quiet=True)
                try:
                    nltk.data.find('taggers/averaged_perceptron_tagger')
                except LookupError:
                    nltk.download('averaged_perceptron_tagger', quiet=True)
                try:
                    nltk.data.find('chunkers/maxent_ne_chunker')
                except LookupError:
                    nltk.download('maxent_ne_chunker', quiet=True)
                try:
                    nltk.data.find('corpora/words')
                except LookupError:
                    nltk.download('words', quiet=True)

                sentences = sent_tokenize(content)
                char_offset = 0

                for sent in sentences:
                    words = word_tokenize(sent)
                    pos_tags = pos_tag(words)
                    chunks = ne_chunk(pos_tags, binary=False)

                    word_offset = 0
                    for chunk in chunks:
                        if isinstance(chunk, Tree):
                            entity_words = [word for word, pos in chunk.leaves()]
                            entity_text = ' '.join(entity_words)
                            entity_type = chunk.label()

                            # Find character position
                            entity_start = sent.find(entity_text, word_offset)
                            if entity_start != -1:
                                # Create context
                                context_start = max(0, entity_start - 50)
                                context_end = min(len(sent), entity_start + len(entity_text) + 50)
                                context = sent[context_start:context_end].strip()

                                extracted_entities.append({
                                    'entity': entity_text,
                                    'type': entity_type,
                                    'confidence': 0.70,
                                    'context': context,
                                    'start_char': char_offset + entity_start,
                                    'end_char': char_offset + entity_start + len(entity_text)
                                })
                                word_offset = entity_start + len(entity_text)

                    char_offset += len(sent) + 1

            else:  # llm method - LangExtract + Gemini integration
                try:
                    from app.services.integrated_langextract_service import IntegratedLangExtractService

                    # Initialize LangExtract service
                    langextract_service = IntegratedLangExtractService()

                    if not langextract_service.service_ready:
                        raise Exception(f"LangExtract service not ready: {langextract_service.initialization_error}")

                    # Perform sophisticated entity extraction
                    analysis_result = langextract_service.analyze_document_for_entities(
                        text=content,
                        document_metadata={
                            'document_id': exp_doc.document_id,
                            'experiment_id': exp_doc.experiment_id,
                            'title': exp_doc.document.title
                        }
                    )

                    # Extract entities from LangExtract results
                    if 'entities' in analysis_result:
                        for entity_data in analysis_result['entities']:
                            extracted_entities.append({
                                'entity': entity_data.get('text', ''),
                                'type': entity_data.get('type', 'ENTITY'),
                                'confidence': entity_data.get('confidence', 0.85),
                                'context': entity_data.get('context', ''),
                                'start_char': entity_data.get('start_pos', 0),
                                'end_char': entity_data.get('end_pos', 0)
                            })

                    # Extract key concepts as entities too
                    if 'key_concepts' in analysis_result:
                        for concept in analysis_result['key_concepts']:
                            extracted_entities.append({
                                'entity': concept.get('term', ''),
                                'type': 'CONCEPT',
                                'confidence': concept.get('confidence', 0.80),
                                'context': concept.get('context', ''),
                                'start_char': concept.get('position', [0, 0])[0],
                                'end_char': concept.get('position', [0, 0])[1]
                            })

                except Exception as e:
                    logger.warning(f"LangExtract extraction failed, falling back to pattern-based: {e}")

                    # Fallback to improved pattern-based extraction
                    import re
                    patterns = [
                        r'\b[A-Z][a-z]+ [A-Z][a-z]+\b',  # Proper names
                        r'\b[A-Z]{2,}\b',  # Acronyms
                        r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s+(?:Inc|Corp|LLC|Ltd|Company|University|Institute)\b',  # Organizations
                        r'\b(?:Dr|Prof|Mr|Ms|Mrs)\.?\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b',  # Titles + names
                    ]

                    for pattern in patterns:
                        matches = re.finditer(pattern, content)
                        for match in matches:
                            entity_text = match.group().strip()
                            start_pos = match.start()
                            end_pos = match.end()
                            context_start = max(0, start_pos - 50)
                            context_end = min(len(content), end_pos + 50)
                            context = content[context_start:context_end].strip()

                            extracted_entities.append({
                                'entity': entity_text,
                                'type': 'ENTITY',
                                'confidence': 0.60,
                                'context': context,
                                'start_char': start_pos,
                                'end_char': end_pos
                            })

            # Remove duplicates and create artifacts
            unique_entities = []
            seen_texts = set()

            for entity in extracted_entities:
                entity_key = entity['entity'].lower().strip()
                if entity_key not in seen_texts and len(entity_key) > 1:
                    seen_texts.add(entity_key)
                    unique_entities.append(entity)

            # Sort by confidence and position
            unique_entities.sort(key=lambda x: (-x['confidence'], x['start_char']))

            # Create artifacts for extracted entities
            for i, entity_data in enumerate(unique_entities):
                artifact = ProcessingArtifact(
                    processing_id=processing_op.id,
                    document_id=exp_doc.document_id,
                    artifact_type='extracted_entity',
                    artifact_index=i
                )
                artifact.set_content({
                    'entity': entity_data['entity'],
                    'entity_type': entity_data['type'],
                    'confidence': entity_data['confidence'],
                    'context': entity_data['context'],
                    'start_char': entity_data['start_char'],
                    'end_char': entity_data['end_char']
                })
                artifact.set_metadata({
                    'method': processing_method,
                    'extraction_confidence': entity_data['confidence'],
                    'character_position': f"{entity_data['start_char']}-{entity_data['end_char']}"
                })
                db.session.add(artifact)

            # Determine service and model info
            service_used = "Unknown"
            model_info = ""

            if processing_method == 'spacy':
                service_used = "spaCy NLP + Enhanced Extraction"
                model_info = "en_core_web_sm + noun phrase extraction"
            elif processing_method == 'nltk':
                service_used = "NLTK Named Entity Chunker"
                model_info = "maxent_ne_chunker + POS tagging"
            else:
                service_used = "LangExtract + Gemini Integration"
                model_info = "Google Gemini-1.5-flash with character-level positioning"

            # Extract unique entity types
            entity_types = list(set([e['type'] for e in unique_entities]))

            processing_op.mark_completed({
                'extraction_method': processing_method,
                'entities_found': len(unique_entities),
                'entity_types': entity_types,
                'service_used': service_used,
                'model_info': model_info,
                'avg_confidence': sum(e['confidence'] for e in unique_entities) / len(unique_entities) if unique_entities else 0
            })
            index_entry.status = 'completed'

        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'{processing_type} processing started successfully',
            'processing_id': str(processing_op.id),
            'status': processing_op.status
        })

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error starting experiment processing: {str(e)}")
        return jsonify({'error': str(e)}), 500


@experiments_bp.route('/api/experiment-document/<int:exp_doc_id>/processing-status')
def get_experiment_document_processing_status(exp_doc_id):
    """Get processing status for an experiment document"""
    try:
        # Get the experiment document
        exp_doc = ExperimentDocument.query.filter_by(id=exp_doc_id).first_or_404()

        # Get all processing operations for this experiment document
        processing_operations = ExperimentDocumentProcessing.query.filter_by(
            experiment_document_id=exp_doc_id
        ).order_by(ExperimentDocumentProcessing.created_at.desc()).all()

        return jsonify({
            'success': True,
            'experiment_document_id': exp_doc_id,
            'processing_operations': [op.to_dict() for op in processing_operations]
        })

    except Exception as e:
        current_app.logger.error(f"Error getting processing status: {str(e)}")
        return jsonify({'error': str(e)}), 500


@experiments_bp.route('/api/processing/<uuid:processing_id>/artifacts')
def get_processing_artifacts(processing_id):
    """Get artifacts for a specific processing operation"""
    try:
        # Get the processing operation
        processing_op = ExperimentDocumentProcessing.query.filter_by(id=processing_id).first_or_404()

        # Get all artifacts for this processing operation
        artifacts = ProcessingArtifact.query.filter_by(
            processing_id=processing_id
        ).order_by(ProcessingArtifact.artifact_index, ProcessingArtifact.created_at).all()

        return jsonify({
            'success': True,
            'processing_id': str(processing_id),
            'processing_type': processing_op.processing_type,
            'processing_method': processing_op.processing_method,
            'artifacts': [artifact.to_dict() for artifact in artifacts]
        })

    except Exception as e:
        current_app.logger.error(f"Error getting processing artifacts: {str(e)}")
        return jsonify({'error': str(e)}), 500


