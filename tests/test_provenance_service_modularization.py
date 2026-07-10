"""Regression coverage for focused provenance service mixins."""

import uuid
from datetime import datetime


def test_provenance_query_methods_have_canonical_module():
    from app.services.provenance_service import ProvenanceService

    expected_module = "app.services.provenance.queries"
    assert ProvenanceService.get_timeline.__module__ == expected_module
    assert ProvenanceService.get_entity_lineage.__module__ == expected_module
    assert ProvenanceService.get_graph_data.__module__ == expected_module


def test_provenance_deletion_methods_have_canonical_module():
    from app.services.provenance_service import ProvenanceService

    expected_module = "app.services.provenance.deletion"
    method_names = (
        "delete_or_invalidate_entity",
        "delete_or_invalidate_document_provenance",
        "delete_or_invalidate_term_provenance",
        "delete_or_invalidate_experiment_provenance",
    )
    assert {
        name: getattr(ProvenanceService, name).__module__
        for name in method_names
    } == {name: expected_module for name in method_names}


def test_provenance_term_methods_have_canonical_module():
    from app.services.provenance_service import ProvenanceService

    expected_module = "app.services.provenance.terms"
    assert ProvenanceService.track_term_creation.__module__ == expected_module
    assert ProvenanceService.track_term_update.__module__ == expected_module


def test_provenance_orchestration_methods_have_canonical_module():
    from app.services.provenance_service import ProvenanceService

    expected_module = "app.services.provenance.orchestration"
    assert ProvenanceService.track_orchestration_start.__module__ == expected_module
    assert ProvenanceService.track_orchestration_complete.__module__ == expected_module


def test_provenance_serializer_handles_nested_special_values():
    from app.services.provenance.serialization import _serialize_value

    identifier = uuid.uuid4()
    timestamp = datetime(2026, 7, 10, 12, 30)
    assert _serialize_value({
        "identifier": identifier,
        "nested": [timestamp, (identifier,)],
    }) == {
        "identifier": str(identifier),
        "nested": [timestamp.isoformat(), [str(identifier)]],
    }


def test_public_provenance_singleton_retains_query_api():
    from app.services.provenance_service import (
        ProvenanceService,
        provenance_service,
    )

    assert isinstance(provenance_service, ProvenanceService)
    assert callable(provenance_service.get_timeline)
    assert callable(provenance_service.get_entity_lineage)
    assert callable(provenance_service.get_graph_data)
    assert callable(provenance_service.delete_or_invalidate_entity)
    assert callable(provenance_service.delete_or_invalidate_document_provenance)
    assert callable(provenance_service.track_term_creation)
    assert callable(provenance_service.track_term_update)
    assert callable(provenance_service.track_orchestration_start)
    assert callable(provenance_service.track_orchestration_complete)


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


def test_provenance_entity_can_be_soft_invalidated(db_session):
    from app.models.prov_o_models import ProvActivity, ProvEntity
    from app.services.provenance_service import provenance_service

    activity = ProvActivity(activity_type="test_invalidation")
    db_session.add(activity)
    db_session.flush()
    entity = ProvEntity(
        entity_type="test_entity",
        wasgeneratedby=activity.activity_id,
        entity_value={"test": True},
    )
    db_session.add(entity)
    db_session.commit()
    entity_id = entity.entity_id

    result = provenance_service.delete_or_invalidate_entity(
        entity_id,
        purge=False,
    )

    assert result == {
        "success": True,
        "action": "invalidated",
        "entities_invalidated": 1,
    }
    assert db_session.get(ProvEntity, entity_id).invalidatedattime is not None


def test_provenance_entity_purge_removes_relationships(db_session):
    from app.models.prov_o_models import (
        ProvActivity,
        ProvEntity,
        ProvRelationship,
    )
    from app.services.provenance_service import provenance_service

    activity = ProvActivity(activity_type="test_purge")
    db_session.add(activity)
    db_session.flush()
    entity = ProvEntity(
        entity_type="test_entity",
        wasgeneratedby=activity.activity_id,
        entity_value={"test": True},
    )
    db_session.add(entity)
    db_session.flush()
    relationship = ProvRelationship(
        relationship_type="wasGeneratedBy",
        subject_type="entity",
        subject_id=entity.entity_id,
        object_type="activity",
        object_id=activity.activity_id,
    )
    db_session.add(relationship)
    db_session.commit()
    entity_id = entity.entity_id
    relationship_id = relationship.relationship_id

    result = provenance_service.delete_or_invalidate_entity(
        entity_id,
        purge=True,
    )

    assert result == {
        "success": True,
        "action": "purged",
        "entities_deleted": 1,
        "relationships_deleted": 1,
    }
    assert db_session.get(ProvEntity, entity_id) is None
    assert db_session.get(ProvRelationship, relationship_id) is None


def test_term_tracking_creates_creation_and_update_provenance(
    db_session, sample_term, test_user
):
    from app.models.prov_o_models import ProvActivity, ProvEntity
    from app.services.provenance_service import provenance_service

    creation_activity, creation_entity = provenance_service.track_term_creation(
        sample_term,
        test_user,
    )
    update_activity, update_entity = provenance_service.track_term_update(
        sample_term,
        test_user,
        {"status": {"old": "draft", "new": "active"}},
    )

    assert creation_activity.activity_type == "term_creation"
    assert creation_entity.entity_type == "term"
    assert creation_entity.entity_value["term_id"] == str(sample_term.id)
    assert update_activity.activity_type == "term_update"
    assert update_entity.entity_metadata["changes"]["status"]["new"] == "active"
    assert ProvActivity.query.filter_by(activity_type="term_creation").count() == 1
    assert ProvActivity.query.filter_by(activity_type="term_update").count() == 1
    assert ProvEntity.query.filter_by(entity_type="term").count() == 2


def test_orchestration_tracking_records_complete_lifecycle(
    db_session, temporal_experiment, test_user
):
    from app.models.prov_o_models import ProvActivity, ProvEntity
    from app.services.provenance_service import provenance_service

    run_id = str(uuid.uuid4())
    activity = provenance_service.track_orchestration_start(
        run_id,
        temporal_experiment,
        test_user,
        {"goal": "Analyze agency"},
    )
    entity = provenance_service.track_orchestration_complete(
        run_id,
        {
            "confidence": 0.9,
            "reasoning": "The strategy covers the requested analyses.",
        },
        {"artifact_id": uuid.uuid4()},
    )

    db_session.refresh(activity)
    assert activity.activity_status == "completed"
    assert activity.activity_parameters["experiment_id"] == temporal_experiment.id
    assert isinstance(activity.activity_metadata["artifact_id"], str)
    assert entity.entity_type == "processing_strategy"
    assert entity.wasgeneratedby == activity.activity_id
    assert ProvActivity.query.filter_by(activity_type="orchestration_run").count() == 1
    assert ProvEntity.query.filter_by(entity_type="processing_strategy").count() == 1
