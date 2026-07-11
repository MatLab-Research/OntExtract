"""Merriam-Webster dictionary and thesaurus lookup client."""

from datetime import datetime
from urllib.parse import quote

import requests

from app.services.base_service import ServiceError, ValidationError


class MerriamWebsterConfigurationError(ServiceError):
    """A required Merriam-Webster API credential is not configured."""


class MerriamWebsterUpstreamError(ServiceError):
    """The Merriam-Webster upstream request could not be completed."""


class MerriamWebsterService:
    """Fetch and normalize Merriam-Webster API responses."""

    API_URLS = {
        'dictionary': (
            'https://www.dictionaryapi.com/api/v3/references/collegiate/json'
        ),
        'thesaurus': (
            'https://www.dictionaryapi.com/api/v3/references/thesaurus/json'
        ),
    }
    WEB_URLS = {
        'dictionary': 'https://www.merriam-webster.com/dictionary',
        'thesaurus': 'https://www.merriam-webster.com/thesaurus',
    }
    SERVICE_LABELS = {
        'dictionary': 'Merriam-Webster.com Dictionary',
        'thesaurus': 'Merriam-Webster.com Thesaurus',
    }

    def __init__(
        self,
        dictionary_key=None,
        thesaurus_key=None,
        timeout=10,
        http_client=None,
        clock=None,
    ):
        self.api_keys = {
            'dictionary': dictionary_key,
            'thesaurus': thesaurus_key,
        }
        self.timeout = float(timeout)
        self.http_client = http_client or requests
        self.clock = clock or datetime.now

    def search_dictionary(self, term):
        return self._search(term, 'dictionary')

    def search_thesaurus(self, term):
        return self._search(term, 'thesaurus')

    def configuration_status(self):
        return {
            service: bool(key)
            for service, key in self.api_keys.items()
        }

    def _search(self, term, service):
        term = term.strip() if isinstance(term, str) else ''
        if not term:
            raise ValidationError('Search term is required')
        api_key = self.api_keys[service]
        if not api_key:
            raise MerriamWebsterConfigurationError(
                f'Merriam-Webster {service} API is not configured'
            )
        encoded_term = quote(term, safe='')
        url = f'{self.API_URLS[service]}/{encoded_term}'
        try:
            response = self.http_client.get(
                url,
                params={'key': api_key},
                timeout=self.timeout,
            )
            response.raise_for_status()
            data = response.json()
        except (requests.RequestException, ValueError, TypeError) as exc:
            raise MerriamWebsterUpstreamError(
                f'Merriam-Webster {service} lookup failed'
            ) from exc
        if not isinstance(data, list):
            raise MerriamWebsterUpstreamError(
                f'Merriam-Webster {service} returned an invalid response'
            )

        now = self.clock()
        return {
            'success': True,
            'term': term,
            'service': service,
            'results': self._normalize(data, service),
            'citation': self._citation(term, service, now),
            'access_date': now.strftime('%B %d, %Y'),
            'current_year': now.year,
        }

    @staticmethod
    def _normalize(data, service):
        results = []
        for entry in data:
            if not isinstance(entry, dict) or 'meta' not in entry:
                continue
            if service == 'dictionary':
                results.append({
                    'id': entry.get('meta', {}).get('id', ''),
                    'word': entry.get('hwi', {}).get('hw', ''),
                    'pronunciation': entry.get('hwi', {}).get('prs', []),
                    'functional_label': entry.get('fl', ''),
                    'definitions': entry.get('shortdef', []),
                    'etymology': entry.get('et', []),
                    'date': entry.get('date', ''),
                    'offensive': entry.get('meta', {}).get(
                        'offensive', False
                    ),
                })
            else:
                results.append({
                    'id': entry.get('meta', {}).get('id', ''),
                    'word': entry.get('hwi', {}).get('hw', ''),
                    'functional_label': entry.get('fl', ''),
                    'synonyms': entry.get('meta', {}).get('syns', []),
                    'antonyms': entry.get('meta', {}).get('ants', []),
                    'shortdef': entry.get('shortdef', []),
                })
        return results

    def _citation(self, term, service, now):
        web_term = quote(term, safe='')
        return (
            f'{self.SERVICE_LABELS[service]}, s.v. "{term}," accessed '
            f'{now.strftime("%B %d, %Y")}, '
            f'{self.WEB_URLS[service]}/{web_term}.'
        )
