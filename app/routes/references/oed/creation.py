"""Single and batch OED reference creation routes."""

from flask import current_app, flash, redirect, request, url_for
from flask_login import current_user

from app import db
from app.models.document import Document
from app.models.experiment import Experiment
from app.services.oed_service import OEDService
from app.utils.auth_decorators import api_require_login_for_write

from .. import references_bp
from .builder import _build_oed_reference


@references_bp.route('/oed/add', methods=['POST'])
@api_require_login_for_write
def add_oed_reference():
    """Create a reference Document from an OED entry_id, allowing sense selection and storing minimal sense info."""
    entry_id = (request.form.get('entry_id') or '').strip()
    if not entry_id:
        flash('Entry ID is required (e.g., orchestra_nn01)', 'error')
        return redirect(url_for('references.new_oed_reference', experiment_id=request.form.get('experiment_id')))

    svc = OEDService()
    data = svc.get_word(entry_id)
    if not data.get('success'):
        flash(f"OED lookup failed: {data.get('error','unknown error')}", 'error')
        return redirect(url_for('references.new_oed_reference', experiment_id=request.form.get('experiment_id')))

    api_payload = data.get('data') or {}
    headword = api_payload.get('headword') or api_payload.get('word') or entry_id
    pos = api_payload.get('pos') or api_payload.get('part_of_speech')

    # Robustly extract all senses (flatten nested, handle various field names)
    def extract_senses(senses):
        result = []
        for s in senses:
            # Some OED entries nest senses under 'subsenses' or similar
            sid = str(s.get('sense_id') or s.get('id') or s.get('oid') or '')
            label = s.get('label', '')
            # Use only a short excerpt of the definition (first 200 chars, no full text)
            definition = s.get('definition', '')
            if isinstance(definition, list):
                definition = definition[0] if definition else ''
            if definition:
                # Only keep a short excerpt (first 20 words or 200 chars)
                words = definition.split()
                excerpt = ' '.join(words[:20])
                if len(excerpt) > 200:
                    excerpt = excerpt[:200]
                definition_excerpt = excerpt
            else:
                definition_excerpt = ''
            if sid:
                result.append({
                    'sense_id': sid,
                    'label': label,
                    'definition': definition_excerpt
                })
            # Recursively extract from subsenses if present
            for subfield in ['subsenses', 'children', 'senses']:
                if subfield in s and isinstance(s[subfield], list):
                    result.extend(extract_senses(s[subfield]))
        return result

    # Prefer server-provided flattened senses if available
    extracted_flat = api_payload.get('extracted_senses') or []
    senses = extract_senses(api_payload.get('senses') or [])
    # Merge with extracted_senses (use dict by id to avoid duplication)
    sense_map = {s['sense_id']: s for s in senses if s.get('sense_id')}
    for es in extracted_flat:
        sid = es.get('sense_id')
        if sid and sid not in sense_map:
            # Keep only minimal approved fields
            sense_map[sid] = {
                'sense_id': sid,
                'label': es.get('label', ''),
                'definition': es.get('definition', '')
            }
    senses = list(sense_map.values())
    selected_sense_ids = request.form.getlist('sense_id')
    selected_senses = [s for s in senses if s['sense_id'] in selected_sense_ids]

    # Build minimal, non-infringing content
    content = f"OED entry: {entry_id}\nHeadword: {headword}"
    if pos:
        content += f"\nPart of speech: {pos}"
    if selected_senses:
        content += f"\nSelected senses: {', '.join([ss['sense_id'] for ss in selected_senses])}"

    title = (request.form.get('title') or '').strip() or f"OED: {headword}"

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

    document = Document(
        title=title,
        content_type='text',
        document_type='reference',
        reference_subtype='dictionary_oed',
        content=content,
        content_preview=content[:500],
        source_metadata=source_metadata,
        user_id=current_user.id,
        status='completed',
        word_count=len(content.split()),
        character_count=len(content)
    )

    db.session.add(document)
    db.session.commit()

    experiment_id = request.form.get('experiment_id')
    if experiment_id:
        experiment = Experiment.query.get(experiment_id)
        if experiment and experiment.user_id == current_user.id:
            experiment.add_reference(document, include_in_analysis=(request.form.get('include_in_analysis') == 'true'))
            flash(f'Reference linked to experiment "{experiment.name}"', 'success')
            return redirect(url_for('experiments.view', experiment_id=experiment_id))

    flash(f'Added OED reference for "{headword}"', 'success')
    return redirect(url_for('references.view', id=document.id))
@references_bp.route('/oed/add_batch', methods=['POST'])
@api_require_login_for_write
def add_oed_references_batch():
    """Batch add multiple OED entry_ids (each with all senses by default)."""
    entry_ids = request.form.getlist('entry_id')
    if not entry_ids:
        flash('No entry IDs selected.', 'error')
        return redirect(url_for('references.new_oed_reference', experiment_id=request.form.get('experiment_id')))

    added = 0
    errors: list[str] = []
    docs: list[Document] = []
    for eid in entry_ids:
        eid_clean = (eid or '').strip()
        if not eid_clean:
            continue
        built_doc, err = _build_oed_reference(eid_clean, current_user.id, selected_sense_ids=None)
        if err or built_doc is None:
            errors.append(f"{eid_clean}: {err}")
            continue
        db.session.add(built_doc)
        docs.append(built_doc)
        added += 1
    if docs:
        db.session.commit()

    if added:
        flash(f'Added {added} OED reference(s).', 'success')
    if errors:
        flash('Some entries failed: ' + '; '.join(errors[:4]) + (' …' if len(errors) > 4 else ''), 'warning')

    experiment_id = request.form.get('experiment_id')
    if experiment_id and added:
        experiment = Experiment.query.get(experiment_id)
        if experiment and experiment.user_id == current_user.id:
            for d in docs:
                experiment.add_reference(d, include_in_analysis=(request.form.get('include_in_analysis') == 'true'))
            db.session.commit()
            flash(f'Linked to experiment "{experiment.name}"', 'success')
            return redirect(url_for('experiments.view', experiment_id=experiment_id))

    return redirect(url_for('references.index'))
