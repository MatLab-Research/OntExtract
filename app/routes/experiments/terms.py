"""
Experiments Term Management Routes

This module handles term management for domain comparison experiments.

Routes:
- GET  /experiments/<id>/manage_terms       - Term management UI
- POST /experiments/<id>/update_terms       - Update terms and domains
- GET  /experiments/<id>/get_terms          - Get saved terms
- POST /experiments/<id>/fetch_definitions  - Fetch term definitions
"""

from flask import render_template, request, jsonify, flash, redirect, url_for
from flask_login import current_user
from app.utils.auth_decorators import api_require_login_for_write
from app import db
from app.models import Experiment
from datetime import datetime
import json
from typing import Dict, List

from . import experiments_bp


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
