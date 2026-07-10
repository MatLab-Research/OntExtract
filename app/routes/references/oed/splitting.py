"""Split OED references into sense-level child references."""

from flask import flash, redirect, url_for
from flask_login import current_user

from app import db
from app.models.document import Document
from app.utils.auth_decorators import api_require_login_for_write

from .. import references_bp


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
