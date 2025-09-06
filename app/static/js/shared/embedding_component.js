// Shared Embedding Component JavaScript
// Include this in templates that use the embedding component

// Embedding and segmentation options modal
let currentDocumentId = null;
let selectedEmbeddingMethod = 'local';
let selectedSegmentationMethod = 'paragraph';

function showEmbeddingOptions(documentId) {
    console.log('showEmbeddingOptions called for document:', documentId);
    
    currentDocumentId = documentId;
    selectedEmbeddingMethod = 'local'; // Default selection

    // Clear previous selections
    document.querySelectorAll('.method-option').forEach(option => {
        option.classList.remove('border-primary', 'bg-light');
    });

    // Select default method
    const defaultOption = document.querySelector('[data-method="local"]');
    if (defaultOption) {
        defaultOption.classList.add('border-primary', 'bg-light');
    }

    // Ensure modal is properly positioned and remove any existing instances
    const modalElement = document.getElementById('embeddingModal');
    if (!modalElement) {
        console.error('Embedding modal element not found');
        return;
    }
    
    console.log('Modal element found, Bootstrap available:', typeof bootstrap !== 'undefined');
    
    // Clean up any existing modal instances
    const existingModal = bootstrap.Modal.getInstance(modalElement);
    if (existingModal) {
        existingModal.dispose();
    }
    
    // Remove any leftover backdrops
    document.querySelectorAll('.modal-backdrop').forEach(backdrop => backdrop.remove());
    
    // Remove modal-open class from body
    document.body.classList.remove('modal-open');
    
    // Force modal visibility and positioning
    modalElement.style.display = 'block';
    modalElement.style.position = 'fixed';
    modalElement.style.zIndex = '10050';
    modalElement.style.top = '0';
    modalElement.style.left = '0';
    modalElement.style.width = '100%';
    modalElement.style.height = '100%';
    modalElement.classList.add('show');
    
    // Add modal-open class to body
    document.body.classList.add('modal-open');
    
    console.log('Modal should be visible now');
}

function selectEmbeddingMethod(method) {
    selectedEmbeddingMethod = method;

    // Clear all selections
    document.querySelectorAll('.method-option').forEach(option => {
        option.classList.remove('border-primary', 'bg-light');
    });

    // Highlight selected method
    const selectedOption = document.querySelector(`[data-method="${method}"]`);
    if (selectedOption) {
        selectedOption.classList.add('border-primary', 'bg-light');
    }
}

function generateEmbeddingsWithMethod() {
    if (!currentDocumentId || !selectedEmbeddingMethod) {
        alert('Please select an embedding method');
        return;
    }

    // Close modal
    const modalElement = document.getElementById('embeddingModal');
    const modal = bootstrap.Modal.getInstance(modalElement);
    if (modal) {
        modal.hide();
    } else {
        modalElement.style.display = 'none';
        document.body.classList.remove('modal-open');
        const backdrop = document.querySelector('.modal-backdrop');
        if (backdrop) backdrop.remove();
    }

    // Call the actual embedding generation with method
    generateEmbeddings(currentDocumentId, selectedEmbeddingMethod);
}

function closeEmbeddingModal() {
    const modalElement = document.getElementById('embeddingModal');
    const modal = bootstrap.Modal.getInstance(modalElement);
    if (modal) {
        modal.hide();
    } else {
        modalElement.style.display = 'none';
        document.body.classList.remove('modal-open');
        const backdrop = document.querySelector('.modal-backdrop');
        if (backdrop) backdrop.remove();
    }
}

// Processing options functions
function generateEmbeddings(documentId, method = 'local') {
    showLoading('Generating embeddings...');

    fetch(`/process/document/${documentId}/embeddings`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            'method': method
        })
    })
        .then(response => response.json())
        .then(data => {
            hideLoading();
            if (data.success) {
                alert('Embeddings generated successfully!');
                location.reload(); // Refresh to show updated statistics
            } else {
                alert('Error generating embeddings: ' + (data.error || 'Unknown error'));
            }
        })
        .catch(error => {
            hideLoading();
            console.error('Error:', error);
            alert('Error generating embeddings');
        });
}

// Segmentation options modal functions
function showSegmentationOptions(documentId) {
    console.log('showSegmentationOptions called for document:', documentId);
    
    currentDocumentId = documentId;
    selectedSegmentationMethod = 'paragraph'; // Default selection

    // Clear previous selections
    document.querySelectorAll('.segment-option').forEach(option => {
        option.classList.remove('border-primary', 'bg-light');
    });

    // Select default method
    const defaultOption = document.querySelector('.segment-option[data-method="paragraph"]');
    if (defaultOption) {
        defaultOption.classList.add('border-primary', 'bg-light');
    }

    // Ensure modal is properly positioned and remove any existing instances
    const modalElement = document.getElementById('segmentationModal');
    if (!modalElement) {
        console.error('Segmentation modal element not found');
        return;
    }
    
    console.log('Segmentation modal element found');
    
    // Clean up any existing modal instances
    const existingModal = bootstrap.Modal.getInstance(modalElement);
    if (existingModal) {
        existingModal.dispose();
    }
    
    // Remove any leftover backdrops
    document.querySelectorAll('.modal-backdrop').forEach(backdrop => backdrop.remove());
    
    // Remove modal-open class from body
    document.body.classList.remove('modal-open');
    
    // Force modal visibility and positioning
    modalElement.style.display = 'block';
    modalElement.style.position = 'fixed';
    modalElement.style.zIndex = '10050';
    modalElement.style.top = '0';
    modalElement.style.left = '0';
    modalElement.style.width = '100%';
    modalElement.style.height = '100%';
    modalElement.classList.add('show');
    
    // Add modal-open class to body
    document.body.classList.add('modal-open');
    
    console.log('Segmentation modal should be visible now');
}

function selectSegmentationMethod(method) {
    selectedSegmentationMethod = method;

    // Clear all selections
    document.querySelectorAll('.segment-option').forEach(option => {
        option.classList.remove('border-primary', 'bg-light');
    });

    // Highlight selected method
    const selectedOption = document.querySelector(`[data-method="${method}"]`);
    if (selectedOption) {
        selectedOption.classList.add('border-primary', 'bg-light');
    }
}

function segmentDocumentWithMethod() {
    if (!currentDocumentId || !selectedSegmentationMethod) {
        alert('Please select a segmentation method');
        return;
    }

    // Close modal
    const modalElement = document.getElementById('segmentationModal');
    const modal = bootstrap.Modal.getInstance(modalElement);
    if (modal) {
        modal.hide();
    } else {
        modalElement.style.display = 'none';
        document.body.classList.remove('modal-open');
        const backdrop = document.querySelector('.modal-backdrop');
        if (backdrop) backdrop.remove();
    }

    // Call the actual segmentation with method
    segmentDocument(currentDocumentId, selectedSegmentationMethod);
}

function closeSegmentationModal() {
    const modalElement = document.getElementById('segmentationModal');
    const modal = bootstrap.Modal.getInstance(modalElement);
    if (modal) {
        modal.hide();
    } else {
        modalElement.style.display = 'none';
        document.body.classList.remove('modal-open');
        const backdrop = document.querySelector('.modal-backdrop');
        if (backdrop) backdrop.remove();
    }
}

function segmentDocument(documentId, method = 'paragraph') {
    showLoading('Segmenting document...');

    fetch(`/process/document/${documentId}/segment`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            'method': method
        })
    })
        .then(response => response.json())
        .then(data => {
            hideLoading();
            if (data.success) {
                alert('Document segmented successfully!');
                location.reload(); // Refresh to show segments
            } else {
                alert('Error segmenting document: ' + (data.error || 'Unknown error'));
            }
        })
        .catch(error => {
            hideLoading();
            console.error('Error:', error);
            alert('Error segmenting document');
        });
}

function extractEntities(documentId) {
    showLoading('Extracting entities...');

    fetch(`/process/document/${documentId}/entities`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        }
    })
        .then(response => response.json())
        .then(data => {
            hideLoading();
            if (data.success) {
                alert('Entities extracted successfully!');
                location.reload(); // Refresh to show updated statistics
            } else {
                alert('Error extracting entities: ' + (data.error || 'Unknown error'));
            }
        })
        .catch(error => {
            hideLoading();
            console.error('Error:', error);
            alert('Error extracting entities');
        });
}

function analyzeMetadata(documentId) {
    showLoading('Analyzing metadata...');

    fetch(`/process/document/${documentId}/metadata`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        }
    })
        .then(response => response.json())
        .then(data => {
            hideLoading();
            if (data.success) {
                alert('Metadata analyzed successfully!');
                location.reload(); // Refresh to show updated information
            } else {
                alert('Error analyzing metadata: ' + (data.error || 'Unknown error'));
            }
        })
        .catch(error => {
            hideLoading();
            console.error('Error:', error);
            alert('Error analyzing metadata');
        });
}

// View embedding details function
function viewEmbeddingDetails(documentId) {
    showLoading('Loading embedding details...');

    fetch(`/api/embeddings/document/${documentId}/sample`)
        .then(response => response.json())
        .then(data => {
            hideLoading();
            if (data.success) {
                showEmbeddingDetailsModal(data);
            } else {
                alert('Error loading embedding details: ' + (data.error || 'No embeddings found'));
            }
        })
        .catch(error => {
            hideLoading();
            console.error('Error:', error);
            alert('Error loading embedding details');
        });
}

function showEmbeddingDetailsModal(data) {
    const modalHtml = `
        <div class="modal fade" id="embeddingDetailsModal" tabindex="-1">
            <div class="modal-dialog modal-lg">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">
                            <i class="fas fa-vector-square me-2"></i>Embedding Details
                        </h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <div class="row mb-3">
                            <div class="col-md-4">
                                <div class="card bg-light">
                                    <div class="card-body text-center">
                                        <h4 class="text-success">${data.method.toUpperCase()}</h4>
                                        <small class="text-muted">Method Used</small>
                                    </div>
                                </div>
                            </div>
                            <div class="col-md-4">
                                <div class="card bg-light">
                                    <div class="card-body text-center">
                                        <h4 class="text-info">${data.total_dimensions}</h4>
                                        <small class="text-muted">Dimensions</small>
                                    </div>
                                </div>
                            </div>
                            <div class="col-md-4">
                                <div class="card bg-light">
                                    <div class="card-body text-center">
                                        <h4 class="text-warning">${data.total_chunks}</h4>
                                        <small class="text-muted">Text Chunks</small>
                                    </div>
                                </div>
                            </div>
                        </div>
                        
                        <h6>Sample Embedding Vectors:</h6>
                        <p class="text-muted small">${data.note}</p>
                        
                        ${data.sample_chunks.map((chunk, i) => `
                            <div class="border rounded p-3 mb-2">
                                <div class="d-flex justify-content-between align-items-center mb-2">
                                    <strong>Chunk ${chunk.chunk_id + 1}</strong>
                                    <span class="badge bg-secondary">${chunk.word_count} words</span>
                                </div>
                                <p class="small text-muted mb-2">"${chunk.text_preview}"</p>
                                <div class="small">
                                    <strong>Vector sample (${chunk.vector_sample.length}/${chunk.vector_length}):</strong>
                                    <br>
                                    <code>[${chunk.vector_sample.join(', ')}...]</code>
                                </div>
                            </div>
                        `).join('')}
                        
                        <div class="alert alert-warning">
                            <i class="fas fa-exclamation-triangle me-2"></i>
                            <strong>Note:</strong> Full embedding vectors are not displayed due to size (${data.total_dimensions * data.total_chunks} values). 
                            This sample shows the first ${Math.min(10, data.total_dimensions)} dimensions of the first ${data.sample_chunks.length} chunks.
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                    </div>
                </div>
            </div>
        </div>
    `;

    // Remove any existing modal
    const existingModal = document.getElementById('embeddingDetailsModal');
    if (existingModal) {
        existingModal.remove();
    }

    // Add new modal to page
    document.body.insertAdjacentHTML('beforeend', modalHtml);

    // Show modal
    new bootstrap.Modal(document.getElementById('embeddingDetailsModal')).show();
}

// Clear processing history function
function clearProcessingHistory(documentId) {
    if (confirm('Are you sure you want to clear all processing history for this document? This action cannot be undone.')) {
        showLoading('Clearing processing history...');

        fetch(`/process/document/${documentId}/clear-jobs`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            }
        })
            .then(response => response.json())
            .then(data => {
                hideLoading();
                if (data.success) {
                    alert(`Successfully cleared ${data.deleted_count} processing jobs`);
                    location.reload(); // Refresh to show cleared history
                } else {
                    alert('Error clearing processing history: ' + (data.error || 'Unknown error'));
                }
            })
            .catch(error => {
                hideLoading();
                console.error('Error:', error);
                alert('Error clearing processing history');
            });
    }
}