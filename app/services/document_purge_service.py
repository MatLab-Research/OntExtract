"""Administrative purge of all documents and dependent records."""

from sqlalchemy import text

from app import db
from app.models import Experiment
from app.models.document import Document
from app.models.experiment_document import ExperimentDocument
from app.models.experiment_processing import (
    ExperimentDocumentProcessing,
    ProcessingArtifact,
)
from app.models.processing_job import ProcessingJob
from app.models.provenance import ProvenanceEntity


class DocumentPurgeService:
    """Delete every document while respecting cross-table FK order."""

    @staticmethod
    def rollback():
        db.session.rollback()

    @staticmethod
    def purge_all(user_id, logger):
        experiments = db.session.execute(text('''
            SELECT DISTINCT e.id, e.name
            FROM experiments e
            WHERE EXISTS (
                SELECT 1 FROM experiment_documents_v2 ed
                WHERE ed.experiment_id = e.id
            ) OR EXISTS (
                SELECT 1 FROM experiment_documents ed2
                WHERE ed2.experiment_id = e.id
            )
            LIMIT 5
        ''')).fetchall()

        if experiments:
            total = Experiment.query.count()
            names = ', '.join(f'"{exp.name}"' for exp in experiments[:3])
            if len(experiments) > 3:
                names += f' and {total - 3} more'
            return {
                'success': False,
                'status': 409,
                'error': (
                    f'Cannot delete documents: {total} experiment(s) still '
                    f'reference documents. Please delete experiments first: {names}'
                ),
                'experiments': [
                    {'id': exp.id, 'name': exp.name} for exp in experiments
                ],
            }

        total_documents = Document.query.count()
        logger.warning(
            f"Admin {user_id} initiating deletion of ALL {total_documents} documents"
        )

        provenance_count = ProvenanceEntity.query.filter(
            ProvenanceEntity.document_id.isnot(None)
        ).count()
        ProvenanceEntity.query.filter(
            ProvenanceEntity.document_id.isnot(None)
        ).delete(synchronize_session=False)

        artifact_count = ProcessingArtifact.query.count()
        ProcessingArtifact.query.delete(synchronize_session=False)
        db.session.execute(text('DELETE FROM processing_artifact_groups'))
        db.session.execute(text('DELETE FROM document_processing_index'))
        ExperimentDocumentProcessing.query.delete(synchronize_session=False)

        experiment_relationships = ExperimentDocument.query.count()
        ExperimentDocument.query.delete(synchronize_session=False)
        db.session.execute(text('DELETE FROM experiment_documents_v2'))
        db.session.execute(text('DELETE FROM experiment_references'))
        db.session.execute(text('DELETE FROM orchestration_decisions'))
        db.session.execute(text('DELETE FROM version_changelog'))
        db.session.execute(text('DELETE FROM document_temporal_metadata'))
        db.session.execute(text('DELETE FROM term_disciplinary_definitions'))
        db.session.execute(text('DELETE FROM semantic_shift_analysis'))
        ProcessingJob.query.delete(synchronize_session=False)
        db.session.execute(text('DELETE FROM text_segments'))

        documents = Document.query.all()
        deleted_files = 0
        for document in documents:
            try:
                document.delete_file()
                deleted_files += 1
            except Exception as exc:
                logger.error(
                    f"Error deleting file for document {document.id}: {exc}"
                )

        db.session.execute(text(
            'UPDATE documents '
            'SET source_document_id = NULL, parent_document_id = NULL'
        ))
        Document.query.delete(synchronize_session=False)
        db.session.commit()

        logger.warning(
            f"Successfully deleted ALL documents: {total_documents} documents, "
            f"{deleted_files} files, {provenance_count} provenance records"
        )
        return {
            'success': True,
            'details': {
                'documents': total_documents,
                'files': deleted_files,
                'provenance_records': provenance_count,
                'processing_artifacts': artifact_count,
                'experiment_relationships': experiment_relationships,
            },
        }
