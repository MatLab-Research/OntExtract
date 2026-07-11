"""Regression coverage for modular experiment route packages."""


def test_experiment_routes_are_grouped_by_responsibility(app):
    expected_modules = {
        # CRUD
        "experiments.index": "app.routes.experiments.crud.pages",
        "experiments.new": "app.routes.experiments.crud.pages",
        "experiments.wizard": "app.routes.experiments.crud.pages",
        "experiments.create": "app.routes.experiments.crud.creation",
        "experiments.create_sample": "app.routes.experiments.crud.creation",
        "experiments.view": "app.routes.experiments.crud.detail",
        "experiments.results": "app.routes.experiments.crud.detail",
        "experiments.edit": "app.routes.experiments.crud.editing",
        "experiments.update": "app.routes.experiments.crud.editing",
        "experiments.delete": "app.routes.experiments.crud.lifecycle",
        "experiments.duplicate": "app.routes.experiments.crud.lifecycle",
        "experiments.mark_complete": "app.routes.experiments.crud.lifecycle",
        "experiments.run": "app.routes.experiments.crud.lifecycle",
        "experiments.api_list": "app.routes.experiments.crud.api",
        "experiments.api_get": "app.routes.experiments.crud.api",
        # Orchestration
        "experiments.orchestration_provenance_json": "app.routes.experiments.orchestration.provenance",
        "experiments.download_llm_provenance": "app.routes.experiments.orchestration.provenance",
        "experiments.start_llm_orchestration": "app.routes.experiments.orchestration.analysis",
        "experiments.check_experiment_processing_status": "app.routes.experiments.orchestration.status",
        "experiments.get_latest_orchestration_run": "app.routes.experiments.orchestration.status",
        "experiments.get_orchestration_status": "app.routes.experiments.orchestration.status",
        "experiments.orchestration_review_page": "app.routes.experiments.orchestration.review",
        "experiments.approve_orchestration_strategy": "app.routes.experiments.orchestration.review",
        "experiments.llm_orchestration_results": "app.routes.experiments.orchestration.results",
        # Results
        "experiments.experiment_definitions_results": "app.routes.experiments.results.definitions",
        "experiments.experiment_entities_results": "app.routes.experiments.results.entities",
        "experiments.experiment_temporal_results": "app.routes.experiments.results.temporal",
        "experiments.experiment_embeddings_results": "app.routes.experiments.results.embeddings",
        "experiments.experiment_segments_results": "app.routes.experiments.results.segments",
        # Temporal
        "experiments.manage_temporal_terms": "app.routes.experiments.temporal.pages",
        "experiments.timeline_view": "app.routes.experiments.temporal.pages",
        "experiments.update_temporal_terms": "app.routes.experiments.temporal.configuration",
        "experiments.get_temporal_terms": "app.routes.experiments.temporal.configuration",
        "experiments.generate_periods_from_documents": "app.routes.experiments.temporal.configuration",
        "experiments.fetch_temporal_data": "app.routes.experiments.temporal.analysis",
        "experiments.get_experiment_documents": "app.routes.experiments.temporal.documents",
        "experiments.save_semantic_event": "app.routes.experiments.temporal.events",
        "experiments.remove_semantic_event": "app.routes.experiments.temporal.events",
        "experiments.ontology_info": "app.routes.experiments.temporal.ontology",
        "experiments.get_semantic_event_types": "app.routes.experiments.temporal.ontology",
        "experiments.get_period_types": "app.routes.experiments.temporal.ontology",
    }

    actual_modules = {
        endpoint: app.view_functions[endpoint].__module__
        for endpoint in expected_modules
    }

    assert actual_modules == expected_modules


def test_experiment_result_helpers_have_one_canonical_home():
    from app.routes.experiments.results import helpers

    assert helpers._get_experiment_documents.__module__ == (
        "app.routes.experiments.results.helpers"
    )
    assert helpers._get_orchestration_results.__module__ == (
        "app.routes.experiments.results.helpers"
    )


def test_split_route_dependencies_have_canonical_contexts():
    from app.routes.experiments.crud import context as crud_context
    from app.routes.experiments.orchestration import context as orchestration_context
    from app.routes.experiments.temporal import context as temporal_context

    assert crud_context.experiment_service.__class__.__module__ == (
        "app.services.experiment_service"
    )
    assert orchestration_context.orchestration_service.__class__.__module__ == (
        "app.services.orchestration_service"
    )
    assert temporal_context.temporal_service.__class__.__module__ == (
        "app.services.temporal_service"
    )
    assert temporal_context.ontserve_client.__class__.__module__ == (
        "app.services.ontserve_client"
    )
