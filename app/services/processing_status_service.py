"""Read models for processing dashboards and legacy job diagnostics."""

import json
import os
import tempfile
from uuid import UUID

from sqlalchemy import func

from app import db
from app.models.document import Document
from app.models.experiment import Experiment
from app.models.experiment_document import ExperimentDocument
from app.models.experiment_processing import ExperimentDocumentProcessing
from app.models.processing_job import ProcessingJob
from app.services.base_service import NotFoundError, ValidationError


class ProcessingStatusService:
    """Query and serialize live and legacy processing status."""

    @classmethod
    def get_dashboard_context(cls):
        return {
            'stats': {
                'documents': cls._status_counts(Document),
                'processing_operations': cls._status_counts(
                    ExperimentDocumentProcessing,
                    error_status='failed',
                ),
            },
            'recent_documents': (
                db.session.query(Document)
                .join(
                    ExperimentDocument,
                    Document.id == ExperimentDocument.document_id,
                )
                .order_by(ExperimentDocument.added_at.desc())
                .limit(10)
                .all()
            ),
            'recent_processing': (
                db.session.query(ExperimentDocumentProcessing)
                .join(
                    ExperimentDocument,
                    ExperimentDocumentProcessing.experiment_document_id
                    == ExperimentDocument.id,
                )
                .join(Document, ExperimentDocument.document_id == Document.id)
                .join(
                    Experiment,
                    ExperimentDocument.experiment_id == Experiment.id,
                )
                .order_by(ExperimentDocumentProcessing.created_at.desc())
                .limit(10)
                .all()
            ),
        }

    @staticmethod
    def _status_counts(model, error_status='error'):
        return {
            'total': db.session.query(func.count(model.id)).scalar() or 0,
            'uploaded': (
                db.session.query(func.count(model.id))
                .filter(model.status == 'uploaded')
                .scalar() or 0
            ) if model is Document else 0,
            'processing': (
                db.session.query(func.count(model.id))
                .filter(model.status == 'processing')
                .scalar() or 0
            ) if model is Document else 0,
            'pending': (
                db.session.query(func.count(model.id))
                .filter(model.status == 'pending')
                .scalar() or 0
            ) if model is not Document else 0,
            'running': (
                db.session.query(func.count(model.id))
                .filter(model.status == 'running')
                .scalar() or 0
            ) if model is not Document else 0,
            'completed': (
                db.session.query(func.count(model.id))
                .filter(model.status == 'completed')
                .scalar() or 0
            ),
            'error' if model is Document else 'failed': (
                db.session.query(func.count(model.id))
                .filter(model.status == error_status)
                .scalar() or 0
            ),
        }

    @staticmethod
    def get_job_list_context():
        processing_operations = (
            db.session.query(ExperimentDocumentProcessing)
            .join(
                ExperimentDocument,
                ExperimentDocumentProcessing.experiment_document_id
                == ExperimentDocument.id,
            )
            .join(Document, ExperimentDocument.document_id == Document.id)
            .join(
                Experiment,
                ExperimentDocument.experiment_id == Experiment.id,
            )
            .order_by(ExperimentDocumentProcessing.created_at.desc())
            .limit(100)
            .all()
        )
        legacy_jobs = (
            db.session.query(ProcessingJob)
            .order_by(ProcessingJob.created_at.desc())
            .limit(50)
            .all()
        )
        return {
            'processing_operations': processing_operations,
            'legacy_jobs': legacy_jobs,
        }

    @classmethod
    def get_langextract_details(cls, job_id):
        job = db.session.get(ProcessingJob, job_id)
        if not job:
            raise NotFoundError(f'Processing job {job_id} not found')
        if job.job_type != 'langextract_segmentation':
            raise ValidationError(
                'This endpoint is only for LangExtract segmentation jobs'
            )

        parameters = job.get_parameters()
        results = job.get_result_data() or {}
        response = {
            'success': True,
            'job_info': {
                'job_id': job.id,
                'document_id': job.document_id,
                'status': job.status,
                'created_at': (
                    job.created_at.isoformat() if job.created_at else None
                ),
                'processing_time': job.processing_time,
            },
            'parameters': parameters,
            'results': results,
            'summary': {
                'key_concepts_extracted': parameters.get(
                    'key_concepts_extracted', 0
                ),
                'temporal_markers_found': parameters.get(
                    'temporal_markers_found', 0
                ),
                'domain_indicators_identified': parameters.get(
                    'domain_indicators_identified', 0
                ),
                'segments_created': parameters.get('segments_created', 0),
                'character_level_positions': parameters.get(
                    'character_level_positions', True
                ),
                'prov_o_tracking_complete': parameters.get(
                    'prov_o_tracking_complete', False
                ),
            },
        }
        analysis_id = (
            parameters.get('langextract_analysis_id')
            or results.get('analysis_id')
        )
        if analysis_id:
            cls._add_detailed_analysis(response, analysis_id)
        return response

    @staticmethod
    def _add_detailed_analysis(response, analysis_id):
        analysis_file = os.path.join(
            tempfile.gettempdir(),
            f'langextract_analysis_{analysis_id}.json',
        )
        if not os.path.exists(analysis_file):
            return
        try:
            with open(analysis_file, 'r') as file_handle:
                analysis = json.load(file_handle)
            response['detailed_analysis'] = {
                'key_concepts': analysis.get('key_concepts', []),
                'temporal_markers': analysis.get('temporal_markers', []),
                'domain_indicators': analysis.get('domain_indicators', []),
                'structural_segments': analysis.get('structural_segments', []),
                'semantic_segments': analysis.get('semantic_segments', []),
                'analysis_metadata': analysis.get('metadata', {}),
            }
        except Exception as exc:
            response['detailed_analysis_error'] = str(exc)

    @staticmethod
    def get_job_status(job_id):
        job = db.session.get(ProcessingJob, job_id)
        if not job:
            raise NotFoundError(f'Processing job {job_id} not found')
        parameters = job.get_parameters()
        response = {
            'success': True,
            'job_id': job.id,
            'status': job.status,
            'created_at': job.created_at.isoformat() if job.created_at else None,
            'completed_at': (
                job.completed_at.isoformat() if job.completed_at else None
            ),
            'parameters': parameters,
            'result_data': job.get_result_data(),
        }
        if 'current_chunk' in parameters and 'total_chunks' in parameters:
            total = parameters['total_chunks']
            response['progress'] = {
                'current': parameters['current_chunk'],
                'total': total,
                'message': parameters.get('progress_message', ''),
                'percentage': int(
                    (parameters['current_chunk'] / total) * 100
                ) if total > 0 else 0,
            }
        return response

    @classmethod
    def get_document_processing_jobs(cls, document_uuid):
        try:
            normalized_uuid = UUID(str(document_uuid))
        except (TypeError, ValueError, AttributeError):
            raise NotFoundError(f'Document {document_uuid} not found')

        document = Document.query.filter_by(uuid=normalized_uuid).first()
        if not document:
            raise NotFoundError(f'Document {document_uuid} not found')

        jobs = ProcessingJob.query.filter_by(document_id=document.id).all()
        for job in ProcessingJob.query.filter(
            ProcessingJob.document_id != document.id
        ).all():
            if job.get_parameters().get('original_document_id') == document.id:
                jobs.append(job)
        jobs.sort(
            key=lambda job: (job.created_at is None, job.created_at),
            reverse=True,
        )

        grouped_jobs = {}
        for job in jobs:
            method = cls._job_method(job)
            key = f'{job.job_type}:{method}'
            grouped_jobs.setdefault(key, {
                'latest': job,
                'method': method,
                'all_jobs': [],
            })['all_jobs'].append(job)

        operations = []
        for group in grouped_jobs.values():
            latest = group['latest']
            all_jobs = group['all_jobs']
            count = len(all_jobs)
            operations.append({
                'id': latest.id,
                'processing_type': latest.job_type,
                'processing_method': group['method'],
                'status': latest.status,
                'created_at': (
                    latest.created_at.isoformat() if latest.created_at else None
                ),
                'completed_at': (
                    latest.completed_at.isoformat()
                    if latest.completed_at else None
                ),
                'error_message': latest.error_message,
                'run_count': count,
                'has_history': count > 1,
                'all_job_ids': [job.id for job in all_jobs] if count > 1 else [],
            })
        operations.sort(
            key=lambda operation: operation['created_at'] or '',
            reverse=True,
        )
        return {'success': True, 'processing_operations': operations}

    @staticmethod
    def _job_method(job):
        parameters = job.get_parameters()
        if job.job_type in ('generate_embeddings', 'segment_document'):
            return parameters.get('method', 'default')
        if job.job_type == 'extract_entities':
            entity_types = parameters.get('entity_types', [])
            return f'{len(entity_types)} types' if entity_types else 'default'
        if job.job_type == 'analyze_metadata':
            return 'auto'
        if job.job_type == 'enhanced_processing':
            if parameters.get('extract_terms') and parameters.get('enrich_with_oed'):
                return 'terms+OED'
            if parameters.get('extract_terms'):
                return 'terms'
        return 'default'
