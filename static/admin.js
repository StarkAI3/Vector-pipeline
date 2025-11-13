/**
 * Admin Panel JavaScript
 * Handles file upload, questionnaire, progress tracking, and job monitoring
 */

// State management
let selectedFile = null;
let currentJobId = null;
let pollingInterval = null;

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    initializeUpload();
    loadRecentJobs();
    
    // Refresh jobs every 5 seconds
    setInterval(loadRecentJobs, 5000);
});

/**
 * Initialize file upload handlers
 */
function initializeUpload() {
    const uploadSection = document.getElementById('uploadSection');
    const fileInput = document.getElementById('fileInput');
    
    // Click to upload
    uploadSection.addEventListener('click', () => {
        fileInput.click();
    });
    
    // File selected
    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            handleFileSelection(e.target.files[0]);
        }
    });
    
    // Drag and drop
    uploadSection.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadSection.classList.add('dragover');
    });
    
    uploadSection.addEventListener('dragleave', () => {
        uploadSection.classList.remove('dragover');
    });
    
    uploadSection.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadSection.classList.remove('dragover');
        
        if (e.dataTransfer.files.length > 0) {
            handleFileSelection(e.dataTransfer.files[0]);
        }
    });
}

/**
 * Handle file selection
 */
function handleFileSelection(file) {
    // Detect file type
    const fileType = getFileType(file.name);
    
    // Validate file type
    const supportedTypes = ['json', 'excel', 'csv', 'text', 'pdf'];
    if (!supportedTypes.includes(fileType)) {
        alert('Unsupported file type. Supported: JSON, Excel (.xlsx, .xls), CSV, Text (.txt, .md), PDF');
        return;
    }
    
    // Validate file size (50MB max)
    if (file.size > 50 * 1024 * 1024) {
        alert('File size must be less than 50MB');
        return;
    }
    
    selectedFile = file;
    
    // Update file info display
    document.getElementById('selectedFileInfo').textContent = `${file.name} (${formatFileSize(file.size)})`;
    
    // Populate structure options based on file type
    populateStructureOptions(fileType);
    
    // Show questionnaire
    document.getElementById('uploadSection').style.display = 'none';
    document.getElementById('questionnaireSection').classList.add('active');
}

/**
 * Get file type from filename
 */
function getFileType(filename) {
    const ext = filename.toLowerCase().split('.').pop();
    
    if (ext === 'json') return 'json';
    if (ext === 'xlsx' || ext === 'xls' || ext === 'xlsm') return 'excel';
    if (ext === 'csv' || ext === 'tsv') return 'csv';
    if (ext === 'txt' || ext === 'md' || ext === 'markdown') return 'text';
    if (ext === 'pdf') return 'pdf';
    
    return 'unknown';
}

/**
 * Format file size for display
 */
function formatFileSize(bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}

/**
 * Populate structure options based on file type
 */
function populateStructureOptions(fileType) {
    const select = document.getElementById('contentStructure');
    const helpText = document.getElementById('structureHelp');
    
    // Clear existing options
    select.innerHTML = '<option value="">Select structure type...</option>';
    
    let structures = [];
    let help = '';
    
    if (fileType === 'json') {
        structures = [
            {value: 'array_of_objects', label: 'Array of Objects (Standard table-like data)', help: 'Each object is like a table row'},
            {value: 'nested_objects', label: 'Nested Objects (Hierarchical structure)', help: 'Objects within objects'},
            {value: 'web_scraping_output', label: 'Web Scraping Output (url, title, content)', help: 'Contains web page data'},
            {value: 'api_response', label: 'API Response (status, data wrapper)', help: 'Standard API response format'}
        ];
        help = 'Select the structure that matches your JSON file';
        
    } else if (fileType === 'excel') {
        structures = [
            {value: 'standard_table', label: 'Standard Data Table (Headers + rows)', help: 'Most common: one header row, data rows below'},
            {value: 'faq_table', label: 'FAQ Table (Question & Answer columns)', help: '2 or 4 columns with Q&A'},
            {value: 'directory_list', label: 'Directory/Contact List (Name, Position, etc.)', help: 'Officer directories, contact lists'},
            {value: 'service_catalog', label: 'Service Catalog (Service descriptions)', help: 'Government services and schemes'},
            {value: 'multiple_sheets', label: 'Multiple Sheets (Different data per sheet)', help: 'Workbook with multiple sheets'},
            {value: 'text_in_cells', label: 'Text in Cells (Long paragraphs)', help: 'Cells contain narrative text'},
            {value: 'complex_layout', label: 'Complex Layout (Merged cells, multiple tables)', help: 'Irregular structure'}
        ];
        help = 'Select the structure that best matches your Excel file';
        
    } else if (fileType === 'csv') {
        structures = [
            {value: 'standard_table', label: 'Standard Data Table (Headers + rows)', help: 'Most common CSV format'},
            {value: 'faq_table', label: 'FAQ Table (Question & Answer columns)', help: 'CSV with Q&A format'},
            {value: 'directory_list', label: 'Directory/Contact List', help: 'Contact information table'},
            {value: 'service_catalog', label: 'Service Catalog', help: 'Services and schemes'}
        ];
        help = 'Select the structure that matches your CSV file';
        
    } else if (fileType === 'text') {
        structures = [
            {value: 'narrative_document', label: 'Narrative Document (Paragraphs and text)', help: 'Policy documents, guidelines, articles'},
            {value: 'structured_markdown', label: 'Structured Markdown (Headings, lists, tables)', help: 'Markdown with # headings and formatting'},
            {value: 'faq_format', label: 'FAQ Format (Q: A: pattern)', help: 'Question and Answer pairs in text'},
            {value: 'directory_format', label: 'Directory Format (Name: Position: Contact:)', help: 'Contact information in text format'},
            {value: 'mixed_content', label: 'Mixed Content (Various formats)', help: 'Text with multiple content types'}
        ];
        help = 'Select the structure that matches your text/markdown file';
        
    } else if (fileType === 'pdf') {
        structures = [
            {value: 'text_document', label: 'Text Document (Articles, policies, guidelines)', help: 'Pure text PDF with paragraphs'},
            {value: 'document_with_tables', label: 'Document with Tables (Mix of text and tables)', help: 'PDF containing both text and tables'},
            {value: 'mostly_tables', label: 'Mostly Tables (Directory, lists, data tables)', help: 'PDF is primarily tables, like Excel in PDF format'},
            {value: 'faq_document', label: 'FAQ Document (Question-Answer format)', help: 'PDF with Q&A pairs'},
            {value: 'scanned_document', label: 'Scanned Document (Needs OCR)', help: 'Old scanned papers, will use OCR'},
            {value: 'form_template', label: 'Form/Application (Form fields and instructions)', help: 'Application forms, registration forms'},
            {value: 'complex_mix', label: 'Complex Mix (Text + Tables + Images)', help: 'PDF with all types of content - let system auto-detect'}
        ];
        help = 'Select the structure that best matches your PDF document';
    }
    
    // Add options
    structures.forEach(s => {
        const option = document.createElement('option');
        option.value = s.value;
        option.textContent = s.label;
        option.title = s.help;
        select.appendChild(option);
    });
    
    helpText.textContent = help;
}

/**
 * Cancel upload and return to file selection
 */
function cancelUpload() {
    selectedFile = null;
    document.getElementById('fileInput').value = '';
    document.getElementById('uploadSection').style.display = 'block';
    document.getElementById('questionnaireSection').classList.remove('active');
}

/**
 * Submit upload with questionnaire data
 */
async function submitUpload() {
    if (!selectedFile) {
        alert('No file selected');
        return;
    }
    
    // Get form data
    const contentStructure = document.getElementById('contentStructure').value;
    const language = document.getElementById('language').value;
    const category = document.getElementById('category').value;
    const importance = document.getElementById('importance').value;
    const chunkSize = document.getElementById('chunkSize').value;
    
    // Validate required fields
    if (!contentStructure || !category) {
        alert('Please fill in all required fields');
        return;
    }
    
    // Detect file type
    const fileType = getFileType(selectedFile.name);
    
    // Prepare form data
    const formData = new FormData();
    formData.append('file', selectedFile);
    formData.append('file_type', fileType);
    formData.append('content_structure', contentStructure);
    formData.append('language', language);
    formData.append('category', category);
    formData.append('importance', importance);
    formData.append('chunk_size', chunkSize);
    formData.append('special_elements', JSON.stringify([]));
    
    // Show progress section
    document.getElementById('questionnaireSection').classList.remove('active');
    document.getElementById('progressSection').classList.add('active');
    updateProgress(5, 'Uploading file...');
    
    try {
        // Upload file
        const response = await fetch('/api/admin/upload', {
            method: 'POST',
            body: formData
        });
        
        const result = await response.json();
        
        if (!result.success) {
            throw new Error(result.detail || 'Upload failed');
        }
        
        currentJobId = result.job_id;
        updateProgress(10, 'File uploaded. Starting processing...');
        
        // Start polling for job status
        startJobPolling();
        
    } catch (error) {
        console.error('Upload error:', error);
        showError('Upload failed: ' + error.message);
    }
}

/**
 * Start polling for job status updates
 */
function startJobPolling() {
    if (pollingInterval) {
        clearInterval(pollingInterval);
    }
    
    pollingInterval = setInterval(async () => {
        try {
            const response = await fetch(`/api/admin/job/${currentJobId}`);
            const result = await response.json();
            
            if (result.success) {
                const job = result.job;
                
                // Update progress
                updateProgress(
                    job.progress_percentage,
                    job.current_step || 'Processing...'
                );
                
                // Check if completed or failed
                if (job.status === 'completed') {
                    clearInterval(pollingInterval);
                    showSuccess(job);
                    loadRecentJobs();
                } else if (job.status === 'failed') {
                    clearInterval(pollingInterval);
                    showError('Processing failed: ' + (job.error_message || 'Unknown error'));
                    loadRecentJobs();
                }
            }
        } catch (error) {
            console.error('Polling error:', error);
        }
    }, 2000); // Poll every 2 seconds
}

/**
 * Update progress bar
 */
function updateProgress(percentage, message) {
    const progressFill = document.getElementById('progressFill');
    const progressText = document.getElementById('progressText');
    
    progressFill.style.width = percentage + '%';
    progressFill.textContent = percentage + '%';
    progressText.textContent = message;
}

/**
 * Show success result
 */
function showSuccess(job) {
    const resultSection = document.getElementById('resultSection');
    const progressSection = document.getElementById('progressSection');
    
    progressSection.classList.remove('active');
    resultSection.classList.add('active');
    
    // Check if this was a duplicate upload
    if (job.is_duplicate) {
        showDuplicateNotification(job);
    }
    
    resultSection.innerHTML = `
        <div class="success-message">
            <h3>✅ Processing Complete!</h3>
            <p><strong>File:</strong> ${job.filename}</p>
            <p><strong>Job ID:</strong> ${job.job_id}</p>
            <p><strong>Source ID:</strong> ${job.source_id || 'N/A'}</p>
            ${job.is_duplicate ? '<span class="duplicate-badge">🔄 Duplicate Data Updated</span>' : ''}
            
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-value">${job.chunks_created || 0}</div>
                    <div class="stat-label">Chunks Created</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">${job.chunks_uploaded || 0}</div>
                    <div class="stat-label">Vectors ${job.is_duplicate ? 'Updated' : 'Uploaded'}</div>
                </div>
            </div>
            
            <button class="btn btn-primary" onclick="resetUpload()" style="margin-top: 20px; width: 100%;">
                Upload Another File
            </button>
        </div>
    `;
}

/**
 * Show error result
 */
function showError(message) {
    const resultSection = document.getElementById('resultSection');
    const progressSection = document.getElementById('progressSection');
    
    progressSection.classList.remove('active');
    resultSection.classList.add('active');
    
    resultSection.innerHTML = `
        <div class="error-message">
            <h3>❌ Processing Failed</h3>
            <p>${message}</p>
            
            <button class="btn btn-primary" onclick="resetUpload()" style="margin-top: 15px; width: 100%;">
                Try Again
            </button>
        </div>
    `;
}

/**
 * Reset upload for new file
 */
function resetUpload() {
    selectedFile = null;
    currentJobId = null;
    document.getElementById('fileInput').value = '';
    
    // Reset all sections
    document.getElementById('uploadSection').style.display = 'block';
    document.getElementById('questionnaireSection').classList.remove('active');
    document.getElementById('progressSection').classList.remove('active');
    document.getElementById('resultSection').classList.remove('active');
    
    // Reset form
    document.getElementById('contentStructure').value = '';
    document.getElementById('language').value = 'en';
    document.getElementById('category').value = '';
    document.getElementById('importance').value = 'normal';
    document.getElementById('chunkSize').value = 'medium';
    
    // Reload jobs
    loadRecentJobs();
}

/**
 * Load recent jobs
 */
async function loadRecentJobs() {
    try {
        const response = await fetch('/api/admin/jobs?limit=10');
        const result = await response.json();
        
        if (result.success && result.jobs.length > 0) {
            displayJobs(result.jobs);
        }
    } catch (error) {
        console.error('Error loading jobs:', error);
    }
}

/**
 * Display jobs list
 */
function displayJobs(jobs) {
    const jobsList = document.getElementById('jobsList');
    
    if (jobs.length === 0) {
        jobsList.innerHTML = '<p style="text-align: center; color: #666;">No jobs yet. Upload a file to get started!</p>';
        return;
    }
    
    jobsList.innerHTML = jobs.map(job => {
        const statusClass = `status-${job.status}`;
        const statusText = job.status.charAt(0).toUpperCase() + job.status.slice(1);
        
        return `
            <div class="job-item">
                <div class="job-info">
                    <strong>${job.filename}</strong>
                    <br>
                    <small style="color: #666;">
                        ${new Date(job.created_at).toLocaleString()}
                        ${job.status === 'processing' ? ` • ${job.progress_percentage}%` : ''}
                    </small>
                </div>
                <div class="job-status ${statusClass}">${statusText}</div>
            </div>
        `;
    }).join('');
}

/**
 * Format file size
 */
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i];
}

/**
 * Show duplicate data notification
 */
function showDuplicateNotification(job) {
    const container = document.getElementById('notificationContainer');
    
    const notification = document.createElement('div');
    notification.className = 'notification warning';
    notification.innerHTML = `
        <div class="notification-header">
            <div class="notification-title">
                <span class="notification-icon">⚠️</span>
                Duplicate Data Detected
            </div>
            <button class="notification-close" onclick="closeNotification(this)">×</button>
        </div>
        <div class="notification-body">
            <p><strong>This file has been uploaded before!</strong></p>
            <p>The system detected that <strong>"${job.filename}"</strong> contains data that already exists in the vector database.</p>
            <p>✅ <strong>Action Taken:</strong> Existing vectors were updated with the new data (no duplicates created).</p>
            <p style="margin-top: 10px;">
                <strong>📊 Details:</strong><br>
                • Source ID: <code style="background: #f3f4f6; padding: 2px 6px; border-radius: 4px;">${job.source_id}</code><br>
                • Vectors Updated: ${job.chunks_uploaded || 0}<br>
                • Previous Count: ${job.existing_vectors || 0}
            </p>
        </div>
        <div class="notification-actions">
            <button class="notification-btn notification-btn-primary" onclick="closeNotification(this.parentElement.parentElement.parentElement)">
                Got It
            </button>
        </div>
    `;
    
    container.appendChild(notification);
    
    // Auto-close after 15 seconds
    setTimeout(() => {
        if (notification.parentElement) {
            closeNotification(notification);
        }
    }, 15000);
}

/**
 * Show a notification message
 */
function showNotification(message, type = 'info') {
    const container = document.getElementById('notificationContainer');
    
    const icons = {
        'success': '✅',
        'error': '❌',
        'warning': '⚠️',
        'info': 'ℹ️'
    };
    
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.innerHTML = `
        <div class="notification-header">
            <div class="notification-title">
                <span class="notification-icon">${icons[type] || icons['info']}</span>
                ${type.charAt(0).toUpperCase() + type.slice(1)}
            </div>
            <button class="notification-close" onclick="closeNotification(this)">×</button>
        </div>
        <div class="notification-body">
            <p>${message}</p>
        </div>
    `;
    
    container.appendChild(notification);
    
    // Auto-close after 5 seconds for non-error messages
    if (type !== 'error') {
        setTimeout(() => {
            if (notification.parentElement) {
                closeNotification(notification);
            }
        }, 5000);
    }
}

/**
 * Close notification
 */
function closeNotification(element) {
    // Find the notification element
    const notification = element.classList && element.classList.contains('notification') 
        ? element 
        : element.closest('.notification');
    
    if (notification) {
        notification.style.animation = 'slideOut 0.3s ease-out';
        setTimeout(() => {
            notification.remove();
        }, 300);
    }
}

// Add slide-out animation dynamically
const style = document.createElement('style');
style.textContent = `
    @keyframes slideOut {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(400px);
            opacity: 0;
        }
    }
`;
document.head.appendChild(style);

// ============================================================================
// DELETION FUNCTIONALITY
// ============================================================================

// State for deletion
let selectedChunks = [];
let selectedDocuments = [];
let deletionPreview = null;

/**
 * Switch between Upload and Delete tabs
 */
function switchTab(tabName) {
    // Update tab buttons
    document.querySelectorAll('.tab').forEach(tab => {
        tab.classList.remove('active');
        if (tab.textContent.includes(tabName === 'upload' ? 'Upload' : 'Delete')) {
            tab.classList.add('active');
        }
    });
    
    // Update tab content
    document.getElementById('uploadTab').classList.toggle('active', tabName === 'upload');
    document.getElementById('deleteTab').classList.toggle('active', tabName === 'delete');
}

/**
 * Search chunks by semantic content
 */
async function searchByContent() {
    const query = document.getElementById('contentSearch').value.trim();
    const topK = parseInt(document.getElementById('topK').value) || 10;
    
    if (!query) {
        showNotification('Please enter a search query', 'error');
        return;
    }
    
    const resultsDiv = document.getElementById('contentSearchResults');
    resultsDiv.innerHTML = '<p>Searching...</p>';
    
    try {
        const formData = new FormData();
        formData.append('query', query);
        formData.append('top_k', topK.toString());
        
        const response = await fetch('/api/admin/search/semantic', {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        if (data.success && data.result.chunks.length > 0) {
            displayContentSearchResults(data.result.chunks);
        } else {
            resultsDiv.innerHTML = '<p>No results found.</p>';
        }
    } catch (error) {
        showNotification('Search failed: ' + error.message, 'error');
        resultsDiv.innerHTML = '<p>Error: ' + error.message + '</p>';
    }
}

/**
 * Display semantic search results
 */
function displayContentSearchResults(chunks) {
    const resultsDiv = document.getElementById('contentSearchResults');
    resultsDiv.innerHTML = `<h4>Found ${chunks.length} results:</h4>`;
    
    chunks.forEach((chunk, index) => {
        const confidence = chunk.confidence_level;
        const confidenceClass = `confidence-${confidence}`;
        const confidenceIcon = confidence === 'high' ? '✅' : confidence === 'medium' ? '⚠️' : '❌';
        
        const item = document.createElement('div');
        item.className = 'result-item';
        item.innerHTML = `
            <div style="display: flex; align-items: start; gap: 10px;">
                <input type="checkbox" class="checkbox" onchange="toggleChunkSelection('${chunk.chunk_id}', this.checked, '${chunk.source_id}')">
                <div style="flex: 1;">
                    <div style="display: flex; align-items: center; margin-bottom: 8px;">
                        <strong>${confidenceIcon} ${confidence.toUpperCase()}</strong>
                        <span class="confidence-badge ${confidenceClass}">Score: ${(chunk.similarity_score || 0).toFixed(3)}</span>
                    </div>
                    <p><strong>File:</strong> ${chunk.metadata.filename || 'unknown'}</p>
                    <p><strong>Chunk ID:</strong> ${chunk.chunk_id}</p>
                    <p style="margin-top: 8px; color: #666; font-style: italic;">${chunk.text_preview || 'No preview available'}...</p>
                </div>
            </div>
        `;
        resultsDiv.appendChild(item);
    });
    
    updateSelectedItemsDisplay();
}

/**
 * Search documents by filename
 */
async function searchByFilename() {
    const filename = document.getElementById('filenameSearch').value.trim();
    
    if (!filename) {
        showNotification('Please enter a filename', 'error');
        return;
    }
    
    const resultsDiv = document.getElementById('filenameSearchResults');
    resultsDiv.innerHTML = '<p>Searching...</p>';
    
    try {
        const response = await fetch(`/api/admin/search/filename?filename=${encodeURIComponent(filename)}&exact=true`);
        const data = await response.json();
        
        if (data.success && data.documents.length > 0) {
            displayFilenameSearchResults(data.documents);
        } else {
            resultsDiv.innerHTML = '<p>No documents found with that filename.</p>';
        }
    } catch (error) {
        showNotification('Search failed: ' + error.message, 'error');
        resultsDiv.innerHTML = '<p>Error: ' + error.message + '</p>';
    }
}

/**
 * Display filename search results
 */
function displayFilenameSearchResults(documents) {
    const resultsDiv = document.getElementById('filenameSearchResults');
    resultsDiv.innerHTML = `<h4>Found ${documents.length} document(s):</h4>`;
    
    documents.forEach(doc => {
        const item = document.createElement('div');
        item.className = 'document-item';
        item.innerHTML = `
            <div class="document-info">
                <h4>${doc.filename}</h4>
                <div class="document-meta">
                    Source ID: ${doc.source_id} | 
                    Chunks: ${doc.chunk_count} | 
                    Category: ${doc.category || 'N/A'} | 
                    Uploaded: ${doc.upload_date || 'N/A'}
                </div>
            </div>
            <input type="checkbox" class="checkbox" onchange="toggleDocumentSelection('${doc.source_id}', this.checked, '${doc.filename}', ${doc.chunk_count})">
        `;
        resultsDiv.appendChild(item);
    });
    
    updateSelectedItemsDisplay();
}

/**
 * Load all documents
 */
async function loadAllDocuments() {
    const resultsDiv = document.getElementById('allDocumentsList');
    resultsDiv.innerHTML = '<p>Loading documents...</p>';
    
    try {
        const response = await fetch('/api/admin/documents?limit=100');
        const data = await response.json();
        
        if (data.success && data.documents.length > 0) {
            displayAllDocuments(data.documents);
        } else {
            resultsDiv.innerHTML = '<p>No documents found in database.</p>';
        }
    } catch (error) {
        showNotification('Failed to load documents: ' + error.message, 'error');
        resultsDiv.innerHTML = '<p>Error: ' + error.message + '</p>';
    }
}

/**
 * Display all documents
 */
function displayAllDocuments(documents) {
    const resultsDiv = document.getElementById('allDocumentsList');
    resultsDiv.innerHTML = `<h4>All Documents (${documents.length}):</h4>`;
    
    documents.forEach(doc => {
        const item = document.createElement('div');
        item.className = 'document-item';
        item.innerHTML = `
            <div class="document-info">
                <h4>${doc.filename}</h4>
                <div class="document-meta">
                    Source ID: ${doc.source_id} | 
                    Chunks: ${doc.chunk_count} | 
                    Category: ${doc.category || 'N/A'} | 
                    Uploaded: ${doc.upload_date || 'N/A'}
                </div>
            </div>
            <input type="checkbox" class="checkbox" onchange="toggleDocumentSelection('${doc.source_id}', this.checked, '${doc.filename}', ${doc.chunk_count})">
        `;
        resultsDiv.appendChild(item);
    });
    
    updateSelectedItemsDisplay();
}

/**
 * Toggle chunk selection
 */
function toggleChunkSelection(chunkId, selected, sourceId) {
    if (selected) {
        if (!selectedChunks.find(c => c.chunk_id === chunkId)) {
            selectedChunks.push({ chunk_id: chunkId, source_id: sourceId });
        }
    } else {
        selectedChunks = selectedChunks.filter(c => c.chunk_id !== chunkId);
    }
    updateSelectedItemsDisplay();
}

/**
 * Toggle document selection
 */
function toggleDocumentSelection(sourceId, selected, filename, chunkCount) {
    if (selected) {
        if (!selectedDocuments.find(d => d.source_id === sourceId)) {
            selectedDocuments.push({ source_id: sourceId, filename, chunk_count: chunkCount });
        }
    } else {
        selectedDocuments = selectedDocuments.filter(d => d.source_id !== sourceId);
    }
    updateSelectedItemsDisplay();
}

/**
 * Update selected items display
 */
function updateSelectedItemsDisplay() {
    const selectedDiv = document.getElementById('selectedForDeletion');
    const itemsList = document.getElementById('selectedItemsList');
    
    const totalSelected = selectedChunks.length + selectedDocuments.length;
    
    if (totalSelected > 0) {
        selectedDiv.style.display = 'block';
        itemsList.innerHTML = '';
        
        if (selectedDocuments.length > 0) {
            const docsHtml = selectedDocuments.map(doc => 
                `<div style="padding: 10px; background: white; border-radius: 5px; margin-bottom: 5px;">
                    📄 ${doc.filename} (${doc.chunk_count} chunks) - ${doc.source_id}
                </div>`
            ).join('');
            itemsList.innerHTML += `<h4>Documents (${selectedDocuments.length}):</h4>${docsHtml}`;
        }
        
        if (selectedChunks.length > 0) {
            itemsList.innerHTML += `<h4 style="margin-top: 15px;">Chunks (${selectedChunks.length}):</h4>`;
            selectedChunks.slice(0, 10).forEach(chunk => {
                itemsList.innerHTML += `<div style="padding: 10px; background: white; border-radius: 5px; margin-bottom: 5px; font-size: 0.9rem;">
                    📝 ${chunk.chunk_id}
                </div>`;
            });
            if (selectedChunks.length > 10) {
                itemsList.innerHTML += `<p style="color: #666;">... and ${selectedChunks.length - 10} more chunks</p>`;
            }
        }
    } else {
        selectedDiv.style.display = 'none';
    }
}

/**
 * Clear selection
 */
function clearSelection() {
    selectedChunks = [];
    selectedDocuments = [];
    updateSelectedItemsDisplay();
    document.getElementById('deletionPreview').style.display = 'none';
}

/**
 * Preview deletion
 */
async function previewDeletion() {
    if (selectedChunks.length === 0 && selectedDocuments.length === 0) {
        showNotification('Please select items to delete', 'error');
        return;
    }
    
    const previewDiv = document.getElementById('deletionPreview');
    const previewContent = document.getElementById('previewContent');
    previewContent.innerHTML = '<p>Generating preview...</p>';
    previewDiv.style.display = 'block';
    
    try {
        const sourceIds = selectedDocuments.map(d => d.source_id);
        const chunkIds = selectedChunks.map(c => c.chunk_id);
        
        const response = await fetch('/api/admin/delete/preview', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ source_ids: sourceIds, chunk_ids: chunkIds })
        });
        
        const data = await response.json();
        
        if (data.success) {
            const preview = data.preview;
            previewContent.innerHTML = `
                <p><strong>Documents to delete:</strong> ${preview.total_documents}</p>
                <p><strong>Chunks to delete:</strong> ${preview.total_chunks}</p>
                ${preview.warnings.length > 0 ? `<div style="margin-top: 10px; color: #dc3545;"><strong>Warnings:</strong><ul>${preview.warnings.map(w => `<li>${w}</li>`).join('')}</ul></div>` : ''}
            `;
            deletionPreview = preview;
        } else {
            previewContent.innerHTML = '<p style="color: #dc3545;">Error generating preview</p>';
        }
    } catch (error) {
        previewContent.innerHTML = '<p style="color: #dc3545;">Error: ' + error.message + '</p>';
    }
}

/**
 * Cancel deletion
 */
function cancelDeletion() {
    document.getElementById('deletionPreview').style.display = 'none';
    deletionPreview = null;
}

/**
 * Confirm and execute deletion
 */
async function confirmDeletion() {
    if (!deletionPreview) {
        showNotification('Please preview deletion first', 'error');
        return;
    }
    
    if (!confirm('Are you sure you want to delete these items? This action cannot be undone!')) {
        return;
    }
    
    const sourceIds = selectedDocuments.map(d => d.source_id);
    const chunkIds = selectedChunks.map(c => c.chunk_id);
    
    try {
        showNotification('Deleting items...', 'info');
        
        // Delete documents
        if (sourceIds.length > 0) {
            const response = await fetch('/api/admin/delete/documents', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(sourceIds)
            });
            const data = await response.json();
            
            if (!data.success) {
                const errorMsg = data.message || data.result?.errors?.join(', ') || 'Document deletion failed';
                throw new Error(errorMsg);
            }
        }
        
        // Delete chunks
        if (chunkIds.length > 0) {
            const response = await fetch('/api/admin/delete/chunks', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(chunkIds)
            });
            const data = await response.json();
            
            if (!data.success) {
                const errorMsg = data.message || data.result?.errors?.join(', ') || 'Chunk deletion failed';
                throw new Error(errorMsg);
            }
        }
        
        const totalDeleted = sourceIds.length + chunkIds.length;
        showNotification(`Successfully deleted ${totalDeleted} item(s) from the vector database!`, 'success');
        
        // Clear selection and reset UI
        clearSelection();
        document.getElementById('deletionPreview').style.display = 'none';
        
        // Clear search results
        document.getElementById('contentSearchResults').innerHTML = '';
        document.getElementById('filenameSearchResults').innerHTML = '';
        document.getElementById('allDocumentsList').innerHTML = '';
        
    } catch (error) {
        showNotification('Deletion failed: ' + error.message, 'error');
    }
}

