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
    assets: document.getElementById('view-assets'),
    create: document.getElementById('view-create'),
    contextReview: document.getElementById('view-context-review'),
    pipelinePreview: document.getElementById('view-pipeline-preview'),
    emailReview: document.getElementById('view-email-review')
  };

  const navLinks = {
    brand: document.getElementById('nav-brand'),
    dashboard: document.getElementById('nav-dashboard'),
    assets: document.getElementById('nav-assets'),
    create: document.getElementById('nav-create')
  };

  const telemetryPill = document.getElementById('telemetry-pill');
  const telemetryJobName = document.getElementById('telemetry-job-name');
  const pastJobsGrid = document.getElementById('past-jobs-grid');
  const pipelineStageContent = document.getElementById('pipeline-stage-content');
  const pipelineActions = document.getElementById('pipeline-actions');

  const gmailConnectBtn = document.getElementById('gmail-connect-btn');
  const gmailLogoutBtn = document.getElementById('gmail-logout-btn');
  const gmailStatusEmpty = document.getElementById('gmail-status-empty');
  const gmailStatusConnected = document.getElementById('gmail-status-connected');
  const gmailProfileImage = document.getElementById('gmail-profile-image');
  const gmailAccountName = document.getElementById('gmail-account-name');
  const gmailAccountEmail = document.getElementById('gmail-account-email');
  const gmailAccountState = document.getElementById('gmail-account-state');

  // Modals & Toasts
  const telemetryModal = document.getElementById('telemetry-modal');
  const telemetryStatusMsg = document.getElementById('telemetry-status-msg');
  const regenConfirmModal = document.getElementById('regen-confirm-modal');
  const testConfirmModal = document.getElementById('test-confirm-modal');
  const testConfirmList = document.getElementById('test-confirm-list');
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
  const btnCancelTestSend = document.getElementById('btn-cancel-test-send');
  const btnConfirmTestSend = document.getElementById('btn-confirm-test-send');

  
  // Email Review Elements
  const emailPreviewIframe = document.getElementById('email-preview-iframe');
  const btnViewportDesktop = document.getElementById('btn-viewport-desktop');
  const btnViewportMobile = document.getElementById('btn-viewport-mobile');
  const emailIframeWrapper = document.getElementById('email-iframe-wrapper');
  
  const telemetrySubject = document.getElementById('telemetry-subject');
  const telemetryPreheader = document.getElementById('telemetry-preheader');
  const telemetryPoster = document.getElementById('telemetry-poster');
  const telemetryBg = document.getElementById('telemetry-bg');
  const telemetrySections = document.getElementById('telemetry-sections');
  const telemetryCta = document.getElementById('telemetry-cta');
  
  const btnRegenEmail = document.getElementById('btn-regen-email');
  const btnApproveEmail = document.getElementById('btn-approve-email');

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
    const data = await res.json();
    
    // Display background dimension warning if present
    if (data.warning) {
      showToast(`⚠️ ${data.warning}`, 8000);
    }
    
    return data;
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
  
  async function apiGenerateEmail(jobId) {
    const res = await fetch(`/api/jobs/${jobId}/email/generate`, {
      method: 'POST'
    });
    return await res.json();
  }

  async function apiApproveEmail(jobId) {
    const res = await fetch(`/api/jobs/${jobId}/email/approve`, {
      method: 'POST'
    });
    return await res.json();
  }

  async function apiDeleteJob(jobId) {
    const res = await fetch(`/api/jobs/${jobId}`, {
      method: 'DELETE'
    });
    return await res.json();
  }

  async function apiFetchAssets() {
    try {
      const res = await fetch('/api/assets/posters');
      const data = await res.json();
      if (data.success) {
        renderAssetsGrid(data.assets);
      } else {
        showToast(`Failed to load assets: ${data.error}`);
      }
    } catch (err) {
      showToast('Network error loading asset telemetry.');
    }
  }

  async function apiDeleteAsset(posterUrl) {
    const res = await fetch('/api/assets/posters', {
      method: 'DELETE',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url: posterUrl })
    });
    return await res.json();
  }

  async function apiFetchGmailSession() {
    try {
      const res = await fetch('/api/gmail/session');
      return await res.json();
    } catch (err) {
      return { success: false, authenticated: false, sender: null, error: 'Unable to load sender state.' };
    }
  }

  async function apiLogoutGmail() {
    const res = await fetch('/api/gmail/logout', { method: 'POST' });
    return await res.json();
  }

  function renderGmailSenderState(sender) {
    const connected = !!sender && sender.email;

    gmailStatusEmpty.classList.toggle('hidden', connected);
    gmailStatusConnected.classList.toggle('hidden', !connected);
    gmailConnectBtn.classList.toggle('hidden', connected);
    gmailLogoutBtn.classList.toggle('hidden', !connected);

    if (!connected) {
      gmailAccountName.textContent = 'Google Account';
      gmailAccountEmail.textContent = 'not connected';
      gmailAccountState.textContent = 'Disconnected';
      gmailProfileImage.src = '';
      gmailProfileImage.alt = 'No account connected';
      return;
    }

    gmailProfileImage.src = sender.picture_url || 'https://lh3.googleusercontent.com/a/default-user';
    gmailProfileImage.alt = `${sender.display_name || sender.email} profile`;
    gmailAccountName.textContent = sender.display_name || 'Google Account';
    gmailAccountEmail.textContent = sender.email;
    gmailAccountState.textContent = sender.status === 'connected' ? 'Connected' : 'Authenticated';
  }

  async function refreshGmailSenderState() {
    const data = await apiFetchGmailSession();
    if (data.success) {
      renderGmailSenderState(data.sender);
    }
  }

  async function apiFetchTestRecipients() {
    try {
      const res = await fetch('/api/transmission/test-recipients');
      return await res.json();
    } catch (err) {
      return { success: false, recipients: [], error: 'Unable to load test recipients.' };
    }
  }

  function sanitizeHtmlList(items) {
    return (items || []).map(item => `<li>${item}</li>`).join('');
  }

  function renderPipelineActions(buttonMarkup) {
    pipelineActions.innerHTML = buttonMarkup;
  }

  async function renderPipelineStage(job) {
    if (!job) return;

    const testRecipientsResponse = await apiFetchTestRecipients();
    const testRecipients = testRecipientsResponse.success ? testRecipientsResponse.recipients : [];
    const previewHtml = job.email_html || '<html><body><p>No approved email content is available.</p></body></html>';

    if (job.status === 'EMAIL_APPROVED') {
      pipelineStageContent.innerHTML = `
        <div class="stage-header" style="display: flex; justify-content: space-between; align-items: center; gap: 16px; margin-bottom: 18px; flex-wrap: wrap;">
          <div>
            <span class="section-tag" style="margin-bottom: 8px; display: inline-block;">// EXECUTIVE TRANSMISSION READY</span>
            <h2 class="panel-title" style="font-size: 28px; margin: 0;">EXECUTIVE TEST TRANSMISSION</h2>
          </div>
          <span class="status-badge badge-approved">● AUTHORIZATION READY</span>
        </div>

        <p style="color: var(--text-muted); margin-bottom: 24px; max-width: 760px; line-height: 1.6;">
          The generated email is ready for executive verification. A test copy will be sent to the configured executive test recipients.
        </p>

        <div class="form-grid" style="margin-bottom: 24px;">
          <div class="space-panel" style="padding: 18px; border: 1px solid var(--border-subtle);">
            <span class="section-tag" style="display: inline-block; margin-bottom: 8px;">TEST RECIPIENTS</span>
            <ul style="margin: 0; padding-left: 18px; color: var(--text-bright); line-height: 1.8;">
              ${sanitizeHtmlList(testRecipients.length ? testRecipients : ['No recipients configured'])}
            </ul>
          </div>
        </div>

        <div class="space-panel" style="padding: 18px; border: 1px solid var(--border-subtle); margin-bottom: 20px;">
          <span class="section-tag" style="display: inline-block; margin-bottom: 10px;">EMAIL PREVIEW</span>
          <div class="iframe-wrapper desktop-mode" style="height: 500px; border: 1px solid var(--border-subtle); background: #fff;">
            <iframe sandbox="allow-same-origin" title="Stage 06 email preview" srcdoc="${previewHtml.replace(/"/g, '&quot;')}"></iframe>
          </div>
        </div>
      `;

      renderPipelineActions(`
        <button type="button" class="btn-mission btn-mission-secondary" id="btn-pipeline-return">RETURN TO DASHBOARD</button>
        <button type="button" class="btn-mission btn-mission-primary" id="btn-trigger-test-send">SEND TEST EMAILS</button>
      `);

      const triggerTestBtn = document.getElementById('btn-trigger-test-send');
      const pipelineReturnBtn = document.getElementById('btn-pipeline-return');
      triggerTestBtn.addEventListener('click', openTestConfirmation);
      pipelineReturnBtn.addEventListener('click', () => {
        apiFetchJobs();
        switchView('dashboard', 1);
      });
      return;
    }

    if (job.status === 'TEST_SENT') {
      pipelineStageContent.innerHTML = `
        <div class="status-panel success" style="padding: 26px; border: 1px solid rgba(79, 209, 197, 0.4); border-radius: var(--radius-md); background: rgba(12, 25, 35, 0.7);">
          <span class="section-tag" style="display: inline-block; margin-bottom: 8px;">// TEST TRANSMISSION COMPLETE</span>
          <h2 class="panel-title" style="margin: 0 0 12px; font-size: 30px;">TEST TRANSMISSION COMPLETE</h2>
          <p style="color: var(--text-muted); margin-bottom: 18px; line-height: 1.6;">
            ${testRecipients.length} executive test recipient(s) received the approved email successfully through the authenticated Gmail account.
          </p>
          <div style="display: grid; gap: 10px; margin-bottom: 18px;">
            <div><strong>RECIPIENTS</strong><br><span style="color: var(--text-bright);">${testRecipients.join(', ')}</span></div>
            <div><strong>TIMESTAMP</strong><br><span style="color: var(--text-bright);">${new Date().toLocaleString()}</span></div>
            <div><strong>GMAIL STATUS</strong><br><span style="color: var(--status-connected);">GMAIL API SUCCESS</span></div>
          </div>
        </div>
      `;

      renderPipelineActions(`
        <button type="button" class="btn-mission btn-mission-primary" id="btn-proceed-to-send">PROCEED TO SEND</button>
      `);

      document.getElementById('btn-proceed-to-send').addEventListener('click', async () => {
        try {
          const res = await fetch(`/api/jobs/${job.id}/test/approve`, { method: 'POST' });
          const data = await res.json();
          if (!data.success) {
            showToast(data.error || 'Unable to advance to final send.');
            return;
          }
          state.activeJob.status = data.status;
          await renderPipelineStage(state.activeJob);
        } catch (err) {
          showToast('Unable to advance to the final send stage.');
        }
      });
      return;
    }

    if (job.status === 'TEST_APPROVED') {
      const finalRecipientsResponse = await fetch('/api/transmission/final-recipients');
      const finalRecipientsData = finalRecipientsResponse.ok ? await finalRecipientsResponse.json() : { recipients: [] };
      const finalRecipients = finalRecipientsData.recipients || [];

      pipelineStageContent.innerHTML = `
        <div class="status-panel" style="padding: 26px; border: 1px solid rgba(90, 160, 255, 0.35); border-radius: var(--radius-md); background: rgba(8, 20, 31, 0.7);">
          <span class="section-tag" style="display: inline-block; margin-bottom: 8px;">// FINAL SEND READY</span>
          <h2 class="panel-title" style="margin: 0 0 12px; font-size: 30px;">FINAL TRANSMISSION PREPARED</h2>
          <p style="color: var(--text-muted); margin-bottom: 18px; line-height: 1.6;">
            The executive test send succeeded. The approved email is ready for the configured final delivery recipient.
          </p>
          <div class="space-panel" style="padding: 18px; border: 1px solid var(--border-subtle); margin-bottom: 16px;">
            <span class="section-tag" style="display: inline-block; margin-bottom: 8px;">FINAL RECIPIENT</span>
            <ul style="margin: 0; padding-left: 18px; color: var(--text-bright); line-height: 1.8;">
              ${sanitizeHtmlList(finalRecipients.length ? finalRecipients : ['No final recipient configured'])}
            </ul>
          </div>
          <div class="iframe-wrapper desktop-mode" style="height: 420px; border: 1px solid var(--border-subtle); background: #fff;">
            <iframe sandbox="allow-same-origin" title="Final email preview" srcdoc="${previewHtml.replace(/"/g, '&quot;')}"></iframe>
          </div>
        </div>
      `;

      renderPipelineActions(`
        <button type="button" class="btn-mission btn-mission-secondary" id="btn-pipeline-return">RETURN TO DASHBOARD</button>
        <button type="button" class="btn-mission btn-mission-primary" id="btn-trigger-final-send">SEND FINAL EMAIL</button>
      `);

      document.getElementById('btn-trigger-final-send').addEventListener('click', async () => {
        const res = await fetch(`/api/jobs/${job.id}/final-send`, { method: 'POST' });
        const data = await res.json();
        if (data.success) {
          state.activeJob.status = data.status;
          showToast('Final email transmission sent successfully.');
          await renderPipelineStage(state.activeJob);
        } else {
          showToast(data.error || 'Final send failed.');
        }
      });

      document.getElementById('btn-pipeline-return').addEventListener('click', () => {
        apiFetchJobs();
        switchView('dashboard', 1);
      });
      return;
    }

    if (job.status === 'FINAL_SENT') {
      pipelineStageContent.innerHTML = `
        <div class="status-panel success" style="padding: 24px; border: 1px solid rgba(79, 209, 197, 0.4); border-radius: var(--radius-md); background: rgba(12, 25, 35, 0.7);">
          <span class="section-tag" style="display: inline-block; margin-bottom: 8px;">// FINAL MESSAGE DISPATCHED</span>
          <h2 class="panel-title" style="margin: 0 0 12px; font-size: 30px;">FINAL TRANSMISSION COMPLETE</h2>
          <p style="color: var(--text-muted);">The final approved email was sent successfully through the authenticated Gmail account.</p>
        </div>
      `;
      renderPipelineActions(`<button type="button" class="btn-mission btn-mission-secondary" id="btn-pipeline-return">RETURN TO DASHBOARD</button>`);
      document.getElementById('btn-pipeline-return').addEventListener('click', () => {
        apiFetchJobs();
        switchView('dashboard', 1);
      });
      return;
    }

    pipelineStageContent.innerHTML = `
      <div class="space-panel" style="text-align: center; padding: 60px 40px;">
        <div style="font-size: 48px; color: var(--cyan-primary); margin-bottom: 16px;">✨</div>
        <h2 class="panel-title" style="font-size: 24px; margin-bottom: 12px;">MISSION STATUS: ${job.status}</h2>
        <p style="color: var(--text-muted); max-width: 540px; margin: 0 auto 28px auto;">The workflow is active and ready for the next transmission stage.</p>
      </div>
    `;
    renderPipelineActions(`<button type="button" class="btn-mission btn-mission-secondary" id="btn-pipeline-return">RETURN TO DASHBOARD</button>`);
    document.getElementById('btn-pipeline-return').addEventListener('click', () => {
      apiFetchJobs();
      switchView('dashboard', 1);
    });
  }

  function openTestConfirmation() {
    if (!state.activeJob) return;
    apiFetchTestRecipients().then((data) => {
      const recipients = data.success ? data.recipients : [];
      testConfirmList.innerHTML = recipients.map((recipient) => `<li>${recipient}</li>`).join('');
      testConfirmModal.classList.add('active');
    });
  }

  async function submitTestEmailSend() {
    if (!state.activeJob) return;

    const submitButton = document.getElementById('btn-confirm-test-send');
    if (submitButton) {
      submitButton.disabled = true;
      submitButton.textContent = 'TRANSMITTING TEST EMAILS...';
    }

    testConfirmModal.classList.remove('active');
    startTelemetryLoader(['PREPARING TEST DISPATCH...', 'CONNECTING TO GMAIL API...', 'TRANSMITTING EXECUTIVE COPIES...']);

    try {
      const res = await fetch(`/api/jobs/${state.activeJob.id}/test-send`, { method: 'POST' });
      const data = await res.json();
      stopTelemetryLoader();

      if (data.success) {
        state.activeJob.status = data.status;
        if (data.already_sent) {
          showToast('This test transmission was already completed.');
        }
        await renderPipelineStage(state.activeJob);
        showToast('Test transmission complete.');
      } else {
        if (submitButton) {
          submitButton.disabled = false;
          submitButton.textContent = 'SEND TEST';
        }
        pipelineStageContent.innerHTML = `
          <div class="status-panel error" style="padding: 26px; border: 1px solid rgba(255, 112, 112, 0.45); border-radius: var(--radius-md); background: rgba(28, 16, 16, 0.7);">
            <span class="section-tag" style="display: inline-block; margin-bottom: 8px;">// TEST TRANSMISSION FAILED</span>
            <h2 class="panel-title" style="margin: 0 0 12px; font-size: 30px;">TEST TRANSMISSION FAILED</h2>
            <p style="color: var(--text-muted); margin-bottom: 12px;">${(data.error || 'The Gmail API rejected the test transmission.').replace(/\n/g, ' ')}</p>
          </div>
        `;
        renderPipelineActions(`
          <button type="button" class="btn-mission btn-mission-secondary" id="btn-pipeline-return">RETURN TO DASHBOARD</button>
          <button type="button" class="btn-mission btn-mission-primary" id="btn-retry-test-send">RETRY TEST</button>
        `);
        document.getElementById('btn-retry-test-send').addEventListener('click', openTestConfirmation);
        document.getElementById('btn-pipeline-return').addEventListener('click', () => {
          apiFetchJobs();
          switchView('dashboard', 1);
        });
        showToast(data.error || 'Test transmission failed.');
      }
    } catch (err) {
      stopTelemetryLoader();
      if (submitButton) {
        submitButton.disabled = false;
        submitButton.textContent = 'SEND TEST';
      }
      pipelineStageContent.innerHTML = `
        <div class="status-panel error" style="padding: 26px; border: 1px solid rgba(255, 112, 112, 0.45); border-radius: var(--radius-md); background: rgba(28, 16, 16, 0.7);">
          <span class="section-tag" style="display: inline-block; margin-bottom: 8px;">// TEST TRANSMISSION FAILED</span>
          <h2 class="panel-title" style="margin: 0 0 12px; font-size: 30px;">TEST TRANSMISSION FAILED</h2>
          <p style="color: var(--text-muted);">A network or Gmail API error prevented the test from sending.</p>
        </div>
      `;
      renderPipelineActions(`
        <button type="button" class="btn-mission btn-mission-secondary" id="btn-pipeline-return">RETURN TO DASHBOARD</button>
        <button type="button" class="btn-mission btn-mission-primary" id="btn-retry-test-send">RETRY TEST</button>
      `);
      document.getElementById('btn-retry-test-send').addEventListener('click', openTestConfirmation);
      document.getElementById('btn-pipeline-return').addEventListener('click', () => {
        apiFetchJobs();
        switchView('dashboard', 1);
      });
      showToast('Test transmission failed.');
    }
  }

  // =========================================================================
  // DASHBOARD RENDERER
  // =========================================================================
  function getStatusBadgeHtml(status) {
    switch (status) {
      case 'DRAFT': return '<span class="status-badge badge-draft">● DRAFT</span>';
      case 'CONTEXT_GENERATED': return '<span class="status-badge badge-generated">● CONTEXT GENERATED</span>';
      case 'CONTEXT_APPROVED': return '<span class="status-badge badge-approved">● CONTEXT APPROVED</span>';
      case 'EMAIL_RENDERED': return '<span class="status-badge badge-rendered">● EMAIL RENDERED</span>';
      case 'EMAIL_APPROVED': return '<span class="status-badge badge-approved">● EMAIL APPROVED</span>';
      case 'TEST_SENT': return '<span class="status-badge badge-sent">● TEST SENT</span>';
      case 'TEST_APPROVED': return '<span class="status-badge badge-sent">● TEST APPROVED</span>';
      case 'FINAL_SENT': return '<span class="status-badge badge-sent">● FINAL SENT</span>';
      default: return `<span class="status-badge badge-draft">● ${status}</span>`;
    }
  }

  function isJobDeletable(status) {
    const sentStates = ['TEST_SENT', 'TEST_APPROVED', 'FINAL_SENT'];
    return !sentStates.includes(status);
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
    pastJobsGrid.innerHTML = sortedJobs.map(job => {
      const deletable = isJobDeletable(job.status);
      return `
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
          <div style="display: flex; gap: 8px;">
            ${deletable ? `<button class="btn-mission btn-mission-danger btn-sm delete-job-btn" data-id="${job.id}">DELETE</button>` : ''}
            <button class="btn-mission btn-mission-secondary btn-sm open-job-btn" data-id="${job.id}">RESUME ➔</button>
          </div>
        </div>
      </div>
    `}).join('');

    document.querySelectorAll('.open-job-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const jobId = parseInt(e.target.getAttribute('data-id'), 10);
        loadMissionWorkflow(jobId);
      });
    });

    document.querySelectorAll('.delete-job-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const jobId = parseInt(e.target.getAttribute('data-id'), 10);
        confirmDeleteJob(jobId);
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

        if (data.job.status === 'EMAIL_RENDERED') {
          populateEmailReview(data.job);
          switchView('emailReview', 5);
        } else if (data.job.status === 'EMAIL_APPROVED' || data.job.status.includes('TEST') || data.job.status.includes('FINAL')) {
          renderPipelineStage(data.job);
          switchView('pipelinePreview', 6);
        } else if (data.job.status === 'CONTEXT_GENERATED' || data.job.status === 'CONTEXT_APPROVED') {
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

  async function confirmDeleteJob(jobId) {
    if (!confirm('Are you sure you want to delete this mission? This action cannot be undone.')) {
      return;
    }

    try {
      const res = await apiDeleteJob(jobId);
      if (res.success) {
        showToast('Mission deleted successfully.');
        await apiFetchJobs(); // Refresh the grid
      } else {
        showToast(`Delete failed: ${res.error}`);
      }
    } catch (err) {
      showToast('Network error during deletion.');
    }
  }

  function renderAssetsGrid(assets) {
    const assetsGrid = document.getElementById('assets-grid');
    if (!assets || assets.length === 0) {
      assetsGrid.innerHTML = `
        <div class="empty-state-card" style="grid-column: 1 / -1; text-align: center; padding: 60px 40px; background: rgba(15, 23, 42, 0.4); border: 1px dashed var(--border-subtle); border-radius: var(--radius-lg);">
          <div style="font-size: 32px; color: var(--text-dim); margin-bottom: 16px;">⊘</div>
          <h3 style="font-family: var(--font-heading); font-size: 16px; color: var(--text-main); margin-bottom: 8px;">NO POSTER ASSETS FOUND</h3>
          <p style="color: var(--text-muted); font-family: var(--font-mono); font-size: 12px;">NO CLOUDINARY POSTERS HAVE BEEN UPLOADED YET.</p>
        </div>
      `;
      return;
    }

    assetsGrid.innerHTML = assets.map(asset => {
      const protectionBadge = asset.has_sent_reference 
        ? '<span class="status-badge badge-sent">PROTECTED</span>' 
        : '<span class="status-badge badge-draft">DELETABLE</span>';
      
      const referencesList = asset.references.map(ref => `
        <div style="font-size: 11px; color: var(--text-dim); padding: 4px 0; border-bottom: 1px solid var(--border-subtle);">
          <span style="color: ${ref.is_sent ? 'var(--status-sent)' : 'var(--text-muted)'};">●</span>
          Mission #${ref.id}: ${ref.event_name} (${ref.status})
        </div>
      `).join('');

      return `
      <div class="job-card asset-card" data-url="${asset.url}">
        <div>
          <div class="job-card-meta">
            <span style="font-family: var(--font-mono); font-size: 11px; color: var(--text-dim);">ASSET</span>
            ${protectionBadge}
          </div>
          <div style="margin: 12px 0;">
            <img src="${asset.url}" alt="Poster" style="width: 100%; max-height: 200px; object-fit: cover; border-radius: var(--radius-sm); border: 1px solid var(--border-subtle);">
          </div>
          <h3 class="job-card-title" style="font-size: 14px;">${asset.reference_count} Reference(s)</h3>
          <div style="margin: 12px 0; max-height: 120px; overflow-y: auto;">
            ${referencesList}
          </div>
        </div>
        <div class="job-card-footer">
          <span>${asset.deletable ? 'SAFE TO DELETE' : 'PROTECTED BY SENT EMAILS'}</span>
          ${asset.deletable ? `<button class="btn-mission btn-mission-danger btn-sm delete-asset-btn" data-url="${asset.url}">DELETE</button>` : ''}
        </div>
      </div>
    `}).join('');

    document.querySelectorAll('.delete-asset-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const posterUrl = e.target.getAttribute('data-url');
        confirmDeleteAsset(posterUrl);
      });
    });
  }

  async function confirmDeleteAsset(posterUrl) {
    if (!confirm('Are you sure you want to delete this poster asset? This will remove it from all non-sent jobs. This action cannot be undone.')) {
      return;
    }

    try {
      const res = await apiDeleteAsset(posterUrl);
      if (res.success) {
        showToast('Asset deleted successfully.');
        await apiFetchAssets(); // Refresh the grid
      } else {
        showToast(`Delete failed: ${res.error}`);
      }
    } catch (err) {
      showToast('Network error during deletion.');
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
        
        // NOW AUTO-GENERATE EMAIL
        startTelemetryLoader(["RENDERING RESPONSIVE HTML..."]);
        const emailRes = await apiGenerateEmail(state.activeJob.id);
        stopTelemetryLoader();
        
        if (emailRes.success) {
            state.activeJob.status = emailRes.status;
            state.activeJob.email_html = emailRes.email_html;
            showToast('Context approved and Email rendered! Advancing to Email Review.');
            populateEmailReview(state.activeJob);
            switchView('emailReview', 5);
        } else {
            showToast(`Email rendering failed: ${emailRes.error}`);
            // Stay here or go to some error view
        }
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

  

  async function apiSaveEmailContent(jobId, contextPayload) {
    const res = await fetch(`/api/jobs/${jobId}/email/content`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(contextPayload)
    });
    return await res.json();
  }

  function serializeEmailSections(sections) {
    return (sections || []).map((section) => [section.heading, section.body, ...(section.bullets || [])].join('\n')).join('\n\n---\n\n');
  }

  function parseEmailSections(value) {
    if (!value.trim()) return [];
    return value.split(/\n\s*---\s*\n/).map((block) => {
      const lines = block.split('\n').map((line) => line.trim()).filter(Boolean);
      return { heading: lines.shift() || 'Section', body: lines.shift() || '', bullets: lines };
    });
  }

  function openEmailEditor() {
    const context = state.activeJob && state.activeJob.email_context;
    if (!context) return;
    document.getElementById('email-edit-subject').value = context.subject || '';
    document.getElementById('email-edit-preheader').value = context.preheader || '';
    document.getElementById('email-edit-headline').value = context.headline || '';
    document.getElementById('email-edit-intro').value = context.intro || '';
    document.getElementById('email-edit-date').value = context.event_details?.date || '';
    document.getElementById('email-edit-time').value = context.event_details?.time || '';
    document.getElementById('email-edit-venue').value = context.event_details?.venue || '';
    document.getElementById('email-edit-cta-label').value = context.cta?.label || 'Register Now';
    document.getElementById('email-edit-cta-url').value = context.cta?.url || context.event_details?.registration_url || '';
    document.getElementById('email-edit-closing').value = context.closing || '';
    document.getElementById('email-edit-contacts').value = (context.contact_details || []).join('\n');
    document.getElementById('email-edit-sections').value = serializeEmailSections(context.sections);
    document.getElementById('email-editor-panel').hidden = false;
  }

  document.getElementById('btn-edit-email').addEventListener('click', openEmailEditor);
  document.getElementById('btn-cancel-email-edit').addEventListener('click', () => {
    document.getElementById('email-editor-panel').hidden = true;
  });
  document.getElementById('email-content-form').addEventListener('submit', async (event) => {
    event.preventDefault();
    if (!state.activeJob) return;
    const existing = state.activeJob.email_context;
    const ctaUrl = document.getElementById('email-edit-cta-url').value.trim() || null;
    const context = {
      subject: document.getElementById('email-edit-subject').value.trim(),
      preheader: document.getElementById('email-edit-preheader').value.trim(),
      headline: document.getElementById('email-edit-headline').value.trim(),
      intro: document.getElementById('email-edit-intro').value.trim(),
      sections: parseEmailSections(document.getElementById('email-edit-sections').value),
      event_details: {
        date: document.getElementById('email-edit-date').value.trim(),
        time: document.getElementById('email-edit-time').value.trim(),
        venue: document.getElementById('email-edit-venue').value.trim() || null,
        registration_url: existing.event_details?.registration_url || ctaUrl
      },
      cta: { label: document.getElementById('email-edit-cta-label').value.trim() || 'Register Now', url: ctaUrl },
      closing: document.getElementById('email-edit-closing').value.trim(),
      contact_details: document.getElementById('email-edit-contacts').value.split('\n').map((line) => line.trim()).filter(Boolean),
      brahmand_logo_url: existing.brahmand_logo_url || null,
      snt_logo_url: existing.snt_logo_url || null,
      osail_logo_url: existing.osail_logo_url || null,
      logo_urls: existing.logo_urls || {}
    };
    const result = await apiSaveEmailContent(state.activeJob.id, context);
    if (!result.success) { showToast(`Save failed: ${result.error}`); return; }
    state.activeJob.email_context = result.email_context;
    state.activeJob.email_html = result.email_html;
    state.activeJob.status = result.status;
    document.getElementById('email-editor-panel').hidden = true;
    populateEmailReview(state.activeJob);
    showToast('Email changes saved.');
  });

  // =========================================================================
  // STAGE 05: EMAIL REVIEW
  // =========================================================================
  function populateEmailReview(job) {
    if (!job) return;
    state.activeJob = job;

    // Insert HTML into iframe safely
    if (job.email_html) {
      emailPreviewIframe.srcdoc = job.email_html;
    } else {
      emailPreviewIframe.srcdoc = "<html><body><p>Error: No HTML content found.</p></body></html>";
    }

    // Update Telemetry Panel
    if (job.email_context) {
      telemetrySubject.textContent = job.email_context.subject || 'N/A';
      telemetryPreheader.textContent = job.email_context.preheader || 'N/A';
      
      const sectionCount = (job.email_context.sections || []).length;
      telemetrySections.textContent = `SECTIONS ${sectionCount}`;
      
      telemetryCta.textContent = (job.email_context.cta && job.email_context.cta.label) ? 'CTA ENABLED' : 'CTA DISABLED';
    }

    // Check asset status by examining the rendered HTML (authoritative source)
    const html = job.email_html || '';
    
    // Poster is used if the actual poster URL appears in the rendered HTML
    const posterUsed = job.event_poster && html.includes(job.event_poster);
    telemetryPoster.innerHTML = posterUsed 
      ? `POSTER <span class="t-ok">✓ USED</span>` 
      : `POSTER <span class="t-none">— NOT USED</span>`;

    // Background is used if the actual background URL appears in the rendered HTML
    const backgroundUsed = job.email_bg && html.includes(job.email_bg);
    telemetryBg.innerHTML = backgroundUsed 
      ? `BACKGROUND <span class="t-ok">✓ USED</span>` 
      : `BACKGROUND <span class="t-none">— NOT USED</span>`;
  }

  // Viewport Controls
  btnViewportDesktop.addEventListener('click', () => {
    btnViewportDesktop.classList.add('active');
    btnViewportMobile.classList.remove('active');
    emailIframeWrapper.classList.add('desktop-mode');
    emailIframeWrapper.classList.remove('mobile-mode');
  });

  btnViewportMobile.addEventListener('click', () => {
    btnViewportMobile.classList.add('active');
    btnViewportDesktop.classList.remove('active');
    emailIframeWrapper.classList.add('mobile-mode');
    emailIframeWrapper.classList.remove('desktop-mode');
  });

  // Regenerate Email Action
  btnRegenEmail.addEventListener('click', async () => {
    if (!state.activeJob) return;

    startTelemetryLoader([
      "RE-INITIALIZING EMAIL MAKER...",
      "RENDERING RESPONSIVE HTML...",
      "UPDATING TRANSMISSION PAYLOAD..."
    ]);

    try {
      const res = await apiGenerateEmail(state.activeJob.id);
      stopTelemetryLoader();

      if (res.success) {
        state.activeJob.status = res.status;
        state.activeJob.email_html = res.email_html;
        populateEmailReview(state.activeJob);
        showToast('Email regenerated successfully!');
      } else {
        showToast(`Regeneration failed: ${res.error}`);
      }
    } catch (err) {
      stopTelemetryLoader();
      showToast('Network error during email regeneration.');
    }
  });

  // Approve Email Action
  btnApproveEmail.addEventListener('click', async () => {
    if (!state.activeJob) return;

    startTelemetryLoader([
      "AUTHORIZING TRANSMISSION...",
      "SECURING EMAIL PAYLOAD...",
      "UPDATING MISSION STATUS..."
    ]);

    try {
      const res = await apiApproveEmail(state.activeJob.id);
      stopTelemetryLoader();

      if (res.success) {
        state.activeJob.status = res.status;
        showToast('EMAIL APPROVED. TRANSMISSION AUTHORIZED.');
        renderPipelineStage(state.activeJob);
        switchView('pipelinePreview', 6);
      } else {
        showToast(`Approval failed: ${res.error}`);
      }
    } catch (err) {
      stopTelemetryLoader();
      showToast('Network error during email approval.');
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

  navLinks.assets.addEventListener('click', (e) => {
    e.preventDefault();
    apiFetchAssets();
    switchView('assets', 1);
  });

  document.getElementById('btn-refresh-assets').addEventListener('click', (e) => {
    e.preventDefault();
    apiFetchAssets();
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

  btnCancelTestSend.addEventListener('click', () => {
    testConfirmModal.classList.remove('active');
  });

  btnConfirmTestSend.addEventListener('click', submitTestEmailSend);

  gmailConnectBtn.addEventListener('click', () => {
    window.location.href = '/api/gmail/connect';
  });

  gmailLogoutBtn.addEventListener('click', async () => {
    const result = await apiLogoutGmail();
    if (result.success) {
      showToast('Gmail sender disconnected.');
      renderGmailSenderState(null);
    } else {
      showToast('Unable to log out of Gmail.');
    }
  });

  // INITIAL BOOTSTRAP
  refreshGmailSenderState();
  apiFetchJobs();
});
