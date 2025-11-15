"""
References OED Operations Routes

This module handles Oxford English Dictionary (OED) operations and API endpoints.

Routes:
- GET  /references/api/oed/entry                    - Lookup OED entry by headword
- GET  /references/api/oed/word/<entry_id>          - Get OED word details
- GET  /references/api/oed/word/<entry_id>/quotations - Get OED quotations
- GET  /references/api/oed/suggest                  - OED entry suggestions
- GET  /references/api/oed/variants                 - OED variant forms
- GET  /references/oed/new                          - New OED reference form
- POST /references/oed/add                          - Add OED reference
- POST /references/oed/add_batch                    - Batch add OED references
- POST /references/oed/split/<parent_id>            - Split OED entry by senses
"""

from flask import render_template, request, redirect, url_for, flash, jsonify, current_app
from flask_login import current_user
from app.utils.auth_decorators import api_require_login_for_write
from app import db
from app.models.document import Document
from app.models.experiment import Experiment
from app.services.oed_service import OEDService

from . import references_bp


@references_bp.route('/api/oed/entry')
@api_require_login_for_write
def api_oed_entry():
    """Lookup an OED entry by headword via OED API (if enabled)."""
    headword = request.args.get('q', '').strip()
    if not headword:
        return jsonify({"success": False, "error": "Missing 'q' query param"}), 400

    svc = OEDService()
    data = svc.get_entry(headword)
    status = 200 if data.get('success', True) else 502
    return jsonify(data), status


@references_bp.route('/api/oed/word/<entry_id>')
@api_require_login_for_write
def api_oed_word(entry_id: str):
    svc = OEDService()
    data = svc.get_word(entry_id)
    status = 200 if data.get('success', True) else 502
    return jsonify(data), status


@references_bp.route('/api/oed/word/<entry_id>/quotations')
@api_require_login_for_write
def api_oed_word_quotations(entry_id: str):
    svc = OEDService()
    # Optional pagination
    try:
        limit_str = request.args.get('limit')
        offset_str = request.args.get('offset')
        limit = int(limit_str) if isinstance(limit_str, str) and limit_str.strip() else None
        offset = int(offset_str) if isinstance(offset_str, str) and offset_str.strip() else None
    except ValueError:
        return jsonify({"success": False, "error": "limit/offset must be integers"}), 400
    data = svc.get_quotations(entry_id, limit=limit, offset=offset)
    status = 200 if data.get('success', True) else 502
    return jsonify(data), status


@references_bp.route('/api/oed/suggest')
@api_require_login_for_write
def api_oed_suggest():
    q = (request.args.get('q') or '').strip()
    if not q:
        return jsonify({"success": False, "error": "Missing 'q' headword"}), 400
    svc = OEDService()
    data = svc.suggest_ids(q)
    status = 200 if data.get('success', True) else 502
    return jsonify(data), status


@references_bp.route('/api/oed/variants')
@api_require_login_for_write
def api_oed_variants():
    q = (request.args.get('q') or '').strip()
    if not q:
        return jsonify({"success": False, "error": "Missing 'q' headword"}), 400
    svc = OEDService()
    data = svc.get_variants(q)
    status = 200 if data.get('success', True) else 502
    return jsonify(data), status


@references_bp.route('/oed/new')
@api_require_login_for_write
def new_oed_reference():
    """Render a page to add an OED entry as a reference.

    For now we accept an entry_id (e.g., orchestra_nn01). We'll offer a preview via the API.
    """
    experiment_id = request.args.get('experiment_id')
    return render_template('references/add_oed.html', experiment_id=experiment_id)


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
            return redirect(url_for('experiments.view', id=experiment_id))

    flash(f'Added OED reference for "{headword}"', 'success')
    return redirect(url_for('references.view', id=document.id))


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
            return redirect(url_for('experiments.view', id=experiment_id))

    return redirect(url_for('references.index'))


@references_bp.route('/oed/split/<int:parent_id>', methods=['POST'])
@api_require_login_for_write
def split_oed_reference(parent_id: int):
    """Create individual child reference documents for each selected sense under a master OED entry.

    The parent remains a summary entry; children receive parent_document_id.
    """
    parent_doc = Document.query.filter_by(id=parent_id, document_type='reference').first_or_404()
    meta = parent_doc.source_metadata or {}
    selected = meta.get('selected_senses') or []
    if not selected:
        flash('No senses stored on this reference to split.', 'warning')
        return redirect(url_for('references.view', id=parent_doc.id))

    created = 0
    existing_child_ids = {child.source_metadata.get('sense_id') for child in parent_doc.children if child.source_metadata}
    for s in selected:
        sid = s.get('sense_id')
        if not sid or sid in existing_child_ids:
            continue
        # Build minimal child content
        label = s.get('label') or ''
        definition = s.get('definition') or ''
        child_title = f"OED: {meta.get('headword','')} [{sid}]"
        child_content = f"OED {meta.get('oed_entry_id','')} Sense {sid}\nHeadword: {meta.get('headword','')}"
        if label:
            child_content += f"\nLabel: {label}"
        if definition:
            child_content += f"\nDefinition excerpt: {definition}"
        child_meta = {
            'source': 'OED Researcher API',
            'oed_entry_id': meta.get('oed_entry_id'),
            'headword': meta.get('headword'),
            'part_of_speech': meta.get('part_of_speech'),
            'sense_id': sid,
            'label': label,
            'definition': definition,
            'parent_reference_id': parent_doc.id,
        }
        child_doc = Document(
            title=child_title,
            content_type='text',
            document_type='reference',
            reference_subtype='dictionary_oed',
            content=child_content,
            content_preview=child_content[:500],
            source_metadata=child_meta,
            user_id=current_user.id,
            status='completed',
            word_count=len(child_content.split()),
            character_count=len(child_content),
            parent_document_id=parent_doc.id
        )
        db.session.add(child_doc)
        created += 1
    if created:
        db.session.commit()
        flash(f'Created {created} sense-level reference(s).', 'success')
    else:
        flash('No new sense references created (perhaps already split).', 'info')
    return redirect(url_for('references.view', id=parent_doc.id))
