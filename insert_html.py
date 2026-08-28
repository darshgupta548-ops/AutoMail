import re

with open('templates/app/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

new_view = """
    <!-- VIEW 4: EMAIL REVIEW (STAGE 05) -->
    <section class="view-section" id="view-email-review">
      <div class="editorial-header">
        <span class="section-tag">// STAGE 05 — EMAIL VERIFICATION</span>
        <h1 class="editorial-title">EMAIL TRANSMISSION<br><span style="color: var(--text-muted);">REVIEW & VERIFY</span></h1>
        <p class="editorial-subtitle">The communication payload has been rendered. Inspect the final HTML before authorizing transmission.</p>
      </div>

      <div class="email-review-layout">
        <!-- LEFT: Preview -->
        <div class="email-preview-container">
          <div class="preview-controls">
            <span style="font-family: var(--font-mono); font-size: 11px; color: var(--text-muted); letter-spacing: 0.1em;">VIEWPORT MODE</span>
            <div class="viewport-toggles">
              <button type="button" class="btn-viewport active" id="btn-viewport-desktop">DESKTOP</button>
              <button type="button" class="btn-viewport" id="btn-viewport-mobile">MOBILE</button>
            </div>
          </div>
          <div class="iframe-wrapper desktop-mode" id="email-iframe-wrapper">
            <iframe sandbox="allow-same-origin" id="email-preview-iframe" title="Email Preview"></iframe>
          </div>
        </div>

        <!-- RIGHT: Telemetry & Approval -->
        <div class="email-telemetry-sidebar">
          <div class="space-panel telemetry-panel">
            <h2 class="panel-title" style="margin-bottom: 20px;">MISSION TELEMETRY</h2>
            
            <div class="telemetry-readout">
              <div class="telemetry-item">
                <span class="t-label">TRANSMISSION STATUS</span>
                <span class="t-value status-rendered">● EMAIL_RENDERED</span>
              </div>
              <div class="telemetry-item">
                <span class="t-label">SUBJECT</span>
                <span class="t-value" id="telemetry-subject">...</span>
              </div>
              <div class="telemetry-item">
                <span class="t-label">PREHEADER</span>
                <span class="t-value" id="telemetry-preheader">...</span>
              </div>
              
              <div class="telemetry-divider"></div>
              
              <div class="telemetry-item">
                <span class="t-label">ASSET STATUS</span>
                <span class="t-value" id="telemetry-poster">POSTER <span class="t-ok">✓ LOADED</span></span>
                <span class="t-value" id="telemetry-bg">BACKGROUND <span class="t-none">✓ / — NOT USED</span></span>
              </div>
              
              <div class="telemetry-divider"></div>
              
              <div class="telemetry-item">
                <span class="t-label">CONTENT</span>
                <span class="t-value" id="telemetry-sections">SECTIONS 0</span>
                <span class="t-value" id="telemetry-cta">CTA ENABLED</span>
              </div>
            </div>
          </div>

          <div class="approval-gate">
            <div class="approval-gate-header">
              <span style="font-family: var(--font-mono); font-size: 11px; color: #fde047; letter-spacing: 0.1em;">HUMAN VERIFICATION REQUIRED</span>
            </div>
            <div class="approval-gate-body">
              <p>Review the rendered communication before authorizing the next transmission stage.</p>
              <div class="approval-actions">
                <button type="button" class="btn-mission btn-mission-secondary" id="btn-regen-email">REGENERATE EMAIL</button>
                <button type="button" class="btn-mission btn-mission-primary" id="btn-approve-email">APPROVE EMAIL ➔</button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>

"""

content = content.replace('    <!-- VIEW 4: FUTURE PIPELINE STAGES (STAGE 04-07) -->', new_view + '    <!-- VIEW 5: FUTURE PIPELINE STAGES (STAGE 06-07) -->')

with open('templates/app/index.html', 'w', encoding='utf-8') as f:
    f.write(content)
