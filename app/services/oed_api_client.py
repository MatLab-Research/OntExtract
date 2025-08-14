import os
import time
from typing import Any, Dict, Optional

import httpx
from flask import current_app

class OEDApiError(Exception):
    pass

class OEDApiClient:
    """Thin client for OED Researcher API.

    Auth: App ID + Access Key via headers.
    Base URL is expected to be provided; endpoints depend on API version.
    """

    def __init__(self,
                 app_id: Optional[str] = None,
                 access_key: Optional[str] = None,
                 base_url: Optional[str] = None,
                 timeout: Optional[float] = None):
        self.app_id = app_id or os.environ.get('OED_APP_ID')
        self.access_key = access_key or os.environ.get('OED_ACCESS_KEY')
        # Default to the documented base if not provided in env
        default_base = 'https://oed-researcher-api.oxfordlanguages.com/oed/api/v0.2'
        self.base_url = (base_url or current_app.config.get('OED_API_BASE_URL') or default_base).rstrip('/')
        self.timeout = timeout or float(current_app.config.get('OED_API_TIMEOUT', 15))

        if not self.app_id or not self.access_key:
            raise OEDApiError("OED credentials missing: set OED_APP_ID and OED_ACCESS_KEY in env")
        if not self.base_url:
            # Docs site doesn’t expose explicit base; allow env-based override for now
            raise OEDApiError("OED API base URL not configured: set OED_API_BASE_URL in env")

        self._client = httpx.Client(timeout=self.timeout)

    def _headers(self) -> Dict[str, str]:
        # Per docs: headers are app_id and app_key
        assert self.app_id is not None and self.access_key is not None
        return {
            'app_id': str(self.app_id),
            'app_key': str(self.access_key),
            'accept': 'application/json',
            'User-Agent': 'OntExtract/0.1 (research)'
        }

    def _get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        url = f"{self.base_url}/{path.lstrip('/')}"
        resp = self._client.get(url, headers=self._headers(), params=params or {})
        if resp.status_code == 401:
            raise OEDApiError("Unauthorized: check OED_APP_ID / OED_ACCESS_KEY")
        if resp.status_code == 429:
            raise OEDApiError("Rate limited by OED API (Fair Use Policy)")
        if resp.status_code >= 400:
            raise OEDApiError(f"HTTP {resp.status_code}: {resp.text}")
        return resp.json()

    # Word endpoints per example docs
    def get_word(self, entry_id: str) -> Dict[str, Any]:
        """Fetch word details by entry id, e.g., orchestra_nn01"""
        return self._get(f"/word/{entry_id}/")

    def get_quotations(self, entry_id: str, *, limit: Optional[int] = None, offset: Optional[int] = None) -> Dict[str, Any]:
        """Fetch quotations for a word entry id."""
        params: Dict[str, Any] = {}
        if limit is not None:
            params['limit'] = limit
        if offset is not None:
            params['offset'] = offset
        return self._get(f"/word/{entry_id}/quotations/", params=params)
