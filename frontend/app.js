// API Base URL
const API_BASE = '/api';

// State
let currentContent = [];
let currentFilter = '';
let currentSort = 'date';

// Initialize dashboard
document.addEventListener('DOMContentLoaded', () => {
    initializeDashboard();
    setupEventListeners();
});

// Setup event listeners
function setupEventListeners() {
    document.getElementById('extract-all-btn').addEventListener('click', extractAllSources);
    document.getElementById('submit-pending-btn').addEventListener('click', submitPending);
    document.getElementById('refresh-btn').addEventListener('click', loadContent);
    document.getElementById('status-filter').addEventListener('change', handleFilterChange);
    document.getElementById('sort-by').addEventListener('change', handleSortChange);
    document.querySelector('.close').addEventListener('click', closeModal);

    // Close modal on outside click
    window.addEventListener('click', (event) => {
        const modal = document.getElementById('content-modal');
        if (event.target === modal) {
            closeModal();
        }
    });
}

// Initialize dashboard data
async function initializeDashboard() {
    await loadStatistics();
    await loadContent();
    await loadSources();

    // Refresh data every 30 seconds
    setInterval(async () => {
        await loadStatistics();
        await loadContent();
    }, 30000);
}

// Load statistics
async function loadStatistics() {
    try {
        const response = await fetch(`${API_BASE}/stats`);
        const data = await response.json();

        // Update stat cards
        document.getElementById('total-today').textContent = data.extraction.totalToday;
        document.getElementById('total-submitted').textContent = data.submission.totalSubmitted;
        document.getElementById('success-rate').textContent = `${data.submission.successRate}%`;
        document.getElementById('avg-score').textContent = data.extraction.averageScore;

        // Update status breakdown
        const statusBreakdown = document.getElementById('status-breakdown');
        statusBreakdown.innerHTML = '';

        const statuses = [
            { key: 'pending', label: 'Pending', class: 'status-pending' },
            { key: 'submitted', label: 'Submitted', class: 'status-submitted' },
            { key: 'rejected', label: 'Rejected', class: 'status-rejected' },
            { key: 'failed', label: 'Failed', class: 'status-failed' }
        ];

        statuses.forEach(status => {
            const count = data.extraction.totalByStatus[status.key] || 0;
            const div = document.createElement('div');
            div.className = `status-item ${status.class}`;
            div.innerHTML = `
                <span class="count">${count}</span>
                <span class="label">${status.label}</span>
            `;
            statusBreakdown.appendChild(div);
        });

    } catch (error) {
        console.error('Error loading statistics:', error);
    }
}

// Load content
async function loadContent() {
    try {
        const statusFilter = currentFilter ? `&status=${currentFilter}` : '';
        const response = await fetch(`${API_BASE}/content?limit=50${statusFilter}`);
        const data = await response.json();

        currentContent = data.content;
        renderContentTable(currentContent);

    } catch (error) {
        console.error('Error loading content:', error);
    }
}

// Render content table
function renderContentTable(content) {
    const tbody = document.getElementById('content-tbody');

    if (!content || content.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" class="empty-state">No content found</td></tr>';
        return;
    }

    // Sort content based on current sort option
    const sortedContent = [...content];
    if (currentSort === 'score') {
        sortedContent.sort((a, b) => b.preFilterScore - a.preFilterScore);
    } else {
        // Sort by date (newest first)
        sortedContent.sort((a, b) => new Date(b.extractedAt) - new Date(a.extractedAt));
    }

    tbody.innerHTML = sortedContent.map(item => `
        <tr>
            <td>
                <a href="#" onclick="showContentDetails('${item._id}'); return false;">
                    ${truncate(item.title, 60)}
                </a>
            </td>
            <td>${item.sourceName}</td>
            <td>${item.preFilterScore}</td>
            <td>
                <span class="status-badge badge-${item.status}">${item.status}</span>
                ${item.verificationRequestId ?
                    `<br><small style="color: #7f8c8d;">VR: ${item.verificationRequestId.substring(0, 8)}</small>` :
                    ''}
            </td>
            <td>${formatDate(item.extractedAt)}</td>
        </tr>
    `).join('');
}

// Load sources
async function loadSources() {
    try {
        const response = await fetch(`${API_BASE}/sources`);
        const data = await response.json();

        const sourcesList = document.getElementById('sources-list');
        sourcesList.innerHTML = '';

        data.sources.forEach(source => {
            const div = document.createElement('div');
            div.className = 'source-item';
            div.innerHTML = `
                <div class="source-name">${source.name}</div>
                <div class="source-status ${source.isActive ? 'source-active' : 'source-inactive'}">
                    ${source.isActive ? '● Active' : '○ Inactive'}
                </div>
                <div class="source-status">
                    Last extraction: ${source.lastExtraction ? formatDate(source.lastExtraction) : 'Never'}
                </div>
                <div class="source-status">
                    Extracted: ${source.totalExtracted} | Submitted: ${source.totalSubmitted}
                </div>
            `;
            sourcesList.appendChild(div);
        });

    } catch (error) {
        console.error('Error loading sources:', error);
    }
}

// Extract from all sources
async function extractAllSources() {
    if (!confirm('Trigger extraction from all active sources?')) {
        return;
    }

    try {
        const btn = document.getElementById('extract-all-btn');
        btn.disabled = true;
        btn.textContent = 'Extracting...';

        const response = await fetch(`${API_BASE}/sources/extract-all`, {
            method: 'POST'
        });

        const data = await response.json();

        if (response.ok) {
            alert(`Extraction complete!\nTotal extracted: ${data.totalExtracted}\nSources processed: ${data.sourceCount}`);
            await loadStatistics();
            await loadContent();
            await loadSources();
        } else {
            throw new Error(data.detail || 'Extraction failed');
        }

    } catch (error) {
        console.error('Error extracting sources:', error);
        alert('Error: ' + error.message);
    } finally {
        const btn = document.getElementById('extract-all-btn');
        btn.disabled = false;
        btn.textContent = 'Extract All Sources';
    }
}

// Submit pending items
async function submitPending() {
    if (!confirm('Submit all pending items that meet the score threshold?')) {
        return;
    }

    try {
        const btn = document.getElementById('submit-pending-btn');
        btn.disabled = true;
        btn.textContent = 'Submitting...';

        const response = await fetch(`${API_BASE}/aletheia/submit-pending`, {
            method: 'POST'
        });

        const data = await response.json();

        if (response.ok) {
            alert(`Submission complete:\nSuccessful: ${data.result.successful}\nFailed: ${data.result.failed}`);
            await loadStatistics();
            await loadContent();
        } else {
            throw new Error(data.detail || 'Submission failed');
        }

    } catch (error) {
        console.error('Error submitting pending:', error);
        alert('Error: ' + error.message);
    } finally {
        const btn = document.getElementById('submit-pending-btn');
        btn.disabled = false;
        btn.textContent = 'Submit Pending Items';
    }
}


// Show content details in modal
async function showContentDetails(contentId) {
    try {
        const response = await fetch(`${API_BASE}/content/${contentId}`);
        const content = await response.json();

        const modal = document.getElementById('content-modal');
        const modalTitle = document.getElementById('modal-title');
        const modalBody = document.getElementById('modal-body');

        modalTitle.textContent = content.title;

        modalBody.innerHTML = `
            <div class="detail-row">
                <div class="detail-label">Source</div>
                <div class="detail-value">${content.sourceName}</div>
            </div>
            <div class="detail-row">
                <div class="detail-label">URL</div>
                <div class="detail-value"><a href="${content.sourceUrl}" target="_blank">${content.sourceUrl}</a></div>
            </div>
            <div class="detail-row">
                <div class="detail-label">Content</div>
                <div class="detail-value">${content.content}</div>
            </div>
            <div class="detail-row">
                <div class="detail-label">Pre-Filter Score</div>
                <div class="detail-value">${content.preFilterScore} / 60</div>
            </div>
            <div class="detail-row">
                <div class="detail-label">Status</div>
                <div class="detail-value"><span class="status-badge badge-${content.status}">${content.status}</span></div>
            </div>
            <div class="detail-row">
                <div class="detail-label">Extracted At</div>
                <div class="detail-value">${formatDate(content.extractedAt)}</div>
            </div>
            ${content.verificationRequestId ? `
                <div class="detail-row">
                    <div class="detail-label">Verification Request ID</div>
                    <div class="detail-value">${content.verificationRequestId}</div>
                </div>
            ` : ''}
            ${content.submissionError ? `
                <div class="detail-row">
                    <div class="detail-label">Submission Error</div>
                    <div class="detail-value" style="color: #e74c3c;">${content.submissionError}</div>
                </div>
            ` : ''}
        `;

        modal.style.display = 'block';

    } catch (error) {
        console.error('Error loading content details:', error);
    }
}

// Close modal
function closeModal() {
    document.getElementById('content-modal').style.display = 'none';
}

// Handle filter change
function handleFilterChange(event) {
    currentFilter = event.target.value;
    loadContent();
}

// Handle sort change
function handleSortChange(event) {
    currentSort = event.target.value;
    // Re-render current content with new sort
    renderContentTable(currentContent);
}

// Utility functions
function truncate(text, maxLength) {
    if (text.length <= maxLength) return text;
    return text.substring(0, maxLength) + '...';
}

function formatDate(dateString) {
    if (!dateString) return 'N/A';
    const date = new Date(dateString);
    return date.toLocaleString('pt-BR', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit'
    });
}
