"""Human-in-the-loop orchestration review routes."""

from flask import render_template, request, jsonify
from flask_login import current_user
from app.utils.auth_decorators import api_require_login_for_write
from app.services.orchestration_service import get_orchestration_service
from app.services.workflow_executor import get_workflow_executor
from app.services.base_service import ServiceError, NotFoundError
import markdown
from app.models.experiment_orchestration_run import ExperimentOrchestrationRun
from app.models import Experiment
from app import db
import logging
from datetime import datetime
from .. import experiments_bp


@experiments_bp.route('/<int:experiment_id>/orchestration/review/<uuid:run_id>')
@api_require_login_for_write
def orchestration_review_page(experiment_id, run_id):
    """
    Dedicated page for reviewing and modifying LLM orchestration strategy.

    Shows:
    - LLM analysis (experiment goal, reasoning, confidence)
    - Per-document tool recommendations with edit capability
    - Temporal period configuration (for temporal_evolution experiments)
    - Approve/Reject buttons
    """
    try:
        # Get experiment
        experiment = Experiment.query.get(experiment_id)
        if not experiment:
            from flask import abort
            abort(404)

        # Get orchestration run
        run = ExperimentOrchestrationRun.query.get(run_id)
        if not run or run.experiment_id != experiment_id:
            from flask import abort
            abort(404)

        # Verify run is in reviewing state
        if run.status != 'reviewing':
            # If not in reviewing state, redirect to pipeline
            from flask import redirect, url_for, flash
            flash(f'Orchestration run is not in review state (current: {run.status})', 'warning')
            return redirect(url_for('experiments.document_pipeline', experiment_id=experiment_id))

        # Get documents for this experiment
        from app.models import Document
        documents = Document.query.filter_by(experiment_id=experiment_id).all()

        # Build document list with metadata
        doc_list = []
        for doc in documents:
            doc_list.append({
                'id': doc.id,
                'uuid': str(doc.uuid),
                'title': doc.title or 'Untitled',
                'authors': doc.authors,
                'publication_year': doc.publication_date.year if doc.publication_date else None,
                'word_count': doc.word_count
            })

        # Get recommended strategy (maps doc_id -> [tool_names])
        recommended_strategy = run.recommended_strategy or {}

        # Check for existing temporal periods (for temporal_evolution experiments)
        has_existing_periods = False
        existing_periods = []
        suggested_periods = []

        if experiment.experiment_type == 'temporal_evolution':
            # First check experiment.configuration for named_periods (preferred storage)
            config = experiment.configuration or {}
            # Handle case where config is a JSON string
            if isinstance(config, str):
                import json
                try:
                    config = json.loads(config)
                except (json.JSONDecodeError, TypeError):
                    config = {}
            named_periods = config.get('named_periods', [])
            period_documents = config.get('period_documents', {})

            if named_periods:
                has_existing_periods = True
                for period in named_periods:
                    # Count documents in this period's year range
                    start_year = period.get('start_year')
                    end_year = period.get('end_year')
                    doc_count = 0
                    for year_str, docs in period_documents.items():
                        try:
                            year = int(year_str)
                            if start_year and end_year and start_year <= year <= end_year:
                                doc_count += len(docs) if isinstance(docs, list) else 1
                        except (ValueError, TypeError):
                            pass

                    existing_periods.append({
                        'temporal_period': period.get('name', 'Unnamed Period'),
                        'temporal_start_year': start_year,
                        'temporal_end_year': end_year,
                        'description': period.get('description', ''),
                        'marker_color': '#6c757d',  # Default color
                        'document_count': doc_count
                    })
            else:
                # Fall back to DocumentTemporalMetadata table
                from app.models.temporal_experiment import DocumentTemporalMetadata

                existing_meta = DocumentTemporalMetadata.query.filter_by(
                    experiment_id=experiment_id
                ).all()

                if existing_meta:
                    has_existing_periods = True
                    # Group by period
                    period_docs = {}
                    for meta in existing_meta:
                        period_name = meta.temporal_period
                        if period_name not in period_docs:
                            period_docs[period_name] = {
                                'temporal_period': period_name,
                                'temporal_start_year': meta.temporal_start_year,
                                'temporal_end_year': meta.temporal_end_year,
                                'marker_color': meta.marker_color,
                                'document_count': 0
                            }
                        period_docs[period_name]['document_count'] += 1

                    existing_periods = list(period_docs.values())

            # If no existing periods, suggest auto-generating one per document
            if not has_existing_periods:
                # Build suggested periods - one per document based on publication date
                for doc in documents:
                    if doc.publication_date:
                        year = doc.publication_date.year
                        suggested_periods.append({
                            'name': f"{doc.title[:30]}..." if len(doc.title or '') > 30 else (doc.title or 'Untitled'),
                            'start_year': year,
                            'end_year': year,
                            'document_id': doc.id,
                            'document_count': 1
                        })

            # Also get time_periods (individual years) and period_documents for artifact display
            time_periods = config.get('time_periods', [])
            period_documents = config.get('period_documents', {})
            period_metadata = config.get('period_metadata', {})
        else:
            time_periods = []
            period_documents = {}
            period_metadata = {}

        return render_template(
            'experiments/orchestration_review.html',
            experiment=experiment,
            run=run,
            documents=doc_list,
            recommended_strategy=recommended_strategy,
            has_existing_periods=has_existing_periods,
            existing_periods=existing_periods,
            suggested_periods=suggested_periods,
            time_periods=time_periods,
            period_documents=period_documents,
            period_metadata=period_metadata
        )

    except Exception as e:
        from werkzeug.exceptions import HTTPException
        if isinstance(e, HTTPException):
            raise
        logger.error(f"Error loading orchestration review page: {e}", exc_info=True)
        from flask import abort
        abort(500)

@experiments_bp.route('/orchestration/approve-strategy/<uuid:run_id>', methods=['POST'])
@api_require_login_for_write
def approve_orchestration_strategy(run_id):
    """
    Approve strategy and continue to execution (Stages 4-5)

    POST Body:
    {
        "strategy_approved": true,
        "modified_strategy": {  // Optional: user modifications
            "217": ["extract_entities_spacy", "extract_temporal"]
        },
        "review_notes": "Added temporal extraction to first document"
    }

    Returns:
    {
        "success": true,
        "status": "executing",
        "message": "Strategy approved - beginning execution"
    }
    """
    try:
        run = ExperimentOrchestrationRun.query.get(run_id)
        if not run:
            return jsonify({
                'success': False,
                'error': 'Orchestration run not found'
            }), 404

        # Verify run is in correct state
        if run.status != 'reviewing':
            return jsonify({
                'success': False,
                'error': f'Cannot approve strategy in {run.status} state'
            }), 400

        # Get approval data
        data = request.get_json() or {}
        strategy_approved = data.get('strategy_approved', True)

        if not strategy_approved:
            # User rejected strategy
            run.status = 'cancelled'
            run.review_notes = data.get('review_notes', 'User rejected strategy')
            db.session.commit()

            return jsonify({
                'success': True,
                'status': 'cancelled',
                'message': 'Strategy rejected'
            }), 200

        # Handle generate_periods option for temporal_evolution experiments
        generate_periods = data.get('generate_periods', False)
        suggested_periods = data.get('suggested_periods', [])

        if generate_periods and suggested_periods:
            experiment = run.experiment
            if experiment and experiment.experiment_type == 'temporal_evolution':
                # Check if periods already exist
                from app.models.temporal_experiment import DocumentTemporalMetadata
                existing_meta = DocumentTemporalMetadata.query.filter_by(
                    experiment_id=experiment.id
                ).first()

                # Also check configuration
                config = experiment.configuration or {}
                # Handle case where config is a JSON string
                if isinstance(config, str):
                    import json
                    try:
                        config = json.loads(config)
                    except (json.JSONDecodeError, TypeError):
                        config = {}
                has_named_periods = bool(config.get('named_periods'))

                if not existing_meta and not has_named_periods:
                    import json
                    # Use the periods provided from the frontend (user may have removed some)
                    created_count = 0
                    periods = []
                    period_documents = {}

                    for period_data in suggested_periods:
                        period_name = period_data.get('name', '')
                        document_id = period_data.get('document_id')
                        start_year = period_data.get('start_year')
                        end_year = period_data.get('end_year')

                        if document_id and start_year:
                            # Create DocumentTemporalMetadata record
                            meta = DocumentTemporalMetadata(
                                document_id=document_id,
                                experiment_id=experiment.id,
                                temporal_period=period_name,
                                temporal_start_year=start_year,
                                temporal_end_year=end_year or start_year,
                                publication_year=start_year,
                                extraction_method='auto_generated'
                            )
                            db.session.add(meta)
                            created_count += 1

                            # Track for experiment.configuration
                            if start_year not in periods:
                                periods.append(start_year)
                            year_str = str(start_year)
                            if year_str not in period_documents:
                                period_documents[year_str] = []
                            period_documents[year_str].append({
                                'id': document_id,
                                'title': period_name,
                                'date_source': 'publication_date'
                            })

                    # Update experiment.configuration so manage_temporal_terms page shows them
                    periods = sorted(periods)
                    config['time_periods'] = periods
                    config['period_documents'] = period_documents
                    config['period_metadata'] = {
                        str(year): {'source': 'auto-generated', 'document_count': len(period_documents.get(str(year), []))}
                        for year in periods
                    }
                    if periods:
                        config['start_year'] = min(periods)
                        config['end_year'] = max(periods)
                        config['periods_source'] = 'orchestration'

                    experiment.configuration = json.dumps(config) if isinstance(config, dict) else config

                    db.session.flush()
                    logger.info(f"Generated temporal metadata for {created_count} documents in experiment {experiment.id}")

        # Store approval info
        run.strategy_approved = True
        run.modified_strategy = data.get('modified_strategy')
        run.review_notes = data.get('review_notes')
        run.reviewed_by = current_user.id
        run.reviewed_at = datetime.utcnow()
        run.status = 'executing'
        run.current_stage = 'executing'
        db.session.commit()

        # Execute processing phase via Celery task
        from app.tasks.orchestration import run_execution_phase_task
        task = run_execution_phase_task.delay(
            str(run.id),
            modified_strategy=data.get('modified_strategy'),
            review_notes=data.get('review_notes'),
            reviewer_id=current_user.id
        )

        # Store Celery task ID for monitoring
        run.celery_task_id = task.id
        db.session.commit()

        logger.info(f"Started Celery task {task.id} for execution phase of run {run.id}")

        return jsonify({
            'success': True,
            'status': 'executing',
            'message': 'Strategy approved - processing started in background'
        }), 200

    except Exception as e:
        logger.error(f"Error approving strategy for run {run_id}: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
