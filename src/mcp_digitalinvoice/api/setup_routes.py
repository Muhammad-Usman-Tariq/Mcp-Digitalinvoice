"""Route and HTML template for the self-contained MCP onboarding/setup web page."""

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

setup_router = APIRouter(tags=["Setup"])

SETUP_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Digital Invoicing Software — MCP Setup & Onboarding</title>
  <style>
    :root {
      --primary: #1a3a8f;
      --primary-hover: #132c70;
      --bg: #f8fafc;
      --card-bg: #ffffff;
      --text: #0f172a;
      --text-muted: #64748b;
      --border: #e2e8f0;
      --input-border: #cbd5e1;
      --code-bg: #0f172a;
      --code-text: #f8fafc;
      --error-bg: #fef2f2;
      --error-border: #fca5a5;
      --error-text: #991b1b;
      --success: #16a34a;
    }

    * {
      box-sizing: border-box;
      margin: 0;
      padding: 0;
    }

    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      background-color: var(--bg);
      color: var(--text);
      line-height: 1.5;
      display: flex;
      justify-content: center;
      align-items: center;
      min-height: 100vh;
      padding: 24px 16px;
    }

    .container {
      width: 100%;
      max-width: 740px;
      background: var(--card-bg);
      border: 1px solid var(--border);
      border-radius: 12px;
      box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03);
      padding: 36px 32px;
    }

    .header {
      text-align: center;
      margin-bottom: 28px;
    }

    .logo {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      width: 48px;
      height: 48px;
      background-color: rgba(26, 58, 143, 0.08);
      color: var(--primary);
      border-radius: 10px;
      margin-bottom: 12px;
      font-weight: 700;
      font-size: 20px;
    }

    h1 {
      font-size: 22px;
      font-weight: 700;
      color: var(--primary);
      margin-bottom: 6px;
    }

    p.subtitle {
      font-size: 14px;
      color: var(--text-muted);
    }

    .error-alert {
      display: none;
      background-color: var(--error-bg);
      border: 1px solid var(--error-border);
      color: var(--error-text);
      padding: 12px 16px;
      border-radius: 8px;
      font-size: 14px;
      margin-bottom: 20px;
      word-break: break-word;
    }

    .form-group {
      margin-bottom: 20px;
    }

    label {
      display: block;
      font-size: 14px;
      font-weight: 600;
      margin-bottom: 6px;
      color: var(--text);
    }

    input[type="text"],
    input[type="email"],
    input[type="password"] {
      width: 100%;
      padding: 10px 14px;
      font-size: 14px;
      border: 1px solid var(--input-border);
      border-radius: 6px;
      background-color: #fff;
      transition: border-color 0.15s ease, box-shadow 0.15s ease;
    }

    input:focus {
      outline: none;
      border-color: var(--primary);
      box-shadow: 0 0 0 3px rgba(26, 58, 143, 0.15);
    }

    .btn {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      width: 100%;
      padding: 12px 16px;
      font-size: 15px;
      font-weight: 600;
      color: #ffffff;
      background-color: var(--primary);
      border: none;
      border-radius: 6px;
      cursor: pointer;
      transition: background-color 0.15s ease;
    }

    .btn:hover {
      background-color: var(--primary-hover);
    }

    .btn:disabled {
      opacity: 0.7;
      cursor: not-allowed;
    }

    .spinner {
      display: inline-block;
      width: 16px;
      height: 16px;
      border: 2px solid rgba(255, 255, 255, 0.3);
      border-radius: 50%;
      border-top-color: #ffffff;
      animation: spin 0.8s linear infinite;
      margin-right: 8px;
    }

    @keyframes spin {
      to { transform: rotate(360deg); }
    }

    /* Step 2 Styles */
    .step-2 {
      display: none;
    }

    .info-card {
      background-color: #f1f5f9;
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 16px;
      margin-bottom: 24px;
    }

    .info-row {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 12px;
      font-size: 14px;
      gap: 12px;
    }

    .info-row:last-child {
      margin-bottom: 0;
    }

    .info-label {
      font-weight: 600;
      color: var(--text-muted);
      flex-shrink: 0;
    }

    .info-val-wrap {
      display: flex;
      align-items: center;
      gap: 8px;
      overflow: hidden;
      justify-content: flex-end;
      flex: 1;
    }

    .info-value {
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
      font-size: 12.5px;
      background: #ffffff;
      border: 1px solid var(--border);
      padding: 4px 8px;
      border-radius: 4px;
      word-break: break-all;
    }

    .guide-header {
      margin-bottom: 16px;
    }

    .guide-title {
      font-size: 17px;
      font-weight: 700;
      color: var(--text);
      margin-bottom: 4px;
    }

    .guide-subtitle {
      font-size: 13.5px;
      color: var(--text-muted);
    }

    /* Tabs Navigation */
    .tabs-nav {
      display: flex;
      gap: 4px;
      border-bottom: 1px solid var(--border);
      margin-bottom: 20px;
      overflow-x: auto;
      padding-bottom: 1px;
    }

    .tab-btn {
      padding: 9px 15px;
      font-size: 14px;
      font-weight: 600;
      color: var(--text-muted);
      background: transparent;
      border: none;
      border-bottom: 2px solid transparent;
      cursor: pointer;
      white-space: nowrap;
      transition: all 0.15s ease;
    }

    .tab-btn:hover {
      color: var(--primary);
    }

    .tab-btn.active {
      color: var(--primary);
      border-bottom-color: var(--primary);
    }

    /* Tab Panes */
    .tab-pane {
      display: none;
    }

    .tab-pane.active {
      display: block;
      animation: tabFadeIn 0.15s ease;
    }

    @keyframes tabFadeIn {
      from { opacity: 0; transform: translateY(2px); }
      to { opacity: 1; transform: translateY(0); }
    }

    /* Auto-connect button box */
    .auto-connect-box {
      background: #f8fafc;
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 16px;
      margin-bottom: 20px;
      text-align: center;
    }

    .btn-auto {
      background: #1e3a8a;
      color: #ffffff;
      font-size: 15px;
      font-weight: 600;
      text-decoration: none;
      padding: 12px 20px;
      border-radius: 6px;
      display: block;
      width: 100%;
      box-sizing: border-box;
      transition: background-color 0.15s ease;
    }

    .btn-auto:hover {
      background: #172554;
    }

    .auto-note {
      font-size: 13px;
      color: var(--text-muted);
      margin-top: 8px;
      line-height: 1.4;
    }

    /* Section divider */
    .divider {
      display: flex;
      align-items: center;
      text-align: center;
      margin: 20px 0 16px 0;
      color: var(--text-muted);
      font-size: 12px;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }

    .divider::before,
    .divider::after {
      content: '';
      flex: 1;
      border-bottom: 1px solid var(--border);
    }

    .divider span {
      padding: 0 10px;
    }

    /* Step List */
    .step-list {
      display: flex;
      flex-direction: column;
      gap: 14px;
    }

    .step-row {
      display: flex;
      align-items: flex-start;
      gap: 12px;
      font-size: 14px;
      line-height: 1.5;
    }

    .step-num {
      flex-shrink: 0;
      width: 24px;
      height: 24px;
      background: rgba(26, 58, 143, 0.1);
      color: var(--primary);
      font-size: 12px;
      font-weight: 700;
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      margin-top: 1px;
    }

    .step-body {
      flex: 1;
      color: var(--text);
    }

    /* Copy boxes */
    .copy-box-inline {
      display: flex;
      align-items: center;
      justify-content: space-between;
      background: #f1f5f9;
      border: 1px solid var(--border);
      border-radius: 6px;
      padding: 6px 10px;
      margin-top: 6px;
      gap: 10px;
    }

    .copy-box-inline code {
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
      font-size: 12.5px;
      color: #0f172a;
      word-break: break-all;
      user-select: all;
    }

    .code-box {
      margin-top: 8px;
      background-color: var(--code-bg);
      border-radius: 8px;
      overflow: hidden;
    }

    .code-box-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 8px 12px;
      background: rgba(255, 255, 255, 0.05);
      border-bottom: 1px solid rgba(255, 255, 255, 0.1);
    }

    .code-box-label {
      font-size: 11px;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      color: #94a3b8;
    }

    .code-box pre {
      background: transparent;
      padding: 12px 14px;
      margin: 0;
      border-radius: 0;
      color: var(--code-text);
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
      font-size: 12px;
      line-height: 1.45;
      overflow-x: auto;
      white-space: pre-wrap;
      word-break: break-all;
    }

    .copy-btn-sm {
      flex-shrink: 0;
      padding: 4px 10px;
      font-size: 12px;
      font-weight: 600;
      color: var(--primary);
      background-color: #ffffff;
      border: 1px solid var(--input-border);
      border-radius: 4px;
      cursor: pointer;
      transition: all 0.15s ease;
    }

    .copy-btn-sm:hover {
      background-color: #f1f5f9;
      border-color: var(--primary);
    }

    .copy-btn-sm.copied {
      background-color: var(--success);
      color: #ffffff;
      border-color: var(--success);
    }

    .openai-box {
      background: #f8fafc;
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 20px;
      font-size: 14px;
      line-height: 1.6;
      color: var(--text);
    }
  </style>
</head>
<body>

  <div class="container">
    <div class="header">
      <div class="logo">FBR</div>
      <h1>Digital Invoicing Software MCP Setup</h1>
      <p class="subtitle">Connect your account to generate MCP credentials for Claude, Gemini, and GPT</p>
    </div>

    <div id="error-box" class="error-alert"></div>

    <!-- STEP 1: FORM -->
    <div id="setup-step-1">
      <form id="connect-form">
        <div class="form-group">
          <label for="business_name">Business Name</label>
          <input type="text" id="business_name" required placeholder="e.g. Your Business Name">
        </div>

        <div class="form-group">
          <label for="email">Digital Invoicing Software Email</label>
          <input type="email" id="email" required placeholder="user@example.com">
        </div>

        <div class="form-group">
          <label for="password">Digital Invoicing Software Password</label>
          <input type="password" id="password" required placeholder="••••••••••••">
        </div>

        <button type="submit" id="submit-btn" class="btn">Connect Account & Generate MCP Key</button>
      </form>
    </div>

    <!-- STEP 2: RESULT SCREEN -->
    <div id="setup-step-2" class="step-2">
      <!-- Credentials Card -->
      <div class="info-card">
        <div class="info-row">
          <span class="info-label">MCP Server URL</span>
          <div class="info-val-wrap">
            <span id="mcp-url-display" class="info-value"></span>
            <button type="button" class="copy-btn-sm" onclick="copyTextFromElement('mcp-url-display', this)">Copy</button>
          </div>
        </div>
        <div class="info-row">
          <span class="info-label">MCP API Key</span>
          <div class="info-val-wrap">
            <span id="mcp-key-display" class="info-value"></span>
            <button type="button" class="copy-btn-sm" onclick="copyTextFromElement('mcp-key-display', this)">Copy</button>
          </div>
        </div>
      </div>

      <!-- Tabbed Connection Guide -->
      <div class="guide-header">
        <h2 class="guide-title">Connect to Your AI Assistant</h2>
        <p class="guide-subtitle">Select your platform below for simple, step-by-step setup instructions:</p>
      </div>

      <div class="tabs-nav" role="tablist">
        <button type="button" class="tab-btn active" onclick="switchTab('claude', this)" role="tab" aria-selected="true">Claude</button>
        <button type="button" class="tab-btn" onclick="switchTab('cursor', this)" role="tab" aria-selected="false">Cursor</button>
        <button type="button" class="tab-btn" onclick="switchTab('windsurf', this)" role="tab" aria-selected="false">Windsurf</button>
        <button type="button" class="tab-btn" onclick="switchTab('antigravity', this)" role="tab" aria-selected="false">Antigravity</button>
        <button type="button" class="tab-btn" onclick="switchTab('openai', this)" role="tab" aria-selected="false">OpenAI</button>
      </div>

      <!-- TAB 1: CLAUDE -->
      <div id="tab-claude" class="tab-pane active" role="tabpanel">
        <div class="auto-connect-box">
          <a id="claude-auto-btn" href="#" target="_blank" rel="noopener noreferrer" class="btn btn-auto">Click here to connect automatically</a>
          <p class="auto-note">This fills in the first two fields for you — you'll still need to complete a couple of quick steps after it opens (shown below).</p>
        </div>

        <div class="divider">
          <span>Or follow these manual steps</span>
        </div>

        <div class="step-list">
          <div class="step-row">
            <div class="step-num">1</div>
            <div class="step-body">Open Claude (web at claude.ai, or the Claude Desktop app) and go to Settings.</div>
          </div>
          <div class="step-row">
            <div class="step-num">2</div>
            <div class="step-body">Click "Connectors" in the settings sidebar.</div>
          </div>
          <div class="step-row">
            <div class="step-num">3</div>
            <div class="step-body">Click "Add custom connector".</div>
          </div>
          <div class="step-row">
            <div class="step-num">4</div>
            <div class="step-body">
              Name field: type a name:
              <div class="copy-box-inline">
                <code id="claude-name-val"></code>
                <button type="button" class="copy-btn-sm" onclick="copyTextFromElement('claude-name-val', this)">Copy</button>
              </div>
            </div>
          </div>
          <div class="step-row">
            <div class="step-num">5</div>
            <div class="step-body">
              Remote MCP server URL field: paste the MCP Server URL:
              <div class="copy-box-inline">
                <code id="claude-url-val"></code>
                <button type="button" class="copy-btn-sm" onclick="copyTextFromElement('claude-url-val', this)">Copy</button>
              </div>
            </div>
          </div>
          <div class="step-row">
            <div class="step-num">6</div>
            <div class="step-body">Click "Continue".</div>
          </div>
          <div class="step-row">
            <div class="step-num">7</div>
            <div class="step-body">It may show "Couldn't determine the server settings" — this is expected, not an error. Click "Next".</div>
          </div>
          <div class="step-row">
            <div class="step-num">8</div>
            <div class="step-body">Under "Authentication", select "None".</div>
          </div>
          <div class="step-row">
            <div class="step-num">9</div>
            <div class="step-body">Scroll to "Additional request headers" / "Request headers", click "Add header".</div>
          </div>
          <div class="step-row">
            <div class="step-num">10</div>
            <div class="step-body">In the header name dropdown, search for and select "x-api-key" (must pick from the list, typing a custom name won't work).</div>
          </div>
          <div class="step-row">
            <div class="step-num">11</div>
            <div class="step-body">
              In the Value field, paste the MCP API Key:
              <div class="copy-box-inline">
                <code id="claude-key-val"></code>
                <button type="button" class="copy-btn-sm" onclick="copyTextFromElement('claude-key-val', this)">Copy</button>
              </div>
            </div>
          </div>
          <div class="step-row">
            <div class="step-num">12</div>
            <div class="step-body">Click "Add".</div>
          </div>
          <div class="step-row">
            <div class="step-num">13</div>
            <div class="step-body">If it briefly shows "Connection issue": start a brand new chat and check again — it usually shows "Connected" once a fresh chat is opened. If not, click the connector and press "Reconnect".</div>
          </div>
          <div class="step-row">
            <div class="step-num">14</div>
            <div class="step-body">Start a new chat, describe an invoice (or attach a photo of a receipt), and say "fill this invoice".</div>
          </div>
        </div>
      </div>

      <!-- TAB 2: CURSOR -->
      <div id="tab-cursor" class="tab-pane" role="tabpanel">
        <div class="auto-connect-box">
          <a id="cursor-auto-btn" href="#" class="btn btn-auto">Click here to connect automatically</a>
          <p class="auto-note">This only works if you already have Cursor installed</p>
        </div>

        <div class="divider">
          <span>Or follow these manual steps</span>
        </div>

        <div class="step-list">
          <div class="step-row">
            <div class="step-num">1</div>
            <div class="step-body">Open Cursor, then open Cursor Settings (gear icon, or Cmd+Shift+J / Ctrl+Shift+J).</div>
          </div>
          <div class="step-row">
            <div class="step-num">2</div>
            <div class="step-body">Click "Tools &amp; MCP" in the sidebar.</div>
          </div>
          <div class="step-row">
            <div class="step-num">3</div>
            <div class="step-body">Click "+ New MCP Server" (or "Add new MCP server") — this opens a file called mcp.json.</div>
          </div>
          <div class="step-row">
            <div class="step-num">4</div>
            <div class="step-body">
              Paste this block:
              <div class="code-box">
                <div class="code-box-header">
                  <span class="code-box-label">Setup code</span>
                  <button type="button" class="copy-btn-sm" onclick="copySnippet('cursor-code', this)">Copy</button>
                </div>
                <pre id="cursor-code"></pre>
              </div>
            </div>
          </div>
          <div class="step-row">
            <div class="step-num">5</div>
            <div class="step-body">Save the file.</div>
          </div>
          <div class="step-row">
            <div class="step-num">6</div>
            <div class="step-body">Go back to "Tools &amp; MCP" — a green dot next to the server name means it connected.</div>
          </div>
          <div class="step-row">
            <div class="step-num">7</div>
            <div class="step-body">Open the Agent/Composer chat, describe an invoice, and ask Cursor to fill it in.</div>
          </div>
        </div>
      </div>

      <!-- TAB 3: WINDSURF -->
      <div id="tab-windsurf" class="tab-pane" role="tabpanel">
        <div class="step-list">
          <div class="step-row">
            <div class="step-num">1</div>
            <div class="step-body">Open Windsurf, click the Cascade panel icon (usually top-right).</div>
          </div>
          <div class="step-row">
            <div class="step-num">2</div>
            <div class="step-body">Click the hammer/MCP servers icon, then click "Configure" (or "MCPs setting icon").</div>
          </div>
          <div class="step-row">
            <div class="step-num">3</div>
            <div class="step-body">Click "View raw config" — this opens a file called mcp_config.json.</div>
          </div>
          <div class="step-row">
            <div class="step-num">4</div>
            <div class="step-body">
              Paste this block:
              <div class="code-box">
                <div class="code-box-header">
                  <span class="code-box-label">Setup code</span>
                  <button type="button" class="copy-btn-sm" onclick="copySnippet('windsurf-code', this)">Copy</button>
                </div>
                <pre id="windsurf-code"></pre>
              </div>
            </div>
          </div>
          <div class="step-row">
            <div class="step-num">5</div>
            <div class="step-body">Save the file, then click "Refresh" in the MCP panel to load it.</div>
          </div>
          <div class="step-row">
            <div class="step-num">6</div>
            <div class="step-body">In the Cascade chat, describe an invoice and ask it to fill it in.</div>
          </div>
        </div>
      </div>

      <!-- TAB 4: ANTIGRAVITY -->
      <div id="tab-antigravity" class="tab-pane" role="tabpanel">
        <div class="step-list">
          <div class="step-row">
            <div class="step-num">1</div>
            <div class="step-body">Open Antigravity.</div>
          </div>
          <div class="step-row">
            <div class="step-num">2</div>
            <div class="step-body">Click the "..." (Additional Options) menu and select "MCP Servers" (or open the setup file at ~/.gemini/config/mcp_config.json).</div>
          </div>
          <div class="step-row">
            <div class="step-num">3</div>
            <div class="step-body">Click "View raw config" (or open mcp_config.json).</div>
          </div>
          <div class="step-row">
            <div class="step-num">4</div>
            <div class="step-body">
              Paste this block:
              <div class="code-box">
                <div class="code-box-header">
                  <span class="code-box-label">Setup code</span>
                  <button type="button" class="copy-btn-sm" onclick="copySnippet('antigravity-code', this)">Copy</button>
                </div>
                <pre id="antigravity-code"></pre>
              </div>
            </div>
          </div>
          <div class="step-row">
            <div class="step-num">5</div>
            <div class="step-body">Save the file.</div>
          </div>
          <div class="step-row">
            <div class="step-num">6</div>
            <div class="step-body">In the chat panel, describe an invoice (or attach a photo of a receipt) and ask it to fill it in.</div>
          </div>
        </div>
      </div>

      <!-- TAB 5: OPENAI -->
      <div id="tab-openai" class="tab-pane" role="tabpanel">
        <div class="openai-box">
          <p>OpenAI supports connecting to this server through their REST API (the Responses API). This is for developers integrating this into their own OpenAI-based application or script. [Contact us / see developer docs] for a ready-to-use code example.</p>
        </div>
      </div>
    </div>
  </div>

  <script>
    function makeServerSlug(str) {
      const clean = (str || '')
        .toString()
        .toLowerCase()
        .trim()
        .replace(/[^a-z0-9]+/g, '-')
        .replace(/^-+|-+$/g, '');
      return (clean || 'digital') + '-invoicing';
    }

    function toBase64(str) {
      try {
        return btoa(unescape(encodeURIComponent(str)));
      } catch (e) {
        return btoa(str);
      }
    }

    function switchTab(tabId, btnElement) {
      const allBtns = document.querySelectorAll('.tab-btn');
      allBtns.forEach(btn => {
        btn.classList.remove('active');
        btn.setAttribute('aria-selected', 'false');
      });

      const allPanes = document.querySelectorAll('.tab-pane');
      allPanes.forEach(pane => {
        pane.classList.remove('active');
      });

      btnElement.classList.add('active');
      btnElement.setAttribute('aria-selected', 'true');

      const targetPane = document.getElementById('tab-' + tabId);
      if (targetPane) {
        targetPane.classList.add('active');
      }
    }

    document.getElementById('connect-form').addEventListener('submit', async function(e) {
      e.preventDefault();
      const errBox = document.getElementById('error-box');
      const submitBtn = document.getElementById('submit-btn');
      const name = document.getElementById('business_name').value.trim();
      const email = document.getElementById('email').value.trim();
      const passInput = document.getElementById('password');
      const password = passInput.value;

      // Immediately clear password from input element
      passInput.value = '';

      errBox.style.display = 'none';
      errBox.textContent = '';
      submitBtn.disabled = true;
      submitBtn.innerHTML = '<span class="spinner"></span> Connecting Account...';

      try {
        const res = await fetch('/api/v1/connect_account', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ name, email, password })
        });

        const data = await res.json();

        if (!res.ok) {
          const errMsg = data.detail || data.message || data.error || 'Failed to connect account.';
          throw new Error(errMsg);
        }

        const apiKey = data.mcp_api_key;
        const origin = window.location.origin;
        const mcpUrl = origin + '/mcp';
        const tenantName = name || 'Digital Invoicing';
        const serverSlug = makeServerSlug(tenantName);

        // 1. Credentials summary displays
        document.getElementById('mcp-url-display').textContent = mcpUrl;
        document.getElementById('mcp-key-display').textContent = apiKey;

        // 2. Tab 1: Claude
        const claudeDeeplink = 'https://claude.ai/customize/connectors?modal=add-custom-connector&connectorName=' +
          encodeURIComponent(tenantName) +
          '&connectorUrl=' + encodeURIComponent(mcpUrl);
        document.getElementById('claude-auto-btn').href = claudeDeeplink;
        document.getElementById('claude-name-val').textContent = tenantName;
        document.getElementById('claude-url-val').textContent = mcpUrl;
        document.getElementById('claude-key-val').textContent = apiKey;

        // 3. Tab 2: Cursor
        const cursorConfigObj = {
          url: mcpUrl,
          headers: {
            "x-api-key": apiKey
          }
        };
        const cursorConfigJson = JSON.stringify(cursorConfigObj);
        const cursorConfigB64 = toBase64(cursorConfigJson);
        const cursorDeeplink = 'cursor://anysphere.cursor-deeplink/mcp/install?name=' +
          encodeURIComponent(tenantName) +
          '&config=' + encodeURIComponent(cursorConfigB64);
        document.getElementById('cursor-auto-btn').href = cursorDeeplink;

        const cursorServerConfig = {
          "mcpServers": {
            [serverSlug]: {
              "url": mcpUrl,
              "headers": {
                "x-api-key": apiKey
              }
            }
          }
        };
        document.getElementById('cursor-code').textContent = JSON.stringify(cursorServerConfig, null, 2);

        // 4. Tab 3: Windsurf
        const windsurfServerConfig = {
          "mcpServers": {
            [serverSlug]: {
              "url": mcpUrl,
              "headers": {
                "x-api-key": apiKey
              }
            }
          }
        };
        document.getElementById('windsurf-code').textContent = JSON.stringify(windsurfServerConfig, null, 2);

        // 5. Tab 4: Antigravity (serverUrl and X-MCP-API-Key as verified in mcp_config.json)
        const antigravityServerConfig = {
          "mcpServers": {
            [serverSlug]: {
              "serverUrl": mcpUrl,
              "headers": {
                "X-MCP-API-Key": apiKey
              }
            }
          }
        };
        document.getElementById('antigravity-code').textContent = JSON.stringify(antigravityServerConfig, null, 2);

        // Switch to Step 2
        document.getElementById('setup-step-1').style.display = 'none';
        document.getElementById('setup-step-2').style.display = 'block';

      } catch (err) {
        errBox.textContent = err.message || 'An error occurred during account connection.';
        errBox.style.display = 'block';
      } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = 'Connect Account & Generate MCP Key';
      }
    });

    function copyText(text, btnElement) {
      function handleSuccess() {
        const originalText = btnElement.textContent;
        btnElement.textContent = 'Copied!';
        btnElement.classList.add('copied');
        setTimeout(() => {
          btnElement.textContent = originalText;
          btnElement.classList.remove('copied');
        }, 2000);
      }

      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(text).then(handleSuccess).catch(() => {
          fallbackCopy(text, handleSuccess);
        });
      } else {
        fallbackCopy(text, handleSuccess);
      }
    }

    function fallbackCopy(text, callback) {
      const textarea = document.createElement('textarea');
      textarea.value = text;
      textarea.style.position = 'fixed';
      textarea.style.opacity = '0';
      document.body.appendChild(textarea);
      textarea.select();
      try {
        document.execCommand('copy');
        callback();
      } catch (e) {
        console.error('Fallback copy failed', e);
      }
      document.body.removeChild(textarea);
    }

    function copyTextFromElement(elementId, btnElement) {
      const el = document.getElementById(elementId);
      if (el) {
        copyText(el.textContent, btnElement);
      }
    }

    function copySnippet(elementId, btnElement) {
      copyTextFromElement(elementId, btnElement);
    }
  </script>
</body>
</html>
"""


@setup_router.get("/setup", response_class=HTMLResponse)
async def setup_page():
    return HTMLResponse(content=SETUP_HTML_TEMPLATE)
