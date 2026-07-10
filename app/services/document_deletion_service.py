"""User-scoped document and document-family deletion operations."""

from sqlalchemy import text

from app import db
from app.models.document import Document
from app.models.processing_job import ProcessingJob
from app.services.provenance_service import provenance_service


class DocumentDeletionService:
    """Delete individual documents and version families."""

    @staticmethod
    def get_referencing_experiments(document_id):
        return db.session.execute(
            text('''
                SELECT DISTINCT e.id, e.name
                FROM experiments e
                LEFT JOIN experiment_documents_v2 ed
                    ON ed.experiment_id = e.id
                LEFT JOIN experiment_documents ed_old
                    ON ed_old.experiment_id = e.id
                WHERE ed.document_id = :doc_id OR ed_old.document_id = :doc_id
            '''),
            {'doc_id': document_id},
        ).fetchall()

    @staticmethod
    def delete_document(document, logger):
        result = provenance_service.delete_or_invalidate_document_provenance(
            document.id
        )
        logger.info(f"Provenance handling for document {document.id}: {result}")
        document.delete_file()
        db.session.delete(document)
        db.session.commit()

    @staticmethod
    def delete_family(base_document_id, logger):
        base_document = Document.query.get_or_404(base_document_id)
        if base_document.source_document_id:
            actual_base = db.session.get(
                Document,
                base_document.source_document_id,
            )
            if actual_base:
                base_document = actual_base

        documents = [base_document]
        documents.extend(
            Document.query.filter_by(
                source_document_id=base_document.id
            ).all()
        )
        title = base_document.title

        for document in documents:
            result = provenance_service.delete_or_invalidate_document_provenance(
                document.id
            )
            logger.info(
                f"Provenance handling for document {document.id}: {result}"
            )

        for document in reversed(documents):
            ProcessingJob.query.filter_by(document_id=document.id).delete()
            db.session.execute(
                text('DELETE FROM text_segments WHERE document_id = :doc_id'),
                {'doc_id': document.id},
            )
            db.session.delete(document)

        db.session.commit()
        deleted_count = len(documents)
        logger.info(
            f"Successfully deleted {deleted_count} versions of document family "
            f"'{title}'"
        )
        return {'deleted_count': deleted_count, 'document_title': title}
