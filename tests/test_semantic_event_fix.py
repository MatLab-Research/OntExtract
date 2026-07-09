"""Regression coverage for temporal period-document JSON serialization."""

import json
from datetime import date

from app.services.temporal_service import get_temporal_service


def test_temporal_ui_period_documents_are_serialized(
    db_session, temporal_experiment, sample_document
):
    sample_document.publication_date = date(1995, 6, 15)
    temporal_experiment.configuration = json.dumps({
        "target_terms": ["algorithm"],
        "time_periods": [1990, 2000],
        "start_year": 1990,
        "end_year": 2000,
        "period_documents": {
            "1990-2000": [{
                "id": sample_document.id,
                "title": "Stale configured title",
                "date_source": "publication_date",
            }]
        },
        "period_metadata": {"1990-2000": {"label": "Web era"}},
        "semantic_events": [{"type": "Emergence", "year": 1995}],
    })
    db_session.commit()

    data = get_temporal_service().get_temporal_ui_data(temporal_experiment.id)

    period_documents = data["period_documents"]
    json.dumps(period_documents)
    assert period_documents == {
        "1990-2000": [{
            "id": sample_document.id,
            "uuid": str(sample_document.uuid),
            "title": sample_document.title,
            "publication_date": "1995-06-15",
            "date_source": "publication_date",
        }]
    }
    assert data["time_periods"] == [1990, 2000]
    assert data["terms"] == ["algorithm"]
    assert data["start_year"] == 1990
    assert data["end_year"] == 2000
    assert data["period_metadata"]["1990-2000"]["label"] == "Web era"
    assert data["semantic_events"][0]["type"] == "Emergence"
