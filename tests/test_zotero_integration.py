"""Credential-free coverage plus opt-in live tests for Zotero integration."""

import os
from unittest.mock import Mock

import pytest

import app.services.reference_metadata_enricher as enricher_module
from app.services.reference_metadata_enricher import ReferenceMetadataEnricher
from shared_services.zotero.metadata_mapper import ZoteroMetadataMapper
from shared_services.zotero.zotero_service import ZoteroService


@pytest.fixture
def zotero_item():
    return {
        "data": {
            "key": "ABCD1234",
            "version": 7,
            "itemType": "journalArticle",
            "title": "Ontology Extraction in Practice",
            "date": "2024-03-12",
            "creators": [
                {
                    "creatorType": "author",
                    "firstName": "Ada",
                    "lastName": "Lovelace",
                },
                {"creatorType": "author", "name": "Research Collective"},
            ],
            "publicationTitle": "Journal of Ontologies",
            "DOI": "10.1234/example",
            "url": "https://example.org/article",
            "volume": "12",
            "issue": "2",
            "pages": "10-20",
            "tags": [{"tag": "ontology"}, {"tag": "metadata"}],
            "_match_score": 0.95,
            "_match_type": "combined",
        }
    }


def test_metadata_mapping_is_credential_free(zotero_item):
    metadata = ZoteroMetadataMapper.map_to_source_metadata(zotero_item)

    assert metadata["title"] == "Ontology Extraction in Practice"
    assert metadata["authors"] == ["Ada Lovelace", "Research Collective"]
    assert metadata["publication_date"] == "2024-03-12"
    assert metadata["journal"] == "Journal of Ontologies"
    assert metadata["doi"] == "10.1234/example"
    assert metadata["zotero_key"] == "ABCD1234"
    assert metadata["tags"] == ["ontology", "metadata"]


def test_enricher_merges_mocked_zotero_metadata_without_overwriting_pdf_data(
    monkeypatch, zotero_item
):
    zotero_service = Mock()
    zotero_service.search_by_multiple_fields.return_value = [zotero_item]
    monkeypatch.setattr(
        enricher_module, "ZoteroService", Mock(return_value=zotero_service)
    )
    enricher = ReferenceMetadataEnricher(use_zotero=True)
    monkeypatch.setattr(
        enricher,
        "extract",
        Mock(return_value={"title": "Title extracted from PDF", "doi": "10.pdf/source"}),
    )

    metadata = enricher.extract_with_zotero(
        "/unused/test.pdf",
        title="Search title",
        existing={"authors": ["Existing Author"]},
    )

    zotero_service.search_by_multiple_fields.assert_called_once_with(
        title="Search title",
        doi="10.pdf/source",
        authors=["Existing Author"],
        year=None,
    )
    assert metadata["title"] == "Title extracted from PDF"
    assert metadata["doi"] == "10.pdf/source"
    assert metadata["authors"] == ["Ada Lovelace", "Research Collective"]
    assert metadata["journal"] == "Journal of Ontologies"
    assert metadata["zotero_key"] == "ABCD1234"
    assert metadata["zotero_match_score"] == 0.95


LIVE_ZOTERO_ENABLED = (
    os.getenv("RUN_ZOTERO_INTEGRATION") == "1"
    and bool(os.getenv("ZOTERO_API_KEY"))
    and bool(os.getenv("ZOTERO_USER_ID") or os.getenv("ZOTERO_GROUP_ID"))
)


@pytest.mark.integration
@pytest.mark.skipif(
    not LIVE_ZOTERO_ENABLED,
    reason="Set RUN_ZOTERO_INTEGRATION=1 and configure Zotero credentials",
)
def test_live_zotero_connection():
    """The Zotero client should initialize and expose collections when configured."""
    service = ZoteroService()
    collections = service.get_collections()

    assert isinstance(collections, list)


@pytest.mark.integration
@pytest.mark.skipif(
    not LIVE_ZOTERO_ENABLED,
    reason="Set RUN_ZOTERO_INTEGRATION=1 and configure Zotero credentials",
)
def test_live_search_by_title():
    """Title search should return results for a known query."""
    service = ZoteroService()
    results = service.search_by_title('ontology', limit=3)

    assert isinstance(results, list)
