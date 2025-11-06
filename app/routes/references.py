from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, send_file
from flask_login import current_user
from app.utils.auth_decorators import require_login_for_write, api_require_login_for_write
from werkzeug.utils import secure_filename
import os
import json
from datetime import datetime
from app import db
from flask import current_app
from app.models.document import Document
from app.models.experiment import Experiment
from app.services.text_processing import TextProcessingService
from app.utils.file_handler import FileHandler
from app.services.oed_service import OEDService
from app.services.wordnet_service import WordNetService

references_bp = Blueprint('references', __name__, url_prefix='/references')

@references_bp.route('/')
def index():
    """List all references for all users - public view"""
    references = Document.query.filter_by(
        document_type='reference'
    ).order_by(Document.created_at.desc()).all()
    
    return render_template('references/index.html', references=references)

@references_bp.route('/<int:id>/download')
@api_require_login_for_write
def download(id: int):
    """Download the original file for a reference document if present."""
    doc = Document.query.filter_by(id=id).first_or_404()
    if not doc.file_path:
        flash('No file attached to this reference.', 'warning')
        return redirect(url_for('references.view', id=id))
    try:
        filename = doc.original_filename or os.path.basename(doc.file_path)
        # as_attachment forces browser download
        return send_file(doc.file_path, as_attachment=True, download_name=filename)
    except Exception as e:
        flash(f'Failed to download file: {e}', 'error')
        return redirect(url_for('references.view', id=id))

@references_bp.route('/upload', methods=['GET', 'POST'])
@api_require_login_for_write
def upload():
    """Upload a new reference document"""
    # Check if we should use the new tabbed interface
    use_tabbed = request.args.get('tabbed', 'true').lower() == 'true'
    
    if request.method == 'POST':
        # Check if file was uploaded
        if 'file' not in request.files:
            flash('No file provided', 'error')
            return redirect(request.url)
        
        file = request.files['file']
        if file.filename == '':
            flash('No file selected', 'error')
            return redirect(request.url)
        
        # Get metadata from form
        title = request.form.get('title')
        reference_subtype = request.form.get('reference_subtype', 'other')
        authors = request.form.get('authors', '').split(',')
        authors = [a.strip() for a in authors if a.strip()]
        publication_date = request.form.get('publication_date')
        journal = request.form.get('journal')
        doi = request.form.get('doi')
        isbn = request.form.get('isbn')
        url = request.form.get('url')
        abstract = request.form.get('abstract')
        citation = request.form.get('citation')
        
        # Save file
        from flask import current_app
        file_handler = FileHandler()
        saved_path, file_size = file_handler.save_file(file, upload_folder=current_app.config.get('UPLOAD_FOLDER'))
        
        if not saved_path:
            flash('Failed to save file', 'error')
            return redirect(request.url)
        
        # Create source metadata
        source_metadata = {
            'authors': authors,
            'publication_date': publication_date,
            'journal': journal,
            'doi': doi,
            'isbn': isbn,
            'url': url,
            'abstract': abstract,
            'citation': citation
        }
        
        # Remove empty values
        source_metadata = {k: v for k, v in source_metadata.items() if v}

        # Create document record
        original_name = file.filename or ''
        document = Document(
            title=title or secure_filename(original_name),
            content_type='file',
            document_type='reference',
            reference_subtype=reference_subtype,
            file_type=file_handler.get_file_extension(original_name),
            original_filename=original_name,
            file_path=saved_path,
            file_size=file_size,
            source_metadata=source_metadata if source_metadata else None,
            user_id=current_user.id,
            status='uploaded'
        )
        
        # Phase 1: prefill metadata from PDF via heuristics (pypdf) and Zotero, if enabled
        try:
            fext = (file_handler.get_file_extension(original_name) or '').lower()
            if current_app.config.get('PREFILL_METADATA', True) and saved_path and fext == 'pdf':
                from app.services.reference_metadata_enricher import ReferenceMetadataEnricher
                
                # Enable Zotero lookup by default (can be disabled in config)
                use_zotero = current_app.config.get('USE_ZOTERO_METADATA', True)
                enricher = ReferenceMetadataEnricher(use_zotero=use_zotero)
                
                # Use the new method that includes Zotero lookup
                delta = enricher.extract_with_zotero(
                    saved_path, 
                    title=title,
                    existing=document.source_metadata or {}, 
                    allow_overwrite=False
                )
                
                if delta:
                    # merge into document.source_metadata and persist
                    merged = document.source_metadata or {}
                    for k, v in delta.items():
                        if k not in merged or not merged.get(k):
                            merged[k] = v
                    document.source_metadata = merged
                    
                    # Log if we found Zotero metadata
                    if 'zotero_key' in delta:
                        current_app.logger.info(
                            f"Enriched document {document.id} with Zotero metadata "
                            f"(key: {delta['zotero_key']}, match score: {delta.get('zotero_match_score', 0):.2f})"
                        )
        except Exception as _e:
            # Soft-fail: enrichment is best-effort
            current_app.logger.warning(f"Metadata enrichment failed: {str(_e)}")
            pass

        db.session.add(document)
        db.session.commit()
        
        # Process the reference document
        try:
            processing_service = TextProcessingService()
            processing_service.process_document(document)
            flash(f'Reference "{document.title}" uploaded and processed successfully', 'success')
        except Exception as e:
            flash(f'Reference uploaded but processing failed: {str(e)}', 'warning')
        
        # Check if this was uploaded from an experiment
        experiment_id = request.form.get('experiment_id')
        if experiment_id:
            experiment = Experiment.query.get(experiment_id)
            if experiment:
                experiment.add_reference(document, 
                                       include_in_analysis=request.form.get('include_in_analysis') == 'true')
                flash(f'Reference linked to experiment "{experiment.name}"', 'success')
                return redirect(url_for('experiments.view', id=experiment_id))
        
        return redirect(url_for('references.view', id=document.id))
    
    # GET request - show upload form
    experiment_id = request.args.get('experiment_id')
    experiment = None
    if experiment_id:
        experiment = Experiment.query.filter_by(
            id=experiment_id
        ).first()
    
    # Use tabbed interface by default for better UX
    if use_tabbed:
        return render_template('references/upload_tabbed.html', experiment=experiment)
    else:
        return render_template('references/upload.html', experiment=experiment)

@references_bp.route('/parse_oed_pdf', methods=['POST'])
@api_require_login_for_write
def parse_oed_pdf():
    """Parse uploaded OED PDF and return structured data"""
    import tempfile
    from app.services.oed_parser_final import OEDParser
    from flask import current_app
    
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    # Check if it's a PDF
    if not (file.filename or '').lower().endswith('.pdf'):
        return jsonify({'error': 'Only PDF files are supported'}), 400
    
    # Save temporarily
    temp_dir = tempfile.gettempdir()
    temp_name = secure_filename(file.filename or 'oed.pdf')
    temp_path = os.path.join(temp_dir, temp_name)
    
    try:
        file.save(temp_path)
        
        # Parse with OED parser
        parser = OEDParser()
        extracted_data = parser.parse_pdf(temp_path)
        
        # Format for frontend
        response_data = {
            'success': True,
            'data': extracted_data,
            'message': 'Successfully parsed OED entry'
        }
        
        return jsonify(response_data)
        
    except Exception as e:
        current_app.logger.error(f"Error parsing OED PDF: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e),
            'message': 'Failed to parse OED PDF'
        }), 500
    
    finally:
        # Clean up temp file
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except:
                pass

@references_bp.route('/extract_metadata', methods=['POST'])
@api_require_login_for_write
def extract_metadata():
    """Extract metadata from uploaded PDF for auto-population (Zotero-style)"""
    from datetime import datetime
    # Debug: write to file
    with open('/tmp/references_extract_debug.log', 'a') as f:
        f.write(f"\n===== REFERENCES FUNCTION CALLED at {datetime.now()} =====\n")
        f.flush()

    import tempfile
    from app.services.reference_metadata_enricher import ReferenceMetadataEnricher
    from flask import current_app

    current_app.logger.error("=== REFERENCES EXTRACT_METADATA CALLED ===")

    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'No file provided'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'error': 'No file selected'}), 400

    # Check if it's a PDF
    if not (file.filename or '').lower().endswith('.pdf'):
        return jsonify({'success': False, 'error': 'Only PDF files are supported'}), 400

    # Save temporarily
    temp_dir = tempfile.gettempdir()
    temp_name = secure_filename(file.filename or 'reference.pdf')
    temp_path = os.path.join(temp_dir, temp_name)

    try:
        file.save(temp_path)

        # Extract metadata using the enricher with Zotero
        use_zotero = current_app.config.get('USE_ZOTERO_METADATA', True)
        enricher = ReferenceMetadataEnricher(use_zotero=use_zotero)

        # Extract without existing metadata
        metadata = enricher.extract_with_zotero(temp_path, title=None, existing={}, allow_overwrite=False)

        # Convert authors list to comma-separated string for form
        if 'authors' in metadata and isinstance(metadata['authors'], list):
            metadata['authors'] = ', '.join(metadata['authors'])

        # Log the extraction
        current_app.logger.info(f"Extracted metadata from {file.filename}: {list(metadata.keys())}")

        # Format response
        response_data = {
            'success': True,
            'metadata': metadata,
            'message': 'Successfully extracted metadata'
        }

        # Add information about Zotero match if present
        if 'zotero_key' in metadata:
            response_data['zotero_match'] = {
                'key': metadata['zotero_key'],
                'score': metadata.get('zotero_match_score', 0),
                'type': metadata.get('zotero_match_type', 'unknown')
            }

        return jsonify(response_data)

    except Exception as e:
        current_app.logger.error(f"Error extracting metadata from PDF: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e),
            'message': 'Failed to extract metadata'
        }), 500

    finally:
        # Clean up temp file
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except:
                pass

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

@references_bp.route('/api/oed/timeline/<entry_id>')
@api_require_login_for_write
def api_oed_timeline(entry_id):
    """Get temporal waypoints for an OED entry showing semantic evolution."""
    if not entry_id:
        return jsonify({"success": False, "error": "Missing entry_id"}), 400

    limit = request.args.get('limit', 50, type=int)

    svc = OEDService()
    data = svc.get_temporal_waypoints(entry_id, limit=limit)
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

    from flask import current_app as _ca
    _api_base = (_ca.config.get('OED_API_BASE_URL') or 'https://oed-researcher-api.oxfordlanguages.com/oed/api/v0.2').rstrip('/')
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
        return None, data.get('error','lookup failed')
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
            'label': s.get('label',''),
            'definition': excerpt
        })

    content = f"OED entry: {entry_id}\nHeadword: {headword}"
    if pos:
        content += f"\nPart of speech: {pos}"
    if selected_senses:
        content += f"\nSelected senses: {', '.join(ss['sense_id'] for ss in selected_senses)}"

    from flask import current_app as _ca
    _api_base = (_ca.config.get('OED_API_BASE_URL') or 'https://oed-researcher-api.oxfordlanguages.com/oed/api/v0.2').rstrip('/')
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

@references_bp.route('/<int:id>')
@api_require_login_for_write
def view(id):
    """View reference details"""
    reference = Document.query.filter_by(
        id=id,
        document_type='reference'
    ).first_or_404()
    
    # Get experiments that use this reference (use relationship.any to avoid typing issues)
    experiments_using = Experiment.query.filter(
        Experiment.references.any(Document.id == reference.id)
    ).all()
    
    return render_template('references/view.html', 
                         reference=reference,
                         experiments_using=experiments_using)

@references_bp.route('/<int:id>/edit', methods=['GET', 'POST'])
@api_require_login_for_write
def edit(id):
    """Edit reference metadata"""
    reference = Document.query.filter_by(
        id=id,
        document_type='reference'
    ).first_or_404()
    
    if request.method == 'POST':
        # Update basic info
        reference.title = request.form.get('title', reference.title)
        reference.reference_subtype = request.form.get('reference_subtype', reference.reference_subtype)
        
        # Update source metadata
        authors = request.form.get('authors', '').split(',')
        authors = [a.strip() for a in authors if a.strip()]
        
        provided_meta = {
            'authors': authors,
            'publication_date': request.form.get('publication_date'),
            'journal': request.form.get('journal'),
            'doi': request.form.get('doi'),
            'isbn': request.form.get('isbn'),
            'url': request.form.get('url'),
            'abstract': request.form.get('abstract'),
            'citation': request.form.get('citation')
        }
        
        # Remove empty values and merge into existing metadata to preserve OED-specific fields
        provided_meta = {k: v for k, v in provided_meta.items() if v}
        existing_meta = reference.source_metadata or {}
        if not isinstance(existing_meta, dict):
            existing_meta = {}
        merged = {**existing_meta, **provided_meta}
        reference.source_metadata = merged if merged else None
        
        db.session.commit()
        flash('Reference updated successfully', 'success')
        return redirect(url_for('references.view', id=reference.id))
    
    return render_template('references/edit.html', reference=reference)

@references_bp.route('/<int:id>/delete', methods=['POST'])
@api_require_login_for_write
def delete(id):
    """Delete a reference"""
    reference = Document.query.filter_by(
        id=id,
        document_type='reference'
    ).first_or_404()
    
    # Delete file if exists
    reference.delete_file()
    
    # Delete from database
    db.session.delete(reference)
    db.session.commit()
    
    flash('Reference deleted successfully', 'success')
    return redirect(url_for('references.index'))

# API endpoints for AJAX operations
@references_bp.route('/api/search')
@api_require_login_for_write
def api_search():
    """Search references for autocomplete/selection"""
    query = request.args.get('q', '')
    
    if not query:
        references = Document.query.filter_by(
            document_type='reference'
        ).limit(20).all()
    else:
        references = Document.query.filter(
            Document.document_type == 'reference',
            Document.title.contains(query)
        ).limit(20).all()
    
    return jsonify([{
        'id': ref.id,
        'title': ref.title,
        'source_info': ref.get_source_info(),
        'citation': ref.get_citation()
    } for ref in references])

@references_bp.route('/upload_dictionary', methods=['POST'])
@api_require_login_for_write
def upload_dictionary():
    """Upload a dictionary entry (OED or general)"""
    # Helper cleaners to strip NULs from inputs (Postgres cannot store \x00)
    def _clean_str(val):
        if val is None:
            return None
        try:
            return val.replace('\x00', '')
        except Exception:
            return val

    def _clean_meta(obj):
        if obj is None:
            return None
        if isinstance(obj, str):
            return _clean_str(obj)
        if isinstance(obj, dict):
            return {k: _clean_meta(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [_clean_meta(v) for v in obj]
        return obj
    # Get form data
    title = _clean_str(request.form.get('title') or '')
    content = _clean_str(request.form.get('content') or '')  # This is the full text field
    reference_subtype = request.form.get('reference_subtype', 'dictionary_general')
    
    if not title or not content:
        flash('Term and definition are required', 'error')
        return redirect(url_for('references.upload'))
    
    # Build source metadata based on dictionary type
    source_metadata = {}
    
    if reference_subtype == 'dictionary_oed':
        # OED-specific fields - store everything in metadata for reference
        source_metadata = _clean_meta({
            'pronunciation': request.form.get('pronunciation'),
            'etymology': request.form.get('etymology'),
            'usage_notes': request.form.get('usage_notes'),
            'examples': request.form.get('examples'),  # Temporal quotations
            'first_use': request.form.get('first_use'),
            'edition': request.form.get('edition'),
            'journal': 'Oxford English Dictionary',
            'url': request.form.get('url'),
            'citation': request.form.get('citation'),
            'pdf_link': request.form.get('pdf_link')  # Store PDF filename reference
        })
        
        # Store the FULL content as-is (no formatting, just the complete text)
        # This ensures we capture everything from the OED entry
        formatted_content = content  # Already cleaned above
            
    else:
        # General dictionary fields
        source_metadata = _clean_meta({
            'journal': request.form.get('journal'),  # Dictionary source
            'context': request.form.get('context'),
            'synonyms': request.form.get('synonyms'),
            'url': request.form.get('url')
        })
        
        # Format the content for general dictionary
        formatted_content = f"Term: {title}\n\n"
        if source_metadata and isinstance(source_metadata, dict):
            formatted_content += f"Source: {source_metadata.get('journal', 'Unknown')}\n\n"
            if source_metadata.get('context'):
                formatted_content += f"Context/Domain: {source_metadata.get('context')}\n\n"
        formatted_content += f"Definition:\n{content}\n"
        if source_metadata and isinstance(source_metadata, dict) and source_metadata.get('synonyms'):
            formatted_content += f"\nSynonyms: {source_metadata.get('synonyms')}\n"
    
    # Remove empty values from metadata (ensure it's a dict first)
    if not isinstance(source_metadata, dict):
        source_metadata = {}
    else:
        source_metadata = {k: v for k, v in source_metadata.items() if v}
    
    # Create document record
    document = Document(
        title=title or '',
        content_type='text',
        document_type='reference',
        reference_subtype=reference_subtype,
        content=formatted_content or '',
        content_preview=(formatted_content or '')[:500] + ('...' if len(formatted_content or '') > 500 else ''),
        source_metadata=source_metadata if source_metadata else None,
        user_id=current_user.id,
        status='completed',  # Text entries are immediately available
        word_count=len((formatted_content or '').split()),
        character_count=len(formatted_content or '')
    )
    
    db.session.add(document)
    db.session.commit()
    
    flash(f'Dictionary entry "{document.title}" saved successfully', 'success')
    
    # Check if this was linked from an experiment
    experiment_id = request.form.get('experiment_id')
    if experiment_id:
        experiment = Experiment.query.get(experiment_id)
        if experiment and experiment.user_id == current_user.id:
            experiment.add_reference(document, 
                                   include_in_analysis=request.form.get('include_in_analysis') == 'true')
            flash(f'Dictionary entry linked to experiment "{experiment.name}"', 'success')
            return redirect(url_for('experiments.view', id=experiment_id))
    
    return redirect(url_for('references.view', id=document.id))

@references_bp.route('/api/wordnet/search')
@api_require_login_for_write
def api_wordnet_search():
    """Search WordNet for a word and return synsets with definitions."""
    word = request.args.get('q', '').strip()
    if not word:
        return jsonify({"success": False, "error": "Missing 'q' query parameter"}), 400

    service = WordNetService()
    data = service.search_word(word)
    status = 200 if data.get('success', True) else 500
    return jsonify(data), status

@references_bp.route('/api/wordnet/similarity')
@api_require_login_for_write
def api_wordnet_similarity():
    """Calculate semantic similarity between two words using WordNet."""
    word1 = request.args.get('word1', '').strip()
    word2 = request.args.get('word2', '').strip()
    
    if not word1 or not word2:
        return jsonify({"success": False, "error": "Missing 'word1' or 'word2' query parameters"}), 400

    service = WordNetService()
    data = service.get_word_similarity(word1, word2)
    status = 200 if data.get('success', True) else 500
    return jsonify(data), status
