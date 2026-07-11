"""Regression coverage for orchestration review and approval services."""

import json
from datetime import date
from types import SimpleNamespace

import pytest


@pytest.fixture
def review_setup(db_session, temporal_experiment, test_user):
    from app.models import Document
    from app.models.experiment_orchestration_run import ExperimentOrchestrationRun

    documents = []
    for index, year in enumerate((1990, 2005), 1):
        document = Document(
            title=f"Temporal Document {index}",
            content=f"Content for temporal document {index}",
            document_type="document",
            content_type="text/plain",
            status="completed",
            user_id=test_user.id,
            experiment_id=temporal_experiment.id,
            publication_date=date(year, 1, 1),
            word_count=5,
        )
        db_session.add(document)
        documents.append(document)

    run = ExperimentOrchestrationRun(
        experiment_id=temporal_experiment.id,
        user_id=test_user.id,
        status="reviewing",
        current_stage="reviewing",
        recommended_strategy={"1": ["extract_temporal"]},
        strategy_reasoning="Temporal extraction is appropriate.",
        confidence=0.9,
    )
    db_session.add(run)
    db_session.commit()
    return temporal_experiment, run, documents


def test_review_route_and_services_have_canonical_modules(app):
    from app.services.orchestration_review_service import (
        OrchestrationApprovalService,
        OrchestrationReviewService,
    )

    assert app.view_functions[
        "experiments.orchestration_review_page"
    ].__module__ == "app.routes.experiments.orchestration.review"
    assert app.view_functions[
        "experiments.approve_orchestration_strategy"
    ].__module__ == "app.routes.experiments.orchestration.review"
    assert OrchestrationReviewService.__module__ == (
        "app.services.orchestration_review_service"
    )
    assert OrchestrationApprovalService.__module__ == (
        "app.services.orchestration_review_service"
    )


def test_review_context_suggests_periods_from_publication_dates(review_setup):
    from app.services.orchestration_review_service import OrchestrationReviewService

    experiment, run, documents = review_setup
    context = OrchestrationReviewService.build_review_context(
        experiment.id,
        run.id,
    )

    assert context["experiment"] is experiment
    assert context["run"] is run
    assert [item["id"] for item in context["documents"]] == [
        document.id for document in documents
    ]
    assert context["has_existing_periods"] is False
    assert [period["start_year"] for period in context["suggested_periods"]] == [
        1990,
        2005,
    ]


def test_review_context_uses_named_period_configuration(
    db_session, review_setup
):
    from app.services.orchestration_review_service import OrchestrationReviewService

    experiment, run, _ = review_setup
    experiment.configuration = json.dumps({
        "named_periods": [{
            "name": "Early Computing",
            "start_year": 1980,
            "end_year": 1999,
        }],
        "period_documents": {"1990": [{"id": 1}]},
    })
    db_session.commit()

    context = OrchestrationReviewService.build_review_context(
        experiment.id,
        run.id,
    )

    assert context["has_existing_periods"] is True
    assert context["suggested_periods"] == []
    assert context["existing_periods"][0]["temporal_period"] == "Early Computing"
    assert context["existing_periods"][0]["document_count"] == 1


def test_rejected_strategy_is_cancelled(db_session, review_setup):
    from app.services.orchestration_review_service import OrchestrationApprovalService

    _, run, _ = review_setup
    result = OrchestrationApprovalService.apply_decision(
        run.id,
        {
            "strategy_approved": False,
            "review_notes": "The strategy needs more work.",
        },
        reviewer_id=run.user_id,
    )

    db_session.refresh(run)
    assert result["status"] == "cancelled"
    assert run.status == "cancelled"
    assert run.review_notes == "The strategy needs more work."


def test_approved_strategy_is_stored_and_dispatched(
    db_session, review_setup, monkeypatch
):
    from app.services.orchestration_review_service import OrchestrationApprovalService

    _, run, _ = review_setup
    calls = []
    monkeypatch.setattr(
        OrchestrationApprovalService,
        "_dispatch_execution",
        lambda run, data, reviewer_id: calls.append(
            (run.id, data, reviewer_id)
        ) or SimpleNamespace(id="review-task-id"),
    )
    data = {
        "strategy_approved": True,
        "modified_strategy": {"1": ["extract_temporal", "extract_entities"]},
        "review_notes": "Added entity extraction.",
    }

    result = OrchestrationApprovalService.apply_decision(
        run.id,
        data,
        reviewer_id=run.user_id,
    )

    db_session.refresh(run)
    assert result["status"] == "executing"
    assert run.strategy_approved is True
    assert run.modified_strategy == data["modified_strategy"]
    assert run.status == "executing"
    assert run.current_stage == "executing"
    assert run.celery_task_id == "review-task-id"
    assert calls == [(run.id, data, run.user_id)]


def test_approval_generates_temporal_metadata_and_configuration(
    db_session, review_setup, monkeypatch
):
    from app.models.temporal_experiment import DocumentTemporalMetadata
    from app.services.orchestration_review_service import OrchestrationApprovalService

    experiment, run, documents = review_setup
    monkeypatch.setattr(
        OrchestrationApprovalService,
        "_dispatch_execution",
        lambda run, data, reviewer_id: SimpleNamespace(id="period-task-id"),
    )
    suggested_periods = [
        {
            "name": "1990 Document",
            "document_id": documents[0].id,
            "start_year": 1990,
            "end_year": 1990,
        },
        {
            "name": "2005 Document",
            "document_id": documents[1].id,
            "start_year": 2005,
            "end_year": 2005,
        },
    ]

    OrchestrationApprovalService.apply_decision(
        run.id,
        {
            "strategy_approved": True,
            "generate_periods": True,
            "suggested_periods": suggested_periods,
        },
        reviewer_id=run.user_id,
    )

    metadata = DocumentTemporalMetadata.query.filter_by(
        experiment_id=experiment.id
    ).order_by(DocumentTemporalMetadata.publication_year).all()
    assert [item.publication_year for item in metadata] == [1990, 2005]
    config = json.loads(experiment.configuration)
    assert config["time_periods"] == [1990, 2005]
    assert config["periods_source"] == "orchestration"
    assert config["period_documents"]["1990"][0]["id"] == documents[0].id


def test_review_page_renders_and_invalid_state_redirects(
    auth_client, db_session, review_setup
):
    experiment, run, _ = review_setup

    response = auth_client.get(
        f"/experiments/{experiment.id}/orchestration/review/{run.id}"
    )
    assert response.status_code == 200

    run.status = "executing"
    db_session.commit()
    redirect_response = auth_client.get(
        f"/experiments/{experiment.id}/orchestration/review/{run.id}"
    )
    assert redirect_response.status_code == 302
    assert redirect_response.headers["Location"].endswith(
        f"/experiments/{experiment.id}/document_pipeline"
    )
