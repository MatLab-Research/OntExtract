"""Document-family queries shared by processing result views."""

from app.models.document import Document
from app.services.inheritance_versioning_service import InheritanceVersioningService


def get_document_family_ids(document) -> list[int]:
    """Return IDs for every derived version plus the base document itself."""
    base_document_id = InheritanceVersioningService._get_base_document_id(document)
    versions = Document.query.filter_by(source_document_id=base_document_id).all()
    document_ids = [version.id for version in versions]

    if base_document_id not in document_ids:
        document_ids.append(base_document_id)

    return document_ids