with open('static/css/style.css', 'a', encoding='utf-8') as f:
    f.write('''
/* ==========================================================================
   EMAIL REVIEW PREVIEW & TELEMETRY
   ========================================================================== */

.email-review-layout {
  display: grid;
  grid-template-columns: 1fr 400px;
  gap: 32px;
  align-items: start;
}

.email-preview-container {
  display: flex;
  flex-direction: column;
  gap: 16px;
  align-items: center;
}

.preview-controls {
  display: flex;
  align-items: center;
  gap: 16px;
}

.viewport-toggles {
  display: flex;
  background: var(--bg-panel);
  border: 1px solid var(--border-subtle);
  border-radius: 20px;
  padding: 4px;
}

.btn-viewport {
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--text-muted);
  background: transparent;
  border: none;
  padding: 6px 16px;
  border-radius: 16px;
  cursor: pointer;
  transition: all var(--transition-fast);
}

.btn-viewport.active {
  background: var(--cyan-primary);
  color: #fff;
  box-shadow: 0 0 12px rgba(6, 182, 212, 0.4);
}

.iframe-wrapper {
  background: #ffffff;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  overflow: hidden;
  transition: width 0.5s cubic-bezier(0.22, 1, 0.36, 1);
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.5);
  display: flex;
}

.iframe-wrapper.desktop-mode {
  width: 100%;
  max-width: 800px;
  height: 800px;
}

.iframe-wrapper.mobile-mode {
  width: 375px;
  height: 812px;
  border-radius: 36px;
  border: 8px solid #1e293b;
}

#email-preview-iframe {
  width: 100%;
  height: 100%;
  border: none;
  background: #ffffff;
}

.email-telemetry-sidebar {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.telemetry-readout {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.telemetry-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.t-label {
  font-family: var(--font-mono);
  font-size: 10px;
  color: var(--text-dim);
  text-transform: uppercase;
  letter-spacing: 0.1em;
}

.t-value {
  font-family: var(--font-mono);
  font-size: 13px;
  color: var(--text-main);
  word-break: break-word;
}

.t-value.status-rendered {
  color: #fde047;
  animation: telemetry-pulse-slow 2s infinite;
}

.t-ok {
  color: #6ee7b7;
  font-size: 11px;
  margin-left: 8px;
}

.t-none {
  color: var(--text-dim);
  font-size: 11px;
  margin-left: 8px;
}

.telemetry-divider {
  height: 1px;
  background: var(--border-subtle);
  width: 100%;
}

.approval-gate {
  border: 1px solid var(--cyan-border);
  border-radius: var(--radius-lg);
  background: rgba(234, 179, 8, 0.05);
  overflow: hidden;
}

.approval-gate-header {
  background: rgba(234, 179, 8, 0.1);
  padding: 12px 20px;
  border-bottom: 1px solid rgba(234, 179, 8, 0.2);
}

.approval-gate-body {
  padding: 24px 20px;
}

.approval-gate-body p {
  font-size: 13px;
  color: var(--text-muted);
  margin-bottom: 24px;
  line-height: 1.5;
}

.approval-actions {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

@media (max-width: 1024px) {
  .email-review-layout {
    grid-template-columns: 1fr;
  }
}
''')
