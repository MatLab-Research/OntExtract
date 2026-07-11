"""Deterministic read models for the temporal visualization interface."""

import json
from statistics import mean

from app import db
from app.models.document import Document
from app.models.experiment import Experiment
from app.models.experiment_document import ExperimentDocument
from app.models.temporal_experiment import (
    DocumentTemporalMetadata,
    SemanticShiftAnalysis,
)
from app.models.term import Term
from app.services.base_service import NotFoundError, ValidationError


class TemporalVisualizationService:
    """Build temporal visualization data without synthetic analysis values."""

    @classmethod
    def get_experiment_data(cls, experiment_id):
        experiment = cls._experiment(experiment_id)
        documents, references = cls._experiment_content(experiment)
        config = cls._configuration(experiment)
        shifts = SemanticShiftAnalysis.query.filter_by(
            experiment_id=experiment.id
        ).all()
        return {
            'experiment': {
                'id': experiment.id,
                'name': experiment.name,
                'description': experiment.description,
                'created_at': (
                    experiment.created_at.isoformat()
                    if experiment.created_at else None
                ),
                'experiment_type': experiment.experiment_type,
            },
            'documents': [
                cls._document_summary(document, experiment.id)
                for document in documents
            ],
            'references': [
                cls._document_summary(reference, experiment.id)
                for reference in references
            ],
            'temporal_data': {
                'terms_tracked': cls._terms(experiment, config),
                'time_periods': (
                    config.get('time_periods')
                    or config.get('named_periods')
                    or []
                ),
                'analysis_results': [shift.to_dict() for shift in shifts],
            },
        }

    @classmethod
    def analyze(cls, data):
        if not isinstance(data, dict):
            raise ValidationError('JSON payload required')
        term = data.get('term', '')
        term = term.strip() if isinstance(term, str) else ''
        if not term:
            raise ValidationError('Term is required')
        start_year, end_year = cls._time_range(
            data.get('time_range', '2000-2024')
        )
        period_length = cls._period_length(data.get('period_length', 5))
        periods = cls._periods(start_year, end_year, period_length)

        experiment = None
        documents = []
        references = []
        experiment_id = data.get('experiment_id')
        if experiment_id not in (None, ''):
            try:
                experiment_id = int(experiment_id)
            except (TypeError, ValueError) as exc:
                raise ValidationError('Invalid experiment_id') from exc
            experiment = cls._experiment(experiment_id)
            documents, references = cls._experiment_content(experiment)

        grouped = {period['id']: [] for period in periods}
        distinct_documents = {}
        for document in documents + references:
            year = cls._document_year(
                document,
                experiment.id if experiment else None,
            )
            if year is None:
                continue
            for period in periods:
                if period['start_year'] <= year <= period['end_year']:
                    grouped[period['id']].append(
                        cls._timeline_document(document, year)
                    )
                    distinct_documents[document.id] = document
                    break

        shifts = cls._semantic_shifts(experiment, term)
        confidences = [
            float(shift.confidence)
            for shift in shifts
            if shift.confidence is not None
        ]
        confidence = mean(confidences) if confidences else None
        findings = [shift.description for shift in shifts if shift.description]
        if not findings:
            findings = [
                f'No stored semantic shift analyses found for "{term}".'
            ]

        return {
            'success': True,
            'term': term,
            'time_range': f'{start_year}-{end_year}',
            'period_length': period_length,
            'periods': periods,
            'documents_by_period': grouped,
            'analysis_results': {
                'semantic_drift': None,
                'context_stability': None,
                'documents_analyzed': len(distinct_documents),
                'confidence_score': (
                    f'{round(confidence * 100)}%' if confidence is not None else None
                ),
                'key_findings': findings,
                'stored_shift_count': len(shifts),
                'metrics_available': {
                    'semantic_drift': False,
                    'context_stability': False,
                    'confidence_score': confidence is not None,
                },
            },
        }

    @classmethod
    def get_document_details(cls, document_id):
        document = db.session.get(Document, document_id)
        if not document:
            raise NotFoundError(f'Document {document_id} not found')
        return {
            'id': document.id,
            'title': document.title,
            'type': document.document_type or 'unknown',
            'year': cls._document_year(document),
            'metadata': document.source_metadata or {},
            'content_preview': (document.content or '')[:500],
            'file_path': document.file_path,
            'created_at': (
                document.created_at.isoformat() if document.created_at else None
            ),
        }

    @classmethod
    def list_temporal_experiments(cls):
        experiments = Experiment.query.filter_by(
            experiment_type='temporal_evolution'
        ).order_by(Experiment.created_at.desc()).all()
        serialized = []
        for experiment in experiments:
            documents, references = cls._experiment_content(experiment)
            serialized.append({
                'id': experiment.id,
                'name': experiment.name,
                'description': experiment.description,
                'created_at': (
                    experiment.created_at.isoformat()
                    if experiment.created_at else None
                ),
                'status': experiment.status or 'unknown',
                'document_count': len(documents),
                'reference_count': len(references),
            })
        return {'experiments': serialized, 'total_count': len(serialized)}

    @classmethod
    def _experiment_content(cls, experiment):
        canonical_ids = {
            association.document_id
            for association in ExperimentDocument.query.filter_by(
                experiment_id=experiment.id
            ).all()
        }
        compatibility_documents = list(experiment.documents)
        reference_documents = list(experiment.references)
        reference_ids = {reference.id for reference in reference_documents}
        document_ids = canonical_ids | {
            document.id for document in compatibility_documents
        }
        document_ids -= reference_ids
        documents = (
            Document.query.filter(Document.id.in_(document_ids)).all()
            if document_ids else []
        )
        documents.sort(key=lambda document: document.id)
        reference_documents.sort(key=lambda document: document.id)
        return documents, reference_documents

    @classmethod
    def _document_summary(cls, document, experiment_id):
        return {
            'id': document.id,
            'title': document.title,
            'type': document.document_type or 'unknown',
            'year': cls._document_year(document, experiment_id),
            'metadata': document.source_metadata or {},
        }

    @staticmethod
    def _timeline_document(document, year):
        type_config = {
            'reference': ('fa-book', 'doc-type-historical'),
            'document': ('fa-file-alt', 'doc-type-technical'),
        }
        icon, css_class = type_config.get(
            document.document_type,
            ('fa-file', 'doc-type-technical'),
        )
        return {
            'id': document.id,
            'title': document.title,
            'year': year,
            'type': document.document_type or 'unknown',
            'icon': icon,
            'class': css_class,
            'citations': None,
            'relevance': None,
        }

    @staticmethod
    def _document_year(document, experiment_id=None):
        if document.publication_date:
            return document.publication_date.year
        query = DocumentTemporalMetadata.query.filter_by(document_id=document.id)
        if experiment_id is not None:
            scoped = query.filter_by(experiment_id=experiment_id).first()
            if scoped and scoped.publication_year:
                return scoped.publication_year
        metadata = query.order_by(DocumentTemporalMetadata.created_at.desc()).first()
        return metadata.publication_year if metadata else None

    @staticmethod
    def _semantic_shifts(experiment, term):
        if not experiment:
            return []
        query = SemanticShiftAnalysis.query.filter_by(experiment_id=experiment.id)
        term_record = Term.query.filter(
            db.func.lower(Term.term_text) == term.lower()
        ).first()
        if term_record:
            query = query.filter_by(term_id=term_record.id)
        elif experiment.term and experiment.term.term_text.lower() != term.lower():
            return []
        return query.order_by(SemanticShiftAnalysis.created_at).all()

    @staticmethod
    def _terms(experiment, config):
        terms = config.get('target_terms', [])
        if not terms and experiment.term:
            terms = [experiment.term.term_text]
        return terms

    @staticmethod
    def _configuration(experiment):
        if isinstance(experiment.configuration, dict):
            return dict(experiment.configuration)
        if not experiment.configuration:
            return {}
        try:
            parsed = json.loads(experiment.configuration)
            return parsed if isinstance(parsed, dict) else {}
        except (json.JSONDecodeError, TypeError):
            return {}

    @staticmethod
    def _time_range(value):
        if not isinstance(value, str):
            raise ValidationError('Invalid time range format. Use YYYY-YYYY')
        parts = value.split('-')
        if len(parts) != 2:
            raise ValidationError('Invalid time range format. Use YYYY-YYYY')
        try:
            start_year, end_year = (int(part) for part in parts)
        except ValueError as exc:
            raise ValidationError(
                'Invalid time range format. Use YYYY-YYYY'
            ) from exc
        if start_year > end_year:
            raise ValidationError('Start year must not exceed end year')
        if start_year < 1 or end_year > 9999:
            raise ValidationError('Years must be between 1 and 9999')
        return start_year, end_year

    @staticmethod
    def _period_length(value):
        try:
            period_length = int(value)
        except (TypeError, ValueError) as exc:
            raise ValidationError('period_length must be a positive integer') from exc
        if period_length <= 0:
            raise ValidationError('period_length must be a positive integer')
        return period_length

    @staticmethod
    def _periods(start_year, end_year, period_length):
        periods = []
        current = start_year
        while current <= end_year:
            period_end = min(current + period_length - 1, end_year)
            periods.append({
                'id': f'period-{current}',
                'label': f'{current}-{period_end}',
                'start_year': current,
                'end_year': period_end,
            })
            current += period_length
        return periods

    @staticmethod
    def _experiment(experiment_id):
        experiment = db.session.get(Experiment, experiment_id)
        if not experiment:
            raise NotFoundError(f'Experiment {experiment_id} not found')
        return experiment
