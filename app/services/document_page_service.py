"""Read models for public document family list and detail pages."""

from math import ceil
from types import SimpleNamespace
from uuid import UUID

from sqlalchemy import func, or_

from app import db
from app.models.document import Document
from app.models.experiment_document import ExperimentDocument
from app.models.experiment_processing import DocumentProcessingIndex
from app.models.processing_artifact_group import ProcessingArtifactGroup
from app.models.temporal_experiment import DocumentTemporalMetadata
from app.services.base_service import NotFoundError


class DocumentPageService:
    """Build document page contexts without route-level aggregation."""

    @classmethod
    def get_list_context(cls, page=1, source_type='all', per_page=10):
        page = max(page or 1, 1)
        source_type = (
            source_type if source_type in ('all', 'document', 'reference')
            else 'all'
        )
        root_id = func.coalesce(
            Document.source_document_id,
            Document.parent_document_id,
            Document.id,
        )
        grouped_query = db.session.query(
            root_id.label('root_id'),
            func.max(Document.created_at).label('latest_created'),
        )
        if source_type != 'all':
            grouped_query = grouped_query.filter(
                Document.document_type == source_type
            )
        grouped_query = grouped_query.group_by(root_id)
        total = grouped_query.count()
        rows = (
            grouped_query
            .order_by(func.max(Document.created_at).desc(), root_id.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
            .all()
        )
        root_ids = [row.root_id for row in rows]
        documents = (
            Document.query.filter(or_(
                Document.id.in_(root_ids),
                Document.source_document_id.in_(root_ids),
                Document.parent_document_id.in_(root_ids),
            )).all()
            if root_ids else []
        )
        by_root = {root_id_value: [] for root_id_value in root_ids}
        for document in documents:
            family_id = (
                document.source_document_id
                or document.parent_document_id
                or document.id
            )
            if family_id in by_root:
                by_root[family_id].append(document)

        latest_by_root = {row.root_id: row.latest_created for row in rows}
        groups = []
        for root_id_value in root_ids:
            versions = by_root[root_id_value]
            versions.sort(
                key=lambda version: (
                    version.version_number or 0,
                    version.created_at,
                    version.id,
                ),
                reverse=True,
            )
            if not versions:
                continue
            root = next(
                (version for version in versions if version.id == root_id_value),
                min(versions, key=lambda version: version.version_number or 0),
            )
            groups.append(SimpleNamespace(
                base_document=root,
                latest_version=versions[0],
                versions=versions,
                latest_created=latest_by_root[root_id_value],
            ))
        pagination = cls._pagination(groups, page, per_page, total)
        return {'documents': pagination, 'source_type': source_type}

    @classmethod
    def get_detail_context(cls, document_uuid):
        try:
            normalized_uuid = UUID(str(document_uuid))
        except (TypeError, ValueError, AttributeError) as exc:
            raise NotFoundError(f'Document {document_uuid} not found') from exc
        document = Document.query.filter_by(uuid=normalized_uuid).first()
        if not document:
            raise NotFoundError(f'Document {document_uuid} not found')

        versions = document.get_all_versions()
        version_ids = [version.id for version in versions]
        versions_by_id = {version.id: version for version in versions}
        temporal_metadata = (
            DocumentTemporalMetadata.query.filter_by(document_id=document.id)
            .order_by(DocumentTemporalMetadata.created_at.desc())
            .first()
        )
        associations = (
            ExperimentDocument.query.filter(
                ExperimentDocument.document_id.in_(version_ids)
            ).order_by(
                ExperimentDocument.experiment_id,
                ExperimentDocument.document_id,
            ).all()
            if version_ids else []
        )
        indexes = (
            DocumentProcessingIndex.query.filter(
                DocumentProcessingIndex.document_id.in_(version_ids)
            ).order_by(DocumentProcessingIndex.created_at).all()
            if version_ids else []
        )
        processing_by_pair = {}
        for index in indexes:
            processing_by_pair.setdefault(
                (index.document_id, index.experiment_id),
                [],
            ).append(cls._serialize_processing(index))

        all_experiments = [
            cls._serialize_association(
                association,
                versions_by_id.get(association.document_id),
                processing_by_pair.get(
                    (association.document_id, association.experiment_id),
                    [],
                ),
                document.id,
            )
            for association in associations
        ]
        current_experiments = [
            item
            for item in all_experiments
            if item['is_current_version']
        ]
        current_processing_count = sum(
            len(item['processing_results']) for item in current_experiments
        )
        artifact_group_count = ProcessingArtifactGroup.query.filter_by(
            document_id=document.id
        ).count()
        return {
            'document': document,
            'version_family': versions,
            'temporal_metadata': temporal_metadata,
            'is_latest_version': (
                versions[-1].id == document.id if versions else True
            ),
            'this_version_experiments': current_experiments,
            'all_version_experiments': all_experiments,
            'total_processing_count': (
                current_processing_count + artifact_group_count
            ),
        }

    @staticmethod
    def _serialize_processing(index):
        return {
            'processing_type': index.processing_type,
            'processing_method': index.processing_method,
            'status': index.status,
        }

    @staticmethod
    def _serialize_association(
        association,
        version,
        processing_results,
        selected_document_id,
    ):
        return {
            'experiment': association.experiment,
            'document_version': version.version_number if version else 0,
            'version_type': version.version_type if version else 'unknown',
            'is_current_version': association.document_id == selected_document_id,
            'processing_results': processing_results,
        }

    @staticmethod
    def _pagination(items, page, per_page, total):
        pages = ceil(total / per_page) if total else 0
        has_prev = page > 1
        has_next = page < pages

        def iter_pages(*args, **kwargs):
            return range(1, pages + 1)

        return SimpleNamespace(
            items=items,
            page=page,
            pages=pages,
            per_page=per_page,
            total=total,
            has_prev=has_prev,
            has_next=has_next,
            prev_num=page - 1 if has_prev else None,
            next_num=page + 1 if has_next else None,
            iter_pages=iter_pages,
        )
