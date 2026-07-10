"""Regression coverage for semantic-evolution service and route boundaries."""

import json

import pytest


def _user(db_session, suffix):
    from app.models.user import User

    user = User(
        username=f'evolution-{suffix}',
        email=f'evolution-{suffix}@example.com',
        password='password',
        account_status='active',
    )
    db_session.add(user)
    db_session.commit()
    return user


def _term(db_session, user, text='agency', **version_values):
    from app.models.term import Term, TermVersion

    term = Term(term_text=text, status='active', created_by=user.id)
    db_session.add(term)
    db_session.flush()
    version = TermVersion(
        term_id=term.id,
        temporal_period=version_values.pop('temporal_period', '2000-present'),
        temporal_start_year=version_values.pop('temporal_start_year', 2000),
        meaning_description=version_values.pop(
            'meaning_description',
            'The capacity to act.',
        ),
        confidence_level=version_values.pop('confidence_level', 'medium'),
        created_by=user.id,
        **version_values,
    )
    db_session.add(version)
    db_session.commit()
    return term, version


def _experiment(db_session, user, term=None, suffix='service', configuration=None):
    from app.models.experiment import Experiment

    experiment = Experiment(
        name=f'Evolution {suffix}',
        experiment_type='temporal_evolution',
        user_id=user.id,
        term_id=term.id if term else None,
        status='draft',
        configuration=(
            (
                json.dumps(configuration)
                if isinstance(configuration, dict)
                else configuration
            )
            if configuration is not None
            else json.dumps({'target_term': term.term_text if term else 'agency'})
        ),
    )
    db_session.add(experiment)
    db_session.commit()
    return experiment


def test_configuration_parser_tolerates_dictionary_backed_objects():
    from types import SimpleNamespace

    from app.services.evolution_service import EvolutionService

    configuration = {'target_terms': ['agency']}
    parsed = EvolutionService()._parse_configuration(SimpleNamespace(
        id=42,
        configuration=configuration,
    ))
    assert parsed == configuration
    assert parsed is not configuration


def _link(db_session, experiment, document):
    from app.models.experiment_document import ExperimentDocument

    association = ExperimentDocument(
        experiment_id=experiment.id,
        document_id=document.id,
    )
    db_session.add(association)
    db_session.commit()
    return association


class TemporalRecorder:
    def __init__(self):
        self.calls = []

    def extract_temporal_data(self, documents, term, periods):
        self.calls.append(('extract', [item.id for item in documents], term, periods))
        return {'periods': periods}

    def analyze_semantic_drift(self, documents, term, periods):
        self.calls.append(('drift', [item.id for item in documents], term, periods))
        return {
            'average_drift': 0.25,
            'total_drift': 0.5,
            'stable_terms': ['actor'],
            'periods': {},
        }

    def generate_evolution_narrative(self, temporal_data, term, periods):
        self.calls.append(('narrative', temporal_data, term, periods))
        return f'Narrative for {term}'


def test_evolution_routes_remain_canonical(app):
    expected = 'app.routes.experiments.evolution'
    assert app.view_functions['experiments.semantic_evolution_visual'].__module__ == expected
    assert app.view_functions['experiments.analyze_evolution'].__module__ == expected


def test_visualization_resolves_explicit_experiment_term_with_duplicate_text(
    db_session, test_user, tmp_path
):
    from app.services.evolution_service import EvolutionService

    other = _user(db_session, 'duplicate-owner')
    _term(db_session, other, 'agency', extraction_method='other_analysis')
    owned, _ = _term(
        db_session,
        test_user,
        'agency',
        extraction_method='philosophy_analysis',
    )
    experiment = _experiment(db_session, test_user, owned, 'explicit')

    data = EvolutionService(data_root=tmp_path).get_evolution_visualization_data(
        experiment.id
    )
    assert data['experiment'] is experiment
    assert data['term_record'] is owned
    assert data['domains'] == ['philosophy']


def test_visualization_uses_owner_term_without_explicit_term_id(
    db_session, test_user, tmp_path
):
    from app.services.evolution_service import EvolutionService

    other = _user(db_session, 'implicit-duplicate')
    _term(db_session, other, 'actor', extraction_method='other')
    owned, _ = _term(db_session, test_user, 'actor', extraction_method=None)
    experiment = _experiment(
        db_session,
        test_user,
        None,
        'implicit',
        configuration={'target_terms': ['actor']},
    )
    data = EvolutionService(data_root=tmp_path).get_evolution_visualization_data(
        experiment.id
    )
    assert data['term_record'] is owned
    assert data['academic_anchors'][0]['domain'] == 'unknown'


def test_visualization_rejects_term_owned_only_by_another_user(
    db_session, test_user, tmp_path
):
    from app.services.base_service import NotFoundError
    from app.services.evolution_service import EvolutionService

    other = _user(db_session, 'foreign-term-owner')
    _term(db_session, other, 'foreign', extraction_method='history')
    experiment = _experiment(
        db_session,
        test_user,
        None,
        'foreign',
        configuration={'target_term': 'foreign'},
    )
    with pytest.raises(NotFoundError, match='not found'):
        EvolutionService(data_root=tmp_path).get_evolution_visualization_data(
            experiment.id
        )


def test_fallback_files_use_safe_absolute_term_names(tmp_path):
    from app.services.evolution_service import EvolutionService

    (tmp_path / 'oed_agency_term_extraction_provenance.json').write_text(
        json.dumps({'definitions': [{'text': 'safe'}]}),
        encoding='utf-8',
    )
    (tmp_path / 'blacks_law_agency_term_extraction.json').write_text(
        json.dumps({'definition': 'legal'}),
        encoding='utf-8',
    )
    service = EvolutionService(data_root=tmp_path)
    assert service._safe_term_filename('../../Agency Term') == 'agency_term'
    assert service._get_oed_from_files('../../Agency Term')['definitions'][0][
        'text'
    ] == 'safe'
    assert service._get_legal_data('../../Agency Term')['definition'] == 'legal'


def test_malformed_fallback_json_is_ignored(tmp_path):
    from app.services.evolution_service import EvolutionService

    (tmp_path / 'oed_agency_extraction_provenance.json').write_text(
        '{not json',
        encoding='utf-8',
    )
    assert EvolutionService(data_root=tmp_path)._get_oed_from_files('agency') is None


def test_analysis_requires_owner_before_constructing_temporal_service(
    db_session, test_user, sample_document
):
    from app.services.base_service import PermissionError
    from app.services.evolution_service import EvolutionService

    owner = _user(db_session, 'analysis-owner')
    experiment = _experiment(db_session, owner, suffix='permission')
    _link(db_session, experiment, sample_document)
    constructed = []
    service = EvolutionService(
        temporal_service_factory=lambda: constructed.append(True),
    )
    with pytest.raises(PermissionError):
        service.analyze_evolution(
            experiment.id,
            'agency',
            [2000],
            test_user.id,
        )
    assert constructed == []


def test_admin_can_analyze_canonical_latest_documents_and_references(
    db_session, admin_user, test_user, sample_documents
):
    from app.models.document import Document
    from app.services.evolution_service import EvolutionService

    root, reference = sample_documents[:2]
    experiment = _experiment(db_session, test_user, suffix='canonical')
    _link(db_session, experiment, root)
    latest = Document(
        title='Latest analysis document',
        content='Latest content.',
        content_type='text',
        document_type='document',
        status='completed',
        user_id=test_user.id,
        source_document_id=root.id,
        version_number=2,
        version_type='processed',
    )
    reference.document_type = 'reference'
    db_session.add(latest)
    db_session.commit()
    _link(db_session, experiment, latest)
    experiment.references.append(reference)
    db_session.commit()
    recorder = TemporalRecorder()

    result = EvolutionService(
        temporal_service_factory=lambda: recorder,
    ).analyze_evolution(
        experiment.id,
        ' agency ',
        [1990, 2000],
        admin_user.id,
    )

    assert result['drift_metrics'] == {
        'average_drift': 0.25,
        'total_drift': 0.5,
        'stable_term_count': 1,
    }
    assert 'Narrative for agency' in result['analysis']
    assert recorder.calls[0][1] == [reference.id, latest.id]


def test_analysis_rejects_empty_experiment(db_session, test_user):
    from app.services.base_service import ValidationError
    from app.services.evolution_service import EvolutionService

    experiment = _experiment(db_session, test_user, suffix='empty')
    with pytest.raises(ValidationError, match='no documents'):
        EvolutionService(
            temporal_service_factory=TemporalRecorder,
        ).analyze_evolution(
            experiment.id,
            'agency',
            [2000],
            test_user.id,
        )


def test_analysis_routes_map_validation_permission_not_found_and_failures(
    app, auth_client, db_session, test_user, temporal_experiment, monkeypatch
):
    from app.routes.experiments import evolution
    from app.services.base_service import PermissionError

    invalid = auth_client.post(
        f'/experiments/{temporal_experiment.id}/analyze_evolution',
        json={'term': '', 'periods': []},
    )
    missing = auth_client.post(
        '/experiments/999999/analyze_evolution',
        json={'term': 'agency', 'periods': [2000]},
    )
    monkeypatch.setattr(
        evolution.evolution_service,
        'analyze_evolution',
        lambda *args, **kwargs: (_ for _ in ()).throw(PermissionError('secret')),
    )
    forbidden = auth_client.post(
        f'/experiments/{temporal_experiment.id}/analyze_evolution',
        json={'term': 'agency', 'periods': [2000]},
    )
    monkeypatch.setattr(
        evolution.evolution_service,
        'analyze_evolution',
        lambda *args, **kwargs: (_ for _ in ()).throw(
            RuntimeError('secret analysis exception')
        ),
    )
    failure = auth_client.post(
        f'/experiments/{temporal_experiment.id}/analyze_evolution',
        json={'term': 'agency', 'periods': [2000]},
    )

    assert invalid.status_code == 400
    assert invalid.get_json()['error'] == 'Validation failed'
    assert json.loads(json.dumps(invalid.get_json()['details']))
    assert missing.status_code == 404
    assert forbidden.status_code == 403
    assert forbidden.get_json()['error'] == 'Permission denied'
    assert failure.status_code == 500
    assert failure.get_json()['error'] == 'Failed to analyze evolution'
    assert 'secret' not in str(failure.get_json())


def test_analysis_route_requires_authentication(app, temporal_experiment):
    response = app.test_client().post(
        f'/experiments/{temporal_experiment.id}/analyze_evolution',
        json={'term': 'agency', 'periods': [2000]},
    )
    assert response.status_code == 401


def test_public_visualization_hides_enrichment_from_non_owner(
    app, db_session, test_user, tmp_path, monkeypatch
):
    from app.routes.experiments import evolution
    from app.services.evolution_service import EvolutionService

    term, _ = _term(db_session, test_user, 'visibility', extraction_method='history')
    experiment = _experiment(db_session, test_user, term, 'visibility')
    service = EvolutionService(data_root=tmp_path)
    monkeypatch.setattr(evolution, 'evolution_service', service)
    stranger = _user(db_session, 'visualization-viewer')
    public = app.test_client().get(
        f'/experiments/{experiment.id}/semantic_evolution_visual'
    )
    viewer = app.test_client()
    with viewer.session_transaction() as session:
        session['_user_id'] = str(stranger.id)
        session['_fresh'] = True
    viewed = viewer.get(
        f'/experiments/{experiment.id}/semantic_evolution_visual'
    )

    assert public.status_code == 200
    assert viewed.status_code == 200
    assert b'Enrich with OED Data' not in public.data
    assert b'Enrich with OED Data' not in viewed.data
