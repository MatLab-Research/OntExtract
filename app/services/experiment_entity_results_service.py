"""Experiment-scoped entity result read model."""

from app import db
from app.models.experiment import Experiment
from app.models.experiment_document import ExperimentDocument
from app.models.experiment_processing import (
    ExperimentDocumentProcessing,
    ProcessingArtifact,
)
from app.models.extracted_entity import ExtractedEntity
from app.models.processing_job import ProcessingJob
from app.services.base_service import NotFoundError


class ExperimentEntityResultsService:
    """Normalize canonical and legacy entity results for one experiment."""

    @classmethod
    def get_context(cls, experiment_id):
        experiment = db.session.get(Experiment, experiment_id)
        if not experiment:
            raise NotFoundError(f'Experiment {experiment_id} not found')
        documents = cls._latest_documents(experiment_id)
        document_ids = [document.id for document in documents]
        lookup = {document.id: document for document in documents}
        entities = []
        by_type = {}
        by_document = {}

        artifacts = cls._canonical_artifacts(experiment_id, document_ids)
        canonical_document_ids = set()
        for artifact in artifacts:
            canonical_document_ids.add(artifact.document_id)
            cls._append(
                entities,
                by_type,
                by_document,
                cls._artifact_entity(
                    artifact,
                    lookup.get(artifact.document_id),
                ),
                lookup,
            )

        legacy_ids = [
            document_id for document_id in document_ids
            if document_id not in canonical_document_ids
        ]
        jobs = cls._legacy_jobs(legacy_ids)
        jobs_by_id = {job.id: job for job in jobs}
        if jobs_by_id:
            legacy_entities = ExtractedEntity.query.filter(
                ExtractedEntity.processing_job_id.in_(jobs_by_id)
            ).order_by(
                ExtractedEntity.created_at,
                ExtractedEntity.id,
            ).all()
            for entity in legacy_entities:
                job = jobs_by_id.get(entity.processing_job_id)
                if job:
                    cls._append(
                        entities,
                        by_type,
                        by_document,
                        cls._legacy_entity(
                            entity,
                            job,
                            lookup.get(job.document_id),
                        ),
                        lookup,
                    )

        entities.sort(key=lambda item: (
            item.get('document_year') or 9999,
            item.get('text', '').lower(),
            item['id'],
        ))
        return {
            'experiment': experiment,
            'documents': documents,
            'entities': entities,
            'entities_by_type': by_type,
            'entities_by_document': by_document,
            'total_entities': len(entities),
        }

    @staticmethod
    def _latest_documents(experiment_id):
        associations = ExperimentDocument.query.filter_by(
            experiment_id=experiment_id
        ).all()
        families = {}
        for association in associations:
            document = association.document
            root_id = document.source_document_id or document.id
            families.setdefault(root_id, []).append(document)
        documents = [
            max(
                family,
                key=lambda document: (
                    document.version_number or 0,
                    document.id,
                ),
            )
            for family in families.values()
        ]
        documents.sort(key=lambda document: document.id)
        return documents

    @staticmethod
    def _canonical_artifacts(experiment_id, document_ids):
        if not document_ids:
            return []
        return ProcessingArtifact.query.join(
            ExperimentDocumentProcessing,
            ProcessingArtifact.processing_id == ExperimentDocumentProcessing.id,
        ).join(
            ExperimentDocument,
            ExperimentDocumentProcessing.experiment_document_id
            == ExperimentDocument.id,
        ).filter(
            ExperimentDocument.experiment_id == experiment_id,
            ExperimentDocument.document_id.in_(document_ids),
            ExperimentDocumentProcessing.status == 'completed',
            ProcessingArtifact.artifact_type == 'extracted_entity',
        ).order_by(
            ProcessingArtifact.document_id,
            ProcessingArtifact.artifact_index,
            ProcessingArtifact.created_at,
        ).all()

    @staticmethod
    def _legacy_jobs(document_ids):
        if not document_ids:
            return []
        return ProcessingJob.query.filter(
            ProcessingJob.document_id.in_(document_ids),
            ProcessingJob.job_type == 'entity_extraction',
            ProcessingJob.status == 'completed',
        ).order_by(ProcessingJob.created_at, ProcessingJob.id).all()

    @classmethod
    def _artifact_entity(cls, artifact, document):
        content = artifact.get_content()
        metadata = artifact.get_metadata()
        metadata = metadata if isinstance(metadata, dict) else {}
        if isinstance(content, str):
            text = content
            entity_type = 'UNKNOWN'
            values = {}
        elif isinstance(content, dict):
            text = content.get('entity', content.get('text', ''))
            entity_type = content.get(
                'type',
                content.get('entity_type', content.get('label', 'UNKNOWN')),
            )
            values = content
        else:
            text = ''
            entity_type = 'UNKNOWN'
            values = {}
        return {
            'id': f'artifact_{artifact.id}',
            'text': text,
            'entity_type': entity_type or 'UNKNOWN',
            'start_position': values.get('start'),
            'end_position': values.get('end'),
            'confidence': values.get('confidence', 0.85),
            'context': values.get('context', ''),
            'source': metadata.get('method', 'spacy'),
            **cls._document_fields(artifact.document_id, document),
        }

    @classmethod
    def _legacy_entity(cls, entity, job, document):
        return {
            'id': f'old_{entity.id}',
            'text': entity.entity_text,
            'entity_type': entity.entity_type or 'UNKNOWN',
            'start_position': entity.start_position,
            'end_position': entity.end_position,
            'confidence': entity.confidence_score or 0,
            'context': entity.get_display_context(),
            'source': entity.extraction_method or 'manual',
            **cls._document_fields(job.document_id, document),
        }

    @staticmethod
    def _document_fields(document_id, document):
        return {
            'document_id': document_id,
            'document_title': (
                document.title if document else f'Document {document_id}'
            ),
            'document_uuid': str(document.uuid) if document else None,
            'document_year': (
                document.publication_date.year
                if document and document.publication_date else None
            ),
        }

    @staticmethod
    def _append(entities, by_type, by_document, entity, lookup):
        entities.append(entity)
        by_type.setdefault(entity['entity_type'], []).append(entity)
        document_id = entity['document_id']
        by_document.setdefault(document_id, {
            'document': lookup.get(document_id),
            'entities': [],
        })['entities'].append(entity)
