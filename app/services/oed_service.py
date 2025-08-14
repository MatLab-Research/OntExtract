from __future__ import annotations

from typing import Any, Dict, Optional
from flask import current_app

from .oed_api_client import OEDApiClient, OEDApiError

class OEDService:
    """Facade selecting between local PDF parsing and OED API, based on config.

    - If OED_USE_API=true and credentials configured, use API.
    - Otherwise fall back to the existing high-fidelity PDF parser.
    """

    def __init__(self) -> None:
        self.use_api = bool(current_app.config.get('OED_USE_API'))

    def get_entry(self, headword: str) -> Dict[str, Any]:
        if self.use_api:
            try:
                client = OEDApiClient()
                # No headword search endpoint specified in example; return error for now
                return {"success": False, "error": "Headword search not supported; use entry_id (e.g., orchestra_nn01)"}
            except OEDApiError as e:
                # Surface a friendly error; caller can decide how to display
                return {"success": False, "error": str(e)}
        # Fallback: return structured result from local PDF extraction not implemented here
        return {"success": False, "error": "Local fallback requires PDF; not available for headword lookup"}

    def parse_pdf_entry(self, pdf_path: str) -> Dict[str, Any]:
        if self.use_api:
            return {"success": False, "error": "Configured to use API; PDF parsing disabled for OED"}
        # Use the existing layout-preserving parser
        from app.services.oed_parser_final import OEDParser as LayoutOEDParser
        parser = LayoutOEDParser()
        data = parser.parse_pdf(pdf_path)
        return {"success": True, "data": data}

    def get_word(self, entry_id: str) -> Dict[str, Any]:
        if not self.use_api:
            return {"success": False, "error": "OED API is disabled"}
        try:
            client = OEDApiClient()
            data = client.get_word(entry_id)
            # Attach a flattened, minimal sense list for downstream selection/analysis.
            data["extracted_senses"] = self._extract_senses(data)
            return {"success": True, "data": data}
        except OEDApiError as e:
            return {"success": False, "error": str(e)}

    def get_quotations(self, entry_id: str, *, limit: Optional[int] = None, offset: Optional[int] = None) -> Dict[str, Any]:
        if not self.use_api:
            return {"success": False, "error": "OED API is disabled"}
        try:
            client = OEDApiClient()
            data = client.get_quotations(entry_id, limit=limit, offset=offset)
            return {"success": True, "data": data}
        except OEDApiError as e:
            return {"success": False, "error": str(e)}

    def suggest_ids(self, headword: str, *, limit: int = 6) -> Dict[str, Any]:
        """Heuristically suggest likely OED entry_ids for a headword.

        Tries a short list of common POS patterns to minimize API calls and respect rate limits.
        Examples: orchestra -> orchestra_nn01, orchestra_vb01, orchestra_aj01, orchestra_av01
        """
        if not self.use_api:
            return {"success": False, "error": "OED API is disabled"}
        try:
            client = OEDApiClient()
        except OEDApiError as e:
            return {"success": False, "error": str(e)}

        import re
        base = headword.strip().lower()
        base = re.sub(r"\s+", "-", base)
        base = re.sub(r"[^a-z0-9\-]", "", base)
        if not base:
            return {"success": False, "error": "Invalid headword"}

        # Try a small set of common POS codes with limited sense numbers to respect rate limits
        try_list = []
        for pos, rng in (
            ("nn", range(1, 5)),   # noun: 01..04
            ("vb", range(1, 4)),   # verb: 01..03
            ("aj", range(1, 3)),   # adjective: 01..02
            ("av", range(1, 2)),   # adverb: 01
        ):
            for i in rng:
                try_list.append(f"{pos}{i:02d}")

        suggestions: list[dict] = []
        errors: list[str] = []
        for code in try_list:
            entry_id = f"{base}_{code}"
            try:
                data = client.get_word(entry_id)
                if isinstance(data, dict):
                    suggestions.append({
                        "entry_id": entry_id,
                        "headword": data.get("headword") or data.get("word") or base
                    })
                if len(suggestions) >= limit:
                    break
            except OEDApiError as e:
                if len(errors) < 2:
                    errors.append(str(e))
                continue

        return {"success": True, "suggestions": suggestions, "tried": min(len(try_list), len(suggestions) + len(errors))}

    # ---------------- internal helpers -----------------
    @staticmethod
    def _extract_senses(payload: Dict[str, Any]) -> list[Dict[str, str]]:
        """Recursively traverse the API payload to collect sense-like objects.

        We only retain strictly minimal, non-infringing metadata:
        - sense_id (or id/oid fallback)
        - label (if present)
        - definition excerpt: first 20 words (<=200 chars) only
        - hierarchical path (dot-notation indices) to help with future mapping
        """
        senses: list[Dict[str, str]] = []

        def add_sense(obj: Dict[str, Any], path: str):
            sid = obj.get('sense_id') or obj.get('id') or obj.get('oid')
            if not sid:
                return
            label = obj.get('label') or ''
            definition = obj.get('definition') or ''
            if isinstance(definition, list):
                definition = definition[0] if definition else ''
            excerpt = ''
            if isinstance(definition, str) and definition.strip():
                words = definition.split()
                excerpt = ' '.join(words[:20])
                if len(excerpt) > 200:
                    excerpt = excerpt[:200]
            senses.append({
                'sense_id': str(sid),
                'label': label,
                'definition': excerpt,
                'path': path
            })

        def walk(node: Any, path: str = ''):
            if isinstance(node, dict):
                # If it looks like a sense object, add it
                if any(k in node for k in ('sense_id', 'definition')):
                    add_sense(node, path or 'root')
                # Recurse into likely child collections
                for k, v in node.items():
                    if isinstance(v, (dict, list)):
                        walk(v, f"{path}.{k}" if path else k)
            elif isinstance(node, list):
                for idx, item in enumerate(node):
                    walk(item, f"{path}[{idx}]")

        walk(payload)
        # Deduplicate by sense_id preserving first occurrence (which has shortest path typically)
        seen = set()
        unique: list[Dict[str, str]] = []
        for s in senses:
            if s['sense_id'] in seen:
                continue
            seen.add(s['sense_id'])
            unique.append(s)
        return unique

    def get_variants(self, headword: str, *, limit: int = 6) -> Dict[str, Any]:
        """Retrieve multiple POS variants (entry_ids) for a base headword and return minimal metadata.

        This expands upon suggest_ids by also returning the flattened sense metadata
        (extracted_senses) for each variant so the UI can show all possible POS groups.
        """
        if not self.use_api:
            return {"success": False, "error": "OED API is disabled"}
        base = headword.strip()
        if not base:
            return {"success": False, "error": "Empty headword"}
        suggestions = self.suggest_ids(base, limit=limit)
        if not suggestions.get('success'):
            return suggestions
        collected = []
        for s in suggestions.get('suggestions', []):
            entry_id = s.get('entry_id')
            if not entry_id:
                continue
            w = self.get_word(entry_id)
            if not w.get('success'):
                continue
            payload = w.get('data') or {}
            minimal = {
                'entry_id': entry_id,
                'headword': payload.get('headword') or payload.get('word') or base,
                'part_of_speech': payload.get('pos') or payload.get('part_of_speech'),
                'extracted_senses': payload.get('extracted_senses') or []
            }
            collected.append(minimal)
        return {"success": True, "variants": collected}
