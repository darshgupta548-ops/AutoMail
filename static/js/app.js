/**
 * AUTO-MAIL — Space Mission Control Frontend Application
 * Vanilla JS REST API Orchestrator & View Controller
 */

document.addEventListener('DOMContentLoaded', () => {
  // =========================================================================
  // STATE MANAGEMENT
  // =========================================================================
  const state = {
    activeJob: null,
    editableContext: null,
    uploadedFiles: {
      poster: null,
      background: null
    },
    telemetryTimer: null
  };

  // =========================================================================
  // DOM ELEMENT REFERENCES
  // =========================================================================
  const views = {
    dashboard: document.getElementById('view-dashboard'),
    create: document.getElementById('view-create'),
    contextReview: document.getElementById('view-context-review'),
    pipelinePreview: document.getElementById('view-pipeline-preview')
  };

  const navLinks = {
    brand: document.getElementById('nav-brand'),
    dashboard: document.getElementById('nav-dashboard'),
    create: document.getElementById('nav-create')
  };

  const telemetryPill = document.getElementById('telemetry-pill');
  const telemetryJobName = document.getElementById('telemetry-job-name');
  const pastJobsGrid = document.getElementById('past-jobs-grid');

  // Modals & Toasts
  const telemetryModal = document.getElementById('telemetry-modal');
  const telemetryStatusMsg = document.getElementById('telemetry-status-msg');
  const regenConfirmModal = document.getElementById('regen-confirm-modal');
  const toastContainer = document.getElementById('toast-container');

  // Forms & Inputs
  const createJobForm = document.getElementById('create-job-form');
  const reviewContextForm = document.getElementById('review-context-form');
  const editorSectionsContainer = document.getElementById('editor-sections-container');

  // Dropzones
  const dropzonePoster = document.getElementById('dropzone-poster');
  const dropzoneBg = document.getElementById('dropzone-bg');
  const filePosterInput = document.getElementById('file-poster');
  const fileBgInput = document.getElementById('file-bg');
  const posterPreviewContainer = document.getElementById('poster-preview-container');
  const bgPreviewContainer = document.getElementById('bg-preview-container');

  // Buttons
  const btnHeroNew = document.getElementById('btn-hero-new');
  const btnCancelCreate = document.getElementById('btn-cancel-create');
  const btnBackDashboard = document.getElementById('btn-back-dashboard');
  const btnAddSection = document.getElementById('btn-add-section');
  const btnTriggerRegen = document.getElementById('btn-trigger-regen');
  const btnCancelRegen = document.getElementById('btn-cancel-regen');
  const btnConfirmRegen = document.getElementById('btn-confirm-regen');
  const btnPipelineReturn = document.getElementById('btn-pipeline-return');

  // =========================================================================
  // TOAST NOTIFICATIONS & TELEMETRY LOADER
  // =========================================================================
  function showToast(message, duration = 3500) {
    const toast = document.createElement('div');
    toast.className = 'toast-msg';
    toast.textContent = message;
    toastContainer.appendChild(toast);
    setTimeout(() => {
      toast.style.opacity = '0';
      setTimeout(() => toast.remove(), 300);
    }, duration);
  }

  function startTelemetryLoader(statusMessages) {
    telemetryModal.classList.add('active');
    let index = 0;
    telemetryStatusMsg.textContent = statusMessages[0];
    state.telemetryTimer = setInterval(() => {
      index = (index + 1) % statusMessages.length;
      telemetryStatusMsg.textContent = statusMessages[index];
    }, 1400);
  }

  function stopTelemetryLoader() {
    clearInterval(state.telemetryTimer);
    telemetryModal.classList.remove('active');
  }

  // =========================================================================
  // NAVIGATION & STEPPER ROUTER
  // =========================================================================
  function switchView(viewName, stepNumber = 1) {
    Object.keys(views).forEach(key => {
      views[key].classList.toggle('active', key === viewName);
    });

    navLinks.dashboard.classList.toggle('active', viewName === 'dashboard');
    navLinks.create.classList.toggle('active', viewName === 'create');

    updateStepper(stepNumber);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  function updateStepper(activeStep) {
    const stepItems = document.querySelectorAll('.step-item');
    const progressBar = document.getElementById('stepper-bar');

    stepItems.forEach(item => {
      const step = parseInt(item.getAttribute('data-step'), 10);
      item.classList.toggle('active', step === activeStep);
      item.classList.toggle('completed', step < activeStep);
    });

    const progressPercentage = ((activeStep - 1) / 6) * 100;
    progressBar.style.width = `${progressPercentage}%`;
  }

  function updateTelemetryPill(job) {
    if (job) {
      telemetryPill.style.display = 'flex';
      telemetryJobName.textContent = `ACTIVE MISSION: ${job.event_name.toUpperCase()} [#${job.id}]`;
    } else {
      telemetryPill.style.display = 'none';
    }
  }

  // =========================================================================
  // API CLIENT METHODS
  // =========================================================================
  async function apiFetchJobs() {
    try {
      const res = await fetch('/api/jobs');
      const data = await res.json();
      if (data.success) {
        renderJobsGrid(data.jobs);
      } else {
        showToast(`Failed to load missions: ${data.error}`);
      }
    } catch (err) {
      showToast('Network error loading mission telemetry.');
    }
  }

  async function apiCreateJob(jobData) {
    const res = await fetch('/api/jobs', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(jobData)
    });
    return await res.json();
  }

  async function apiUploadAssets(jobId, posterFile, bgFile) {
    const formData = new FormData();
    if (posterFile) formData.append('poster', posterFile);
    if (bgFile) formData.append('background', bgFile);

    const res = await fetch(`/api/jobs/${jobId}/assets`, {
      method: 'POST',
      body: formData
    });
    return await res.json();
  }

  async function apiGenerateContext(jobId) {
    const res = await fetch(`/api/jobs/${jobId}/context/generate`, {
      method: 'POST'
    });
    return await res.json();
  }

  async function apiApproveContext(jobId, contextPayload) {
    const res = await fetch(`/api/jobs/${jobId}/context`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(contextPayload)
    });
    return await res.json();
  }

  // =========================================================================
  // DASHBOARD RENDERER
  // =========================================================================
  function getStatusBadgeHtml(status) {
    switch (status) {
      case 'DRAFT': return '<span class="status-badge badge-draft">● DRAFT</span>';
      case 'CONTEXT_GENERATED': return '<span class="status-badge badge-generated">● CONTEXT GENERATED</span>';
      case 'CONTEXT_APPROVED': return '<span class="status-badge badge-approved">● CONTEXT APPROVED</span>';
      default: return `<span class="status-badge badge-draft">● ${status}</span>`;
    }
  }

  function renderJobsGrid(jobs) {
    if (!jobs || jobs.length === 0) {
      pastJobsGrid.innerHTML = `
        <div class="empty-state-card" style="grid-column: 1 / -1; text-align: center; padding: 60px 40px; background: rgba(15, 23, 42, 0.4); border: 1px dashed var(--border-subtle); border-radius: var(--radius-lg);">
          <div style="font-size: 32px; color: var(--text-dim); margin-bottom: 16px;">⊘</div>
          <h3 style="font-family: var(--font-heading); font-size: 16px; color: var(--text-main); margin-bottom: 8px;">NO MISSIONS LOGGED</h3>
          <p style="color: var(--text-muted); font-family: var(--font-mono); font-size: 12px;">SYSTEM STANDBY. READY TO INITIALIZE NEW CAMPAIGN.</p>
        </div>
      `;
      return;
    }

    // Sort descending by ID
    const sortedJobs = [...jobs].sort((a, b) => b.id - a.id);
    pastJobsGrid.innerHTML = sortedJobs.map(job => `
      <div class="job-card" data-job-id="${job.id}">
        <div>
          <div class="job-card-meta">
            <span style="font-family: var(--font-mono); font-size: 11px; color: var(--text-dim);">MISSION #${job.id}</span>
            ${getStatusBadgeHtml(job.status)}
          </div>
          <h3 class="job-card-title">${job.event_name}</h3>
          <p class="job-card-desc">${job.event_description}</p>
        </div>
        <div class="job-card-footer">
          <span>DATE: ${job.event_date}</span>
          <button class="btn-mission btn-mission-secondary btn-sm open-job-btn" data-id="${job.id}">RESUME ➔</button>
        </div>
      </div>
    `).join('');

    document.querySelectorAll('.open-job-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const jobId = parseInt(e.target.getAttribute('data-id'), 10);
        loadMissionWorkflow(jobId);
      });
    });
  }

  async function loadMissionWorkflow(jobId) {
    try {
      const res = await fetch(`/api/jobs/${jobId}`);
      const data = await res.json();
      if (data.success) {
        state.activeJob = data.job;
        updateTelemetryPill(data.job);

        if (data.job.status === 'CONTEXT_GENERATED' || data.job.status === 'CONTEXT_APPROVED') {
          populateContextEditor(data.job.email_context);
          switchView('contextReview', 3);
        } else {
          showToast(`Mission #${jobId} loaded in ${data.job.status} state.`);
          switchView('create', 1);
        }
      }
    } catch (err) {
      showToast('Failed to load selected mission telemetry.');
    }
  }

  // =========================================================================
  // FILE UPLOAD DROPZONES
  // =========================================================================
  function setupDropzone(zoneEl, inputEl, previewEl, fileTypeKey) {
    zoneEl.addEventListener('click', () => inputEl.click());
    
    ['dragenter', 'dragover'].forEach(eventName => {
      zoneEl.addEventListener(eventName, (e) => {
        e.preventDefault();
        zoneEl.classList.add('dragover');
      }, false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
      zoneEl.addEventListener(eventName, (e) => {
        e.preventDefault();
        zoneEl.classList.remove('dragover');
      }, false);
    });

    zoneEl.addEventListener('drop', (e) => {
      const dt = e.dataTransfer;
      const files = dt.files;
      if (files.length > 0 && files[0].type.startsWith('image/')) {
        handleFileSelect(files[0], previewEl, fileTypeKey);
      }
    });

    inputEl.addEventListener('change', (e) => {
      if (e.target.files.length > 0) {
        handleFileSelect(e.target.files[0], previewEl, fileTypeKey);
      }
    });
  }

  function handleFileSelect(file, previewEl, fileTypeKey) {
    state.uploadedFiles[fileTypeKey] = file;
    const reader = new FileReader();
    reader.onload = (e) => {
      previewEl.innerHTML = `<img src="${e.target.result}" class="asset-preview-img" alt="Preview">`;
    };
    reader.readAsDataURL(file);
    showToast(`Asset attached: ${file.name}`);
  }

  setupDropzone(dropzonePoster, filePosterInput, posterPreviewContainer, 'poster');
  setupDropzone(dropzoneBg, fileBgInput, bgPreviewContainer, 'background');

  // =========================================================================
  // STAGE 01: CREATE JOB & GENERATE CONTEXT
  // =========================================================================
  createJobForm.addEventListener('submit', async (e) => {
    e.preventDefault();

    const jobPayload = {
      event_name: document.getElementById('field-event-name').value.trim(),
      event_date: document.getElementById('field-event-date').value,
      event_start_time: document.getElementById('field-start-time').value,
      event_end_time: document.getElementById('field-end-time').value || null,
      event_venue: document.getElementById('field-venue').value.trim() || null,
      registration_url: document.getElementById('field-reg-url').value.trim() || null,
      event_description: document.getElementById('field-description').value.trim(),
      event_whatsapp_message: document.getElementById('field-whatsapp').value.trim() || null
    };

    startTelemetryLoader([
      "INITIALIZING MAIL ENGINE...",
      "UPLOADING ASSETS TO CLOUDINARY...",
      "CALIBRATING CONTENT PARAMETERS...",
      "ANALYZING EVENT SIGNAL WITH GEMINI...",
      "CONSTRUCTING STRUCTURED CONTEXT..."
    ]);

    try {
      // 1. Create Job
      const createRes = await apiCreateJob(jobPayload);
      if (!createRes.success) {
        stopTelemetryLoader();
        showToast(`Job creation error: ${createRes.error}`);
        return;
      }

      const jobId = createRes.job.id;
      state.activeJob = createRes.job;
      updateTelemetryPill(createRes.job);

      // 2. Upload Assets if attached
      if (state.uploadedFiles.poster || state.uploadedFiles.background) {
        const uploadRes = await apiUploadAssets(jobId, state.uploadedFiles.poster, state.uploadedFiles.background);
        if (!uploadRes.success) {
          showToast(`Asset upload warning: ${uploadRes.error}`);
        }
      }

      // 3. Generate Context via Sense Maker
      const genRes = await apiGenerateContext(jobId);
      stopTelemetryLoader();

      if (genRes.success) {
        state.activeJob.status = genRes.status;
        state.activeJob.email_context = genRes.email_context;
        populateContextEditor(genRes.email_context);
        showToast('Sense Maker context generated successfully!');
        switchView('contextReview', 3);
      } else {
        showToast(`Gemini generation failed: ${genRes.error}`);
      }
    } catch (err) {
      stopTelemetryLoader();
      showToast('Error executing mission initialization flow.');
    }
  });

  // =========================================================================
  // STAGE 03: CONTEXT STRUCTURED EDITOR RENDERER
  // =========================================================================
  function populateContextEditor(context) {
    if (!context) return;
    state.editableContext = JSON.parse(JSON.stringify(context)); // Deep clone

    document.getElementById('edit-ctx-subject').value = context.subject || '';
    document.getElementById('edit-ctx-preheader').value = context.preheader || '';
    document.getElementById('edit-ctx-headline').value = context.headline || '';
    document.getElementById('edit-ctx-intro').value = context.intro || '';

    document.getElementById('edit-ctx-date').value = context.event_details?.date || '';
    document.getElementById('edit-ctx-time').value = context.event_details?.time || '';
    document.getElementById('edit-ctx-venue').value = context.event_details?.venue || '';
    document.getElementById('edit-ctx-reg-url').value = context.event_details?.registration_url || '';

    document.getElementById('edit-ctx-cta-label').value = context.cta?.label || '';
    document.getElementById('edit-ctx-cta-url').value = context.cta?.url || '';
    document.getElementById('edit-ctx-closing').value = context.closing || '';

    renderEditorSections(context.sections || []);
  }

  function renderEditorSections(sections) {
    editorSectionsContainer.innerHTML = sections.map((sec, secIdx) => `
      <div class="editor-section-box" data-section-index="${secIdx}">
        <div class="editor-section-header">
          <span style="font-family: var(--font-mono); font-size: 12px; color: var(--cyan-primary);">SECTION 0${secIdx + 1}</span>
          <button type="button" class="btn-mission btn-mission-danger btn-sm remove-sec-btn" data-sec-idx="${secIdx}">REMOVE SECTION</button>
        </div>

        <div class="form-group" style="margin-bottom: 12px;">
          <label class="form-label">SECTION HEADING</label>
          <input type="text" class="space-input sec-heading-input" value="${sec.heading || ''}" data-sec-idx="${secIdx}">
        </div>

        <div class="form-group" style="margin-bottom: 12px;">
          <label class="form-label">SECTION BODY</label>
          <textarea class="space-textarea sec-body-input" data-sec-idx="${secIdx}">${sec.body || ''}</textarea>
        </div>

        <div class="form-group">
          <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px;">
            <label class="form-label">BULLET HIGHLIGHTS</label>
            <button type="button" class="btn-mission btn-mission-secondary btn-sm add-bullet-btn" data-sec-idx="${secIdx}">+ ADD BULLET</button>
          </div>
          
          <div class="bullet-list-container">
            ${(sec.bullets || []).map((bullet, bulletIdx) => `
              <div class="bullet-item-row">
                <span class="bullet-dot">•</span>
                <input type="text" class="space-input bullet-input" value="${bullet}" data-sec-idx="${secIdx}" data-bullet-idx="${bulletIdx}">
                <button type="button" class="btn-mission btn-mission-danger btn-sm remove-bullet-btn" data-sec-idx="${secIdx}" data-bullet-idx="${bulletIdx}">×</button>
              </div>
            `).join('')}
          </div>
        </div>
      </div>
    `).join('');

    attachSectionEventListeners();
  }

  function attachSectionEventListeners() {
    // Heading input sync
    document.querySelectorAll('.sec-heading-input').forEach(input => {
      input.addEventListener('input', (e) => {
        const secIdx = parseInt(e.target.getAttribute('data-sec-idx'), 10);
        state.editableContext.sections[secIdx].heading = e.target.value;
      });
    });

    // Body input sync
    document.querySelectorAll('.sec-body-input').forEach(input => {
      input.addEventListener('input', (e) => {
        const secIdx = parseInt(e.target.getAttribute('data-sec-idx'), 10);
        state.editableContext.sections[secIdx].body = e.target.value;
      });
    });

    // Bullet input sync
    document.querySelectorAll('.bullet-input').forEach(input => {
      input.addEventListener('input', (e) => {
        const secIdx = parseInt(e.target.getAttribute('data-sec-idx'), 10);
        const bulletIdx = parseInt(e.target.getAttribute('data-bullet-idx'), 10);
        state.editableContext.sections[secIdx].bullets[bulletIdx] = e.target.value;
      });
    });

    // Add Bullet
    document.querySelectorAll('.add-bullet-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const secIdx = parseInt(e.target.getAttribute('data-sec-idx'), 10);
        state.editableContext.sections[secIdx].bullets.push('New key detail');
        renderEditorSections(state.editableContext.sections);
      });
    });

    // Remove Bullet
    document.querySelectorAll('.remove-bullet-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const secIdx = parseInt(e.target.getAttribute('data-sec-idx'), 10);
        const bulletIdx = parseInt(e.target.getAttribute('data-bullet-idx'), 10);
        state.editableContext.sections[secIdx].bullets.splice(bulletIdx, 1);
        renderEditorSections(state.editableContext.sections);
      });
    });

    // Remove Section
    document.querySelectorAll('.remove-sec-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const secIdx = parseInt(e.target.getAttribute('data-sec-idx'), 10);
        state.editableContext.sections.splice(secIdx, 1);
        renderEditorSections(state.editableContext.sections);
      });
    });
  }

  btnAddSection.addEventListener('click', () => {
    if (!state.editableContext.sections) state.editableContext.sections = [];
    state.editableContext.sections.push({
      heading: 'New Section',
      body: 'Add section content here...',
      bullets: ['Key point 1']
    });
    renderEditorSections(state.editableContext.sections);
  });

  // =========================================================================
  // CONTEXT APPROVAL SUBMISSION (PUT /api/jobs/<id>/context)
  // =========================================================================
  reviewContextForm.addEventListener('submit', async (e) => {
    e.preventDefault();

    if (!state.activeJob) {
      showToast('No active mission loaded for approval.');
      return;
    }

    // Collect latest form state into payload
    const contextPayload = {
      subject: document.getElementById('edit-ctx-subject').value.trim(),
      preheader: document.getElementById('edit-ctx-preheader').value.trim(),
      headline: document.getElementById('edit-ctx-headline').value.trim(),
      intro: document.getElementById('edit-ctx-intro').value.trim(),
      sections: state.editableContext.sections || [],
      event_details: {
        date: document.getElementById('edit-ctx-date').value.trim(),
        time: document.getElementById('edit-ctx-time').value.trim(),
        venue: document.getElementById('edit-ctx-venue').value.trim() || null,
        registration_url: document.getElementById('edit-ctx-reg-url').value.trim() || null
      },
      cta: {
        label: document.getElementById('edit-ctx-cta-label').value.trim(),
        url: document.getElementById('edit-ctx-cta-url').value.trim() || null
      },
      closing: document.getElementById('edit-ctx-closing').value.trim()
    };

    startTelemetryLoader(["VERIFYING TRANSMISSION DATA...", "PERSISTING CONTEXT APPROVAL..."]);

    try {
      const res = await apiApproveContext(state.activeJob.id, contextPayload);
      stopTelemetryLoader();

      if (res.success) {
        state.activeJob.status = res.status;
        state.activeJob.email_context = res.email_context;
        showToast('Context approved! Advancing to Email Build pipeline.');
        switchView('pipelinePreview', 4);
      } else {
        showToast(`Approval validation failed: ${res.error}`);
      }
    } catch (err) {
      stopTelemetryLoader();
      showToast('Network error during context approval.');
    }
  });

  // =========================================================================
  // REGENERATE CONTEXT SAFETY MODAL
  // =========================================================================
  btnTriggerRegen.addEventListener('click', () => {
    regenConfirmModal.classList.add('active');
  });

  btnCancelRegen.addEventListener('click', () => {
    regenConfirmModal.classList.remove('active');
  });

  btnConfirmRegen.addEventListener('click', async () => {
    regenConfirmModal.classList.remove('active');
    if (!state.activeJob) return;

    startTelemetryLoader([
      "RE-INITIALIZING GEMINI ENGINE...",
      "CALIBRATING CONTENT PARAMETERS...",
      "SYNTHESIZING NEW EMAIL CONTEXT..."
    ]);

    try {
      const genRes = await apiGenerateContext(state.activeJob.id);
      stopTelemetryLoader();

      if (genRes.success) {
        state.activeJob.status = genRes.status;
        state.activeJob.email_context = genRes.email_context;
        populateContextEditor(genRes.email_context);
        showToast('New AI context version generated!');
      } else {
        showToast(`Regeneration failed: ${genRes.error}`);
      }
    } catch (err) {
      stopTelemetryLoader();
      showToast('Error triggering context regeneration.');
    }
  });

  // =========================================================================
  // GLOBAL NAVIGATION CLICKS
  // =========================================================================
  navLinks.dashboard.addEventListener('click', (e) => {
    e.preventDefault();
    apiFetchJobs();
    switchView('dashboard', 1);
  });

  navLinks.brand.addEventListener('click', (e) => {
    e.preventDefault();
    apiFetchJobs();
    switchView('dashboard', 1);
  });

  navLinks.create.addEventListener('click', (e) => {
    e.preventDefault();
    state.activeJob = null;
    updateTelemetryPill(null);
    createJobForm.reset();
    posterPreviewContainer.innerHTML = '';
    bgPreviewContainer.innerHTML = '';
    switchView('create', 1);
  });

  btnHeroNew.addEventListener('click', () => {
    state.activeJob = null;
    updateTelemetryPill(null);
    createJobForm.reset();
    posterPreviewContainer.innerHTML = '';
    bgPreviewContainer.innerHTML = '';
    switchView('create', 1);
  });

  btnCancelCreate.addEventListener('click', () => {
    apiFetchJobs();
    switchView('dashboard', 1);
  });

  btnBackDashboard.addEventListener('click', () => {
    apiFetchJobs();
    switchView('dashboard', 1);
  });

  btnPipelineReturn.addEventListener('click', () => {
    apiFetchJobs();
    switchView('dashboard', 1);
  });

  // INITIAL BOOTSTRAP
  apiFetchJobs();
});
