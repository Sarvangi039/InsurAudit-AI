/* -------------------------------------------------------------
   INSURAUDIT.AI FRONTEND APPLICATION CONTROLLER
   Vanilla JavaScript for Responsive UI Interactions & API calls
   ------------------------------------------------------------- */

// State variables
let currentClaimId = null;
let currentClaimData = null;
let activeDocId = null;
let activePageNum = 1;
let viewerZoom = 100;
let viewerRotation = 0;
let ruleFilter = 'all';

// Constants
const API_BASE = '/api';

// DOM Selectors
const dropzone = document.getElementById('dropzone');
const fileInput = document.getElementById('file-input');
const btnBrowse = document.getElementById('btn-browse');
const ledgerBody = document.getElementById('ledger-body');
const ledgerCount = document.getElementById('ledger-count');
const workspaceContent = document.getElementById('workspace-content');
const workspaceEmptyState = document.querySelector('.empty-workspace-message');
const auditWorkspace = document.getElementById('audit-details-workspace');
const docTabsContainer = document.getElementById('doc-tabs-container');
const activeDocName = document.getElementById('active-document-name');

// Ingestion/Viewer Elements
const viewerDisplay = document.getElementById('viewer-display');
const viewerImage = document.getElementById('viewer-image');
const btnZoomIn = document.getElementById('btn-zoom-in');
const btnZoomOut = document.getElementById('btn-zoom-out');
const zoomLevelText = document.getElementById('zoom-level');
const btnRotate = document.getElementById('btn-rotate');
const btnPrevPage = document.getElementById('btn-prev-page');
const btnNextPage = document.getElementById('btn-next-page');
const pageNumDisplay = document.getElementById('page-num-display');
const processingOverlay = document.getElementById('processing-overlay');
const loaderTitle = document.getElementById('loader-title');
const loaderSubtitle = document.getElementById('loader-subtitle');

// Profile Dashboard Elements
const patientNameDisplay = document.getElementById('patient-name-display');
const policyNumDisplay = document.getElementById('policy-num-display');
const riskScoreValue = document.getElementById('risk-score-value');
const gaugeProgress = document.getElementById('gauge-progress');
const riskRatingBadge = document.getElementById('risk-rating-badge');
const aiSummaryText = document.getElementById('ai-summary-text');
const rulesListContainer = document.getElementById('rules-list-container');
const currentClaimStatus = document.getElementById('current-claim-status');
const btnProcessPipeline = document.getElementById('btn-process-pipeline');
const btnSaveProfile = document.getElementById('btn-save-profile');

// Forms & Inputs
const profileForm = document.getElementById('profile-edit-form');
const inputComments = document.getElementById('auditor-comments');

// Settings Modal Elements
const btnSettings = document.getElementById('btn-settings');
const settingsModal = document.getElementById('settings-modal');
const btnCloseSettings = document.getElementById('btn-close-settings');
const inputApiKey = document.getElementById('input-api-key');
const inputAuditorId = document.getElementById('input-auditor-id');
const btnSaveSettings = document.getElementById('btn-save-settings');
const btnTriggerUpload = document.getElementById('btn-trigger-upload');

// Initialize App
document.addEventListener('DOMContentLoaded', () => {
    loadSettings();
    loadClaimsLedger();
    setupEventListeners();
});

// Load Settings from LocalStorage
function loadSettings() {
    const apiKey = localStorage.getItem('gemini_api_key') || '';
    const auditorId = localStorage.getItem('auditor_id') || 'Auditor-01';
    inputApiKey.value = apiKey;
    inputAuditorId.value = auditorId;
}

// Get Dynamic Headers for API requests
function getHeaders() {
    const headers = { 'Content-Type': 'application/json' };
    const apiKey = localStorage.getItem('gemini_api_key');
    if (apiKey && apiKey.trim() !== '') {
        headers['X-Gemini-API-Key'] = apiKey.trim();
    }
    return headers;
}

// Fetch Claims from Registry
async function loadClaimsLedger() {
    try {
        const response = await fetch(`${API_BASE}/claims`);
        const claims = await response.json();
        
        ledgerCount.textContent = `${claims.length} Claims`;
        renderLedgerTable(claims);
    } catch (error) {
        console.error('Error fetching ledger:', error);
        ledgerBody.innerHTML = `
            <tr>
                <td colspan="5" class="text-center text-danger py-4">
                    <i class="fa-solid fa-circle-exclamation"></i> Error loading claims list. Check backend connectivity.
                </td>
            </tr>
        `;
    }
}

// Render ledger rows
function renderLedgerTable(claims) {
    if (claims.length === 0) {
        ledgerBody.innerHTML = `
            <tr>
                <td colspan="5" class="text-center text-muted py-4">
                    <i class="fa-solid fa-folder-open"></i> No claims ingested yet. Click "Upload New Claim" to start.
                </td>
            </tr>
        `;
        return;
    }

    ledgerBody.innerHTML = '';
    claims.forEach(claim => {
        const tr = document.createElement('tr');
        tr.dataset.id = claim.id;
        if (claim.id === currentClaimId) {
            tr.classList.add('active');
        }

        const date = new Date(claim.created_at).toLocaleDateString(undefined, {
            month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit'
        });

        // Determine Risk Band Styling
        let riskClass = 'badge-info';
        if (claim.risk_score >= 56) riskClass = 'badge-danger';
        else if (claim.risk_score >= 26) riskClass = 'badge-warning';
        else if (claim.risk_score > 0) riskClass = 'badge-success';

        // Determine Status Styling
        let statusClass = 'status-pending';
        if (claim.status === 'Approved') statusClass = 'status-approved';
        else if (claim.status === 'Rejected') statusClass = 'status-rejected';
        else if (claim.status === 'Queried') statusClass = 'status-queried';

        tr.innerHTML = `
            <td>
                <div class="font-bold">${claim.patient_name || 'Upload Bundle'}</div>
                <div class="text-xs text-muted">ID: ${claim.id.slice(0,8)}... | Policy: ${claim.policy_number || 'N/A'}</div>
            </td>
            <td>Rs. ${(claim.total_claimed || 0).toLocaleString()}</td>
            <td><span class="badge ${riskClass}">${claim.risk_score}/100</span></td>
            <td><span class="status-badge ${statusClass}">${claim.status}</span></td>
            <td class="text-muted">${date}</td>
            <td style="width: 30px; text-align: right;">
                <button onclick="deleteClaim('${claim.id}', event)" class="btn-delete-claim" title="Delete Claim" style="background:none; border:none; color:#ef4444; cursor:pointer; padding:5px;">
                    <i class="fa-solid fa-trash"></i>
                </button>
            </td>
        `;

        tr.addEventListener('click', () => selectClaim(claim.id));
        ledgerBody.appendChild(tr);
    });
}

// Delete a claim
async function deleteClaim(claimId, event) {
    event.stopPropagation(); // Prevent row click
    if (!confirm('Are you sure you want to permanently delete this claim?')) return;
    
    try {
        const response = await fetch(`${API_BASE}/claims/${claimId}`, {
            method: 'DELETE'
        });
        
        if (response.ok) {
            if (currentClaimId === claimId) {
                currentClaimId = null;
                currentClaimData = null;
                workspaceContent.style.display = 'none';
                workspaceEmptyState.style.display = 'flex';
            }
            loadClaimsLedger();
        } else {
            alert('Failed to delete claim');
        }
    } catch (error) {
        console.error('Error deleting claim:', error);
        alert('Error connecting to server');
    }
}

// Select a claim to inspect
async function selectClaim(claimId) {
    currentClaimId = claimId;
    
    // Highlight selected row
    document.querySelectorAll('#ledger-body tr').forEach(row => {
        row.classList.remove('active');
        if (row.dataset.id === claimId) row.classList.add('active');
    });

    showLoader("Loading claim details...", "Retrieving OCR profiles and rules records");

    try {
        const response = await fetch(`${API_BASE}/claims/${claimId}`);
        const claim = await response.json();
        
        currentClaimData = claim;
        renderClaimWorkspace(claim);
        hideLoader();
    } catch (error) {
        console.error('Error loading claim details:', error);
        hideLoader();
        alert('Could not retrieve claim details.');
    }
}

// Draw/Update Radial Gauge
function updateRiskGauge(score) {
    riskScoreValue.textContent = score;
    
    // Circumference = 2 * pi * r = 2 * 3.14159 * 40 = 251.2
    const offset = 251.2 - (score / 100) * 251.2;
    gaugeProgress.style.strokeDashoffset = offset;
    
    // Animate color based on risk score bands
    let color = 'var(--color-low)';
    let band = 'LOW RISK';
    let badgeClass = 'badge-success';
    
    if (score >= 56) {
        color = 'var(--color-critical)';
        band = 'CRITICAL / FRAUD RISK';
        badgeClass = 'badge-danger';
    } else if (score >= 26) {
        color = 'var(--color-med)';
        band = 'MEDIUM RISK';
        badgeClass = 'badge-warning';
    } else if (score > 0) {
        color = 'var(--color-ok)';
        band = 'LOW RISK';
        badgeClass = 'badge-success';
    } else {
        band = 'PENDING ANALYSIS';
        badgeClass = 'badge-info';
    }
    
    gaugeProgress.style.stroke = color;
    riskRatingBadge.textContent = band;
    riskRatingBadge.className = `badge ${badgeClass}`;
}

// Render workspace info
function renderClaimWorkspace(claim) {
    // Show workspace
    workspaceContent.classList.remove('hidden');
    workspaceEmptyState.classList.add('hidden');
    auditWorkspace.classList.remove('empty-state');

    // Update profile
    patientNameDisplay.textContent = claim.patient_name || 'Awaiting Process...';
    policyNumDisplay.textContent = claim.policy_number || 'N/A';
    
    // Status
    currentClaimStatus.textContent = claim.status.toUpperCase();
    currentClaimStatus.className = `status-badge status-${claim.status.toLowerCase()}`;
    
    // Comments
    const lastDecision = claim.decisions && claim.decisions[0];
    inputComments.value = lastDecision ? lastDecision.comments : '';

    // Risk Gauge
    updateRiskGauge(claim.risk_score);

    // AI Executive Summary
    aiSummaryText.textContent = claim.summary || 'Claims documents ingested. Press "Process Claim" to run the Vision OCR pipelines.';

    // Render documents tabs
    renderDocumentTabs(claim);

    // Render rules list
    renderRulesList(claim.flags);

    // Populate claims data profile form
    populateProfileForm(claim.profile);
    
    // Hide re-evaluate button initially
    btnSaveProfile.classList.add('hidden');
}

// Setup tabs for each uploaded doc
function renderDocumentTabs(claim) {
    docTabsContainer.innerHTML = '';
    activeDocName.textContent = '';
    
    if (!claim.documents || claim.documents.length === 0) {
        // Show dropzone if no docs in claim (fallback)
        dropzone.classList.remove('hidden');
        viewerDisplay.classList.add('hidden');
        return;
    }

    dropzone.classList.add('hidden');
    viewerDisplay.classList.remove('hidden');

    claim.documents.forEach((doc, idx) => {
        const button = document.createElement('button');
        button.className = 'doc-tab';
        if (idx === 0) {
            button.classList.add('active');
            activeDocId = doc.id;
            activePageNum = 1;
            loadPageImage(doc, 1);
        }
        
        // Show truncated label
        const displayLabel = doc.file_name.length > 20 ? doc.file_name.slice(0, 17) + '...' : doc.file_name;
        button.innerHTML = `<i class="fa-solid fa-file-lines text-xs mr-1"></i> ${displayLabel}`;
        button.addEventListener('click', () => {
            document.querySelectorAll('.doc-tab').forEach(b => b.classList.remove('active'));
            button.classList.add('active');
            activeDocId = doc.id;
            activePageNum = 1;
            loadPageImage(doc, 1);
        });
        
        docTabsContainer.appendChild(button);
    });
}

// Display page image in viewer
function loadPageImage(doc, pageNum) {
    activePageNum = pageNum;
    activeDocName.textContent = `— ${doc.doc_type} (${pageNum}/${doc.pages_count})`;
    
    // Determine proper file name
    const ext = doc.file_name.split('.').pop().toLowerCase();
    let imageSrc = '';
    if (ext === 'pdf') {
        imageSrc = `/data/processed/${currentClaimId}/${doc.id}_page_${pageNum}.png`;
    } else {
        imageSrc = `/data/processed/${currentClaimId}/${doc.id}_page_1.${ext}`;
    }
    
    // Cache busted image source
    viewerImage.src = `${imageSrc}?t=${new Date().getTime()}`;
    
    // Reset transforms
    viewerZoom = 100;
    viewerRotation = 0;
    applyViewerTransforms();
    
    // Render pagination display
    pageNumDisplay.textContent = `Page ${pageNum} / ${doc.pages_count}`;
    btnPrevPage.disabled = pageNum <= 1;
    btnNextPage.disabled = pageNum >= doc.pages_count;
}

function applyViewerTransforms() {
    viewerImage.style.transform = `scale(${viewerZoom / 100}) rotate(${viewerRotation}deg)`;
    zoomLevelText.textContent = `${viewerZoom}%`;
}

// Generate Rules Checked elements
function renderRulesList(flags) {
    rulesListContainer.innerHTML = '';
    
    // Static definition of all checks to show complete engine listing
    const defaultRules = [
        { id: 'ID_NAME_CONSISTENCY', name: 'Patient name consistency', category: 'Identity', baseSeverity: 'HIGH' },
        { id: 'ID_POLICY_ELIGIBILITY', name: 'Policy eligibility on admission', category: 'Identity', baseSeverity: 'CRITICAL' },
        { id: 'ID_POLICY_LINKAGE', name: 'ID-to-policy linkage verification', category: 'Identity', baseSeverity: 'HIGH' },
        { id: 'ID_DOCTOR_REGISTRATION', name: 'Doctor registration check', category: 'Identity', baseSeverity: 'MED' },
        { id: 'DATE_ADMISSION_BEFORE_DISCHARGE', name: 'Admission before discharge date', category: 'Date & Timeline', baseSeverity: 'CRITICAL' },
        { id: 'DATE_LOS_PLAUSIBILITY', name: 'LOS vs diagnosis plausibility', category: 'Date & Timeline', baseSeverity: 'MED' },
        { id: 'DATE_PRESCRIPTION_ALIGNMENT', name: 'Prescription date alignment', category: 'Date & Timeline', baseSeverity: 'MED' },
        { id: 'BILL_DUPLICATE_ITEMS', name: 'Duplicate bill line detection', category: 'Billing', baseSeverity: 'CRITICAL' },
        { id: 'BILL_SUM_MISMATCH', name: 'Itemized vs total mismatch', category: 'Billing', baseSeverity: 'HIGH' },
        { id: 'BILL_ROOM_RENT_LIMIT_EXCEEDED', name: 'Room rent vs policy tier limits', category: 'Billing', baseSeverity: 'HIGH' },
        { id: 'FRAUD_BLACKLIST_PROVIDER', name: 'Known fraud provider list check', category: 'Fraud', baseSeverity: 'CRITICAL' },
        { id: 'FRAUD_BLACKLIST_DOCTOR', name: 'Known fraud doctor check', category: 'Fraud', baseSeverity: 'CRITICAL' },
        { id: 'FRAUD_ROUND_BILLING', name: 'Round-number billing audit', category: 'Fraud', baseSeverity: 'LOW' },
        { id: 'FRAUD_IMPOSSIBLE_LOS', name: 'Impossible Length of stay check', category: 'Fraud', baseSeverity: 'CRITICAL' }
    ];

    // Count rules
    let triggeredCount = 0;
    let passedCount = 0;
    
    // Check which checks have active flags
    const activeFlagsMap = {};
    if (flags) {
        flags.forEach(f => {
            activeFlagsMap[f.rule_id] = f;
        });
    }

    // Filter and render
    defaultRules.forEach(rule => {
        const activeFlag = activeFlagsMap[rule.id];
        const isFailed = !!activeFlag;
        
        if (isFailed) triggeredCount++;
        else passedCount++;

        // Filter tab checks
        if (ruleFilter === 'failed' && !isFailed) return;
        if (ruleFilter === 'passed' && isFailed) return;

        const ruleDiv = document.createElement('div');
        ruleDiv.className = 'rule-item';
        
        const severity = isFailed ? activeFlag.severity : rule.baseSeverity;
        const msg = isFailed ? activeFlag.message : `Rule validation cleared. No mismatch detected in ${rule.category.toLowerCase()} checks.`;
        const indicatorClass = isFailed ? 'rule-indicator-fail' : 'rule-indicator-pass';
        
        ruleDiv.innerHTML = `
            <div class="rule-item-top">
                <div class="rule-title-group">
                    <span class="rule-indicator ${indicatorClass}"></span>
                    <span class="rule-name">${rule.name}</span>
                </div>
                <span class="rule-badge rule-badge-${severity.toLowerCase()}">${severity}</span>
            </div>
            <div class="rule-message">${msg}</div>
            ${isFailed && activeFlag.evidence ? `<div class="rule-evidence">Evidence: ${activeFlag.evidence}</div>` : ''}
        `;
        
        rulesListContainer.appendChild(ruleDiv);
    });

    // Populate rule count headings
    document.getElementById('rule-count-all').textContent = defaultRules.length;
    document.getElementById('rule-count-failed').textContent = triggeredCount;
    document.getElementById('rule-count-passed').textContent = passedCount;
}

// Populate claims profile values
function populateProfileForm(profile) {
    if (!profile) return;
    
    document.getElementById('prof-patient-name').value = profile.patient_name || '';
    document.getElementById('prof-policy-num').value = profile.policy_number || '';
    document.getElementById('prof-admission-date').value = profile.admission_date || '';
    document.getElementById('prof-discharge-date').value = profile.discharge_date || '';
    document.getElementById('prof-total-claimed').value = profile.total_billed_amount || 0.0;
    document.getElementById('prof-hospital-name').value = profile.hospital_name || '';
    document.getElementById('prof-doctor-reg').value = profile.doctor_registration || '';
    document.getElementById('prof-diagnosis').value = profile.diagnosis || '';
    document.getElementById('prof-rent-limit').value = profile.policy_room_rent_limit || '';
    document.getElementById('prof-policy-start').value = profile.policy_start_date || '';
    document.getElementById('prof-policy-end').value = profile.policy_end_date || '';
}

// Setup UI Handlers
function setupEventListeners() {
    // Browse button trigger
    btnBrowse.addEventListener('click', () => fileInput.click());
    
    // File input selection
    fileInput.addEventListener('change', () => {
        if (fileInput.files.length > 0) handleFileUpload(fileInput.files);
    });

    // Drag and drop events
    dropzone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropzone.classList.add('dragover');
    });

    dropzone.addEventListener('dragleave', () => {
        dropzone.classList.remove('dragover');
    });

    dropzone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropzone.classList.remove('dragover');
        if (e.dataTransfer.files.length > 0) handleFileUpload(e.dataTransfer.files);
    });

    // Header Trigger Upload button
    btnTriggerUpload.addEventListener('click', () => {
        currentClaimId = null;
        workspaceContent.classList.add('hidden');
        workspaceEmptyState.classList.remove('hidden');
        auditWorkspace.classList.add('empty-state');
        dropzone.classList.remove('hidden');
        viewerDisplay.classList.add('hidden');
        fileInput.value = '';
        fileInput.click(); // Automatically open the file selector dialog
    });

    // Ingestion Actions (Process Pipeline)
    btnProcessPipeline.addEventListener('click', runClaimAIPipeline);

    // Zoom & Rotate Buttons
    btnZoomIn.addEventListener('click', () => {
        if (viewerZoom < 300) {
            viewerZoom += 25;
            applyViewerTransforms();
        }
    });

    btnZoomOut.addEventListener('click', () => {
        if (viewerZoom > 50) {
            viewerZoom -= 25;
            applyViewerTransforms();
        }
    });

    btnRotate.addEventListener('click', () => {
        viewerRotation = (viewerRotation + 90) % 360;
        applyViewerTransforms();
    });

    // Page navigation
    btnPrevPage.addEventListener('click', () => {
        if (activePageNum > 1 && currentClaimData) {
            const activeDoc = currentClaimData.documents.find(d => d.id === activeDocId);
            if (activeDoc) loadPageImage(activeDoc, activePageNum - 1);
        }
    });

    btnNextPage.addEventListener('click', () => {
        if (currentClaimData) {
            const activeDoc = currentClaimData.documents.find(d => d.id === activeDocId);
            if (activeDoc && activePageNum < activeDoc.pages_count) {
                loadPageImage(activeDoc, activePageNum + 1);
            }
        }
    });

    // Auditor Decision Submissions
    document.getElementById('btn-decision-approve').addEventListener('click', () => submitDecision('Approved'));
    document.getElementById('btn-decision-reject').addEventListener('click', () => submitDecision('Rejected'));
    document.getElementById('btn-decision-query').addEventListener('click', () => submitDecision('Queried'));

    // Rules Tabs Filter clicks
    document.querySelectorAll('.rule-tab').forEach(tab => {
        tab.addEventListener('click', (e) => {
            document.querySelectorAll('.rule-tab').forEach(t => t.classList.remove('active'));
            tab.classList.add('active');
            ruleFilter = tab.dataset.filter;
            if (currentClaimData) renderRulesList(currentClaimData.flags);
        });
    });

    // Profile form edits validation (Show save override button when inputs edit)
    profileForm.querySelectorAll('input').forEach(input => {
        input.addEventListener('input', () => {
            btnSaveProfile.classList.remove('hidden');
        });
    });

    // Re-evaluate button click handler
    btnSaveProfile.addEventListener('click', submitProfileOverrides);

    // Settings Modal handlers
    btnSettings.addEventListener('click', () => {
        loadSettings();
        settingsModal.classList.remove('hidden');
    });

    btnCloseSettings.addEventListener('click', () => {
        settingsModal.classList.add('hidden');
    });

    btnSaveSettings.addEventListener('click', () => {
        localStorage.setItem('gemini_api_key', inputApiKey.value);
        localStorage.setItem('auditor_id', inputAuditorId.value);
        settingsModal.classList.add('hidden');
        // Reload details if active
        if (currentClaimId) selectClaim(currentClaimId);
    });

    // Close modal on gray space click
    window.addEventListener('click', (e) => {
        if (e.target === settingsModal) settingsModal.classList.add('hidden');
    });
}

// File Upload Handler (POST multipart)
async function handleFileUpload(filesList) {
    showLoader("Uploading Documents...", "Generating unique claim ID and writing buffer storage");
    
    const formData = new FormData();
    for (let i = 0; i < filesList.length; i++) {
        formData.append('files', filesList[i]);
    }

    try {
        const response = await fetch(`${API_BASE}/claims/upload`, {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) throw new Error('Upload request failed.');
        
        const data = await response.json();
        
        // Refresh claims ledger
        await loadClaimsLedger();
        
        // Auto-select newly uploaded claim
        selectClaim(data.claim_id);
    } catch (error) {
        console.error('Upload error:', error);
        hideLoader();
        alert('File upload failed. Ensure the server is running.');
    }
}

// Trigger Complete Vision OCR & Rule Audit pipeline (POST)
async function runClaimAIPipeline() {
    if (!currentClaimId) return;

    showLoader(
        "Ingesting & Running Vision OCR...", 
        "Extracting layouts, classifying documents, and evaluating rules via Gemini"
    );

    try {
        const response = await fetch(`${API_BASE}/claims/${currentClaimId}/process`, {
            method: 'POST',
            headers: getHeaders()
        });

        if (!response.ok) throw new Error('Claim processing pipeline returned failure.');
        
        const claim = await response.json();
        currentClaimData = claim;
        
        // Refresh ledger entries in backend
        await loadClaimsLedger();
        
        // Redraw workspace
        renderClaimWorkspace(claim);
        hideLoader();
    } catch (error) {
        console.error('Pipeline processing error:', error);
        hideLoader();
        alert('AI processing failed. Check Gemini API key configuration in settings.');
    }
}

// Submit Profile Edits (POST manual overrides)
async function submitProfileOverrides(e) {
    e.preventDefault();
    if (!currentClaimId) return;

    showLoader("Re-evaluating Audit Rules...", "Recalculating fuzzy matches, dates, and score bounds");

    const payload = {
        patient_name: document.getElementById('prof-patient-name').value || null,
        policy_number: document.getElementById('prof-policy-num').value || null,
        admission_date: document.getElementById('prof-admission-date').value || null,
        discharge_date: document.getElementById('prof-discharge-date').value || null,
        total_billed_amount: parseFloat(document.getElementById('prof-total-claimed').value) || 0.0,
        hospital_name: document.getElementById('prof-hospital-name').value || null,
        diagnosis: document.getElementById('prof-diagnosis').value || null,
        doctor_registration: document.getElementById('prof-doctor-reg').value || null,
        policy_room_rent_limit: parseFloat(document.getElementById('prof-rent-limit').value) || null,
        policy_start_date: document.getElementById('prof-policy-start').value || null,
        policy_end_date: document.getElementById('prof-policy-end').value || null
    };

    try {
        const response = await fetch(`${API_BASE}/claims/${currentClaimId}/update`, {
            method: 'POST',
            headers: getHeaders(),
            body: JSON.stringify(payload)
        });

        if (!response.ok) throw new Error('Data override failed.');

        const claim = await response.json();
        currentClaimData = claim;
        
        // Refresh ledger
        await loadClaimsLedger();
        
        // Re-render
        renderClaimWorkspace(claim);
        hideLoader();
    } catch (error) {
        console.error('Override update error:', error);
        hideLoader();
        alert('Could not update profile overrides.');
    }
}

// Submit Final Auditor Decision
async function submitDecision(decision) {
    if (!currentClaimId) return;
    
    const comments = inputComments.value.trim();
    if (comments === '') {
        alert('Please write auditor review findings/notes before submitting.');
        return;
    }

    showLoader("Signing off Claim...", "Writing decision entry into immutable audit log");

    const auditorId = localStorage.getItem('auditor_id') || 'Auditor-01';
    const payload = {
        auditor_id: auditorId,
        decision: decision,
        comments: comments
    };

    try {
        const response = await fetch(`${API_BASE}/claims/${currentClaimId}/decision`, {
            method: 'POST',
            headers: getHeaders(),
            body: JSON.stringify(payload)
        });

        if (!response.ok) throw new Error('Decision submission failed.');

        // Refresh details and ledger
        await loadClaimsLedger();
        
        // Re-select
        const res = await fetch(`${API_BASE}/claims/${currentClaimId}`);
        const claim = await res.json();
        currentClaimData = claim;
        renderClaimWorkspace(claim);
        hideLoader();
    } catch (error) {
        console.error('Decision submission error:', error);
        hideLoader();
        alert('Could not save decision sign-off.');
    }
}

// Loading Spinner Helpers
function showLoader(title, subtitle) {
    loaderTitle.textContent = title;
    loaderSubtitle.textContent = subtitle;
    processingOverlay.classList.remove('hidden');
}

function hideLoader() {
    processingOverlay.classList.add('hidden');
}
