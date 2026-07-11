"""Read model for experiment-level embedding result pages."""

from app import db
from app.models.document import Document
from app.models.experiment import Experiment
from app.models.experiment_document import ExperimentDocument
from app.models.experiment_orchestration_run import ExperimentOrchestrationRun
from app.models.experiment_processing import (
    ExperimentDocumentProcessing,
    ProcessingArtifact,
)
from app.models.processing_job import ProcessingJob
from app.services.base_service import NotFoundError


class ExperimentEmbeddingResultsService:
    """Build experiment-scoped embedding summaries from canonical storage."""

    @classmethod
    def get_context(cls, experiment_id):
        experiment = db.session.get(Experiment, experiment_id)
        if not experiment:
            raise NotFoundError(f'Experiment {experiment_id} not found')
        selected = cls._latest_experiment_documents(experiment_id)
        documents = [document for _, document in selected]
        orchestration_ids = cls._orchestration_document_ids(experiment_id)
        embeddings_info = []
        total_embeddings = 0

        for association, document in selected:
            info = cls._canonical_info(
                association,
                document,
                orchestration_ids,
            )
            if info is None:
                info = cls._legacy_info(experiment_id, document)
            if info is not None:
                embeddings_info.append(info)
                total_embeddings += info['chunk_count'] or 0

        embeddings_info.sort(key=lambda item: (
            item.get('document_year') or 9999,
            item.get('document_title') or '',
        ))
        return {
            'experiment': experiment,
            'documents': documents,
            'embeddings_info': embeddings_info,
            'total_embeddings': total_embeddings,
        }

    @staticmethod
    def _latest_experiment_documents(experiment_id):
        associations = ExperimentDocument.query.filter_by(
            experiment_id=experiment_id
        ).all()
        families = {}
        for association in associations:
            document = association.document
            root_id = document.source_document_id or document.id
            families.setdefault(root_id, []).append((association, document))
        selected = [
            max(
                family,
                key=lambda item: (item[1].version_number or 0, item[1].id),
            )
            for family in families.values()
        ]
        selected.sort(key=lambda item: item[1].id)
        return selected

    @classmethod
    def _canonical_info(cls, association, document, orchestration_ids):
        operation = ExperimentDocumentProcessing.query.filter_by(
            experiment_document_id=association.id,
            processing_type='embeddings',
            status='completed',
        ).order_by(ExperimentDocumentProcessing.created_at.desc()).first()
        if not operation:
            return None
        artifacts = ProcessingArtifact.query.filter_by(
            processing_id=operation.id,
            artifact_type='embedding_vector',
        ).order_by(ProcessingArtifact.artifact_index).all()
        if not artifacts:
            return None
        artifact = artifacts[0]
        metadata = artifact.get_metadata() or {}
        content = artifact.get_content() or {}
        root_id = document.source_document_id or document.id
        source = (
            'llm'
            if document.id in orchestration_ids or root_id in orchestration_ids
            else 'manual'
        )
        return cls._info(
            document=document,
            method=metadata.get('method', content.get('method', 'period_aware')),
            dimensions=metadata.get(
                'dimensions',
                len(content.get('vector', content.get('embedding', []))),
            ),
            chunk_count=len(artifacts),
            model=content.get('model', metadata.get('model', 'unknown')),
            source=source,
            created_at=artifact.created_at,
            metadata=metadata,
        )

    @classmethod
    def _legacy_info(cls, experiment_id, document):
        root_id = document.source_document_id or document.id
        family_versions = Document.query.filter_by(
            source_document_id=root_id
        ).all()
        candidate_ids = {document.id, root_id}
        candidate_ids.update(
            version.id
            for version in family_versions
            if version.experiment_id == experiment_id
        )
        job = ProcessingJob.query.filter(
            ProcessingJob.document_id.in_(candidate_ids),
            ProcessingJob.job_type == 'generate_embeddings',
            ProcessingJob.status == 'completed',
        ).order_by(
            ProcessingJob.completed_at.desc(),
            ProcessingJob.created_at.desc(),
        ).first()
        if not job:
            return None
        result = job.get_result_data() or {}
        period = result.get('period_aware') or {}
        return cls._info(
            document=document,
            method=result.get('embedding_method', 'manual'),
            dimensions=result.get('embedding_dimensions', 'N/A'),
            chunk_count=result.get(
                'chunk_count',
                result.get('total_embeddings', 1),
            ),
            model=result.get('model_used', 'unknown'),
            source='manual',
            created_at=job.completed_at or job.created_at,
            metadata={
                'period_category': period.get('period_category'),
                'selection_reason': period.get('selection_reason'),
                'selection_confidence': period.get('selection_confidence'),
                'era': period.get('era'),
                'handles_archaic': period.get('handles_archaic', False),
                'model_description': period.get('model_description'),
                'model_full': period.get('selected_model'),
                'document_year': period.get('detected_year'),
            },
        )

    @staticmethod
    def _info(
        document,
        method,
        dimensions,
        chunk_count,
        model,
        source,
        created_at,
        metadata,
    ):
        return {
            'document_id': document.id,
            'document_title': document.title or f'Document {document.id}',
            'document_uuid': str(document.uuid),
            'document_year': (
                metadata.get('document_year')
                or (
                    document.publication_date.year
                    if document.publication_date else None
                )
            ),
            'method': method,
            'dimensions': dimensions,
            'chunk_count': chunk_count,
            'model': model,
            'source': source,
            'created_at': created_at,
            'period_category': metadata.get('period_category'),
            'selection_reason': metadata.get('selection_reason'),
            'selection_confidence': metadata.get('selection_confidence'),
            'era': metadata.get('era'),
            'handles_archaic': metadata.get('handles_archaic', False),
            'model_description': metadata.get('model_description'),
            'model_full': metadata.get('model_full'),
        }

    @staticmethod
    def _orchestration_document_ids(experiment_id):
        run = ExperimentOrchestrationRun.query.filter_by(
            experiment_id=experiment_id
        ).order_by(ExperimentOrchestrationRun.started_at.desc()).first()
        if not run or not run.processing_results:
            return set()
        document_ids = set()
        for document_id, results in run.processing_results.items():
            embedding = (results or {}).get('period_aware_embedding')
            if embedding and embedding.get('status') == 'executed':
                try:
                    document_ids.add(int(document_id))
                except (TypeError, ValueError):
                    continue
        return document_ids
