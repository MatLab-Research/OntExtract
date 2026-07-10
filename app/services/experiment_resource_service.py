"""Shared experiment resource resolution and association helpers."""

import logging
from uuid import UUID

from app import db
from app.models.document import Document
from app.models.experiment import experiment_references
from app.models.term import Term
from app.services.base_service import NotFoundError, PermissionError

logger = logging.getLogger(__name__)


class ExperimentResourceService:
    """Resolve authorized resources and associate them without committing."""

    @staticmethod
    def resolve_documents(values, ids, document_type, actor):
        values = list(dict.fromkeys(values or []))
        resolved = []
        resolved_ids = set()
        for value in values:
            try:
                normalized = UUID(str(value))
            except (TypeError, ValueError, AttributeError) as exc:
                raise NotFoundError(
                    f'{document_type.title()} not found'
                ) from exc
            document = Document.query.filter_by(
                uuid=normalized,
                document_type=document_type,
            ).first()
            if not document:
                raise NotFoundError(f'{document_type.title()} not found')
            ExperimentResourceService._append_root(
                resolved,
                resolved_ids,
                document,
                actor,
            )
        for value in dict.fromkeys(ids or []):
            document = db.session.get(Document, value)
            if not document or document.document_type != document_type:
                raise NotFoundError(f'{document_type.title()} not found')
            ExperimentResourceService._append_root(
                resolved,
                resolved_ids,
                document,
                actor,
            )
        return resolved

    @staticmethod
    def resolve_term(term_id, actor):
        if not term_id:
            return None
        try:
            normalized = UUID(str(term_id))
        except (TypeError, ValueError, AttributeError) as exc:
            raise NotFoundError('Term not found') from exc
        term = db.session.get(Term, normalized)
        if not term:
            raise NotFoundError('Term not found')
        if (
            not actor.is_admin
            and term.created_by is not None
            and term.created_by != actor.id
        ):
            raise PermissionError('Permission denied')
        return term

    @staticmethod
    def add_documents(experiment, documents, actor):
        from app.services.inheritance_versioning_service import (
            InheritanceVersioningService,
        )

        for document in documents:
            version, created = (
                InheritanceVersioningService.get_or_create_experiment_version(
                    original_document=document,
                    experiment_id=experiment.id,
                    user=actor,
                    commit=False,
                )
            )
            experiment.add_document(version)
            logger.info(
                'Using experimental version %s for document %s and experiment '
                '%s (%s)',
                version.id,
                document.uuid,
                experiment.id,
                'created' if created else 'existing',
            )

    @staticmethod
    def add_references(experiment, references):
        for reference in references:
            db.session.execute(experiment_references.insert().values(
                experiment_id=experiment.id,
                reference_id=reference.id,
                include_in_analysis=True,
            ))

    @staticmethod
    def replace_references(experiment, references):
        db.session.execute(experiment_references.delete().where(
            experiment_references.c.experiment_id == experiment.id
        ))
        ExperimentResourceService.add_references(experiment, references)

    @staticmethod
    def _append_root(resolved, resolved_ids, document, actor):
        root = document.get_root_document()
        if not actor.can_edit_resource(root):
            raise PermissionError('Permission denied')
        if root.id not in resolved_ids:
            resolved.append(root)
            resolved_ids.add(root.id)
