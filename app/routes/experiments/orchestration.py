"""
Experiments LLM Orchestration Routes

This module handles human-in-the-loop LLM orchestration for experiments.

Routes:
- GET  /experiments/<id>/orchestration-provenance.json - Download PROV-O JSON
- POST /experiments/<id>/orchestration/analyze         - Start LLM orchestration
- GET  /orchestration/status/<run_id>                  - Poll orchestration status
- POST /orchestration/approve-strategy/<run_id>        - Approve strategy & continue
- GET  /experiments/<id>/orchestration/review/<run_id> - Review strategy page
- GET  /experiments/<id>/orchestration/llm-results/<run_id> - View LLM results

Uses OrchestrationService with DTO validation
"""

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

from . import experiments_bp

logger = logging.getLogger(__name__)
orchestration_service = get_orchestration_service()
workflow_executor = get_workflow_executor()

# Background execution handled by LangGraph AsyncPostgresSaver
# No Celery or external workers needed


@experiments_bp.route('/<int:experiment_id>/orchestration-provenance.json')
def orchestration_provenance_json(experiment_id):
    """
    Download PROV-O compliant JSON provenance record for orchestration decisions

    REFACTORED: Now uses OrchestrationService
    """
    try:
        # Get provenance data from service
        provenance_data = orchestration_service.get_orchestration_provenance(experiment_id)

        return jsonify(provenance_data), 200

    except NotFoundError as e:
        logger.warning(f"Experiment {experiment_id} not found: {e}")
        return jsonify({
            'error': 'Experiment not found'
        }), 404

    except ServiceError as e:
        logger.error(f"Service error generating provenance: {e}", exc_info=True)
        return jsonify({
            'error': 'Failed to generate provenance data'
        }), 500


# ============================================================================
# NEW: LLM Analyze Workflow Routes
# ============================================================================

@experiments_bp.route('/<int:experiment_id>/orchestration/analyze', methods=['POST'])
@api_require_login_for_write
def start_llm_orchestration(experiment_id):
    """
    Start LLM orchestration workflow using LangGraph with PostgreSQL checkpointing.

    Background execution with AsyncPostgresSaver - no Celery worker needed.
    State persists in PostgreSQL, survives Flask restarts.
    Always starts fresh - any in-progress runs are marked as failed.

    POST Body:
    {
        "review_choices": true  // Whether to pause for user review
    }

    Returns immediately with run_id. Client polls /orchestration/status/<run_id> for progress.

    Returns:
    {
        "success": true,
        "run_id": "uuid-here",
        "status": "analyzing",
        "message": "Orchestration started with LangGraph checkpointing"
    }
    """
    try:
        # Verify experiment exists
        experiment = Experiment.query.get(experiment_id)
        if not experiment:
            return jsonify({
                'success': False,
                'error': 'Experiment not found'
            }), 404

        # Mark any existing in-progress runs for this experiment as failed
        existing_runs = ExperimentOrchestrationRun.query.filter_by(
            experiment_id=experiment_id
        ).filter(
            ExperimentOrchestrationRun.status.in_(['analyzing', 'recommending', 'reviewing', 'executing', 'synthesizing'])
        ).all()

        for existing_run in existing_runs:
            existing_run.status = 'failed'
            existing_run.error_message = 'Interrupted by new orchestration run'
            existing_run.completed_at = datetime.utcnow()
            logger.info(f"Marked existing run {existing_run.id} as failed (interrupted)")

        db.session.commit()

        # Get user preferences
        data = request.get_json() or {}
        review_choices = data.get('review_choices', True)

        # Create new orchestration run
        run = ExperimentOrchestrationRun(
            experiment_id=experiment_id,
            user_id=current_user.id,
            status='analyzing',
            current_stage='analyzing'
        )
        db.session.add(run)
        db.session.commit()

        logger.info(f"Created orchestration run {run.id} for experiment {experiment_id}")

        # Execute in background thread (LangGraph checkpointer handles persistence)
        import threading
        from flask import current_app

        # Capture the app for use in the thread
        app = current_app._get_current_object()
        run_id = run.id

        def run_workflow():
            # Background threads need their own app context
            with app.app_context():
                try:
                    # Run stages 1-2 (analyze + recommend)
                    result = workflow_executor.execute_recommendation_phase(
                        run_id=run_id,
                        review_choices=review_choices
                    )

                    # If no review required (review_choices=false), automatically run stages 4-5
                    if not review_choices and result.get('status') != 'failed':
                        logger.info(f"Auto-executing processing phase for run {run_id} (review_choices=false)")
                        workflow_executor.execute_processing_phase(run_id=run_id)

                except Exception as e:
                    logger.error(f"Workflow execution failed for run {run_id}: {e}", exc_info=True)

        thread = threading.Thread(target=run_workflow, daemon=True)
        thread.start()

        logger.info(f"Started background thread for orchestration run {run.id}")

        return jsonify({
            'success': True,
            'run_id': str(run.id),
            'status': 'analyzing',
            'current_stage': 'analyzing',
            'message': 'Orchestration started with LangGraph checkpointing. State persists in PostgreSQL.'
        }), 200

    except Exception as e:
        logger.error(f"Error starting orchestration for experiment {experiment_id}: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@experiments_bp.route('/<int:experiment_id>/orchestration/check-status', methods=['GET'])
def check_experiment_processing_status(experiment_id):
    """
    Check if documents have already been processed.

    Used to warn users before starting LLM orchestration on already-processed documents.

    Returns:
    {
        "experiment_id": 123,
        "total_documents": 5,
        "processed_documents": 2,
        "unprocessed_documents": 3,
        "has_partial_processing": true,
        "has_full_processing": false,
        "documents": [
            {
                "document_id": 217,
                "title": "Document A",
                "has_processing": true,
                "processing_types": ["segmentation", "entities"]
            },
            ...
        ]
    }
    """
    try:
        from app.models import TextSegment, ProcessingJob, ProcessingArtifact, Document

        # Get experiment
        experiment = Experiment.query.get(experiment_id)
        if not experiment:
            return jsonify({'error': 'Experiment not found'}), 404

        # Get all documents for this experiment
        documents = Document.query.filter_by(experiment_id=experiment_id).all()

        processing_status = []
        for doc in documents:
            # Check for existing processing
            has_segments = TextSegment.query.filter_by(document_id=doc.id).first() is not None
            has_entities = ProcessingJob.query.filter_by(
                document_id=doc.id,
                job_type='entity_extraction'
            ).first() is not None
            has_artifacts = ProcessingArtifact.query.filter_by(document_id=doc.id).first() is not None

            status = {
                'document_id': doc.id,
                'title': doc.title,
                'has_processing': has_segments or has_entities or has_artifacts,
                'processing_types': []
            }

            if has_segments:
                status['processing_types'].append('segmentation')
            if has_entities:
                status['processing_types'].append('entities')
            if has_artifacts:
                artifacts = ProcessingArtifact.query.filter_by(document_id=doc.id).all()
                # Get unique tool names
                tool_names = list(set(a.tool_name for a in artifacts))
                status['processing_types'].extend(tool_names)

            processing_status.append(status)

        # Summary
        processed_count = sum(1 for s in processing_status if s['has_processing'])
        total_docs = len(documents)

        return jsonify({
            'experiment_id': experiment_id,
            'total_documents': total_docs,
            'processed_documents': processed_count,
            'unprocessed_documents': total_docs - processed_count,
            'has_partial_processing': 0 < processed_count < total_docs,
            'has_full_processing': processed_count == total_docs and total_docs > 0,
            'documents': processing_status
        }), 200

    except Exception as e:
        logger.error(f"Error checking processing status for experiment {experiment_id}: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@experiments_bp.route('/<int:experiment_id>/orchestration/latest-run', methods=['GET'])
def get_latest_orchestration_run(experiment_id):
    """
    Get the latest orchestration run for an experiment (if any in progress).

    Used to resume existing runs instead of creating duplicates.

    Only returns runs that:
    1. Are not completed/failed
    2. Started within the last 30 minutes (prevents resuming stuck/old runs)

    Returns:
    {
        "run_id": "uuid",
        "status": "reviewing|executing|etc",
        "started_at": "timestamp"
    }
    """
    try:
        from datetime import datetime, timedelta

        # Only resume runs that started within the last 30 minutes
        # This prevents picking up stuck/old runs from previous crashes
        time_threshold = datetime.utcnow() - timedelta(minutes=30)

        # Get the most recent non-completed/failed run for this experiment
        latest_run = ExperimentOrchestrationRun.query.filter_by(
            experiment_id=experiment_id
        ).filter(
            ExperimentOrchestrationRun.status.in_(['analyzing', 'recommending', 'reviewing', 'executing', 'synthesizing']),
            ExperimentOrchestrationRun.started_at >= time_threshold
        ).order_by(
            ExperimentOrchestrationRun.started_at.desc()
        ).first()

        if latest_run:
            return jsonify({
                'run_id': str(latest_run.id),
                'status': latest_run.status,
                'current_stage': latest_run.current_stage,
                'started_at': latest_run.started_at.isoformat() if latest_run.started_at else None
            }), 200
        else:
            return jsonify({
                'run_id': None,
                'status': None
            }), 404

    except Exception as e:
        logger.error(f"Error getting latest run for experiment {experiment_id}: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@experiments_bp.route('/orchestration/status/<uuid:run_id>', methods=['GET'])
def get_orchestration_status(run_id):
    """
    Get current status of orchestration run

    Returns status, progress, and recommendations when ready
    """
    try:
        run = ExperimentOrchestrationRun.query.get(run_id)
        if not run:
            return jsonify({
                'error': 'Orchestration run not found'
            }), 404

        # Calculate progress percentage
        stage_progress = {
            'analyzing': 20,
            'recommending': 40,
            'reviewing': 50,
            'executing': 70,
            'synthesizing': 90,
            'completed': 100,
            'failed': 0
        }
        progress_percentage = stage_progress.get(run.status, 0)

        response = {
            'run_id': str(run.id),
            'status': run.status,
            'current_stage': run.current_stage or run.status,
            'current_operation': run.current_operation,  # Detailed progress: "Processing doc 3 with extract_entities_spacy (5/21 operations)"
            'progress_percentage': progress_percentage,
            'error_message': run.error_message
        }

        # Add stage completion flags
        response['stage_completed'] = {
            'analyze_experiment': run.experiment_goal is not None,
            'recommend_strategy': run.recommended_strategy is not None,
            'human_review': run.strategy_approved or False,
            'execute_strategy': run.processing_results is not None,
            'synthesize_experiment': run.cross_document_insights is not None
        }

        # If waiting for review, include strategy details
        if run.status == 'reviewing':
            response['awaiting_user_approval'] = True
            response['recommended_strategy'] = run.recommended_strategy
            response['strategy_reasoning'] = run.strategy_reasoning
            response['confidence'] = run.confidence
            response['experiment_goal'] = run.experiment_goal

        # If completed, include summary
        if run.status == 'completed':
            response['completed_at'] = run.completed_at.isoformat() if run.completed_at else None
            response['duration_seconds'] = (
                (run.completed_at - run.started_at).total_seconds()
                if run.completed_at and run.started_at else None
            )

        return jsonify(response), 200

    except Exception as e:
        logger.error(f"Error getting orchestration status for run {run_id}: {e}", exc_info=True)
        return jsonify({
            'error': str(e)
        }), 500


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
        if generate_periods:
            experiment = run.experiment
            if experiment and experiment.experiment_type == 'temporal_evolution':
                # Check if periods already exist
                from app.models.temporal_experiment import DocumentTemporalMetadata
                existing_meta = DocumentTemporalMetadata.query.filter_by(
                    experiment_id=experiment.id
                ).first()

                # Also check configuration
                config = experiment.configuration or {}
                has_named_periods = bool(config.get('named_periods'))

                if not existing_meta and not has_named_periods:
                    # Create one temporal period per document based on publication date
                    from app.models import Document
                    documents = experiment.documents

                    for doc in documents:
                        if doc.publication_date:
                            year = doc.publication_date.year
                            period_name = f"{year}"

                            meta = DocumentTemporalMetadata(
                                document_id=doc.id,
                                experiment_id=experiment.id,
                                temporal_period=period_name,
                                temporal_start_year=year,
                                temporal_end_year=year,
                                publication_year=year,
                                extraction_method='auto_generated'
                            )
                            db.session.add(meta)

                    db.session.flush()
                    logger.info(f"Generated temporal metadata for {len(documents)} documents in experiment {experiment.id}")

        # Store approval info
        run.strategy_approved = True
        run.modified_strategy = data.get('modified_strategy')
        run.review_notes = data.get('review_notes')
        run.reviewed_by = current_user.id
        run.reviewed_at = datetime.utcnow()
        run.status = 'executing'
        run.current_stage = 'executing'
        db.session.commit()

        # Execute processing phase in background thread
        import threading
        from flask import current_app

        app = current_app._get_current_object()
        run_id_for_thread = run.id
        modified_strategy = data.get('modified_strategy')
        review_notes = data.get('review_notes')
        reviewer_id = current_user.id

        def run_processing():
            with app.app_context():
                try:
                    workflow_executor.execute_processing_phase(
                        run_id=run_id_for_thread,
                        modified_strategy=modified_strategy,
                        review_notes=review_notes,
                        reviewer_id=reviewer_id
                    )
                except Exception as e:
                    logger.error(f"Processing phase failed for run {run_id_for_thread}: {e}", exc_info=True)

        thread = threading.Thread(target=run_processing, daemon=True)
        thread.start()

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


@experiments_bp.route('/<int:experiment_id>/orchestration/llm-results/<uuid:run_id>')
def llm_orchestration_results(experiment_id, run_id):
    """
    Display LLM orchestration results for an experiment

    Shows:
    - Cross-document insights
    - Term evolution analysis
    - Processing summary
    - PROV-O provenance
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

        # Calculate metrics
        duration = None
        if run.completed_at and run.started_at:
            duration_seconds = (run.completed_at - run.started_at).total_seconds()
            duration = {
                'seconds': duration_seconds,
                'formatted': f"{int(duration_seconds // 60)}m {int(duration_seconds % 60)}s"
            }

        # Count operations
        total_operations = 0
        if run.processing_results:
            for doc_results in run.processing_results.values():
                total_operations += len(doc_results)

        # Get document count and build document lookup
        from app.models import Document
        experiment_docs = Document.query.filter_by(experiment_id=experiment_id).all()
        document_count = len(experiment_docs)

        # Build document lookup dict for template (maps string ID to document info)
        document_lookup = {}
        for doc in experiment_docs:
            document_lookup[str(doc.id)] = {
                'id': doc.id,
                'uuid': str(doc.uuid),
                'title': doc.title,
                'authors': doc.authors,
                'publication_date': doc.publication_date.strftime('%Y') if doc.publication_date else None,
                'version_number': doc.version_number,
                'version_type': doc.version_type,
            }

        # Convert markdown to HTML for insights
        insights_html = None
        if run.cross_document_insights:
            insights_html = markdown.markdown(
                run.cross_document_insights,
                extensions=['fenced_code', 'tables', 'nl2br']
            )

        evolution_html = None
        if run.term_evolution_analysis:
            evolution_html = markdown.markdown(
                run.term_evolution_analysis,
                extensions=['fenced_code', 'tables', 'nl2br']
            )

        return render_template(
            'experiments/llm_orchestration_results.html',
            experiment=experiment,
            run=run,
            duration=duration,
            total_operations=total_operations,
            document_count=document_count,
            document_lookup=document_lookup,
            insights_html=insights_html,
            evolution_html=evolution_html
        )

    except Exception as e:
        # Re-raise HTTPExceptions (like abort(404)) without catching them
        from werkzeug.exceptions import HTTPException
        if isinstance(e, HTTPException):
            raise
        logger.error(f"Error displaying LLM orchestration results: {e}", exc_info=True)
        from flask import abort
        abort(500)


@experiments_bp.route('/<int:experiment_id>/orchestration/llm-provenance/<uuid:run_id>')
def download_llm_provenance(experiment_id, run_id):
    """
    Download PROV-O provenance JSON for LLM orchestration run
    """
    try:
        run = ExperimentOrchestrationRun.query.get(run_id)
        if not run or run.experiment_id != experiment_id:
            return jsonify({'error': 'Orchestration run not found'}), 404

        # Build PROV-O structure
        provenance = {
            "@context": "http://www.w3.org/ns/prov",
            "@type": "prov:Bundle",
            "prov:generatedAtTime": run.started_at.isoformat() if run.started_at else None,
            "experiment": {
                "@id": f"experiment:{experiment_id}",
                "@type": "prov:Entity",
                "prov:type": "Experiment"
            },
            "orchestration_run": {
                "@id": f"run:{run.id}",
                "@type": "prov:Activity",
                "prov:startedAtTime": run.started_at.isoformat() if run.started_at else None,
                "prov:endedAtTime": run.completed_at.isoformat() if run.completed_at else None,
                "prov:used": f"experiment:{experiment_id}",
                "status": run.status,
                "confidence": run.confidence
            },
            "strategy": {
                "@id": f"strategy:{run.id}",
                "@type": "prov:Entity",
                "prov:wasGeneratedBy": f"run:{run.id}",
                "recommended_strategy": run.recommended_strategy,
                "modified_strategy": run.modified_strategy,
                "reasoning": run.strategy_reasoning
            },
            "execution_trace": run.execution_trace or [],
            "results": {
                "@id": f"results:{run.id}",
                "@type": "prov:Entity",
                "prov:wasGeneratedBy": f"run:{run.id}",
                "cross_document_insights": run.cross_document_insights,
                "term_evolution_analysis": run.term_evolution_analysis
            }
        }

        return jsonify(provenance), 200

    except Exception as e:
        logger.error(f"Error generating provenance: {e}", exc_info=True)
        return jsonify({'error': 'Failed to generate provenance data'}), 500
