// Zero-Noise SRE Web Cockpit & In-Browser WebGPU Agent Client

let ws = null;
let webllmEngine = null;
let isWebGPULoaded = false;

// DOM Elements
const scenarioSelect = document.getElementById("scenario-select");
const engineSelect = document.getElementById("engine-select");
const btnTrigger = document.getElementById("btn-trigger-incident");
const sloStatus = document.getElementById("slo-status");
const metricP99 = document.getElementById("metric-p99");
const metricError = document.getElementById("metric-error-rate");
const terminalLogs = document.getElementById("terminal-logs");
const pipelinePill = document.getElementById("pipeline-stage-pill");
const prStatusPill = document.getElementById("pr-status-pill");
const prTitle = document.getElementById("pr-title");
const prBranch = document.getElementById("pr-branch");
const rcaView = document.getElementById("rca-view");
const diffView = document.getElementById("diff-view");
const testView = document.getElementById("test-view");
const webgpuProgress = document.getElementById("webgpu-progress-box");
const webgpuBar = document.getElementById("webgpu-bar");
const webgpuPercent = document.getElementById("webgpu-percent");
const webgpuStatus = document.getElementById("webgpu-status");

// Tabs Handling
document.querySelectorAll(".tab-btn").forEach(btn => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
    btn.classList.add("active");
    const targetId = btn.getAttribute("data-tab");
    document.querySelectorAll(".tab-content").forEach(tc => tc.classList.add("hidden"));
    document.getElementById(targetId).classList.remove("hidden");
  });
});

// Setup WebSocket Connection
function connectWebSocket() {
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  ws = new WebSocket(`${protocol}//${window.location.host}/ws`);

  ws.onopen = () => {
    appendLog("[WebSocket Connected] Zero-Noise SRE Daemon stream online.");
  };

  ws.onmessage = async (event) => {
    const msg = JSON.parse(event.data);
    handleServerMessage(msg);
  };

  ws.onclose = () => {
    appendLog("[WebSocket Disconnected] Attempting reconnect in 3s...");
    setTimeout(connectWebSocket, 3000);
  };
}

function appendLog(text) {
  terminalLogs.textContent += `\n${text}`;
  terminalLogs.scrollTop = terminalLogs.scrollHeight;
}

// In-Browser WebGPU Model Initializer using WebLLM
async function initWebGPUModel() {
  try {
    webgpuProgress.classList.remove("hidden");
    webgpuStatus.textContent = "Loading WebGPU...";
    appendLog("[WebGPU] Initializing in-browser Gemma 2B execution engine...");

    // Check if webllm is available on window
    if (window.webllm) {
      const initProgressCallback = (report) => {
        const pct = Math.round(report.progress * 100);
        webgpuBar.style.width = `${pct}%`;
        webgpuPercent.textContent = `${pct}%`;
        appendLog(`[WebGPU Load] ${report.text}`);
      };

      webllmEngine = new window.webllm.MLCEngine();
      webllmEngine.setInitProgressCallback(initProgressCallback);
      // Gemma-2b-it quantized for low-end browser hardware
      await webllmEngine.reload("gemma-2-2b-it-q4f16_1-MLC");
      isWebGPULoaded = true;
      webgpuStatus.textContent = "Gemma-2B (Active)";
      webgpuProgress.classList.add("hidden");
      appendLog("[WebGPU Ready] Gemma-2B loaded in browser window with WebGPU shader acceleration.");
    } else {
      appendLog("[WebGPU Info] WebLLM module binding. Local CPU Ollama mode is fully active.");
      webgpuStatus.textContent = "Ollama/Mock Ready";
      webgpuProgress.classList.add("hidden");
    }
  } catch (err) {
    appendLog(`[WebGPU Error] WebGPU not supported on this browser context. Falling back to local backend: ${err.message}`);
    webgpuStatus.textContent = "Local/Mock Ready";
    webgpuProgress.classList.add("hidden");
  }
}

// Handle Server Messages
async function handleServerMessage(msg) {
  if (msg.type === "TELEMETRY_UPDATE") {
    metricP99.textContent = `${msg.data.p99_ms.toFixed(1)} ms`;
    metricError.textContent = `${msg.data.error_rate.toFixed(2)} %`;

    if (msg.data.error_rate > 2.0 || msg.data.p99_ms > 800) {
      sloStatus.textContent = "SLO BREACHED";
      sloStatus.className = "status-pill red";
      document.getElementById("node-payment").classList.add("failing");
    } else {
      sloStatus.textContent = "SLO HEALTHY";
      sloStatus.className = "status-pill green";
      document.getElementById("node-payment").classList.remove("failing");
    }
  } else if (msg.type === "PIPELINE_UPDATE") {
    pipelinePill.textContent = msg.stage;
    pipelinePill.className = "status-pill amber";

    // Update Steps
    if (msg.stage.includes("STAGE_1")) activateStep(1);
    if (msg.stage.includes("STAGE_2")) activateStep(2);
    if (msg.stage.includes("STAGE_3")) activateStep(3);
    if (msg.stage.includes("STAGE_4")) activateStep(4);
    if (msg.stage === "RESOLVED") {
      pipelinePill.textContent = "RESOLVED";
      pipelinePill.className = "status-pill green";
      document.getElementById("node-payment").classList.remove("failing");
      document.getElementById("node-payment").classList.add("fixed");
    }

    if (msg.logs) {
      msg.logs.forEach(l => appendLog(l));
    }
  } else if (msg.type === "PR_DISPATCHED") {
    prStatusPill.textContent = "DRAFT PR OPEN";
    prStatusPill.className = "status-pill green";
    prTitle.textContent = msg.pr_title;
    prBranch.textContent = `Branch: ${msg.branch_name}`;

    rcaView.innerHTML = `<pre class="code-view">${msg.rca_markdown}</pre>`;
    diffView.textContent = msg.diff_text;
    testView.textContent = msg.test_code;
    appendLog(`[PR Issued] Automated Pull Request created: ${msg.pr_url}`);
  } else if (msg.type === "INFERENCE_REQUEST" && engineSelect.value === "browser_webgpu" && webllmEngine) {
    appendLog("[WebGPU] In-browser Gemma is synthesizing patch & RCA reasoning...");
    const reply = await webllmEngine.chat.completions.create({
      messages: [{ role: "user", content: msg.prompt }],
      temperature: 0.1
    });
    const resultText = reply.choices[0].message.content;
    ws.send(JSON.stringify({ type: "INFERENCE_RESPONSE", text: resultText }));
  }
}

function activateStep(stepNum) {
  for (let i = 1; i <= 4; i++) {
    const card = document.getElementById(`step-${i}`);
    if (i < stepNum) {
      card.className = "step-card completed";
    } else if (i === stepNum) {
      card.className = "step-card active";
    } else {
      card.className = "step-card";
    }
  }
}

// Trigger Mock Incident
btnTrigger.addEventListener("click", async () => {
  const scenario = scenarioSelect ? scenarioSelect.value : "razorpay_payment_capture";
  appendLog(`[Action] Simulating incident scenario: '${scenario}'...`);
  try {
    const resp = await fetch("/api/trigger-incident", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        backend: engineSelect.value,
        scenario: scenario
      })
    });
    const data = await resp.json();
    appendLog(`[Incident Ingested] Incident ID: ${data.incident_id}`);
  } catch (err) {
    appendLog(`[Error] Failed to trigger incident: ${err.message}`);
  }
});

// Initialize on Load
window.addEventListener("DOMContentLoaded", () => {
  connectWebSocket();
  engineSelect.addEventListener("change", (e) => {
    if (e.target.value === "browser_webgpu" && !isWebGPULoaded) {
      initWebGPUModel();
    }
  });
});
