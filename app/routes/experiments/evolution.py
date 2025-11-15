"""
Experiments Semantic Evolution Routes

This module handles semantic evolution analysis for experiments.

Routes:
- GET  /experiments/<id>/semantic_evolution_visual - Semantic evolution visualization
- POST /experiments/<id>/analyze_evolution         - Analyze term evolution over time
"""

from flask import render_template, request, jsonify, flash, redirect, url_for
from flask_login import current_user
from app.utils.auth_decorators import api_require_login_for_write
from app.models import Experiment
import json

from . import experiments_bp


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
