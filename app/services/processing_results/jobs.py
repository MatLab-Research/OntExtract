"""Adapters and queries that normalize processing jobs for result templates."""

from typing import Iterable, List

from app.models.experiment_document import ExperimentDocument
from app.models.experiment_processing import ExperimentDocumentProcessing


class ProcessingJobView:
    """Present experiment processing records through the legacy job interface."""

    def __init__(self, experiment_processing):
        self._experiment_processing = experiment_processing
        self.status = experiment_processing.status
        self.created_at = experiment_processing.created_at
        self.completed_at = experiment_processing.completed_at
        self.job_type = experiment_processing.processing_type

    def get_parameters(self):
        """Return the template-facing processing configuration."""
        return {
            "method": self._experiment_processing.processing_method,
            "processing_type": self._experiment_processing.processing_type,
        }


def append_experiment_jobs(
    jobs: List,
    document_ids: Iterable[int],
    processing_type: str,
) -> List:
    """Append experiment processing records and sort all jobs newest first."""
    for document_id in document_ids:
        experiment_documents = ExperimentDocument.query.filter_by(
            document_id=document_id
        ).all()
        for experiment_document in experiment_documents:
            processing_records = ExperimentDocumentProcessing.query.filter_by(
                experiment_document_id=experiment_document.id,
                processing_type=processing_type,
            ).all()
            jobs.extend(ProcessingJobView(record) for record in processing_records)

    jobs.sort(
        key=lambda job: (job.created_at is None, job.created_at),
        reverse=True,
    )
    return jobs