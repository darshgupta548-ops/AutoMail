import re

with open('static/js/app.js', 'r', encoding='utf-8') as f:
    js_content = f.read()

# Add emailReview to views
js_content = js_content.replace(
    "pipelinePreview: document.getElementById('view-pipeline-preview')",
    "pipelinePreview: document.getElementById('view-pipeline-preview'),\n    emailReview: document.getElementById('view-email-review')"
)

# Add new DOM elements for email review
new_dom_elements = """
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
"""

js_content = js_content.replace(
    "// =========================================================================\n  // TOAST NOTIFICATIONS & TELEMETRY LOADER",
    new_dom_elements + "\n  // =========================================================================\n  // TOAST NOTIFICATIONS & TELEMETRY LOADER"
)

# Add API calls
new_api_calls = """
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
"""

js_content = js_content.replace(
    "// DASHBOARD RENDERER",
    new_api_calls + "\n  // =========================================================================\n  // DASHBOARD RENDERER"
)

# Modify loadMissionWorkflow
new_workflow_logic = """
        if (data.job.status === 'EMAIL_RENDERED') {
          populateEmailReview(data.job);
          switchView('emailReview', 5);
        } else if (data.job.status === 'EMAIL_APPROVED' || data.job.status.includes('TEST') || data.job.status.includes('FINAL')) {
          switchView('pipelinePreview', 6);
        } else if (data.job.status === 'CONTEXT_GENERATED' || data.job.status === 'CONTEXT_APPROVED') {
          populateContextEditor(data.job.email_context);
          switchView('contextReview', 3);
        } else {
"""

# Replace the specific block in loadMissionWorkflow
js_content = re.sub(
    r"if \(data\.job\.status === 'CONTEXT_GENERATED' \|\| data\.job\.status === 'CONTEXT_APPROVED'\) \{[\s\S]*?\} else \{",
    new_workflow_logic.strip(),
    js_content
)

# Add Email Review Logic at the end
new_email_review_logic = """
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

    if (job.event_poster) {
      telemetryPoster.innerHTML = `POSTER <span class="t-ok">✓ LOADED</span>`;
    } else {
      telemetryPoster.innerHTML = `POSTER <span class="t-none">✓ / — NOT USED</span>`;
    }

    if (job.email_bg) {
      telemetryBg.innerHTML = `BACKGROUND <span class="t-ok">✓ LOADED</span>`;
    } else {
      telemetryBg.innerHTML = `BACKGROUND <span class="t-none">✓ / — NOT USED</span>`;
    }
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
        switchView('pipelinePreview', 6);
      } else {
        showToast(`Approval failed: ${res.error}`);
      }
    } catch (err) {
      stopTelemetryLoader();
      showToast('Network error during email approval.');
    }
  });

"""

# Let's insert new_email_review_logic right before GLOBAL NAVIGATION CLICKS
js_content = js_content.replace(
    "// =========================================================================\n  // GLOBAL NAVIGATION CLICKS",
    new_email_review_logic + "\n  // =========================================================================\n  // GLOBAL NAVIGATION CLICKS"
)

# Wait, when CONTEXT is approved, it calls API to advance to BUILD. But `reviewContextForm.addEventListener('submit'` currently switches to `pipelinePreview` which was 4.
# Let's change `switchView('pipelinePreview', 4);` in `reviewContextForm.addEventListener` to actually trigger email rendering!
# Wait, currently the user's prompt says:
# "When a job reaches EMAIL_RENDERED, the user should be able to enter the Email Review interface."
# But how does it reach EMAIL_RENDERED? The backend has an EmailMaker now.
# In the previous code, when context was approved, it went to a placeholder. Let's update `reviewContextForm` submission to ALSO call `apiGenerateEmail`. Or we can just call it there.
update_context_approval = """
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
"""

js_content = re.sub(
    r"if \(res\.success\) \{[\s\S]*?switchView\('pipelinePreview', 4\);[\s\S]*?\} else \{",
    update_context_approval.strip() + " } else {",
    js_content
)


with open('static/js/app.js', 'w', encoding='utf-8') as f:
    f.write(js_content)
