"""Regression coverage for configured Merriam-Webster lookup workflows."""

from datetime import datetime
import pytest
import requests


class FakeResponse:
    def __init__(self, data=None, error=None):
        self.data = data
        self.error = error

    def raise_for_status(self):
        if self.error:
            raise self.error

    def json(self):
        if isinstance(self.data, Exception):
            raise self.data
        return self.data


class RecordingHttpClient:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def get(self, url, params=None, timeout=None):
        self.calls.append((url, params, timeout))
        return self.response


def _service(http, **kwargs):
    from app.services.merriam_webster_service import MerriamWebsterService

    return MerriamWebsterService(
        dictionary_key=kwargs.pop('dictionary_key', 'dictionary-key'),
        thesaurus_key=kwargs.pop('thesaurus_key', 'thesaurus-key'),
        timeout=kwargs.pop('timeout', 3.5),
        http_client=http,
        clock=kwargs.pop('clock', lambda: datetime(2026, 7, 9, 12, 0, 0)),
        **kwargs,
    )


def test_merriam_routes_remain_canonical(app):
    for endpoint in (
        'merriam.search_dictionary',
        'merriam.search_thesaurus',
        'merriam.test_api',
    ):
        assert app.view_functions[endpoint].__module__ == (
            'app.routes.merriam_webster'
        )


def test_dictionary_lookup_encodes_term_and_normalizes_response():
    upstream = [{
        'meta': {
            'id': 'agent:1',
            'offensive': False,
            'extra': 'not exposed',
        },
        'hwi': {
            'hw': 'agent',
            'prs': [{'mw': 'ˈā-jənt'}],
        },
        'fl': 'noun',
        'shortdef': ['one that acts'],
        'et': [['text', 'Latin agere']],
        'date': '15th century',
        'copyright': 'not exposed',
    }, 'agency suggestion']
    http = RecordingHttpClient(FakeResponse(upstream))

    payload = _service(http).search_dictionary('agent / proxy')

    assert http.calls == [(
        'https://www.dictionaryapi.com/api/v3/references/collegiate/json/'
        'agent%20%2F%20proxy',
        {'key': 'dictionary-key'},
        3.5,
    )]
    assert payload == {
        'success': True,
        'term': 'agent / proxy',
        'service': 'dictionary',
        'results': [{
            'id': 'agent:1',
            'word': 'agent',
            'pronunciation': [{'mw': 'ˈā-jənt'}],
            'functional_label': 'noun',
            'definitions': ['one that acts'],
            'etymology': [['text', 'Latin agere']],
            'date': '15th century',
            'offensive': False,
        }],
        'citation': (
            'Merriam-Webster.com Dictionary, s.v. "agent / proxy," '
            'accessed July 09, 2026, '
            'https://www.merriam-webster.com/dictionary/agent%20%2F%20proxy.'
        ),
        'access_date': 'July 09, 2026',
        'current_year': 2026,
    }
    assert 'raw_data' not in payload


def test_thesaurus_lookup_normalizes_synonyms_and_antonyms():
    http = RecordingHttpClient(FakeResponse([{
        'meta': {
            'id': 'agency:1',
            'syns': [['action', 'capacity']],
            'ants': [['inaction']],
        },
        'hwi': {'hw': 'agency'},
        'fl': 'noun',
        'shortdef': ['capacity for action'],
    }]))
    payload = _service(http).search_thesaurus('agency')

    assert payload['service'] == 'thesaurus'
    assert payload['results'] == [{
        'id': 'agency:1',
        'word': 'agency',
        'functional_label': 'noun',
        'synonyms': [['action', 'capacity']],
        'antonyms': [['inaction']],
        'shortdef': ['capacity for action'],
    }]
    assert payload['citation'].startswith('Merriam-Webster.com Thesaurus')
    assert http.calls[0][1] == {'key': 'thesaurus-key'}


def test_suggestion_only_response_returns_no_normalized_entries():
    payload = _service(
        RecordingHttpClient(FakeResponse(['agency', 'agent']))
    ).search_dictionary('agenc')
    assert payload['success'] is True
    assert payload['results'] == []


def test_missing_term_and_credentials_raise_typed_errors():
    from app.services.base_service import ValidationError
    from app.services.merriam_webster_service import (
        MerriamWebsterConfigurationError,
    )

    http = RecordingHttpClient(FakeResponse([]))
    service = _service(http, dictionary_key=None)
    with pytest.raises(ValidationError, match='Search term is required'):
        service.search_dictionary('  ')
    with pytest.raises(MerriamWebsterConfigurationError, match='not configured'):
        service.search_dictionary('agency')
    assert http.calls == []


@pytest.mark.parametrize(
    'response',
    [
        FakeResponse(error=requests.Timeout('secret timeout detail')),
        FakeResponse(ValueError('invalid JSON detail')),
        FakeResponse({'not': 'a list'}),
    ],
)
def test_upstream_failures_raise_sanitized_error(response):
    from app.services.merriam_webster_service import MerriamWebsterUpstreamError

    with pytest.raises(MerriamWebsterUpstreamError, match='lookup failed|invalid response') as exc:
        _service(RecordingHttpClient(response)).search_dictionary('agency')
    assert 'secret timeout detail' not in str(exc.value)
    assert 'invalid JSON detail' not in str(exc.value)


def test_configuration_status_exposes_presence_only():
    status = _service(
        RecordingHttpClient(FakeResponse([])),
        dictionary_key='secret-dictionary',
        thesaurus_key=None,
    ).configuration_status()
    assert status == {'dictionary': True, 'thesaurus': False}
    assert 'secret-dictionary' not in str(status)


def test_dictionary_and_thesaurus_routes_return_normalized_payloads(
    app, monkeypatch
):
    from app.routes import merriam_webster

    class FakeService:
        def search_dictionary(self, term):
            return {'success': True, 'term': term, 'results': [{'definitions': ['d']}]}

        def search_thesaurus(self, term):
            return {'success': True, 'term': term, 'results': [{'synonyms': [['s']]}]}

        @staticmethod
        def configuration_status():
            return {'dictionary': True, 'thesaurus': True}

    monkeypatch.setattr(merriam_webster, '_service', lambda: FakeService())
    client = app.test_client()
    dictionary = client.get('/api/merriam-webster/dictionary/agency')
    thesaurus = client.get('/api/merriam-webster/thesaurus/agency')
    status = client.get('/api/merriam-webster/test')

    assert dictionary.status_code == 200
    assert dictionary.get_json()['results'][0]['definitions'] == ['d']
    assert thesaurus.status_code == 200
    assert thesaurus.get_json()['results'][0]['synonyms'] == [['s']]
    assert status.get_json()['api_keys_configured'] == {
        'dictionary': True,
        'thesaurus': True,
    }


def test_routes_map_configuration_and_upstream_failures(app, monkeypatch):
    from app.routes import merriam_webster
    from app.services.merriam_webster_service import (
        MerriamWebsterConfigurationError,
        MerriamWebsterUpstreamError,
    )

    class MissingConfig:
        @staticmethod
        def search_dictionary(term):
            raise MerriamWebsterConfigurationError('Dictionary API is not configured')

    monkeypatch.setattr(merriam_webster, '_service', lambda: MissingConfig())
    missing = app.test_client().get(
        '/api/merriam-webster/dictionary/agency'
    )
    assert missing.status_code == 503
    assert missing.get_json()['error'] == 'Dictionary API is not configured'

    class UpstreamFailure:
        @staticmethod
        def search_thesaurus(term):
            raise MerriamWebsterUpstreamError('internal secret transport details')

    monkeypatch.setattr(
        merriam_webster,
        '_service',
        lambda: UpstreamFailure(),
    )
    failure = app.test_client().get(
        '/api/merriam-webster/thesaurus/agency'
    )
    assert failure.status_code == 502
    assert failure.get_json() == {
        'success': False,
        'error': 'Failed to fetch thesaurus data',
    }
    assert 'secret' not in str(failure.get_json())


def test_source_contains_no_hardcoded_merriam_webster_keys():
    import ast
    from pathlib import Path

    repository = Path(__file__).resolve().parents[1]
    route_source = (repository / 'app/routes/merriam_webster.py').read_text()
    config_source = (repository / 'config/__init__.py').read_text()
    route_tree = ast.parse(route_source)
    assigned_names = {
        target.id
        for node in ast.walk(route_tree)
        if isinstance(node, (ast.Assign, ast.AnnAssign))
        for target in (
            node.targets if isinstance(node, ast.Assign) else [node.target]
        )
        if isinstance(target, ast.Name)
    }
    assert 'API_KEYS' not in assigned_names
    assert "os.environ.get('MERRIAM_WEBSTER_DICTIONARY_API_KEY')" in config_source
    assert "os.environ.get('MERRIAM_WEBSTER_THESAURUS_API_KEY')" in config_source
