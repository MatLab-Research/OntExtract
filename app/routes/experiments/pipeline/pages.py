"""Experiment pipeline overview and document-processing pages."""

import logging

from flask import abort, flash, redirect, render_template, url_for
from flask_login import current_user, login_required

from app.services.base_service import (
    NotFoundError,
    PermissionError,
    ServiceError,
    ValidationError,
)
from app.services.pipeline_access_service import PipelineAccessService

from .. import experiments_bp
from . import pipeline_service


logger = logging.getLogger(__name__)


@experiments_bp.route('/<int:experiment_id>/document_pipeline')
@login_required
def document_pipeline(experiment_id):
    """Render the experiment document-processing overview."""
    try:
        data = pipeline_service.get_pipeline_overview(
            experiment_id,
            current_user.id,
        )
        return render_template(
            'experiments/document_pipeline.html',
            experiment=data['experiment'],
            documents=data['documents'],
            total_count=data['total_count'],
            completed_count=data['completed_count'],
            progress_percentage=data['progress_percentage'],
            orchestration_run=data.get('orchestration_run'),
        )
    except NotFoundError as exc:
        logger.warning(f"Experiment {experiment_id} not found: {exc}")
        abort(404)
    except PermissionError:
        abort(403)
    except ServiceError as exc:
        logger.error(
            f"Service error getting pipeline overview: {exc}",
            exc_info=True,
        )
        abort(500)


@experiments_bp.route('/<int:experiment_id>/process_document/<uuid:document_uuid>')
@login_required
def process_document(experiment_id, document_uuid):
    """Render processing controls for one experiment document."""
    try:
        document = PipelineAccessService.document_uuid_in_experiment(
            experiment_id,
            document_uuid,
            current_user.id,
        )
        data = pipeline_service.get_process_document_data(
            experiment_id,
            document.id,
            current_user.id,
        )
        operations = data['processing_operations']
        serialized_operations = [
            {
                'id': operation.id,
                'processing_type': operation.processing_type,
                'processing_method': operation.processing_method,
                'status': operation.status,
                'started_at': (
                    operation.started_at.isoformat()
                    if operation.started_at else None
                ),
                'completed_at': (
                    operation.completed_at.isoformat()
                    if operation.completed_at else None
                ),
            }
            for operation in operations
        ]
        return render_template(
            'experiments/process_document.html',
            experiment=data['experiment'],
            document=data['document'],
            experiment_document=data['experiment_document'],
            processing_operations=operations,
            processing_operations_serialized=serialized_operations,
            llm_operations=data.get('llm_operations', {}),
            processing_progress=data['processing_progress'],
            doc_index=data['doc_index'],
            total_docs=data['total_docs'],
            has_previous=data['has_previous'],
            has_next=data['has_next'],
            previous_doc_id=data['previous_doc_id'],
            next_doc_id=data['next_doc_id'],
            all_versions=data.get('all_versions', []),
            is_latest_version=data.get('is_latest_version', True),
            has_cleanup=data.get('has_cleanup', False),
        )
    except ValidationError as exc:
        flash(str(exc), 'error')
        return redirect(url_for(
            'experiments.document_pipeline',
            experiment_id=experiment_id,
        ))
    except NotFoundError as exc:
        logger.warning(
            f"Document {document.id} not found in experiment {experiment_id}: {exc}"
        )
        abort(404)
    except PermissionError:
        abort(403)
    except ServiceError as exc:
        logger.error(
            f"Service error getting process document data: {exc}",
            exc_info=True,
        )
        abort(500)
