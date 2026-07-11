"""Experiment-scoped definition result read model."""

from app import db
from app.models.experiment import Experiment
from app.models.experiment_document import ExperimentDocument
from app.models.experiment_processing import (
    ExperimentDocumentProcessing,
    ProcessingArtifact,
)
from app.models.processing_job import ProcessingJob
from app.services.base_service import NotFoundError


class ExperimentDefinitionResultsService:
    """Normalize canonical and legacy definition results for one experiment."""

    @classmethod
    def get_context(cls, experiment_id):
        experiment = db.session.get(Experiment, experiment_id)
        if not experiment:
            raise NotFoundError(f'Experiment {experiment_id} not found')
        documents = cls._latest_documents(experiment_id)
        document_ids = [document.id for document in documents]
        lookup = {document.id: document for document in documents}
        definitions = []
        grouped = {}

        artifacts = cls._canonical_artifacts(experiment_id, document_ids)
        canonical_document_ids = set()
        for artifact in artifacts:
            canonical_document_ids.add(artifact.document_id)
            definition = cls._artifact_definition(
                artifact,
                lookup.get(artifact.document_id),
            )
            cls._append(definitions, grouped, definition, lookup)

        manual_count = 0
        legacy_ids = [
            document_id for document_id in document_ids
            if document_id not in canonical_document_ids
        ]
        for job in cls._legacy_jobs(legacy_ids):
            result_data = job.get_result_data()
            if not isinstance(result_data, dict):
                continue
            job_definitions = result_data.get('definitions')
            if not isinstance(job_definitions, list):
                continue
            for index, item in enumerate(job_definitions):
                definition = cls._legacy_definition(
                    job,
                    index,
                    item,
                    lookup.get(job.document_id),
                )
                cls._append(definitions, grouped, definition, lookup)
                manual_count += 1

        definitions.sort(key=lambda item: (
            item.get('document_year') or 9999,
            item.get('term', '').lower(),
            item['id'],
        ))
        return {
            'experiment': experiment,
            'documents': documents,
            'definitions': definitions,
            'definitions_by_document': grouped,
            'total_definitions': len(definitions),
            'auto_count': len(artifacts),
            'manual_count': manual_count,
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
            ProcessingArtifact.artifact_type == 'term_definition',
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
            ProcessingJob.job_type == 'definition_extraction',
            ProcessingJob.status == 'completed',
        ).order_by(ProcessingJob.created_at, ProcessingJob.id).all()

    @classmethod
    def _artifact_definition(cls, artifact, document):
        content = artifact.get_content()
        metadata = artifact.get_metadata()
        metadata = metadata if isinstance(metadata, dict) else {}
        if isinstance(content, str):
            values = {
                'term': '',
                'definition': content,
                'pattern': 'unknown',
                'confidence': 0,
                'sentence': '',
            }
        elif isinstance(content, dict):
            values = {
                'term': content.get('term', ''),
                'definition': content.get('definition', ''),
                'pattern': content.get('pattern', 'unknown'),
                'confidence': content.get('confidence', 0),
                'sentence': content.get('sentence', ''),
            }
        else:
            values = {
                'term': '',
                'definition': '',
                'pattern': 'unknown',
                'confidence': 0,
                'sentence': '',
            }
        method = metadata.get('method', 'pattern_matching')
        return {
            'id': f'artifact_{artifact.id}',
            **values,
            'start_char': metadata.get('start_char'),
            'end_char': metadata.get('end_char'),
            'method': method,
            'source': (
                'zeroshot'
                if 'zero_shot' in method.lower() or 'zeroshot' in method.lower()
                else 'pattern'
            ),
            **cls._document_fields(artifact.document_id, document),
        }

    @classmethod
    def _legacy_definition(cls, job, index, item, document):
        item = item if isinstance(item, dict) else {'definition': str(item)}
        return {
            'id': f'job_{job.id}_{index}',
            'term': item.get('term', ''),
            'definition': item.get('definition', ''),
            'pattern': item.get('pattern', 'unknown'),
            'confidence': item.get('confidence', 0),
            'sentence': item.get('sentence', ''),
            'start_char': item.get('start_char'),
            'end_char': item.get('end_char'),
            'method': item.get('method', 'manual'),
            'source': 'manual',
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
    def _append(definitions, grouped, definition, lookup):
        definitions.append(definition)
        document_id = definition['document_id']
        grouped.setdefault(document_id, {
            'document': lookup.get(document_id),
            'definitions': [],
        })['definitions'].append(definition)
