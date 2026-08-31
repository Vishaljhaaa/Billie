from __future__ import annotations


def render_home_page() -> str:
    return """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Multimodal Knowledge Assistant</title>
  <style>
    :root {
      --bg: #f4ede3;
      --panel: rgba(255, 250, 243, 0.92);
      --ink: #1e2933;
      --muted: #5b6875;
      --accent: #b85c38;
      --line: #ddcebb;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: Georgia, "Times New Roman", serif;
      color: var(--ink);
      background:
        radial-gradient(circle at top left, rgba(184, 92, 56, 0.18), transparent 30%),
        radial-gradient(circle at bottom right, rgba(59, 107, 122, 0.16), transparent 26%),
        linear-gradient(180deg, #f8f2ea, #efe2d2);
    }
    main {
      max-width: 1040px;
      margin: 0 auto;
      padding: 40px 20px 56px;
    }
    .hero, .panel {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 22px;
      box-shadow: 0 18px 40px rgba(45, 33, 20, 0.08);
    }
    .hero {
      padding: 28px;
      margin-bottom: 18px;
    }
    .eyebrow {
      text-transform: uppercase;
      letter-spacing: 0.12em;
      font-size: 12px;
      color: var(--accent);
      font-weight: 700;
    }
    h1 {
      margin: 10px 0 12px;
      font-size: clamp(2rem, 4vw, 3.5rem);
      line-height: 1.05;
    }
    p {
      color: var(--muted);
      font-size: 1.05rem;
      line-height: 1.7;
    }
    .actions {
      display: flex;
      gap: 12px;
      flex-wrap: wrap;
      margin-top: 22px;
    }
    .button, .button-secondary {
      display: inline-block;
      padding: 12px 18px;
      border-radius: 999px;
      text-decoration: none;
      font-weight: 700;
    }
    .button {
      background: var(--accent);
      color: #fffaf6;
    }
    .button-secondary {
      border: 1px solid var(--line);
      color: var(--ink);
      background: #fffaf4;
    }
    .grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
      gap: 18px;
    }
    .panel {
      padding: 20px;
    }
    h2, h3 {
      margin-top: 0;
    }
    ul {
      padding-left: 18px;
      color: var(--muted);
      line-height: 1.7;
    }
    code {
      background: #f3e6d7;
      padding: 2px 6px;
      border-radius: 6px;
    }
  </style>
</head>
<body>
  <main>
    <section class="hero">
      <div class="eyebrow">Training Project Extension</div>
      <h1>Multimodal Knowledge Assistant</h1>
      <p>
        This service ingests trusted sources, detects updates, refreshes its retrieval index,
        and serves evidence-based answers using retrieved text, visual inputs, and conversational memory.
        It also includes retrieval and multimodal benchmark results with saved visual outputs for reproducible submission.
      </p>
      <div class="actions">
        <a class="button" href="/admin">Open Admin Dashboard</a>
        <a class="button-secondary" href="/health">Health Check</a>
        <a class="button-secondary" href="/metrics">Metrics</a>
      </div>
    </section>
    <section class="grid">
      <div class="panel">
        <h3>API Endpoints</h3>
        <ul>
          <li><code>GET /health</code> for service status</li>
          <li><code>POST /chat</code> for multimodal question answering</li>
          <li><code>POST /sync</code> for manual knowledge-base refresh</li>
          <li><code>GET /admin/status</code> for indexed-source visibility</li>
        </ul>
      </div>
      <div class="panel">
        <h3>Reasoning Features</h3>
        <ul>
          <li>Scheduled source refresh with fingerprint-based updates</li>
          <li>Session memory across multiple chat turns</li>
          <li>Image evidence extraction with ambiguity detection</li>
          <li>Validation checks before final response delivery</li>
        </ul>
      </div>
      <div class="panel">
        <h3>Experiment Assets</h3>
        <ul>
          <li>Benchmark dataset for retrieval evaluation</li>
          <li>Text-only vs multimodal reasoning comparison</li>
          <li>Saved metrics in <code>artifacts/benchmark_results.json</code></li>
          <li>Generated plots for submission-ready visuals</li>
        </ul>
      </div>
    </section>
  </main>
</body>
</html>
"""


def render_admin_page() -> str:
    return """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Knowledge Base Admin</title>
  <style>
    :root {
      --bg: #f5efe6;
      --panel: #fffaf4;
      --ink: #1f2933;
      --accent: #b85c38;
      --line: #dccfbd;
    }
    body {
      margin: 0;
      font-family: Georgia, "Times New Roman", serif;
      background:
        radial-gradient(circle at top right, rgba(184, 92, 56, 0.16), transparent 28%),
        linear-gradient(180deg, #f7f0e8, #efe3d3);
      color: var(--ink);
    }
    main {
      max-width: 920px;
      margin: 0 auto;
      padding: 32px 20px 48px;
    }
    .panel {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 18px;
      padding: 20px;
      box-shadow: 0 14px 32px rgba(48, 36, 24, 0.08);
      margin-bottom: 18px;
    }
    h1, h2 { margin-top: 0; }
    button {
      border: none;
      border-radius: 999px;
      padding: 12px 18px;
      background: var(--accent);
      color: white;
      font-weight: 700;
      cursor: pointer;
    }
    input {
      width: 100%;
      padding: 12px;
      border-radius: 10px;
      border: 1px solid var(--line);
      margin-bottom: 12px;
      box-sizing: border-box;
    }
    pre {
      white-space: pre-wrap;
      word-break: break-word;
      background: #f2e8db;
      padding: 14px;
      border-radius: 12px;
    }
  </style>
</head>
<body>
  <main>
    <div class="panel">
      <h1>Knowledge Base Admin</h1>
      <p>Use your admin key to inspect sync health and trigger an on-demand refresh.</p>
      <input id="adminKey" type="password" placeholder="Paste X-Admin-Key">
      <button onclick="loadStatus()">Load Status</button>
      <button onclick="runSync()">Run Sync</button>
    </div>
    <div class="panel">
      <h2>Status</h2>
      <pre id="status">No status loaded yet.</pre>
    </div>
  </main>
  <script>
    async function loadStatus() {
      const key = document.getElementById("adminKey").value;
      const response = await fetch("/admin/status", {
        headers: { "X-Admin-Key": key }
      });
      const body = await response.text();
      document.getElementById("status").textContent = body;
    }
    async function runSync() {
      const key = document.getElementById("adminKey").value;
      const response = await fetch("/admin/sync", {
        method: "POST",
        headers: { "X-Admin-Key": key }
      });
      const body = await response.text();
      document.getElementById("status").textContent = body;
    }
  </script>
</body>
</html>
"""
