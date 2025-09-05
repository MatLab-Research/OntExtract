from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from app import db
from app.models import Document, Experiment
from datetime import datetime
import json
from typing import List, Optional
from app.services.text_processing import TextProcessingService
from app.services.experiment_domain_comparison import DomainComparisonService

# Note: experiments.configuration may include a `design` object per Phase 1b of metadata plan.
# Analysis services should read optional design = config.get('design') to drive factor/group logic.

experiments_bp = Blueprint('experiments', __name__, url_prefix='/experiments')

@experiments_bp.route('/')
@login_required
def index():
    """List all experiments for all users"""
    experiments = Experiment.query.order_by(Experiment.created_at.desc()).all()
    return render_template('experiments/index.html', experiments=experiments)

@experiments_bp.route('/new')
@login_required
def new():
    """Create a new experiment"""
    # Get documents and references separately for all users
    documents = Document.query.filter_by(document_type='document').order_by(Document.created_at.desc()).all()
    references = Document.query.filter_by(document_type='reference').order_by(Document.created_at.desc()).all()
    return render_template('experiments/new.html', documents=documents, references=references)

@experiments_bp.route('/wizard')
@login_required
def wizard():
    """Guided wizard to create an experiment with design options (Choi-inspired)."""
    documents = Document.query.filter_by(document_type='document').order_by(Document.created_at.desc()).all()
    references = Document.query.filter_by(document_type='reference').order_by(Document.created_at.desc()).all()
    return render_template('experiments/wizard.html', documents=documents, references=references)

@experiments_bp.route('/create', methods=['POST'])
@login_required
def create():
    """Create a new experiment"""
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
        
        # Redirect to appropriate term manager based on experiment type
        if data['experiment_type'] == 'domain_comparison':
            return jsonify({
                'success': True,
                'message': 'Experiment created successfully',
                'experiment_id': experiment.id,
                'redirect': url_for('experiments.manage_terms', experiment_id=experiment.id)
            })
        elif data['experiment_type'] == 'temporal_evolution':
            return jsonify({
                'success': True,
                'message': 'Experiment created successfully',
                'experiment_id': experiment.id,
                'redirect': url_for('experiments.manage_temporal_terms', experiment_id=experiment.id)
            })
        
        return jsonify({
            'success': True,
            'message': 'Experiment created successfully',
            'experiment_id': experiment.id
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@experiments_bp.route('/sample', methods=['POST', 'GET'])
@login_required
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
@login_required
def view(experiment_id):
    """View experiment details"""
    experiment = Experiment.query.filter_by(id=experiment_id).first_or_404()
    return render_template('experiments/view.html', experiment=experiment)

@experiments_bp.route('/<int:experiment_id>/edit')
@login_required
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
@login_required
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
@login_required
def delete(experiment_id):
    """Delete experiment"""
    try:
        experiment = Experiment.query.filter_by(id=experiment_id).first_or_404()
        
        # Can only delete experiments that are not running
        if experiment.status == 'running':
            return jsonify({'error': 'Cannot delete an experiment that is currently running'}), 400
        
        db.session.delete(experiment)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Experiment deleted successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@experiments_bp.route('/<int:experiment_id>/run', methods=['POST'])
@login_required
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
@login_required
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
@login_required
def api_list():
    """API endpoint to list experiments"""
    experiments = Experiment.query.order_by(Experiment.created_at.desc()).all()
    return jsonify({
        'experiments': [exp.to_dict() for exp in experiments]
    })

@experiments_bp.route('/api/<int:experiment_id>')
@login_required
def api_get(experiment_id):
    """API endpoint to get experiment details"""
    experiment = Experiment.query.filter_by(id=experiment_id).first_or_404()
    return jsonify(experiment.to_dict(include_documents=True))

@experiments_bp.route('/<int:experiment_id>/manage_terms')
@login_required
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
@login_required
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
@login_required
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
@login_required
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
@login_required
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
    
    return render_template('experiments/temporal_term_manager.html', 
                         experiment=experiment,
                         time_periods=time_periods,
                         terms=terms,
                         start_year=start_year,
                         end_year=end_year,
                         use_oed_periods=use_oed_periods,
                         oed_period_data=config.get('oed_period_data', {}),
                         term_periods=config.get('term_periods', {}))

@experiments_bp.route('/<int:experiment_id>/update_temporal_terms', methods=['POST'])
@login_required
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
@login_required
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
@login_required
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
@login_required  
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
    
    # Get reference data for this specific term
    reference_data = {
        'oed_data': None,
        'legal_data': None,
        'temporal_span': temporal_span,
        'domain_count': len(domains),
        'domains': domains
    }
    
    # Try to load OED data
    oed_patterns = [
        f'data/references/oed_{target_term}_extraction_provenance.json',
        f'data/references/{target_term}_oed_extraction.json'
    ]
    
    for pattern in oed_patterns:
        try:
            with open(pattern, 'r') as f:
                reference_data['oed_data'] = json.load(f)
                break
        except FileNotFoundError:
            continue
    
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
                         reference_data=reference_data,
                         temporal_span=temporal_span,
                         domains=domains)

@experiments_bp.route('/<int:experiment_id>/analyze_evolution', methods=['POST'])
@login_required
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
