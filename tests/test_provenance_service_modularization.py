"""Regression coverage for focused provenance service mixins."""

import uuid


def test_provenance_query_methods_have_canonical_module():
    from app.services.provenance_service import ProvenanceService

    expected_module = "app.services.provenance.queries"
    assert ProvenanceService.get_timeline.__module__ == expected_module
    assert ProvenanceService.get_entity_lineage.__module__ == expected_module
    assert ProvenanceService.get_graph_data.__module__ == expected_module


def test_public_provenance_singleton_retains_query_api():
    from app.services.provenance_service import (
        ProvenanceService,
        provenance_service,
    )

    assert isinstance(provenance_service, ProvenanceService)
    assert callable(provenance_service.get_timeline)
    assert callable(provenance_service.get_entity_lineage)
    assert callable(provenance_service.get_graph_data)


def test_provenance_queries_handle_empty_database(db_session):
    from app.models.prov_o_models import ProvActivity, ProvEntity
    from app.services.provenance_service import provenance_service

    ProvEntity.query.delete(synchronize_session=False)
    ProvActivity.query.delete(synchronize_session=False)
    db_session.commit()

    assert provenance_service.get_timeline(limit=5) == []
    assert provenance_service.get_entity_lineage(uuid.uuid4()) == []
    graph = provenance_service.get_graph_data(limit=5)
    assert graph == {
        "nodes": [],
        "edges": [],
        "stats": {"entities": 0, "activities": 0, "agents": 0},
    }
