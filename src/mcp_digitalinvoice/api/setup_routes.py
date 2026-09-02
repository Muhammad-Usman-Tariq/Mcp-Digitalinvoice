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
      max-width: 680px;
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
      margin-bottom: 10px;
      font-size: 14px;
    }

    .info-row:last-child {
      margin-bottom: 0;
    }

    .info-label {
      font-weight: 600;
      color: var(--text-muted);
    }

    .info-value {
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
      font-size: 13px;
      background: #ffffff;
      border: 1px solid var(--border);
      padding: 4px 8px;
      border-radius: 4px;
      word-break: break-all;
    }

    .snippet-section {
      margin-bottom: 24px;
    }

    .snippet-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 8px;
    }

    .snippet-title {
      font-size: 14px;
      font-weight: 700;
      color: var(--text);
    }

    .copy-btn {
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

    .copy-btn:hover {
      background-color: #f1f5f9;
      border-color: var(--primary);
    }

    .copy-btn.copied {
      background-color: var(--success);
      color: #ffffff;
      border-color: var(--success);
    }

    pre {
      background-color: var(--code-bg);
      color: var(--code-text);
      padding: 14px 16px;
      border-radius: 8px;
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
      font-size: 12.5px;
      line-height: 1.45;
      overflow-x: auto;
      white-space: pre-wrap;
      word-break: break-all;
    }

    .snippet-note {
      font-size: 12px;
      color: var(--text-muted);
      margin-top: 6px;
      font-style: italic;
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
      <div class="info-card">
        <div class="info-row">
          <span class="info-label">MCP Server URL</span>
          <span id="mcp-url-display" class="info-value"></span>
        </div>
        <div class="info-row">
          <span class="info-label">MCP API Key</span>
          <span id="mcp-key-display" class="info-value"></span>
        </div>
      </div>

      <!-- a) Claude -->
      <div class="snippet-section">
        <div class="snippet-header">
          <span class="snippet-title">a) Claude (Claude Desktop / claude.ai)</span>
          <button class="copy-btn" onclick="copySnippet('claude-code', this)">Copy</button>
        </div>
        <pre id="claude-code"></pre>
      </div>

      <!-- b) Gemini / Antigravity -->
      <div class="snippet-section">
        <div class="snippet-header">
          <span class="snippet-title">b) Gemini / Antigravity (mcp_config.json)</span>
          <button class="copy-btn" onclick="copySnippet('gemini-code', this)">Copy</button>
        </div>
        <pre id="gemini-code"></pre>
      </div>

      <!-- c) GPT -->
      <div class="snippet-section">
        <div class="snippet-header">
          <span class="snippet-title">c) GPT (via OpenAI Responses API)</span>
          <button class="copy-btn" onclick="copySnippet('gpt-code', this)">Copy</button>
        </div>
        <pre id="gpt-code"></pre>
        <p class="snippet-note">Note: ChatGPT's web application does not support static API keys for custom connectors (OAuth only). This curl snippet is for developers calling the OpenAI API directly.</p>
      </div>
    </div>
  </div>

  <script>
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

        document.getElementById('mcp-url-display').textContent = mcpUrl;
        document.getElementById('mcp-key-display').textContent = apiKey;

        const claudeJson = {
          "mcpServers": {
            "digital_invoicing": {
              "url": mcpUrl,
              "headers": { "X-MCP-API-Key": apiKey }
            }
          }
        };
        document.getElementById('claude-code').textContent = JSON.stringify(claudeJson, null, 2);

        const geminiJson = {
          "mcpServers": {
            "digital_invoicing": {
              "serverUrl": mcpUrl,
              "headers": { "X-MCP-API-Key": apiKey }
            }
          }
        };
        document.getElementById('gemini-code').textContent = JSON.stringify(geminiJson, null, 2);

        const gptCurl = `curl https://api.openai.com/v1/responses \\
  -H "Content-Type: application/json" \\
  -H "Authorization: Bearer $OPENAI_API_KEY" \\
  -d '{
    "model": "gpt-5.6",
    "input": "your prompt here",
    "tools": [{
      "type": "mcp",
      "server_label": "digital_invoicing",
      "server_url": "${mcpUrl}",
      "authorization": "${apiKey}",
      "require_approval": "never"
    }]
  }'`;
        document.getElementById('gpt-code').textContent = gptCurl;

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

    function copySnippet(elementId, btnElement) {
      const text = document.getElementById(elementId).textContent;
      navigator.clipboard.writeText(text).then(() => {
        const originalText = btnElement.textContent;
        btnElement.textContent = 'Copied!';
        btnElement.classList.add('copied');
        setTimeout(() => {
          btnElement.textContent = originalText;
          btnElement.classList.remove('copied');
        }, 2000);
      }).catch(() => {
        const textarea = document.createElement('textarea');
        textarea.value = text;
        document.body.appendChild(textarea);
        textarea.select();
        document.execCommand('copy');
        document.body.removeChild(textarea);
        const originalText = btnElement.textContent;
        btnElement.textContent = 'Copied!';
        btnElement.classList.add('copied');
        setTimeout(() => {
          btnElement.textContent = originalText;
          btnElement.classList.remove('copied');
        }, 2000);
      });
    }
  </script>
</body>
</html>
"""


@setup_router.get("/setup", response_class=HTMLResponse)
async def setup_page():
    return HTMLResponse(content=SETUP_HTML_TEMPLATE)
