"""
Experiments Temporal Analysis Routes

This module handles temporal evolution analysis for experiments.

Routes:
- GET  /experiments/<id>/manage_temporal_terms    - Temporal term management UI
- POST /experiments/<id>/update_temporal_terms    - Update temporal terms and periods
- GET  /experiments/<id>/get_temporal_terms       - Get saved temporal terms
- POST /experiments/<id>/fetch_temporal_data      - Fetch temporal data for analysis
"""

from flask import render_template, request, jsonify, flash, redirect, url_for
from flask_login import current_user
from app.utils.auth_decorators import api_require_login_for_write
from app import db
from app.models import Experiment
from datetime import datetime
import json
from typing import List

from . import experiments_bp


def generate_time_periods(start_year: int, end_year: int, interval: int = 5) -> List[int]:
    """
    Generate a list of time periods between start and end years.

    Args:
        start_year: Starting year
        end_year: Ending year
        interval: Years between periods (default: 5)

    Returns:
        List of years representing time periods
    """
    periods = []
    current_year = start_year
    while current_year <= end_year:
        periods.append(current_year)
        current_year += interval

    # Ensure end year is included if not already
    if periods and periods[-1] < end_year:
        periods.append(end_year)

    # If still empty, create a basic set
    if not periods:
        periods = [start_year, end_year]

    return periods


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
