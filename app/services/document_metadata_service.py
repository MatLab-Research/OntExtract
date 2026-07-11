"""Normalized and custom metadata operations for documents."""

from dateutil import parser as date_parser
from sqlalchemy.orm.attributes import flag_modified


class DocumentMetadataService:
    """Serialize and update the hybrid column/JSON document metadata model."""

    STANDARD_FIELDS = {
        'title', 'authors', 'publication_date', 'journal', 'publisher',
        'doi', 'isbn', 'type', 'abstract', 'url', 'citation',
        'editor', 'edition', 'volume', 'issue', 'pages', 'series',
        'container_title', 'place', 'issn', 'access_date', 'entry_term', 'notes'
    }

    TRUTHY_FIELDS = {
        'title': ('title', 200),
        'authors': ('authors', None),
        'journal': ('journal', 200),
        'publisher': ('publisher', 200),
        'doi': ('doi', 100),
        'isbn': ('isbn', 20),
        'type': ('document_subtype', 50),
        'abstract': ('abstract', None),
        'url': ('url', 500),
        'citation': ('citation', None),
    }

    CLEARABLE_FIELDS = {
        'editor': ('editor', None),
        'edition': ('edition', 50),
        'volume': ('volume', 20),
        'issue': ('issue', 20),
        'pages': ('pages', 50),
        'series': ('series', 200),
        'container_title': ('container_title', 300),
        'place': ('place', 100),
        'issn': ('issn', 20),
        'entry_term': ('entry_term', 200),
        'notes': ('notes', None),
    }

    @classmethod
    def serialize_for_view(cls, document):
        root_document = document.get_root_document()
        is_version = root_document.id != document.id
        metadata = cls._normalized_metadata(
            root_document,
            display_authors=True,
        )
        if root_document.source_metadata:
            for key, value in root_document.source_metadata.items():
                if key not in metadata:
                    metadata[key] = value
        return {
            'metadata': cls._without_none(metadata),
            'is_version': is_version,
            'root_uuid': root_document.uuid if is_version else None,
        }

    @classmethod
    def serialize_after_update(cls, document):
        metadata = cls._normalized_metadata(document, display_authors=False)
        if document.source_metadata:
            metadata.update(document.source_metadata)
        return cls._without_none(metadata)

    @classmethod
    def apply_updates(cls, document, metadata):
        changes = {}

        for input_name, (attribute, max_length) in cls.TRUTHY_FIELDS.items():
            if input_name in metadata and metadata[input_name]:
                cls._set_string_field(
                    document,
                    input_name,
                    attribute,
                    metadata[input_name],
                    max_length,
                    changes,
                    clearable=False,
                )

        for date_name, attribute in (
            ('publication_date', 'publication_date'),
            ('access_date', 'access_date'),
        ):
            if date_name in metadata and metadata[date_name]:
                cls._set_date_field(
                    document,
                    date_name,
                    attribute,
                    metadata[date_name],
                    changes,
                )

        for input_name, (attribute, max_length) in cls.CLEARABLE_FIELDS.items():
            if input_name in metadata:
                cls._set_string_field(
                    document,
                    input_name,
                    attribute,
                    metadata[input_name],
                    max_length,
                    changes,
                    clearable=True,
                )

        custom_fields = {
            key: value
            for key, value in metadata.items()
            if key not in cls.STANDARD_FIELDS
        }
        if custom_fields:
            if not document.source_metadata:
                document.source_metadata = {}
            document.source_metadata.update(custom_fields)
            flag_modified(document, 'source_metadata')

        return changes

    @staticmethod
    def _set_string_field(
        document,
        input_name,
        attribute,
        value,
        max_length,
        changes,
        *,
        clearable,
    ):
        new_value = str(value) if value else None
        if new_value is not None and max_length is not None:
            new_value = new_value[:max_length]
        if not clearable and new_value is None:
            return
        old_value = getattr(document, attribute)
        if old_value != new_value:
            changes[input_name] = {'old': old_value, 'new': new_value}
            setattr(document, attribute, new_value)

    @staticmethod
    def _set_date_field(document, input_name, attribute, value, changes):
        try:
            new_value = date_parser.parse(value).date()
        except (TypeError, ValueError, OverflowError):
            return
        old_value = getattr(document, attribute)
        if old_value != new_value:
            changes[input_name] = {
                'old': old_value.isoformat() if old_value else None,
                'new': new_value.isoformat(),
            }
            setattr(document, attribute, new_value)

    @staticmethod
    def _normalized_metadata(document, *, display_authors):
        return {
            'title': document.title,
            'authors': (
                document.display_authors if display_authors else document.authors
            ),
            'publication_date': (
                document.publication_date.isoformat()
                if document.publication_date else None
            ),
            'journal': document.journal,
            'publisher': document.publisher,
            'doi': document.doi,
            'isbn': document.isbn,
            'type': document.document_subtype,
            'abstract': document.abstract,
            'url': document.url,
            'citation': document.citation,
            'editor': document.editor,
            'edition': document.edition,
            'volume': document.volume,
            'issue': document.issue,
            'pages': document.pages,
            'series': document.series,
            'container_title': document.container_title,
            'place': document.place,
            'issn': document.issn,
            'access_date': (
                document.access_date.isoformat() if document.access_date else None
            ),
            'entry_term': document.entry_term,
            'notes': document.notes,
        }

    @staticmethod
    def _without_none(metadata):
        return {key: value for key, value in metadata.items() if value is not None}
