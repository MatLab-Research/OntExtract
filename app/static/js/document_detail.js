/* Document Detail Page Logic (externalized)
   All dynamic behaviors moved out of Jinja template to avoid syntax collisions.
*/
(function () {
    const cfg = window.DocumentDetailConfig || {};
    const docId = cfg.documentId;
    if (!docId) { console.warn('DocumentDetailConfig.documentId missing'); }

    function safe(fn) { try { fn(); } catch (e) { console.error(e); } }
    function showLoader(msg) { if (typeof showLoading === 'function') showLoading(msg); }
    function hideLoader() { if (typeof hideLoading === 'function') hideLoading(); }

    // Toggle full content
    window.toggleFullContent = function () {
        const preview = document.querySelector('.content-preview');
        const button = event.target.closest('button');
        if (!preview || !button) return;
        if (preview.style.maxHeight === '400px' || !preview.style.maxHeight) {
            preview.style.maxHeight = 'none';
            button.innerHTML = '<i class="fas fa-compress me-2"></i>Show Less';
        } else {
            preview.style.maxHeight = '400px';
            button.innerHTML = '<i class="fas fa-expand me-2"></i>Show Full Content';
        }
    };

    // Delete document
    function deleteDocument(documentId, triggerEl) {
        if (!confirm('Are you sure you want to delete this document? This action cannot be undone.')) return;
        if (triggerEl) triggerEl.classList.add('disabled');
        showLoader('Deleting document...');
        fetch(cfg.routes.delete, { method: 'POST', headers: { 'Accept': 'application/json', 'Content-Type': 'application/json' } })
            .then(async r => { let data = {}; try { data = await r.json(); } catch (_) { } if (!r.ok || !data.success) throw new Error(data.error || ('HTTP ' + r.status)); return data; })
            .then(() => { hideLoader(); window.location.href = cfg.routes.list; })
            .catch(err => { hideLoader(); alert('Error deleting document: ' + err.message); if (triggerEl) triggerEl.classList.remove('disabled'); });
    }
    window.deleteDocument = deleteDocument;

    // Embedding details
    window.viewEmbeddingDetails = function (documentId) {
        showLoader('Loading embedding details...');
        fetch(cfg.routes.embeddingSample)
            .then(r => r.json())
            .then(data => {
                hideLoader();
                if (!data.success) return alert('Error: ' + (data.error || 'No embeddings'));
                buildEmbeddingDetailsModal(data);
            })
            .catch(e => { hideLoader(); alert('Error loading embedding details'); console.error(e); });
    };

    function buildEmbeddingDetailsModal(data) {
        const modalId = 'embeddingDetailsModal';
        document.getElementById(modalId)?.remove();
        const dimNoteTotal = data.total_dimensions * data.total_chunks;
        const showDims = Math.min(10, data.total_dimensions);
        const sampleHtml = (data.sample_chunks || []).map(chunk => `
      <div class="border rounded p-3 mb-2">
        <div class="d-flex justify-content-between align-items-center mb-2">
          <strong>Chunk ${chunk.chunk_id + 1}</strong>
          <span class="badge bg-secondary">${chunk.word_count} words</span>
        </div>
        <p class="small text-muted mb-2">"${chunk.text_preview}"</p>
        <div class="small">
          <strong>Vector sample (${chunk.vector_sample.length}/${chunk.vector_length}):</strong><br>
          <code>[${chunk.vector_sample.join(', ')}...]</code>
        </div>
      </div>`).join('');
        const html = `
      <div class="modal fade" id="${modalId}" tabindex="-1">
        <div class="modal-dialog modal-lg"><div class="modal-content">
          <div class="modal-header"><h5 class="modal-title"><i class="fas fa-vector-square me-2"></i>Embedding Details</h5>
            <button type="button" class="btn-close" data-bs-dismiss="modal"></button></div>
          <div class="modal-body">
            <div class="row mb-3">
              <div class="col-md-4"><div class="card bg-light"><div class="card-body text-center"><h4 class="text-success">${data.method.toUpperCase()}</h4><small class="text-muted">Method Used</small></div></div></div>
              <div class="col-md-4"><div class="card bg-light"><div class="card-body text-center"><h4 class="text-info">${data.total_dimensions}</h4><small class="text-muted">Dimensions</small></div></div></div>
              <div class="col-md-4"><div class="card bg-light"><div class="card-body text-center"><h4 class="text-warning">${data.total_chunks}</h4><small class="text-muted">Text Chunks</small></div></div></div>
            </div>
            <h6>Sample Embedding Vectors:</h6>
            <p class="text-muted small">${data.note}</p>
            ${sampleHtml}
            <div class="alert alert-warning mt-3"><i class="fas fa-exclamation-triangle me-2"></i><strong>Note:</strong> Full embedding vectors not displayed (${dimNoteTotal} values). Showing first ${showDims} dimensions of first ${(data.sample_chunks || []).length} chunks.</div>
          </div>
          <div class="modal-footer"><button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button></div>
        </div></div>
      </div>`;
        document.body.insertAdjacentHTML('beforeend', html);
        new bootstrap.Modal(document.getElementById(modalId)).show();
    }

    // Clear processing history
    window.clearProcessingHistory = function (documentId) {
        if (!confirm('Clear all processing history? This cannot be undone.')) return;
        showLoader('Clearing processing history...');
        fetch(cfg.routes.clearJobs, { method: 'POST', headers: { 'Content-Type': 'application/json' } })
            .then(r => r.json())
            .then(d => { hideLoader(); if (d.success) { alert(`Cleared ${d.deleted_count} processing jobs`); location.reload(); } else alert('Error: ' + (d.error || 'unknown')); })
            .catch(e => { hideLoader(); alert('Error clearing processing history'); console.error(e); });
    };

    // Delete all segments
    window.deleteAllSegments = function (documentId) {
        if (!confirm('Delete ALL segments for this document? This cannot be undone.')) return;
        showLoader('Deleting segments...');
        fetch(cfg.routes.deleteAllSegments, { method: 'DELETE', headers: { 'Content-Type': 'application/json' } })
            .then(r => r.json())
            .then(d => { hideLoader(); if (d.success) { alert(`Deleted ${d.segments_deleted} segments`); location.reload(); } else alert('Error: ' + (d.error || 'unknown')); })
            .catch(e => { hideLoader(); alert('Error deleting segments'); console.error(e); });
    };

    // Zotero enrichment
    window.enrichWithZotero = function (documentId) {
        showLoader('Searching Zotero for metadata...');
        fetch(cfg.routes.zoteroEnrich, { method: 'POST', headers: { 'Content-Type': 'application/json' } })
            .then(r => r.json())
            .then(d => { hideLoader(); if (d.success) { alert('Document enhanced with Zotero metadata!'); location.reload(); } else alert('Zotero enhancement failed: ' + (d.error || 'No matches')); })
            .catch(e => { hideLoader(); alert('Error enriching with Zotero'); console.error(e); });
    };

    // Segments loading (multi-method)
    function loadDocumentSegments(documentId) {
        fetch(cfg.routes.segmentsApi)
            .then(r => r.json())
            .then(data => {
                if (data.success) {
                    document.getElementById('totalSegmentsCount')?.textContent = data.total_segments;
                    window.allSegmentsByMethod = {};
                    (data.segmentation_methods || []).forEach(m => { window.allSegmentsByMethod[m.method] = m.segments; });
                    displaySegmentMethods(data.segmentation_methods || []);
                    if ((data.segmentation_methods || []).length > 0) displaySegments(data.segmentation_methods[0].method); else displayNoSegments();
                } else displayNoSegments();
            })
            .catch(e => { console.error('Error loading segments', e); displayNoSegments(); });
    }
    window.loadDocumentSegments = loadDocumentSegments;

    function displaySegmentMethods(methods) {
        const methodsContainer = document.getElementById('segmentationMethods');
        if (!methodsContainer) return;
        const btnGroup = methodsContainer.querySelector('.btn-group');
        if (!methods || methods.length === 0) { methodsContainer.style.display = 'none'; return; }
        if (methods.length === 1) { methodsContainer.style.display = 'none'; return; }
        btnGroup.innerHTML = '';
        methods.forEach((m, i) => {
            const btn = document.createElement('button');
            btn.type = 'button';
            btn.className = 'btn btn-outline-secondary ' + (i === 0 ? 'active' : '');
            btn.onclick = () => switchSegmentMethod(m.method, btn);
            btn.innerHTML = `<i class="fas fa-${getMethodIcon(m.method)} me-1"></i>${m.method.charAt(0).toUpperCase() + m.method.slice(1)} <span class="badge bg-primary ms-1">${m.segments.length}</span>`;
            btnGroup.appendChild(btn);
        });
    }
    function getMethodIcon(method) {
        switch ((method || '').toLowerCase()) { case 'paragraph': return 'paragraph'; case 'sentence': return 'list-ol'; case 'semantic': return 'brain'; case 'langextract': return 'project-diagram'; case 'hybrid': return 'layer-group'; default: return 'cut'; }
    }
    function switchSegmentMethod(method, btn) {
        document.querySelectorAll('#segmentationMethods .btn').forEach(b => b.classList.remove('active'));
        if (btn) btn.classList.add('active');
        displaySegments(method);
    }
    window.showAllSegments = function (method) { displaySegments(method, true); };
    function displaySegments(method, showAll) {
        const segments = (window.allSegmentsByMethod || {})[method] || [];
        const container = document.getElementById('segmentsList');
        if (!container) return;
        if (segments.length === 0) {
            container.innerHTML = `<div class='text-center p-4'><i class='fas fa-puzzle-piece fa-3x text-muted mb-3'></i><p class='text-muted'>No ${method} segments found for this document.</p></div>`; return;
        }
        const showCount = showAll ? segments.length : Math.min(5, segments.length);
        const hasMore = !showAll && segments.length > 5;
        let html = '<div class="row">';
        segments.slice(0, showCount).forEach(seg => {
            const versionBadge = seg.version_type === 'processed' ? `<span class='badge bg-secondary ms-1'>v${seg.version_number}</span>` : '';
            const processingType = seg.processing_type ? `<small class='text-muted d-block'>${seg.processing_type.replace('_', ' ')}</small>` : '';
            html += `<div class='col-12 mb-3'><div class='border rounded p-3'><div class='d-flex justify-content-between align-items-start mb-2'><span class='badge bg-light text-dark'>${seg.segment_type.charAt(0).toUpperCase() + seg.segment_type.slice(1)} #${seg.segment_number} ${versionBadge}</span><div class='text-end'><small class='text-muted d-block'>${seg.word_count || 0} words</small>${seg.character_count ? `<small class='text-muted'>${seg.character_count} characters</small>` : ''}${processingType}</div></div><p class='mb-0 text-muted small'>${seg.content}</p>${(seg.start_position != null && seg.end_position != null) ? `<div class='mt-2'><small class='text-muted'><i class='fas fa-map-marker-alt me-1'></i>Position: ${seg.start_position} - ${seg.end_position}</small></div>` : ''}${seg.created_at ? `<div class='mt-1'><small class='text-muted'>Created: ${new Date(seg.created_at).toLocaleString()}</small></div>` : ''}</div></div>`;
        });
        if (hasMore) {
            html += `<div class='col-12 text-center'><button class='btn btn-outline-info btn-sm' data-action='show-all-segments' data-method='${method}'><i class='fas fa-chevron-down me-2'></i>Show ${segments.length - showCount} More Segments</button></div>`;
        }
        html += '</div>';
        container.innerHTML = html;
        container.querySelectorAll('[data-action="show-all-segments"]').forEach(btn => {
            btn.addEventListener('click', () => displaySegments(btn.getAttribute('data-method'), true));
        });
    }
    function displayNoSegments() {
        const container = document.getElementById('segmentsList');
        if (!container) return;
        container.innerHTML = `<div class='text-center p-4'><i class='fas fa-puzzle-piece fa-3x text-muted mb-3'></i><p class='text-muted'>No segments have been created for this document yet.</p><button class='btn btn-primary' data-action='open-segmentation'><i class='fas fa-cut me-2'></i>Create Segments</button></div>`;
    }

    // Embeddings list
    function loadDocumentEmbeddings(documentId) {
        fetch(cfg.routes.embeddingsApi)
            .then(r => r.json())
            .then(data => {
                const container = document.getElementById('embeddingsContainer');
                const countEl = document.getElementById('embeddingCount');
                if (!container) return;
                if (data.embeddings && data.embeddings.length > 0) {
                    countEl && (countEl.textContent = data.embeddings.length);
                    let html = '<div class="row">';
                    data.embeddings.forEach((e, i) => {
                        html += `<div class='col-md-6 mb-3'><div class='card h-100'><div class='card-body'><h6 class='card-title'><i class='fas fa-vector-square me-2'></i>Embedding ${i + 1}</h6><div class='mb-2'><small class='text-muted'>Model: ${e.model_name || 'Unknown'}</small></div><div class='mb-2'><small class='text-muted'>Dimensions: ${e.dimensions || 'Unknown'}</small></div><div class='mb-2'><small class='text-muted'>Created: ${e.created_at ? new Date(e.created_at).toLocaleDateString() : 'Unknown'}</small></div></div></div></div>`;
                    });
                    html += '</div>';
                    container.innerHTML = html;
                } else {
                    container.innerHTML = `<div class='text-center p-4'><i class='fas fa-brain fa-2x text-muted mb-3'></i><p class='text-muted'>No embeddings found for this document.</p><button class='btn btn-success btn-sm' data-action='open-embedding'><i class='fas fa-plus me-1'></i>Generate Embeddings</button></div>`;
                    countEl && (countEl.textContent = '0');
                }
            })
            .catch(e => {
                console.error('Error loading embeddings', e);
                const container = document.getElementById('embeddingsContainer');
                if (container) container.innerHTML = `<div class='text-center p-4'><i class='fas fa-exclamation-triangle fa-2x text-warning mb-3'></i><p class='text-muted'>Error loading embeddings. Please try again.</p><button class='btn btn-outline-primary btn-sm' data-action='reload-embeddings'><i class='fas fa-sync me-1'></i>Retry</button></div>`;
            });
    }
    window.loadDocumentEmbeddings = loadDocumentEmbeddings;

    window.refreshEmbeddings = function (documentId) {
        const container = document.getElementById('embeddingsContainer');
        if (container) {
            container.innerHTML = `<div class='text-center p-4'><div class='spinner-border text-primary' role='status'><span class='visually-hidden'>Refreshing embeddings...</span></div><p class='mt-2 text-muted'>Refreshing embeddings...</p></div>`;
        }
        loadDocumentEmbeddings(documentId);
    };

    // Event wiring
    document.addEventListener('DOMContentLoaded', function () {
        // Delete link(s)
        document.querySelectorAll('.js-delete-document').forEach(el => {
            el.addEventListener('click', e => { e.preventDefault(); deleteDocument(docId, el); });
        });
        // Initial loads
        loadDocumentEmbeddings(docId);
        loadDocumentSegments(docId);
    });
})();
