"""Build unsaved reference documents from OED entries."""

from flask import current_app

from app.models.document import Document
from app.services.oed_service import OEDService


def _build_oed_reference(entry_id: str, user_id: int, selected_sense_ids: list[str] | None = None, title_override: str | None = None):
    """Internal helper to construct an OED reference document (not committed).

    Returns (Document, error_message|None)
    """
    svc = OEDService()
    data = svc.get_word(entry_id)
    if not data.get('success'):
        return None, data.get('error', 'lookup failed')
    api_payload = data.get('data') or {}
    headword = api_payload.get('headword') or api_payload.get('word') or entry_id
    pos = api_payload.get('pos') or api_payload.get('part_of_speech')

    # gather senses (flatten if service provided extracted_senses)
    senses_flat = api_payload.get('extracted_senses') or []
    # fallback to top-level senses
    if not senses_flat and isinstance(api_payload.get('senses'), list):
        senses_flat = api_payload['senses']

    # If no explicit selection list provided, include all senses
    chosen_ids = set(selected_sense_ids) if selected_sense_ids else {s.get('sense_id') or s.get('id') or s.get('oid') for s in senses_flat}
    selected_senses: list[dict] = []
    for s in senses_flat:
        sid = str(s.get('sense_id') or s.get('id') or s.get('oid') or '')
        if not sid or sid not in chosen_ids:
            continue
        definition = s.get('definition')
        if isinstance(definition, list):
            definition = definition[0] if definition else ''
        excerpt = ''
        if isinstance(definition, str) and definition.strip():
            words = definition.split()
            excerpt = ' '.join(words[:20])
            if len(excerpt) > 200:
                excerpt = excerpt[:200]
        selected_senses.append({
            'sense_id': sid,
            'label': s.get('label', ''),
            'definition': excerpt
        })

    content = f"OED entry: {entry_id}\nHeadword: {headword}"
    if pos:
        content += f"\nPart of speech: {pos}"
    if selected_senses:
        content += f"\nSelected senses: {', '.join(ss['sense_id'] for ss in selected_senses)}"

    _api_base = (current_app.config.get('OED_API_BASE_URL') or 'https://oed-researcher-api.oxfordlanguages.com/oed/api/v0.2').rstrip('/')
    oed_api_word_url = f"{_api_base}/word/{entry_id}/"
    oed_web_search_url = f"https://www.oed.com/search/dictionary/?q={headword}"

    source_metadata = {
        'source': 'OED Researcher API',
        'oed_entry_id': entry_id,
        'headword': headword,
        'part_of_speech': pos,
        'oed_api_word_url': oed_api_word_url,
        'oed_web_search_url': oed_web_search_url,
    }
    if selected_senses:
        source_metadata['selected_senses'] = selected_senses

    title = title_override or f"OED: {headword}"

    doc = Document(
        title=title,
        content_type='text',
        document_type='reference',
        reference_subtype='dictionary_oed',
        content=content,
        content_preview=content[:500],
        source_metadata=source_metadata,
        user_id=user_id,
        status='completed',
        word_count=len(content.split()),
        character_count=len(content)
    )
    return doc, None
