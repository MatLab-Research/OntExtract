"""Experiment duplication, completion, and synchronous execution workflows."""

import json
from datetime import datetime

from app import db
from app.models.document import Document
from app.models.experiment import (
    Experiment,
    experiment_references,
)
from app.models.experiment_document import ExperimentDocument
from app.models.experiment_processing import ExperimentDocumentProcessing
from app.models.user import User
from app.services.base_service import NotFoundError, PermissionError, ValidationError
from app.services.experiment_domain_comparison import DomainComparisonService
from app.services.text_processing import TextProcessingService


class ExperimentLifecycleService:
    """Coordinate experiment lifecycle transitions against canonical ownership."""

    def __init__(
        self,
        domain_service_factory=DomainComparisonService,
        text_service_factory=TextProcessingService,
        clock=None,
    ):
        self.domain_service_factory = domain_service_factory
        self.text_service_factory = text_service_factory
        self.clock = clock or datetime.utcnow

    @classmethod
    def duplicate(cls, experiment_id, new_owner_id):
        original = cls._experiment(experiment_id)
        new_experiment = Experiment(
            name=f'{original.name} (Copy)',
            description=original.description,
            experiment_type=original.experiment_type,
            configuration=original.configuration,
            status='draft',
            user_id=new_owner_id,
            term_id=original.term_id,
        )
        try:
            db.session.add(new_experiment)
            db.session.flush()
            cls._copy_documents(original, new_experiment)
            cls._copy_references(original.id, new_experiment.id)
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise
        return new_experiment

    @classmethod
    def mark_complete(cls, experiment_id, actor_id):
        experiment = cls._owned_experiment(experiment_id, actor_id)
        if experiment.status != 'draft':
            raise ValidationError(
                f'Cannot mark {experiment.status} experiment as complete. '
                'Only draft experiments can be marked complete.'
            )
        completed_count = db.session.query(
            ExperimentDocumentProcessing.id
        ).join(
            ExperimentDocument,
            ExperimentDocumentProcessing.experiment_document_id
            == ExperimentDocument.id,
        ).filter(
            ExperimentDocument.experiment_id == experiment_id,
            ExperimentDocumentProcessing.status == 'completed',
        ).count()
        if completed_count == 0:
            raise ValidationError(
                'No processing results found. Process at least one document '
                'before marking complete.'
            )
        experiment.status = 'completed'
        experiment.completed_at = datetime.utcnow()
        db.session.commit()
        return experiment

    def run(self, experiment_id, actor_id):
        experiment = self._owned_experiment(experiment_id, actor_id)
        if not self._can_run(experiment):
            raise ValidationError('Experiment cannot be run in its current state')
        experiment.status = 'running'
        experiment.started_at = self.clock()
        db.session.commit()
        try:
            results, summary = self._run_analysis(experiment)
            experiment.status = 'completed'
            experiment.completed_at = self.clock()
            experiment.results_summary = summary
            experiment.results = json.dumps(results)
            db.session.commit()
            return experiment
        except Exception:
            try:
                failed = db.session.get(Experiment, experiment_id)
            except Exception:
                db.session.rollback()
                failed = db.session.get(Experiment, experiment_id)
            if failed:
                failed.status = 'error'
                db.session.commit()
            raise

    def _run_analysis(self, experiment):
        if experiment.experiment_type == 'domain_comparison':
            return self.domain_service_factory().run(
                experiment,
                self.text_service_factory(),
            )
        document_count, total_words = self._document_stats(experiment)
        results = {
            'document_count': document_count,
            'total_words': total_words,
            'experiment_type': experiment.experiment_type,
            'timestamp': self.clock().isoformat(),
        }
        summary = (
            f'Analyzed {document_count} documents with {total_words} total words.'
        )
        return results, summary

    @staticmethod
    def _can_run(experiment):
        if experiment.status not in ('draft', 'completed', 'error'):
            return False
        if experiment.experiment_type == 'domain_comparison':
            return experiment.get_reference_count() > 0
        return (
            ExperimentDocument.query.filter_by(
                experiment_id=experiment.id
            ).count() > 0
            or experiment.get_document_count() > 0
        )

    @staticmethod
    def _document_stats(experiment):
        associations = ExperimentDocument.query.filter_by(
            experiment_id=experiment.id
        ).all()
        if associations:
            document_ids = {association.document_id for association in associations}
            documents = Document.query.filter(Document.id.in_(document_ids)).all()
            return len(documents), sum(document.word_count or 0 for document in documents)
        return experiment.get_document_count(), experiment.get_total_word_count()

    @staticmethod
    def _copy_documents(original, new_experiment):
        canonical = ExperimentDocument.query.filter_by(
            experiment_id=original.id
        ).all()
        document_ids = {association.document_id for association in canonical}
        document_ids.update(document.id for document in original.documents)
        documents = {
            document.id: document
            for document in Document.query.filter(Document.id.in_(document_ids)).all()
        } if document_ids else {}
        for document_id in sorted(document_ids):
            db.session.add(ExperimentDocument(
                experiment_id=new_experiment.id,
                document_id=document_id,
                processing_status='pending',
            ))
            document = documents.get(document_id)
            if document is not None:
                new_experiment.documents.append(document)

    @staticmethod
    def _copy_references(original_id, new_id):
        rows = db.session.execute(
            db.select(experiment_references).where(
                experiment_references.c.experiment_id == original_id
            )
        ).mappings().all()
        for row in rows:
            db.session.execute(experiment_references.insert().values(
                experiment_id=new_id,
                reference_id=row['reference_id'],
                include_in_analysis=row['include_in_analysis'],
                notes=row['notes'],
            ))

    @staticmethod
    def _experiment(experiment_id):
        experiment = db.session.get(Experiment, experiment_id)
        if not experiment:
            raise NotFoundError(f'Experiment {experiment_id} not found')
        return experiment

    @classmethod
    def _owned_experiment(cls, experiment_id, actor_id):
        experiment = cls._experiment(experiment_id)
        actor = db.session.get(User, actor_id)
        if not actor or not actor.can_edit_resource(experiment):
            raise PermissionError('Permission denied')
        return experiment
