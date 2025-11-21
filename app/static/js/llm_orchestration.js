/**
 * LLM Orchestration Client
 *
 * Handles the 5-stage LLM orchestration workflow:
 * 1. Analyze Experiment
 * 2. Recommend Strategy
 * 3. Human Review (optional)
 * 4. Execute Strategy
 * 5. Synthesize Experiment
 */

class LLMOrchestrationClient {
    constructor(experimentId) {
        this.experimentId = experimentId;
        this.currentRunId = null;
        this.pollInterval = null;
        this.pollIntervalMs = 1000; // Poll every 1 second
    }

    /**
     * Start the LLM orchestration workflow
     */
    async startAnalysis() {
        try {
            // STEP 1: Check for existing processing
            const checkResponse = await fetch(`/experiments/${this.experimentId}/orchestration/check-status`);
            const checkData = await checkResponse.json();

            // If documents are already processed, warn user
            if (checkData.has_partial_processing || checkData.has_full_processing) {
                const proceed = await this.showPartialProcessingWarning(checkData);
                if (!proceed) {
                    return; // User cancelled
                }
            }

            // STEP 2: Continue with orchestration
            this.showProgressModal();
            this.updateProgress('analyzing', 20, 'Starting analysis...');

            // Make API call
            const response = await fetch(`/experiments/${this.experimentId}/orchestration/analyze`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    review_choices: true
                })
            });

            const data = await response.json();

            if (!data.success) {
                throw new Error(data.error || 'Failed to start orchestration');
            }

            this.currentRunId = data.run_id;

            // Start polling for status updates
            this.startPolling();

        } catch (error) {
            console.error('Error starting orchestration:', error);
            this.showError(error.message);
        }
    }

    /**
     * Start polling for orchestration status
     */
    startPolling() {
        if (this.pollInterval) {
            clearInterval(this.pollInterval);
        }

        this.pollInterval = setInterval(() => {
            this.checkStatus();
        }, this.pollIntervalMs);

        // Check immediately
        this.checkStatus();
    }

    /**
     * Stop polling
     */
    stopPolling() {
        if (this.pollInterval) {
            clearInterval(this.pollInterval);
            this.pollInterval = null;
        }
    }

    /**
     * Check current orchestration status
     */
    async checkStatus() {
        try {
            const response = await fetch(`/experiments/orchestration/status/${this.currentRunId}`);
            const data = await response.json();

            if (data.error) {
                throw new Error(data.error);
            }

            // Update progress UI
            this.updateProgress(
                data.current_stage,
                data.progress_percentage,
                this.getStageMessage(data.current_stage)
            );

            // Handle different statuses
            if (data.status === 'reviewing') {
                this.stopPolling();
                this.showStrategyReview(data);
            } else if (data.status === 'completed') {
                this.stopPolling();
                this.showCompletionMessage(data);
            } else if (data.status === 'failed') {
                this.stopPolling();

                // Determine error type from message
                let errorType = 'general';
                const errorMsg = data.error_message || '';

                if (errorMsg.includes('timeout') || errorMsg.includes('exceeded timeout')) {
                    errorType = 'timeout';
                } else if (errorMsg.includes('429') || errorMsg.includes('rate limit')) {
                    errorType = 'rate_limit';
                } else if (errorMsg.includes('500') || errorMsg.includes('503') || errorMsg.includes('server error')) {
                    errorType = 'server_error';
                } else if (errorMsg.includes('LLM') || errorMsg.includes('failed after')) {
                    errorType = 'llm_error';
                }

                this.showError(errorMsg, errorType);
            }

        } catch (error) {
            console.error('Error checking status:', error);
            this.stopPolling();
            this.showError(error.message);
        }
    }

    /**
     * Approve strategy and continue to execution
     */
    async approveStrategy(modifiedStrategy = null, reviewNotes = '') {
        try {
            // Update progress
            this.hideStrategyReview();
            this.showProgressModal();
            this.updateProgress('executing', 70, 'Executing approved strategy...');

            const response = await fetch(`/experiments/orchestration/approve-strategy/${this.currentRunId}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    strategy_approved: true,
                    modified_strategy: modifiedStrategy,
                    review_notes: reviewNotes
                })
            });

            const data = await response.json();

            if (!data.success) {
                throw new Error(data.error || 'Failed to approve strategy');
            }

            // Poll for completion
            this.startPolling();

        } catch (error) {
            console.error('Error approving strategy:', error);
            this.showError(error.message);
        }
    }

    /**
     * Show progress modal
     */
    showProgressModal() {
        const modal = document.getElementById('llm-progress-modal');
        if (modal) {
            const bsModal = new bootstrap.Modal(modal);
            bsModal.show();
        }
    }

    /**
     * Hide progress modal
     */
    hideProgressModal() {
        const modal = document.getElementById('llm-progress-modal');
        if (modal) {
            const bsModal = bootstrap.Modal.getInstance(modal);
            if (bsModal) {
                bsModal.hide();
            }
        }
    }

    /**
     * Update progress display
     */
    updateProgress(stage, percentage, message) {
        // Update progress bar
        const progressBar = document.getElementById('llm-progress-bar');
        if (progressBar) {
            progressBar.style.width = `${percentage}%`;
            progressBar.setAttribute('aria-valuenow', percentage);
            progressBar.textContent = `${percentage}%`;
        }

        // Update status message
        const statusMessage = document.getElementById('llm-status-message');
        if (statusMessage) {
            statusMessage.textContent = message;
        }

        // Update stage indicators
        this.updateStageIndicators(stage);
    }

    /**
     * Update stage indicators (visual progress)
     */
    updateStageIndicators(currentStage) {
        const stages = ['analyzing', 'recommending', 'reviewing', 'executing', 'synthesizing'];
        const stageIndex = stages.indexOf(currentStage);

        stages.forEach((stage, index) => {
            const indicator = document.getElementById(`stage-${stage}`);
            if (indicator) {
                indicator.classList.remove('stage-current', 'stage-completed', 'stage-pending');

                if (index < stageIndex) {
                    indicator.classList.add('stage-completed');
                } else if (index === stageIndex) {
                    indicator.classList.add('stage-current');
                } else {
                    indicator.classList.add('stage-pending');
                }
            }
        });
    }

    /**
     * Show strategy review modal
     */
    showStrategyReview(data) {
        // Hide progress modal
        this.hideProgressModal();

        // Populate review modal
        const modal = document.getElementById('strategy-review-modal');
        if (!modal) {
            console.error('Strategy review modal not found');
            return;
        }

        // Set experiment goal
        const goalElement = document.getElementById('review-experiment-goal');
        if (goalElement) {
            goalElement.textContent = data.experiment_goal || 'No goal specified';
        }

        // Set confidence
        const confidenceElement = document.getElementById('review-confidence');
        if (confidenceElement) {
            const confidencePercent = Math.round(data.confidence * 100);
            confidenceElement.textContent = `${confidencePercent}%`;

            // Update progress bar
            const progressBar = confidenceElement.parentElement?.querySelector('.progress-bar');
            if (progressBar) {
                progressBar.style.width = `${confidencePercent}%`;
            }
        }

        // Set reasoning
        const reasoningElement = document.getElementById('review-reasoning');
        if (reasoningElement) {
            reasoningElement.textContent = data.strategy_reasoning || 'No reasoning provided';
        }

        // Build strategy list
        const strategyList = document.getElementById('review-strategy-list');
        if (strategyList && data.recommended_strategy) {
            strategyList.innerHTML = this.buildStrategyHTML(data.recommended_strategy);
        }

        // Show modal
        const bsModal = new bootstrap.Modal(modal);
        bsModal.show();
    }

    /**
     * Hide strategy review modal
     */
    hideStrategyReview() {
        const modal = document.getElementById('strategy-review-modal');
        if (modal) {
            const bsModal = bootstrap.Modal.getInstance(modal);
            if (bsModal) {
                bsModal.hide();
            }
        }
    }

    /**
     * Build HTML for strategy list
     */
    buildStrategyHTML(strategy) {
        let html = '<div class="list-group">';

        for (const [docId, tools] of Object.entries(strategy)) {
            html += `
                <div class="list-group-item">
                    <h6 class="mb-2">Document ${docId}</h6>
                    <ul class="mb-0">
                        ${tools.map(tool => `<li>${this.formatToolName(tool)}</li>`).join('')}
                    </ul>
                </div>
            `;
        }

        html += '</div>';
        return html;
    }

    /**
     * Format tool name for display
     */
    formatToolName(toolName) {
        const toolDisplayNames = {
            'segment_paragraph': 'Paragraph Segmentation',
            'segment_sentence': 'Sentence Segmentation',
            'extract_entities_spacy': 'Entity Extraction (spaCy)',
            'extract_temporal': 'Temporal Extraction',
            'extract_causal': 'Causal Extraction',
            'extract_definitions': 'Definition Extraction',
            'period_aware_embedding': 'Period-Aware Embeddings'
        };

        return toolDisplayNames[toolName] || toolName;
    }

    /**
     * Show completion message and redirect
     */
    showCompletionMessage(data) {
        this.hideProgressModal();

        // Show success message
        const message = `
            <div class="alert alert-success alert-dismissible fade show" role="alert">
                <strong>Analysis Complete!</strong>
                ${data.duration_seconds ? `Completed in ${Math.round(data.duration_seconds)}s.` : ''}
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            </div>
        `;

        const container = document.querySelector('.container-fluid');
        if (container) {
            container.insertAdjacentHTML('afterbegin', message);
        }

        // Redirect to results page after 2 seconds
        setTimeout(() => {
            window.location.href = `/experiments/${this.experimentId}/orchestration/llm-results/${this.currentRunId}`;
        }, 2000);
    }

    /**
     * Show error message with enhanced display and retry option
     */
    showError(message, errorType = 'general', errorData = {}) {
        // Don't hide modal - keep it visible
        const modal = document.getElementById('llm-progress-modal');
        if (!modal) return;

        // Update header to error state
        const modalHeader = modal.querySelector('.modal-header');
        modalHeader.className = 'modal-header bg-danger text-white';
        modalHeader.querySelector('.modal-title').innerHTML = `
            <i class="fas fa-exclamation-triangle me-2"></i>Orchestration Failed
        `;

        // Hide progress indicators
        document.getElementById('llm-progress-bar').parentElement.style.display = 'none';
        document.getElementById('llm-status-message').style.display = 'none';

        // Show error container
        const errorContainer = document.getElementById('llm-error-container');
        errorContainer.style.display = 'block';

        // Set error title based on type
        const errorTitles = {
            'timeout': 'Request Timeout',
            'rate_limit': 'Rate Limit Exceeded',
            'server_error': 'Server Error',
            'llm_error': 'LLM Processing Failed',
            'general': 'Orchestration Failed'
        };
        document.getElementById('error-title').textContent = errorTitles[errorType] || errorTitles['general'];

        // Set user-friendly message
        const friendlyMessage = this.getFriendlyErrorMessage(message, errorType);
        document.getElementById('error-message').textContent = friendlyMessage;

        // Set technical details
        const detailsEl = document.getElementById('error-details');
        detailsEl.textContent = `Technical details: ${message}`;

        // Show/hide retry button based on error type
        const retryBtn = document.getElementById('retry-orchestration-btn');
        const retriableTypes = ['timeout', 'rate_limit', 'server_error'];
        retryBtn.style.display = retriableTypes.includes(errorType) ? 'inline-block' : 'none';

        // Setup retry handler
        if (retryBtn.style.display !== 'none') {
            retryBtn.onclick = () => {
                this.hideError();
                this.startAnalysis();
            };
        }
    }

    /**
     * Get user-friendly error message
     */
    getFriendlyErrorMessage(technicalMessage, errorType) {
        const messages = {
            'timeout': 'The LLM took longer than expected to respond. This usually happens with large documents or high server load. Please try again.',
            'rate_limit': 'Too many requests were made in a short time. Please wait a moment and try again.',
            'server_error': 'The server encountered an unexpected error. This is usually temporary - please try again.',
            'llm_error': 'The LLM encountered an error while processing your request. Please try again or simplify your experiment.',
            'general': 'An unexpected error occurred. Please try again.'
        };

        return messages[errorType] || messages['general'];
    }

    /**
     * Hide error display and restore progress UI
     */
    hideError() {
        const errorContainer = document.getElementById('llm-error-container');
        if (errorContainer) {
            errorContainer.style.display = 'none';
        }

        // Restore progress display
        document.getElementById('llm-progress-bar').parentElement.style.display = 'block';
        document.getElementById('llm-status-message').style.display = 'block';

        // Reset header
        const modal = document.getElementById('llm-progress-modal');
        const modalHeader = modal?.querySelector('.modal-header');
        if (modalHeader) {
            modalHeader.className = 'modal-header bg-primary text-white';
            modalHeader.querySelector('.modal-title').innerHTML = `
                <i class="fas fa-robot me-2"></i>LLM Orchestration in Progress
            `;
        }
    }

    /**
     * Show partial processing warning and get user confirmation
     */
    showPartialProcessingWarning(checkData) {
        return new Promise((resolve) => {
            const modal = document.getElementById('partial-processing-modal');
            if (!modal) {
                resolve(true); // No modal, proceed anyway
                return;
            }

            // Set message
            const messageEl = document.getElementById('partial-processing-message');
            if (checkData.has_full_processing) {
                messageEl.textContent = `All ${checkData.total_documents} documents have existing processing. LLM orchestration may recommend re-processing.`;
            } else {
                messageEl.textContent = `${checkData.processed_documents} of ${checkData.total_documents} documents have existing processing.`;
            }

            // Show processed documents list
            const listEl = document.getElementById('processed-docs-list');
            listEl.innerHTML = checkData.documents
                .filter(d => d.has_processing)
                .map(d => `
                    <div class="list-group-item">
                        <strong>${d.title}</strong>
                        <br>
                        <small class="text-muted">
                            Existing: ${d.processing_types.join(', ')}
                        </small>
                    </div>
                `)
                .join('');

            // Setup buttons
            const proceedBtn = document.getElementById('proceed-anyway-btn');
            const cancelHandler = () => resolve(false);
            const proceedHandler = () => {
                const bsModal = bootstrap.Modal.getInstance(modal);
                if (bsModal) bsModal.hide();
                resolve(true);
            };

            // Remove old listeners by cloning buttons
            const newProceedBtn = proceedBtn.cloneNode(true);
            proceedBtn.parentNode.replaceChild(newProceedBtn, proceedBtn);

            newProceedBtn.addEventListener('click', proceedHandler);

            // Handle modal close/cancel
            modal.addEventListener('hidden.bs.modal', cancelHandler, { once: true });

            // Show modal
            const bsModal = new bootstrap.Modal(modal);
            bsModal.show();
        });
    }

    /**
     * Get user-friendly message for stage
     */
    getStageMessage(stage) {
        const messages = {
            'analyzing': 'Analyzing experiment goals and documents...',
            'recommending': 'Recommending processing strategy...',
            'reviewing': 'Awaiting your review...',
            'executing': 'Processing documents with approved tools...',
            'synthesizing': 'Generating cross-document insights...',
            'completed': 'Analysis complete!',
            'failed': 'Analysis failed'
        };

        return messages[stage] || 'Processing...';
    }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    const analyzeButton = document.getElementById('analyze-experiment-btn');

    if (analyzeButton) {
        // Get experiment ID from button data attribute or URL
        const experimentId = analyzeButton.dataset.experimentId ||
                           window.location.pathname.match(/\/experiments\/(\d+)/)?.[1];

        if (experimentId) {
            const client = new LLMOrchestrationClient(parseInt(experimentId));

            analyzeButton.addEventListener('click', function() {
                client.startAnalysis();
            });

            // Handle approve button in strategy review modal
            const approveButton = document.getElementById('approve-strategy-btn');
            if (approveButton) {
                approveButton.addEventListener('click', function() {
                    const reviewNotes = document.getElementById('review-notes')?.value || '';
                    client.approveStrategy(null, reviewNotes);
                });
            }
        }
    }
});
